#!/bin/bash
# Start DKG SPARQL Server in production mode

cd /home/svagnoni/deliberation-knowledge-graph

# Kill any existing instances
pkill -f "sparql_server_production.py"
sleep 2

# Start server
nohup python3 sparql_server_production.py \
  --kg-file /home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg.ttl \
  --port 8085 \
  > /home/svagnoni/dkg_server.log 2>&1 &

echo "DKG Server started. PID: $!"
echo "Logs: tail -f /home/svagnoni/dkg_server.log"
