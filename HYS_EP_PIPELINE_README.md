# HYS-EP Integration Pipeline: Quick Start Guide

Questa guida fornisce i comandi esatti per eseguire l'esperimento di collegamento tra EU Have Your Say e Parlamento Europeo.

## Prerequisiti

```bash
# Installare dipendenze Python
pip install rdflib requests numpy scikit-learn sentence-transformers

# Verificare che il database HYS sia disponibile
ls -lh /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db
```

## Pipeline Completa

### Step 1: Export Database HYS → CSV

```bash
cd /home/svagnoni/deliberation-knowledge-graph

# Export completo (~3M feedback - può richiedere tempo)
python3 scripts/integrate_hys_full.py \
  --db /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db \
  --output /tmp/hys_export \
  --verbose

# OPPURE: export limitato per test veloce (5k feedback)
python3 scripts/integrate_hys_full.py \
  --db /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db \
  --output /tmp/hys_export \
  --limit-feedback 5000 \
  --verbose
```

**Output**: `/tmp/hys_export/` con `initiatives.csv` e `feedback.csv`

### Step 2: Conversione CSV → RDF

```bash
# Conversione con batch processing (evita memory overflow)
python3 data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py \
  --input-dir /tmp/hys_export \
  --output-dir data/EU_have_your_say \
  --batch-size 50000 \
  --verbose
```

**Output**:
- `data/EU_have_your_say/hys_initiatives.ttl` (~2.6 MB per 3.8k iniziative)
- `data/EU_have_your_say/hys_feedback_full.ttl` (dimensione dipende da quanti feedback)

**Merge opzionale** in un singolo file:
```bash
cat data/EU_have_your_say/hys_initiatives.ttl \
    data/EU_have_your_say/hys_feedback_full.ttl \
    > data/EU_have_your_say/hys_complete.ttl
```

### Step 3: Generazione Embeddings (opzionale ma consigliato)

```bash
mkdir -p embeddings

# Genera embeddings per analisi similarity
python3 scripts/generate_embeddings_batched.py \
  --input /tmp/hys_export/feedback.csv \
  --output embeddings/hys_embeddings.npz \
  --model all-MiniLM-L6-v2 \
  --batch-size 100 \
  --filter-major
```

**Note**:
- `--filter-major`: filtra solo iniziative "major" (riduce il dataset)
- Modello `all-MiniLM-L6-v2`: 384 dimensioni, veloce
- Richiede ~1GB RAM per 100k feedback

### Step 4: Linking EUR-Lex

#### 4a. Estrazione Ares References

```bash
# Estrai Ares da initiatives.csv
cut -d',' -f2 /tmp/hys_export/initiatives.csv | \
  tail -n +2 | \
  grep -v '^$' > /tmp/ares_refs.txt

echo "Trovate $(wc -l < /tmp/ares_refs.txt) references Ares"
```

#### 4b. Mapping Ares → CELEX

```bash
mkdir -p cache

# Cerca CELEX su EUR-Lex (con cache per evitare richieste duplicate)
python3 scripts/eurlex/link_ares_to_celex.py \
  --file /tmp/ares_refs.txt \
  --cache cache/ares_celex_cache.json \
  --wait 2.0
```

**Output**: `cache/ares_celex_cache.json`

**Attenzione**: Questo può richiedere tempo (2 sec/richiesta × N iniziative). Per test, limitare a top-100:
```bash
head -100 /tmp/ares_refs.txt > /tmp/ares_refs_sample.txt
```

#### 4c. Download Atti Legislativi

```bash
mkdir -p data/eurlex/acts

# Estrai CELEX trovati
jq -r '.[] | select(.celex != null) | .celex' cache/ares_celex_cache.json \
  > /tmp/celex_list.txt

# Download XML
python3 scripts/eurlex/fetch_legislation.py \
  --file /tmp/celex_list.txt \
  --output data/eurlex/acts \
  --format xml \
  --wait 2.0
```

**Output**: File XML in `data/eurlex/acts/{CELEX}.xml`

### Step 5: Analisi

#### 5a. Analisi di Rappresentatività

```bash
mkdir -p results

python3 analysis/representativity_analysis.py \
  --feedback /tmp/hys_export/feedback.csv \
  --initiatives /tmp/hys_export/initiatives.csv \
  --output results/representativity.json
```

**Metriche calcolate**:
- Distribuzione geografica (paesi)
- Distribuzione per tipo utente
- Top organizzazioni
- Gini coefficient (concentrazione feedback)
- Coverage top-10, top-100 iniziative

**Output**: `results/representativity.json`

#### 5b. Topic Alignment (TODO)

```bash
# Dopo aver implementato download dibattiti EP
python3 analysis/topic_alignment.py \
  --hys-feedback /tmp/hys_export/feedback.csv \
  --ep-debates data/eurlex/debates/ \
  --output results/topic_alignment.json \
  --n-topics 10
```

## Test Rapido (Pipeline Minima)

Per testare l'intera pipeline su un campione ridotto:

```bash
# 1. Export 5k feedback
python3 scripts/integrate_hys_full.py --limit-feedback 5000 -v

# 2. Conversione RDF
python3 data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py \
  --batch-size 1000 -v

# 3. Analisi rappresentatività
python3 analysis/representativity_analysis.py \
  --output results/test_representativity.json

# 4. Verificare output
ls -lh data/EU_have_your_say/*.ttl
cat results/test_representativity.json | jq '.concentration_metrics'
```

**Tempo stimato**: ~2 minuti

## Risultati Test Preliminari

Con campione di 5,000 feedback:

```
Total feedback: 5,000
Unique countries: 54
Unique user types: 11
Total organizations: 1,330

Concentration metrics:
  Gini coefficient: 0.860
  Top 10 initiatives: 77.1% of feedback
  Top 100 initiatives: 96.4% of feedback

Top 5 countries:
  DEU: 1,279 (37.9%)
  BEL: 432 (12.8%)
  GBR: 410 (12.2%)
  ESP: 256 (7.6%)
  FRA: 162 (4.8%)

User type distribution:
  EU_CITIZEN: 50.8%
  BUSINESS_ASSOCIATION: 16.1%
  COMPANY: 14.9%
  NGO: 9.3%
```

**Osservazioni**:
- Alta concentrazione (Gini 0.86): poche iniziative ricevono la maggior parte dei feedback
- Germania domina (38%), seguita da Belgio/UK
- Cittadini EU sono metà dei partecipanti, resto organizzazioni

## Struttura File Generati

```
/tmp/hys_export/
├── initiatives.csv         # 3,835 righe
├── feedback.csv            # N righe (dipende da --limit-feedback)
├── publications.csv        # placeholder
└── attachments.csv         # placeholder

data/EU_have_your_say/
├── hys_initiatives.ttl     # RDF iniziative
└── hys_feedback_full.ttl   # RDF feedback + partecipanti

embeddings/
└── hys_embeddings.npz      # numpy compressed (embedding + metadata)

cache/
└── ares_celex_cache.json   # mapping Ares → CELEX

data/eurlex/acts/
├── 32023R1234.xml          # atto legislativo
├── 32023R1234.json         # metadata
└── ...

results/
├── representativity.json   # analisi rappresentatività
├── topic_alignment.json    # (da generare)
└── impact_tracing.json     # (da generare)
```

## Script Disponibili

### Export e Conversione
- `scripts/integrate_hys_full.py`: DB → CSV
- `data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py`: CSV → RDF

### EUR-Lex Integration
- `scripts/eurlex/link_ares_to_celex.py`: Ares → CELEX
- `scripts/eurlex/fetch_legislation.py`: Download atti
- `scripts/eurlex/fetch_debates.py`: Download dibattiti (TODO)

### Embeddings
- `scripts/generate_embeddings_batched.py`: Genera embeddings in batch

### Analisi
- `analysis/representativity_analysis.py`: Metriche rappresentatività
- `analysis/topic_alignment.py`: Allineamento tematico (template)
- `analysis/impact_tracing.py`: Similarity feedback↔legislazione (TODO)

## Troubleshooting

### Memory Error durante conversione RDF
```bash
# Ridurre batch size
python3 data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py \
  --batch-size 10000
```

### EUR-Lex timeout / rate limiting
```bash
# Aumentare wait time
python3 scripts/eurlex/link_ares_to_celex.py --wait 5.0
```

### Embeddings: Model download failed
```bash
# Pre-download model
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## Prossimi Passi

1. **Implementare `fetch_debates.py`**: Scaricare trascrizioni dibattiti EP da EUR-Lex
2. **Completare `topic_alignment.py`**: Parsing testi EP + confronto topic
3. **Implementare `impact_tracing.py`**: Similarità embedding feedback ↔ articoli legislativi
4. **Scaling a dataset completo**: Testare su tutti i ~3M feedback
5. **Integrazione nel DKG**: Caricare RDF nel knowledge graph principale

## Riferimenti

- Documentazione completa: [EXPERIMENT_HYS_EP.md](analysis/EXPERIMENT_HYS_EP.md)
- Deliberation Ontology: https://w3id.org/deliberation/ontology
- EUR-Lex API: https://eur-lex.europa.eu/content/tools/webservices.html

---

**Ultimo aggiornamento**: 2026-01-06
**Autore**: Pipeline automatizzata per esperimento HYS-EP
