#!/bin/bash
# Start script for DKG Citizen Interface

echo "=== Starting DKG Citizen Interface ==="

# Check if knowledge graph file exists
KG_FILE="../knowledge_graph/deliberation_kg.ttl"

if [ ! -f "$KG_FILE" ]; then
    echo "Error: Knowledge graph file not found at $KG_FILE"
    echo "Please ensure the knowledge graph is available"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the API server
echo "Starting API server on port 5001..."
cd backend
python api_server.py --kg-path "../../$KG_FILE" --host 0.0.0.0 --port 5001

echo "Citizen Interface started!"
echo "Access at: http://localhost:5001"
