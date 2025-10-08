# EU Have Your Say Data Collection & Integration

Scripts per scaricare consultazioni da EU Have Your Say e integrarle nel Deliberation Knowledge Graph.

## 📦 File Creati

### Script di Download
1. **`haveyoursay_selenium_scraper.py`** - Scraper principale con Selenium
   - Scarica consultazioni e feedback dal sito EU Have Your Say
   - Gestisce contenuto dinamico caricato con Angular/JavaScript
   - Salva dati in JSON e HTML

### Script di Mapping
2. **`map_haveyoursay_to_ontology.py`** - Mapper all'ontologia
   - Converte dati scaricati in formato JSON-LD
   - Mappa alla Deliberation Ontology
   - Crea file conformi al knowledge graph

### Script di Integrazione
3. **`integrate_haveyoursay_to_kg.py`** - Integratore nel KG
   - Integra JSON-LD nel knowledge graph
   - Crea grafo RDF in formato Turtle
   - Gestisce namespaces e URI

## 🚀 Utilizzo Completo

### 1. Download delle Consultazioni

```bash
# Download singola consultazione
python haveyoursay_selenium_scraper.py 14622

# Download multiple consultazioni
python haveyoursay_selenium_scraper.py 14622 13682 13761 14026 13845 13967 14146 13915 13524 13863 13796

# Output in: haveyoursay_data/
```

**Prerequisiti:**
```bash
pip install selenium beautifulsoup4
# E uno dei due:
sudo apt install chromium-chromedriver  # Per Chrome
# oppure
sudo apt install firefox-geckodriver    # Per Firefox
```

### 2. Mapping all'Ontologia

```bash
# Converti i dati scaricati in JSON-LD
python map_haveyoursay_to_ontology.py haveyoursay_data mapped_haveyoursay

# Output in: mapped_haveyoursay/*.jsonld
```

### 3. Integrazione nel Knowledge Graph

```bash
# Crea/aggiorna il knowledge graph
python integrate_haveyoursay_to_kg.py mapped_haveyoursay haveyoursay_knowledge_graph.ttl

# Output: haveyoursay_knowledge_graph.ttl (formato Turtle/RDF)
```

## 📊 Dati Scaricati

### Consultazioni processate (11 totali):
1. **14622** - Digital Fairness Act
2. **13682** - (consultazione)
3. **13761** - Data intermediaries & data altruism organisations
4. **14026** - Plant health – emerald ash borer
5. **13845** - Vehicle safety – eCall systems
6. **13967** - Endangered wild fauna and flora (CITES)
7. **14146** - (consultazione generica)
8. **13915** - State aid in aviation sector
9. **13524** - Aviation – air carriers restrictions
10. **13863** - EU emissions trading system (ETS)
11. **13796** - EU competition law – exclusionary abuses

**Risultati:**
- ✓ 9 consultazioni mappate con successo
- ✓ 189 triple RDF generate
- ✓ 9 feedback/contributi collezionati

## 📁 Struttura dei Dati

### Dati Scaricati (`haveyoursay_data/`)
```
haveyoursay_data/
├── initiative_14622/
│   ├── initiative.json      # Metadati consultazione
│   ├── feedback.csv          # Contributi in CSV
│   ├── feedback.json         # Contributi in JSON
│   └── page_source.html      # HTML originale
├── initiative_13682/
│   └── ...
└── download_summary.json     # Riepilogo download
```

### Dati Mappati (`mapped_haveyoursay/`)
```
mapped_haveyoursay/
├── eu_hys_14622.jsonld            # JSON-LD per singola consultazione
├── eu_hys_13682.jsonld
├── ...
├── eu_have_your_say_all.jsonld    # Tutte le consultazioni combinate
└── conversion_summary.json        # Statistiche conversione
```

### Knowledge Graph (`haveyoursay_knowledge_graph.ttl`)
- Formato: RDF Turtle
- Namespaces:
  - `del:` - Deliberation Ontology
  - `dct:` - Dublin Core Terms
  - `foaf:` - Friend of a Friend
- URI base: `https://svagnoni.linkeddata.es/resource/`

## 🔧 Ontologia Mapping

### Classi Principali
- `del:DeliberationProcess` - Processo di consultazione
- `del:Topic` - Argomento/tema della consultazione
- `del:Participant` - Partecipante (cittadino/organizzazione)
- `del:Organization` - Organizzazione partecipante
- `del:Contribution` - Contributo/feedback

### Proprietà
- `del:identifier` - Identificatore univoco
- `del:name` - Nome/titolo
- `del:text` - Testo del contributo
- `del:platform` - "EU Have Your Say"
- `dct:source` - URL originale
- `dct:created` - Data di creazione/scaricamento

## 📈 Statistiche Finali

```json
{
  "total_initiatives": 11,
  "successful_downloads": 11,
  "successful_mappings": 9,
  "total_triples": 189,
  "total_contributions": 9,
  "integration_date": "2025-09-30T13:12:00"
}
```

## 🔄 Workflow Completo

```bash
# 1. Download
python haveyoursay_selenium_scraper.py 14622 13682 13761 14026 13845 13967 14146 13915 13524 13863 13796

# 2. Mapping
python map_haveyoursay_to_ontology.py haveyoursay_data mapped_haveyoursay

# 3. Integrazione
python integrate_haveyoursay_to_kg.py mapped_haveyoursay haveyoursay_knowledge_graph.ttl

# 4. (Opzionale) Copia nel progetto DKG
# cp haveyoursay_knowledge_graph.ttl /path/to/deliberation-knowledge-graph/data/EU_have_your_say/
```

## ⚠️ Note

1. **Rate Limiting**: Gli script includono pause (2-3 secondi) tra le richieste per rispettare il server EC
2. **Headless Browser**: Selenium usa modalità headless di default (nessuna finestra browser)
3. **Permessi**: Alcuni file nel progetto DKG appartengono a `www-data`, potrebbero servire permessi sudo per copiarli
4. **Contenuto Dinamico**: Il sito EU Have Your Say carica contenuti via JavaScript, necessario Selenium

## 🐛 Troubleshooting

### Problema: ChromeDriver non trovato
```bash
sudo apt install chromium-chromedriver
# oppure
wget https://chromedriver.chromium.org/downloads
```

### Problema: Permessi negati
```bash
# Usa directory temporanea o casa utente
python integrate_haveyoursay_to_kg.py mapped_haveyoursay ~/haveyoursay_kg.ttl
```

### Problema: Timeout durante download
```bash
# Riprova con timeout maggiore o consultazioni singole
python haveyoursay_selenium_scraper.py 14622
```

## 📚 Riferimenti

- **EU Have Your Say**: https://ec.europa.eu/info/law/better-regulation/have-your-say
- **Deliberation Ontology**: https://w3id.org/deliberation/ontology
- **Deliberation Knowledge Graph**: /home/svagnoni/deliberation-knowledge-graph

## ✅ Checklist Completamento

- [x] Script download creato e testato
- [x] Script mapping creato e testato
- [x] Script integrazione creato e testato
- [x] 11 consultazioni scaricate
- [x] 9 consultazioni mappate all'ontologia
- [x] Knowledge graph RDF generato (189 triple)
- [x] Documentazione completa

---

**Data creazione**: 30 Settembre 2025
**Autore**: Claude Code Assistant
**Progetto**: Deliberation Knowledge Graph - EU Have Your Say Integration