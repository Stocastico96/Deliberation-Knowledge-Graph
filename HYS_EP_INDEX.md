# HYS-EP Integration Pipeline - File Index

## 📚 Documentazione

| File | Descrizione |
|------|-------------|
| [HYS_EP_PIPELINE_README.md](HYS_EP_PIPELINE_README.md) | **Guida operativa completa** - comandi, esempi, troubleshooting |
| [analysis/EXPERIMENT_HYS_EP.md](analysis/EXPERIMENT_HYS_EP.md) | **Documentazione esperimento** - obiettivi, metodi, risultati |
| [HYS_EP_SUMMARY.txt](HYS_EP_SUMMARY.txt) | **Summary esecutivo** - overview rapida del progetto |
| Questo file | Indice navigabile di tutti i file della pipeline |

## 🔧 Script Principali

### Fase 1: Export e Conversione HYS

| Script | Funzione | Input | Output |
|--------|----------|-------|--------|
| [scripts/integrate_hys_full.py](scripts/integrate_hys_full.py) | Export DB → CSV | haveyoursay_full_fixed.db | initiatives.csv, feedback.csv |
| [data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py](data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py) | CSV → RDF Turtle | CSV files | hys_initiatives.ttl, hys_feedback_full.ttl |

**Uso rapido:**
```bash
# Export 5k feedback sample
python3 scripts/integrate_hys_full.py --limit-feedback 5000 -v

# Convert to RDF
python3 data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py -v
```

### Fase 2: Embeddings

| Script | Funzione | Input | Output |
|--------|----------|-------|--------|
| [scripts/generate_embeddings_batched.py](scripts/generate_embeddings_batched.py) | Genera embeddings | feedback.csv | hys_embeddings.npz |

**Uso rapido:**
```bash
python3 scripts/generate_embeddings_batched.py \
  --input /tmp/hys_export/feedback.csv \
  --output embeddings/hys_embeddings.npz \
  --filter-major
```

### Fase 3: EUR-Lex Integration

| Script | Funzione | Input | Output |
|--------|----------|-------|--------|
| [scripts/eurlex/link_ares_to_celex.py](scripts/eurlex/link_ares_to_celex.py) | Ares → CELEX mapping | Ares references | ares_celex_cache.json |
| [scripts/eurlex/fetch_legislation.py](scripts/eurlex/fetch_legislation.py) | Download atti | CELEX list | XML/HTML files |
| scripts/eurlex/fetch_debates.py | Download dibattiti EP | CELEX/dossier | Text files |

**Uso rapido:**
```bash
# Map Ares to CELEX
cut -d',' -f2 /tmp/hys_export/initiatives.csv | tail -n +2 > ares_refs.txt
python3 scripts/eurlex/link_ares_to_celex.py --file ares_refs.txt

# Download legislation
jq -r '.[] | select(.celex != null) | .celex' cache/ares_celex_cache.json > celex_list.txt
python3 scripts/eurlex/fetch_legislation.py --file celex_list.txt
```

### Fase 4: Analisi

| Script | Funzione | Input | Output |
|--------|----------|-------|--------|
| [analysis/representativity_analysis.py](analysis/representativity_analysis.py) | Metriche rappresentatività | feedback.csv, initiatives.csv | representativity.json |
| [analysis/topic_alignment.py](analysis/topic_alignment.py) | Allineamento tematico HYS↔EP | feedback + EP debates | topic_alignment.json |
| analysis/impact_tracing.py | Similarity feedback↔legislation | embeddings + acts | impact_tracing.json |

**Uso rapido:**
```bash
python3 analysis/representativity_analysis.py \
  --output results/representativity.json
```

## 🧪 Testing

| File | Descrizione |
|------|-------------|
| [test_pipeline_end_to_end.sh](test_pipeline_end_to_end.sh) | **Test completo automatizzato** - esegue tutti gli step su campione |

**Uso:**
```bash
./test_pipeline_end_to_end.sh
```

## 📁 Struttura Directory

```
deliberation-knowledge-graph/
├── 📖 Documentazione
│   ├── HYS_EP_PIPELINE_README.md          ← INIZIA DA QUI
│   ├── HYS_EP_SUMMARY.txt
│   ├── HYS_EP_INDEX.md                     ← Questo file
│   └── analysis/EXPERIMENT_HYS_EP.md
│
├── 🔧 Scripts
│   ├── scripts/
│   │   ├── integrate_hys_full.py           (DB → CSV)
│   │   ├── generate_embeddings_batched.py  (Embeddings)
│   │   └── eurlex/
│   │       ├── link_ares_to_celex.py       (Ares → CELEX)
│   │       └── fetch_legislation.py        (Download atti)
│   │
│   ├── data/EU_have_your_say/
│   │   └── convert_hys_csv_to_del_rdf_batched.py  (CSV → RDF)
│   │
│   └── analysis/
│       ├── representativity_analysis.py
│       └── topic_alignment.py
│
├── 📊 Dati e Output
│   ├── /tmp/hys_export/                    (CSV temporanei)
│   ├── data/EU_have_your_say/              (RDF output)
│   ├── embeddings/                          (Embeddings NPZ)
│   ├── cache/                               (Ares-CELEX cache)
│   └── results/                             (Analisi JSON)
│
└── 🧪 Test
    └── test_pipeline_end_to_end.sh
```

## 🎯 Quick Start Paths

### Path 1: Solo Test Rapido (5 minuti)
```bash
./test_pipeline_end_to_end.sh
```

### Path 2: Analisi Completa Rappresentatività (15 minuti)
```bash
# 1. Export full dataset
python3 scripts/integrate_hys_full.py -v

# 2. Analisi
python3 analysis/representativity_analysis.py --output results/repr_full.json

# 3. Visualizza risultati
cat results/repr_full.json | jq .
```

### Path 3: Pipeline Completa con EUR-Lex (1+ ore)
```bash
# 1. Export
python3 scripts/integrate_hys_full.py -v

# 2. Conversione RDF
python3 data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py -v

# 3. Ares → CELEX
cut -d',' -f2 /tmp/hys_export/initiatives.csv | tail -n +2 > ares_refs.txt
python3 scripts/eurlex/link_ares_to_celex.py --file ares_refs.txt --wait 2.0

# 4. Download legislazione
jq -r '.[] | select(.celex != null) | .celex' cache/ares_celex_cache.json > celex_list.txt
python3 scripts/eurlex/fetch_legislation.py --file celex_list.txt --wait 2.0

# 5. Analisi
python3 analysis/representativity_analysis.py --output results/repr.json
```

## 📊 Risultati Test (campione 5k feedback)

```
Feedback analizzati: 5,000
Paesi unici: 54
Organizzazioni: 1,330

Distribuzione geografica:
  🇩🇪 Germania: 37.9%
  🇧🇪 Belgio: 12.8%
  🇬🇧 UK: 12.2%

Tipo partecipante:
  👤 Cittadini EU: 50.8%
  🏢 Business: 16.1%
  🏭 Company: 14.9%
  🌱 NGO: 9.3%

Concentrazione:
  Gini: 0.860 (alta)
  Top-10 iniziative: 77.1% feedback
```

## 🔗 Collegamenti Utili

- **Deliberation Ontology**: https://w3id.org/deliberation/ontology
- **Repository GitHub**: https://github.com/Stocastico96/Deliberation-Knowledge-Graph
- **EU Have Your Say**: https://ec.europa.eu/info/law/better-regulation/have-your-say
- **EUR-Lex**: https://eur-lex.europa.eu
- **EUR-Lex SPARQL**: https://publications.europa.eu/webapi/rdf/sparql

## ✅ Checklist Completamento

### Implementato
- [x] Export DB HYS → CSV
- [x] Conversione CSV → RDF (batch processing)
- [x] Generazione embeddings (batch)
- [x] Mapping Ares → CELEX
- [x] Download atti legislativi
- [x] Analisi rappresentatività
- [x] Template topic alignment
- [x] Documentazione completa
- [x] Test end-to-end

### TODO
- [ ] Implementare `fetch_debates.py` (dibattiti EP)
- [ ] Completare `topic_alignment.py` (parsing EP + metrics)
- [ ] Implementare `impact_tracing.py` (similarity analysis)
- [ ] Integrare RDF nel knowledge graph principale
- [ ] Testare su dataset completo (~3M feedback)
- [ ] Pubblicare risultati preliminari

## 🤝 Contribuire

Per contribuire al progetto:
1. Leggere [EXPERIMENT_HYS_EP.md](analysis/EXPERIMENT_HYS_EP.md)
2. Implementare script TODO
3. Testare su campioni
4. Documentare modifiche

---

**Ultimo aggiornamento**: 2026-01-06
**Versione**: 1.0 - Pipeline base completa
