# Guida Configurazione Sottodomini per DKG

## 🎯 Obiettivo
Configurare i sottodomini per rendere tutti i servizi DKG accessibili come:
- **dkg.svagnoni.linkeddata.es** → Homepage principale
- **api.svagnoni.linkeddata.es** → API endpoints
- **sparql.svagnoni.linkeddata.es** → SPARQL endpoint
- **viz.svagnoni.linkeddata.es** → Visualizzazione KG
- **contrib.svagnoni.linkeddata.es** → Exploration contributi

## ✅ ATTUALE: Tutto Funzionante sotto /dkg/

### URL Attuali Funzionanti:
- 🏠 **Homepage**: https://svagnoni.linkeddata.es/dkg
- 👥 **Contributions**: https://svagnoni.linkeddata.es/dkg/contributions
- 📊 **Visualization**: https://svagnoni.linkeddata.es/dkg/visualize
- 🔍 **SPARQL Interface**: https://svagnoni.linkeddata.es/dkg/sparql
- 📈 **Stats API**: https://svagnoni.linkeddata.es/dkg/api/stats
- 📂 **Export TTL**: https://svagnoni.linkeddata.es/dkg/api/export/ttl
- 🔎 **SPARQL Query**: https://svagnoni.linkeddata.es/dkg/sparql?query=...

## 🚀 Configurazione Sottodomini DNS

### 1. DNS Records da Aggiungere
```dns
dkg.svagnoni.linkeddata.es    CNAME   svagnoni.linkeddata.es
api.svagnoni.linkeddata.es    CNAME   svagnoni.linkeddata.es
sparql.svagnoni.linkeddata.es CNAME   svagnoni.linkeddata.es
viz.svagnoni.linkeddata.es    CNAME   svagnoni.linkeddata.es
contrib.svagnoni.linkeddata.es CNAME  svagnoni.linkeddata.es
```

### 2. Nginx Virtual Host Configuration

Creare file: `/etc/nginx/sites-available/dkg-subdomains.conf`

```nginx
# Homepage DKG
server {
    listen 80;
    server_name dkg.svagnoni.linkeddata.es;

    location / {
        proxy_pass http://127.0.0.1:8085/dkg;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# API Subdomain
server {
    listen 80;
    server_name api.svagnoni.linkeddata.es;

    location / {
        proxy_pass http://127.0.0.1:8085/dkg/api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# SPARQL Subdomain
server {
    listen 80;
    server_name sparql.svagnoni.linkeddata.es;

    location / {
        proxy_pass http://127.0.0.1:8085/dkg/sparql;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Visualization Subdomain
server {
    listen 80;
    server_name viz.svagnoni.linkeddata.es;

    location / {
        proxy_pass http://127.0.0.1:8085/dkg/visualize;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Contributions Subdomain
server {
    listen 80;
    server_name contrib.svagnoni.linkeddata.es;

    location / {
        proxy_pass http://127.0.0.1:8085/dkg/contributions;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Attivazione Configurazione
```bash
# Abilitare i nuovi virtual host
sudo ln -s /etc/nginx/sites-available/dkg-subdomains.conf /etc/nginx/sites-enabled/

# Test configurazione
sudo nginx -t

# Ricarica nginx
sudo systemctl reload nginx
```

### 4. SSL/HTTPS (Opzionale)
```bash
# Se hai Let's Encrypt configurato:
sudo certbot --nginx -d dkg.svagnoni.linkeddata.es
sudo certbot --nginx -d api.svagnoni.linkeddata.es
sudo certbot --nginx -d sparql.svagnoni.linkeddata.es
sudo certbot --nginx -d viz.svagnoni.linkeddata.es
sudo certbot --nginx -d contrib.svagnoni.linkeddata.es
```

## 📊 Backend Flask - Già Configurato

Il server Flask è già configurato con tutte le route necessarie:
- ✅ Route duplicate per compatibilità
- ✅ CORS abilitato
- ✅ Frontend self-contained con CSS/JS inline
- ✅ Immagini base64 integrate

## 🎯 Risultato Finale

Dopo la configurazione DNS e nginx, i servizi saranno accessibili come:

```
🏠 Homepage:       https://dkg.svagnoni.linkeddata.es
📈 API Stats:      https://api.svagnoni.linkeddata.es/stats
📂 Export TTL:     https://api.svagnoni.linkeddata.es/export/ttl
🔍 SPARQL:         https://sparql.svagnoni.linkeddata.es
🔎 Query SPARQL:   https://sparql.svagnoni.linkeddata.es?query=...
📊 Visualization: https://viz.svagnoni.linkeddata.es
👥 Contributions: https://contrib.svagnoni.linkeddata.es
```

## ✅ Status Attuale
- ✅ **Backend configurato** e funzionante
- ✅ **Frontend completo** con styling GitHub
- ✅ **Route /dkg/** tutte operative
- ⏳ **DNS e nginx** da configurare per sottodomini

**Tutti i servizi sono già accessibili e funzionanti sotto la struttura /dkg/!**