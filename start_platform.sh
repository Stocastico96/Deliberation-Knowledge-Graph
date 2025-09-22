#!/bin/bash

# Start the Deliberation Knowledge Graph Platform
echo "🗳️ Starting Deliberation Knowledge Graph Platform..."

# Check if knowledge graph exists
if [ ! -f "quick_test_kg_working.ttl" ]; then
    echo "📊 Creating working knowledge graph..."
    python3 quick_integration_test.py
fi

# Kill any existing server
pkill -f sparql_server.py > /dev/null 2>&1

# Start the server
echo "🚀 Starting web server on http://localhost:8081"
echo "📱 Access the platform at: http://localhost:8081"
echo "🔍 SPARQL endpoint: http://localhost:8081/sparql"
echo "📊 API stats: http://localhost:8081/api/stats"
echo ""
echo "Press Ctrl+C to stop the server"

python3 sparql_server.py --kg-file quick_test_kg_working.ttl --port 8081 --host 0.0.0.0