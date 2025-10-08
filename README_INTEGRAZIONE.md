# Guida Completa all'Integrazione dei Dati nel Deliberation Knowledge Graph

## Panoramica

Questa guida spiega come integrare tutti i dati dei dataset nel formato OWL nell'ontologia DEL (Deliberation) e come esporre questi dati attraverso un sito web gestito autonomamente.

## Struttura del Progetto

```
Deliberation-Knowledge-Graph/
├── ontologies/
│   ├── deliberation.owl              # Ontologia principale DEL
│   └── mappings.owl                  # Mappature con altre ontologie
├── data/                             # Dataset originali
│   ├── EU_parliament_debates/
│   ├── decide_Madrid/
│   ├── delidata/
│   └── ...
├── knowledge_graph/                  # Knowledge graph generato
│   ├── deliberation_kg.ttl
│   ├── deliberation_kg.rdf
│   └── deliberation_kg.jsonld
├── integrate_all_data_to_owl.py      # Script di integrazione principale
├── sparql_server.py                  # Server web Python
├── sparql_interface.html             # Interfaccia web SPARQL
└── index.html                        # Sito web principale
```

## Passo 1: Preparazione dell'Ambiente

### Installazione Dipendenze

```bash
# Installa le dipendenze Python necessarie
pip install rdflib flask flask-cors beautifulsoup4

# Oppure usa requirements.txt
pip install -r requirements.txt
```

### File requirements.txt
```
rdflib>=6.0.0
flask>=2.0.0
flask-cors>=3.0.0
beautifulsoup4>=4.9.0
```

## Passo 2: Integrazione dei Dati in Formato OWL

### Esecuzione dello Script di Integrazione

```bash
# Integra tutti i dati nell'ontologia DEL
python integrate_all_data_to_owl.py --include-ontology

# Opzioni avanzate
python integrate_all_data_to_owl.py \
    --data-dir data \
    --ontology ontologies/deliberation.owl \
    --output-dir knowledge_graph \
    --include-ontology
```

### Cosa fa lo Script

1. **Carica l'ontologia DEL** da `ontologies/deliberation.owl`
2. **Processa tutti i dataset** disponibili:
   - European Parliament Debates
   - Decide Madrid
   - DeliData
   - EU Have Your Say
   - Habermas Machine
   - US Supreme Court Arguments
3. **Converte i dati** nel formato RDF/OWL usando l'ontologia DEL
4. **Crea un knowledge graph unificato** in diversi formati:
   - Turtle (.ttl)
   - RDF/XML (.rdf)
   - JSON-LD (.jsonld)
   - N3 (.n3)

### Struttura dei Dati Convertiti

Ogni dataset viene mappato alle classi dell'ontologia DEL:

- **Processi deliberativi** → `del:DeliberationProcess`
- **Partecipanti** → `del:Participant`
- **Contributi/Interventi** → `del:Contribution`
- **Argomenti** → `del:Argument`
- **Topic/Temi** → `del:Topic`
- **Organizzazioni** → `del:Organization`
- **Ruoli** → `del:Role`

## Passo 3: Configurazione del Sito Web

### Avvio del Server Web

```bash
# Avvia il server con il knowledge graph
python sparql_server.py --kg-file knowledge_graph/deliberation_kg.ttl

# Opzioni personalizzate
python sparql_server.py \
    --kg-file knowledge_graph/deliberation_kg.ttl \
    --host 0.0.0.0 \
    --port 8080 \
    --debug
```

### Funzionalità del Server

Il server fornisce:

1. **Interfaccia SPARQL interattiva** su `http://localhost:5000`
2. **Endpoint SPARQL** su `http://localhost:5000/sparql`
3. **API REST** per accesso programmatico:
   - `/api/stats` - Statistiche del knowledge graph
   - `/api/processes` - Lista processi deliberativi
   - `/api/participants` - Lista partecipanti
   - `/api/search?q=termine` - Ricerca nel knowledge graph

### Interfaccia Web

L'interfaccia web include:

- **Editor SPARQL** con syntax highlighting
- **Query di esempio** predefinite
- **Visualizzazione risultati** in formato tabellare
- **API per ricerca** e navigazione dei dati

## Passo 4: Query SPARQL di Esempio

### 1. Lista Processi Deliberativi

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?process ?name ?startDate ?endDate
WHERE {
    ?process a del:DeliberationProcess ;
             del:name ?name .
    OPTIONAL { ?process del:startDate ?startDate }
    OPTIONAL { ?process del:endDate ?endDate }
}
ORDER BY ?startDate
```

### 2. Partecipanti per Organizzazione

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?org ?orgName ?participant ?participantName
WHERE {
    ?participant a del:Participant ;
                del:name ?participantName ;
                del:isAffiliatedWith ?org .
    ?org del:name ?orgName .
}
ORDER BY ?orgName ?participantName
```

### 3. Analisi degli Argomenti

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?argument ?premise ?conclusion ?fallacy
WHERE {
    ?argument a del:Argument .
    OPTIONAL { ?argument del:hasPremise ?premise }
    OPTIONAL { ?argument del:hasConclusion ?conclusion }
    OPTIONAL { ?argument del:containsFallacy ?fallacy }
}
```

### 4. Statistiche Generali

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT 
    (COUNT(DISTINCT ?process) AS ?totalProcesses)
    (COUNT(DISTINCT ?participant) AS ?totalParticipants)
    (COUNT(DISTINCT ?contribution) AS ?totalContributions)
    (COUNT(DISTINCT ?topic) AS ?totalTopics)
WHERE {
    OPTIONAL { ?process a del:DeliberationProcess }
    OPTIONAL { ?participant a del:Participant }
    OPTIONAL { ?contribution a del:Contribution }
    OPTIONAL { ?topic a del:Topic }
}
```

## Passo 5: Personalizzazione e Estensione

### Aggiungere Nuovi Dataset

1. **Crea una funzione di processamento** in `integrate_all_data_to_owl.py`:

```python
def process_new_dataset(graph, file_path):
    """Processa un nuovo dataset"""
    # Logica di conversione specifica
    pass
```

2. **Aggiungi il dataset alla lista** nella funzione `process_all_datasets()`

3. **Esegui nuovamente lo script** di integrazione

### Personalizzare l'Interfaccia Web

1. **Modifica `sparql_interface.html`** per aggiungere nuove funzionalità
2. **Estendi `sparql_server.py`** per nuove API
3. **Aggiorna `index.html`** per nuove sezioni

### Configurazione Avanzata

#### Configurazione Apache/Nginx

Per un deployment in produzione, configura un reverse proxy:

**Nginx:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Configurazione HTTPS

```bash
# Usa Let's Encrypt per certificati SSL
sudo certbot --nginx -d your-domain.com
```

## Passo 6: Monitoraggio e Manutenzione

### Log del Server

Il server registra automaticamente:
- Richieste SPARQL
- Errori di query
- Statistiche di utilizzo

### Backup del Knowledge Graph

```bash
# Backup automatico
cp knowledge_graph/deliberation_kg.ttl backups/kg_$(date +%Y%m%d).ttl
```

### Aggiornamento Dati

Per aggiornare i dati:

1. Aggiungi nuovi file dataset nella directory `data/`
2. Esegui nuovamente `integrate_all_data_to_owl.py`
3. Riavvia il server con il nuovo knowledge graph

## Risoluzione Problemi

### Errori Comuni

1. **"Knowledge graph non caricato"**
   - Verifica che il file .ttl esista
   - Controlla i permessi del file

2. **"Errore nella query SPARQL"**
   - Verifica la sintassi SPARQL
   - Controlla i namespace utilizzati

3. **"Server non raggiungibile"**
   - Verifica che il server sia avviato
   - Controlla firewall e porte

### Debug

```bash
# Avvia in modalità debug
python sparql_server.py --debug

# Verifica il knowledge graph
python -c "
from rdflib import Graph
g = Graph()
g.parse('knowledge_graph/deliberation_kg.ttl', format='turtle')
print(f'Triple caricate: {len(g)}')
"
```

## Conclusioni

Questa integrazione fornisce:

1. **Knowledge graph unificato** con tutti i dati in formato OWL
2. **Interfaccia web completa** per interrogare i dati
3. **API REST** per accesso programmatico
4. **Scalabilità** per aggiungere nuovi dataset
5. **Compatibilità** con standard del Semantic Web

Il sistema è ora pronto per essere utilizzato per analisi avanzate dei processi deliberativi attraverso query SPARQL e visualizzazioni web interattive.