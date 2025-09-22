#!/bin/bash

# Script per sistemare nginx per servire CSS/JS/immagini tramite Flask

echo "🔧 Sistemazione configurazione nginx per file statici..."

# Backup della configurazione attuale
echo "📋 Backup configurazione attuale..."
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S)

# Crea una configurazione nginx che fa proxy di TUTTO al Flask
cat << 'EOF' | sudo tee /etc/nginx/sites-available/linkeddata.conf
server {
    listen 80;
    listen [::]:80;
    server_name svagnoni.linkeddata.es;

    # Aggiungi header CORS per tutti i file
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    # Proxy TUTTO al server Flask locale
    location / {
        proxy_pass http://127.0.0.1:8085;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Headers per WebSocket se necessario
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout aumentati per query SPARQL lunghe
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

echo "✅ Configurazione nginx creata"

# Abilita il sito
echo "🔗 Abilitazione del sito..."
sudo ln -sf /etc/nginx/sites-available/linkeddata.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testa la configurazione
echo "🧪 Test configurazione nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Configurazione nginx valida"
    echo "🔄 Riavvio nginx..."
    sudo systemctl reload nginx
    echo "✅ Nginx ricaricato con successo!"
    echo ""
    echo "🌐 Il sito https://svagnoni.linkeddata.es ora dovrebbe servire:"
    echo "   ✅ CSS da /css/styles.css"
    echo "   ✅ JS da /js/main.js"
    echo "   ✅ Immagini da /*.png"
    echo "   ✅ API da /api/*"
    echo "   ✅ SPARQL da /sparql"
else
    echo "❌ Errore nella configurazione nginx!"
    exit 1
fi