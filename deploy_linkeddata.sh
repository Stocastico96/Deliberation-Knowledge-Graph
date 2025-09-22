#!/bin/bash

# Deployment script for svagnoni.linkeddata.es
# Deliberation Knowledge Graph Platform

echo "========================================================="
echo "🌐 DEPLOYING TO svagnoni.linkeddata.es"
echo "🏛️  DELIBERATION KNOWLEDGE GRAPH PLATFORM"
echo "========================================================="
echo "📊  Dataset: comprehensive_real_kg.ttl (12,295 triples)"
echo "🔍  559 real contributions, 386 participants, 5 processes"
echo "🌍  Platforms: Decide Madrid, EU Parliament, DeliData"
echo "========================================================="
echo ""

# Configuration
DOMAIN="svagnoni.linkeddata.es"
PORT="8085"
HOST="0.0.0.0"
KG_FILE="comprehensive_real_kg.ttl"

# Check if files exist
echo "🔍 Checking required files..."

if [ ! -f "$KG_FILE" ]; then
    echo "❌ Error: Knowledge graph file $KG_FILE not found!"
    exit 1
fi

if [ ! -f "index.html" ] || [ ! -f "visualize_kg.html" ] || [ ! -f "contributions.html" ]; then
    echo "❌ Error: Required HTML files missing!"
    exit 1
fi

if [ ! -f "sparql_server_production.py" ]; then
    echo "❌ Error: Production server script not found!"
    exit 1
fi

echo "✅ All required files present"

# Check Python dependencies
echo "🔍 Checking Python dependencies..."
python3 -c "import flask, rdflib" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: Python dependencies missing!"
    echo "   Installing dependencies..."
    pip install flask rdflib
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

echo "✅ Dependencies confirmed"

# Stop any existing instances
echo "🔄 Stopping any existing instances..."
pkill -f "sparql_server_production.py" 2>/dev/null || true
sleep 2

# Start the server
echo "🚀 Starting production server..."
echo ""
echo "🌐 Domain: https://$DOMAIN"
echo "📡 Server: http://$HOST:$PORT"
echo ""
echo "🔗 Available endpoints:"
echo "   Main interface:   https://$DOMAIN/"
echo "   Visualization:    https://$DOMAIN/visualize"
echo "   Contributions:    https://$DOMAIN/contributions"
echo "   SPARQL endpoint:  https://$DOMAIN/sparql"
echo "   API stats:        https://$DOMAIN/api/stats"
echo "   API export:       https://$DOMAIN/api/export/ttl"
echo ""
echo "📝 To stop the server: pkill -f sparql_server_production.py"
echo "========================================================="
echo ""

# Start the server in the background with logging
nohup python3 sparql_server_production.py \
    --kg-file "$KG_FILE" \
    --port "$PORT" \
    --host "$HOST" \
    > deployment.log 2>&1 &

SERVER_PID=$!
echo "✅ Server started with PID: $SERVER_PID"
echo "📋 Logs are being written to: deployment.log"

# Wait a moment and check if server started successfully
sleep 3
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Server is running successfully!"
    echo ""
    echo "🌐 Your Deliberation Knowledge Graph is now available at:"
    echo "   https://$DOMAIN/"
    echo ""
    echo "ℹ️  Note: Make sure your web server (Apache/Nginx) is configured"
    echo "   to proxy requests to localhost:$PORT"
else
    echo "❌ Server failed to start. Check deployment.log for details."
    exit 1
fi