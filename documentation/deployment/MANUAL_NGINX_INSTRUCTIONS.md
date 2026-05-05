# Istruzioni per Sistemare Nginx

Il problema è che nginx sta bloccando l'accesso ai file CSS/JS/immagini con errore 403 Forbidden.

## Il server Flask funziona correttamente:
- ✅ CSS: http://localhost:8085/css/styles.css
- ✅ JS: http://localhost:8085/js/main.js
- ✅ API: http://localhost:8085/api/stats
- ✅ SPARQL: http://localhost:8085/sparql

## Il problema è nginx che intercetta le richieste

### Soluzione: Configurare nginx per fare proxy di TUTTO al Flask

Eseguire come root o con sudo:

```bash
# Backup configurazione attuale
sudo cp /etc/nginx/sites-available/svagnoni.linkeddata.es /etc/nginx/sites-available/svagnoni.linkeddata.es.backup

# Sostituire il contenuto di /etc/nginx/sites-available/svagnoni.linkeddata.es con:
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name svagnoni.linkeddata.es;

    # Aggiungi header CORS
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

        # Headers per WebSocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout per query SPARQL lunghe
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

```bash
# Testare la configurazione
sudo nginx -t

# Se ok, ricaricare nginx
sudo systemctl reload nginx
```

## Risultato atteso:
- ✅ https://svagnoni.linkeddata.es/css/styles.css
- ✅ https://svagnoni.linkeddata.es/js/main.js
- ✅ https://svagnoni.linkeddata.es/DKG%20daft.png
- ✅ Tutti i CSS e stili funzionanti