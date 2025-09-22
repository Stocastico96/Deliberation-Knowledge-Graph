#!/bin/bash

# Script di avvio per la piattaforma Deliberation Knowledge Graph - PRODUCTION

echo "========================================================"
echo "🏛️  DELIBERATION KNOWLEDGE GRAPH - PRODUCTION PLATFORM"
echo "========================================================"
echo "📊  Dataset: comprehensive_real_kg.ttl (12,295 triple)"
echo "🔍  559 contribution reali, 386 partecipanti, 5 processi"
echo "🌍  Piattaforme: Decide Madrid, EU Parliament"
echo "========================================================"
echo ""

# Controlla se il file knowledge graph esiste
if [ ! -f "comprehensive_real_kg.ttl" ]; then
    echo "❌ Error: File comprehensive_real_kg.ttl non trovato!"
    echo "   Assicurati di essere nella directory corretta del progetto."
    exit 1
fi

# Controlla se i file HTML esistono
if [ ! -f "index.html" ] || [ ! -f "contributions.html" ] || [ ! -f "visualize_kg.html" ]; then
    echo "❌ Error: File HTML mancanti!"
    echo "   Assicurati che index.html, contributions.html e visualize_kg.html esistano."
    exit 1
fi

# Controlla le dipendenze Python
echo "🔍 Controllo dipendenze Python..."
python3 -c "import flask, rdflib" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: Dipendenze Python mancanti!"
    echo "   Installa le dipendenze con: pip install flask rdflib"
    exit 1
fi

echo "✅ Controlli completati"
echo ""

# Determina la porta
PORT=${1:-8085}

echo "🚀 Avvio server production sulla porta $PORT..."
echo ""
echo "🌐 URL principali:"
echo "   Interfaccia principale: http://localhost:$PORT/"
echo "   Esplora Contributions:  http://localhost:$PORT/contributions"
echo "   Visualizzazione KG:     http://localhost:$PORT/visualize"
echo "   API Statistiche:        http://localhost:$PORT/api/stats"
echo "   Export KG:              http://localhost:$PORT/api/export/ttl"
echo "   Endpoint SPARQL:        http://localhost:$PORT/sparql"
echo ""
echo "📝 Per terminare il server: Ctrl+C"
echo "========================================================"
echo ""

# Avvia il server
python3 sparql_server_production.py --kg-file comprehensive_real_kg.ttl --port $PORT --host 0.0.0.0