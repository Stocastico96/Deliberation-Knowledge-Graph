#!/bin/bash
# Start Citizen Interface Server with updated Knowledge Graph and Embeddings

cd /home/svagnoni/deliberation-knowledge-graph

# Kill any existing instances
pkill -f "simple_server.py"
sleep 2

# Activate venv and start server
source venv/bin/activate
nohup python3 citizen_interface/backend/simple_server.py \
  --kg-path knowledge_graph/deliberation_kg.ttl \
  --embeddings-path knowledge_graph/embeddings.pkl \
  --host 0.0.0.0 \
  --port 5001 \
  > /tmp/citizen_interface.log 2>&1 &

echo "Citizen Interface Server started. PID: $!"
echo "Logs: tail -f /tmp/citizen_interface.log"
echo "Access: http://citizen.svagnoni.linkeddata.es"
