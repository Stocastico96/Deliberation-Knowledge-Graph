# Deliberation Knowledge Graph - TODO List

## 🚀 In Progress

- [ ] Fix Decidim Barcelona comment mapping (use real commentable_id)
- [ ] Push to GitLab and GitHub
- [ ] Implement topic modeling
- [ ] Increase dataset limits (process all available data)

## 📋 Planned Features

### 1. Analisi delle Fallacie Argomentative 🎯
**Priority**: High
**Effort**: Medium

- Usare OpenRouter LLM per identificare fallacie logiche
- Implementare classificazione per tipo di fallacia (ad hominem, strawman, false dilemma, etc.)
- Aggiungere entità RDF: Argument, Premise, Conclusion, Fallacy
- Collegare fallacie ai contributi con property `hasFallacy`
- Creare report sulla qualità argomentativa delle deliberazioni

**File da creare**:
- `analyze_fallacies.py` - Script principale
- `fallacy_detector.py` - Modulo per detection
- `fallacy_types.py` - Definizioni tipi di fallacie

### 2. Espansione Dataset 📊
**Priority**: High
**Effort**: High

**Nuove fonti da integrare**:
- [ ] CIP (Collective Intelligence Project) - Dataset deliberazione pubblica
- [ ] DeliData - Dataset deliberativi europei
- [ ] Kialo - Dibattiti strutturati con argomenti pro/contro
- [ ] ChangeMyView (Reddit) - Discussioni con cambio opinione
- [ ] US Supreme Court - Trascrizioni argomentazioni orali
- [ ] Più dibattiti Parlamento Europeo (2023, 2022)
- [ ] Più iniziative EU Have Your Say

**File da creare**:
- `data/kialo/fetch_kialo.py`
- `data/reddit_cmv/fetch_cmv.py`
- `data/supreme_court/fetch_scotus.py`

### 3. Topic Modeling 🏷️
**Priority**: High
**Effort**: Medium

- Implementare LDA (Latent Dirichlet Allocation)
- Implementare BERTopic per topic modeling semantico
- Supporto multilingue (IT, ES, CA, EN)
- Aggiungere topic come entità RDF
- Creare visualizzazioni topic più discussi
- Analisi evoluzione topic nel tempo

**File da creare**:
- `topic_modeling.py` - Script principale
- `visualize_topics.py` - Visualizzazioni
- Update ontology con topic properties

### 4. Sentiment Analysis 😊😐😢
**Priority**: Medium
**Effort**: Medium

- Usare modelli multilingue (IT, ES, CA, EN)
- Aggiungere property `hasSentiment` (positive/neutral/negative)
- Aggiungere score numerico (-1 a +1)
- Visualizzare trend sentiment nel tempo
- Analisi sentiment per piattaforma/topic

**File da creare**:
- `sentiment_analysis.py`
- `visualize_sentiment.py`

### 5. Network Analysis 🕸️
**Priority**: Medium
**Effort**: High

**Metriche da calcolare**:
- Centrality (chi è più influente?)
- Communities (gruppi di discussione)
- Response patterns (chi risponde a chi?)
- Clustering coefficient
- Path lengths

**Visualizzazioni**:
- Network graphs interattivi (D3.js)
- Community detection visualization
- Influence maps

**File da creare**:
- `network_analysis.py` - Analisi con NetworkX
- `citizen_interface/visualizations/network.js` - Viz D3.js

### 6. Interfaccia di Ricerca Avanzata 🔍
**Priority**: Medium
**Effort**: Medium

**Features**:
- Full-text search con Whoosh/Elasticsearch
- Filtri: piattaforma, data, topic, sentiment, fallacie
- Ricerca semantica con sentence-transformers
- Export risultati (CSV, JSON, RDF)
- Query builder UI

**File da modificare/creare**:
- `citizen_interface/backend/search_api.py`
- `citizen_interface/frontend/search.html`

### 7. Dashboard Analytics 📊
**Priority**: Medium
**Effort**: High

**Visualizzazioni da creare**:
- Timeline deliberazioni
- Distribuzione geografica (mappa)
- Topic trends nel tempo
- Partecipazione per piattaforma
- Qualità argomentativa (fallacie)
- Sentiment trends
- Network metrics

**File da creare**:
- `citizen_interface/dashboard.html`
- `citizen_interface/backend/analytics_api.py`

### 8. API RESTful Completa 🚀
**Priority**: High
**Effort**: Medium

**Nuovi endpoint da aggiungere**:
```
GET  /api/search?q=query&filters=...
GET  /api/process/{id}
GET  /api/process/{id}/contributions
GET  /api/participant/{id}
GET  /api/participant/{id}/contributions
GET  /api/topics
GET  /api/topics/{id}/processes
GET  /api/fallacies
GET  /api/fallacies/{id}
GET  /api/analytics/sentiment-timeline
GET  /api/analytics/topic-distribution
GET  /api/analytics/platform-stats
GET  /api/analytics/network-metrics
POST /api/query (SPARQL endpoint)
```

**File da modificare**:
- `citizen_interface/backend/simple_server.py`

### 9. Data Quality & Validation 🔍
**Priority**: Medium
**Effort**: Low

- Validare tutti i dati contro ontologia
- Identificare missing data
- Rimuovere duplicati
- Normalizzare formati date
- Validare URIs

**File da creare**:
- `validate_kg.py`
- `data_quality_report.py`

### 10. Documentation 📚
**Priority**: Low
**Effort**: Low

- API documentation (OpenAPI/Swagger)
- User guide per citizen interface
- Developer guide
- Dataset documentation
- Ontology documentation

**File da creare**:
- `docs/API.md`
- `docs/USER_GUIDE.md`
- `docs/DEVELOPER.md`
- `docs/DATASETS.md`

## 🔧 Technical Debt

- [ ] Ottimizzare query SPARQL (indici)
- [ ] Caching per API calls
- [ ] Tests unitari
- [ ] CI/CD pipeline
- [ ] Monitoring & logging
- [ ] Backup automatici KG
- [ ] Performance profiling

## 📈 Dataset Statistics (Current)

- **Total Triples**: 881,257
- **Processes**: 15,060
- **Contributions**: 84,975
- **Participants**: 62,757
- **Topics**: 1,058

### Available Data (Not Yet Processed)

- **Decidim Barcelona**: 245,191 proposals (using: 10,000)
- **Decidim Comments**: 45,228 comments (using: 20,000)
- **Decide Madrid**: 29,129 debates (using: 5,006)
- **Madrid Comments**: 217,623 comments (using: 32,964)

**Potential**: ~2-3 million triples with full dataset!

## 🎯 Immediate Next Steps

1. ✅ Fix Decidim comment mapping
2. ✅ Push to GitLab/GitHub
3. ✅ Topic modeling implementation
4. ✅ Increase dataset limits

## 📝 Notes

- OpenRouter API already configured
- Server running on port 5001
- Citizen interface: https://citizen.svagnoni.linkeddata.es
- SPARQL endpoint on port 8085
