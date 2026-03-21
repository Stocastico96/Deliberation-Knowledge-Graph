# Pilot Study Plan: HYS vs EP Debates Comparison

## Obiettivo
Testare la metodologia di confronto su 3 dossier (AIA, DMA, DSA) prima di scalare.

---

## 1. DATA ACQUISITION

### 1.1 EU Have Your Say (già disponibile)
- **Database**: `/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db`
- **Filtro**: Solo feedback per AIA, DMA, DSA
- **Ares references**:
  - AIA: da identificare
  - DMA: da identificare
  - DSA: da identificare

```bash
# Query per estrarre feedback per dossier specifici
# TODO: identificare Ares reference per AIA/DMA/DSA
```

### 1.2 EP Debates (da acquisire)

**Opzione A: ParlaMint (raccomandato)**
```bash
# Download ParlaMint EU Parliament corpus
# URL: https://www.clarin.si/repository/xmlui/handle/11356/2004
# Selezionare: ParlaMint-EU (European Parliament)
```

**Opzione B: EUR-Lex diretto**
```bash
# Usare script esistente per cercare dibattiti
# TODO: implementare fetch_debates.py
```

**Keywords per filtraggio**:
- AIA: "artificial intelligence", "AI act", "high-risk AI"
- DMA: "digital markets", "gatekeeper", "platform regulation"
- DSA: "digital services", "content moderation", "illegal content"

---

## 2. PREPROCESSING

### 2.1 HYS Feedback
```python
# Pipeline esistente
1. Export da DB con integrate_hys_full.py
2. Filtrare per Ares reference (AIA/DMA/DSA)
3. Pulizia testo (remove HTML, normalize)
4. Lingua: mantenere solo EN o tradurre tutto in EN
```

### 2.2 EP Debates
```python
# Se ParlaMint:
1. Parse TEI-XML
2. Estrarre speech text + metadata (speaker, party, date)
3. Filtrare per keyword/periodo rilevante
4. Output: lista di interventi con metadati
```

---

## 3. ANALYSIS PIPELINE

### 3.1 Topic Modeling (BERTopic)

```python
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# Configurazione
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
topic_model = BERTopic(embedding_model=embedding_model, language="multilingual")

# Fit su corpus combinato (HYS + EP)
all_docs = hys_docs + ep_docs
topics, probs = topic_model.fit_transform(all_docs)

# Analisi per corpus
hys_topic_dist = get_topic_distribution(topics[:len(hys_docs)])
ep_topic_dist = get_topic_distribution(topics[len(hys_docs):])
```

### 3.2 Topic Overlap Metrics

```python
import numpy as np
from scipy.spatial.distance import jensenshannon

def topic_overlap(dist_a, dist_b):
    """Jensen-Shannon divergence tra distribuzioni topic"""
    return 1 - jensenshannon(dist_a, dist_b)

def top_k_overlap(topics_a, topics_b, k=10):
    """Jaccard overlap tra top-k topics"""
    top_a = set(sorted(topics_a, key=topics_a.get, reverse=True)[:k])
    top_b = set(sorted(topics_b, key=topics_b.get, reverse=True)[:k])
    return len(top_a & top_b) / len(top_a | top_b)
```

### 3.3 Salience Comparison

```python
def salience_divergence(topics_a, topics_b):
    """
    Misura differenza in importanza relativa dei topic.
    Un topic può essere presente in entrambi ma con salience diversa.
    """
    common_topics = set(topics_a.keys()) & set(topics_b.keys())
    if not common_topics:
        return 1.0  # Massima divergenza

    divergences = []
    for topic in common_topics:
        # Normalizza per ottenere proporzioni
        prop_a = topics_a[topic] / sum(topics_a.values())
        prop_b = topics_b[topic] / sum(topics_b.values())
        divergences.append(abs(prop_a - prop_b))

    return np.mean(divergences)
```

### 3.4 Actor Analysis

```python
def actor_representation_index(hys_data, ep_data):
    """
    Confronta chi parla in HYS vs chi parla in EP.
    """
    # HYS: distribuzione per user_type
    hys_actors = Counter(fb['user_type'] for fb in hys_data)

    # EP: distribuzione per party/gruppo
    ep_actors = Counter(speech['party'] for speech in ep_data)

    # Mapping concettuale (da definire manualmente)
    # es. "business_association" ↔ "EPP", "NGO" ↔ "Greens", etc.

    return hys_actors, ep_actors
```

### 3.5 Temporal Analysis

```python
def temporal_lead_lag(hys_timeline, ep_timeline, topic):
    """
    Chi ha parlato prima di un topic: HYS o EP?
    """
    hys_first = min(hys_timeline[topic]) if topic in hys_timeline else None
    ep_first = min(ep_timeline[topic]) if topic in ep_timeline else None

    if hys_first and ep_first:
        lag_days = (ep_first - hys_first).days
        return lag_days  # Positivo = HYS prima, Negativo = EP prima
    return None
```

---

## 4. DELIBERATIVE DISTANCE INDEX (DDI)

### 4.1 Definizione Operativa

```python
def compute_ddi(hys_corpus, ep_corpus, weights=None):
    """
    Deliberative Distance Index: misura multi-dimensionale
    della distanza tra due forum deliberativi.

    Basato su letteratura:
    - Policy congruence (Golder & Stramski 2010)
    - Uptake measurement (Vrydagh 2022)
    - Topic modeling (Blei et al.)

    Returns: DDI in [0, 1], dove 0 = identici, 1 = completamente diversi
    """
    if weights is None:
        weights = {
            'topic': 0.3,
            'salience': 0.3,
            'temporal': 0.2,
            'actor': 0.2
        }

    # 1. Topic Distance
    topic_dist = 1 - topic_overlap(
        get_topic_dist(hys_corpus),
        get_topic_dist(ep_corpus)
    )

    # 2. Salience Distance
    salience_dist = salience_divergence(
        get_topic_salience(hys_corpus),
        get_topic_salience(ep_corpus)
    )

    # 3. Temporal Distance (normalizzato)
    temporal_dist = compute_temporal_distance(hys_corpus, ep_corpus)

    # 4. Actor Representation Distance
    actor_dist = compute_actor_distance(hys_corpus, ep_corpus)

    # Weighted sum
    ddi = (
        weights['topic'] * topic_dist +
        weights['salience'] * salience_dist +
        weights['temporal'] * temporal_dist +
        weights['actor'] * actor_dist
    )

    return ddi
```

### 4.2 Interpretazione

| DDI Range | Interpretazione |
|-----------|-----------------|
| 0.0 - 0.2 | Alta congruenza: cittadini e legislatori allineati |
| 0.2 - 0.4 | Moderata congruenza: sovrapposizione parziale |
| 0.4 - 0.6 | Moderata distanza: temi diversi o priorità diverse |
| 0.6 - 0.8 | Alta distanza: agende significativamente diverse |
| 0.8 - 1.0 | Massima distanza: quasi nessuna sovrapposizione |

### 4.3 Validazione

Per validare DDI:
1. **Face validity**: I risultati hanno senso intuitivamente?
2. **Confronto con uptake manuale**: Su subset, codifica manuale e confronto
3. **Sensitivity analysis**: Variare pesi e verificare robustezza
4. **Known-group validity**: Dossier con esito diverso dovrebbero avere DDI diverso

---

## 5. EXPECTED OUTPUTS

### 5.1 Tabelle

**Tabella 1: Topic Overlap per Dossier**
| Dossier | HYS Topics | EP Topics | Overlap | JS Divergence |
|---------|------------|-----------|---------|---------------|
| AIA     | TBD        | TBD       | TBD     | TBD           |
| DMA     | TBD        | TBD       | TBD     | TBD           |
| DSA     | TBD        | TBD       | TBD     | TBD           |

**Tabella 2: DDI Scores**
| Dossier | Topic Dist | Salience Dist | Temporal Dist | Actor Dist | **DDI** |
|---------|------------|---------------|---------------|------------|---------|
| AIA     | TBD        | TBD           | TBD           | TBD        | TBD     |
| DMA     | TBD        | TBD           | TBD           | TBD        | TBD     |
| DSA     | TBD        | TBD           | TBD           | TBD        | TBD     |

### 5.2 Visualizzazioni

1. **Heatmap topic similarity**: HYS topics vs EP topics
2. **Timeline chart**: Evoluzione topic nel tempo, HYS vs EP
3. **Sankey diagram**: Flusso temi da HYS a EP
4. **Radar chart**: DDI components per dossier

---

## 6. IMPLEMENTATION STEPS

### Week 1: Data Acquisition
- [ ] Identificare Ares reference per AIA/DMA/DSA
- [ ] Estrarre feedback HYS per i 3 dossier
- [ ] Download ParlaMint EU Parliament corpus
- [ ] Filtrare dibattiti EP rilevanti

### Week 2: Preprocessing
- [ ] Pulire testi HYS
- [ ] Parsare ParlaMint XML
- [ ] Unificare formato dati
- [ ] Verificare copertura temporale

### Week 3: Topic Modeling
- [ ] Installare/configurare BERTopic
- [ ] Fit model su corpus combinato
- [ ] Estrarre topic distributions
- [ ] Validazione qualitativa topics

### Week 4: DDI Computation
- [ ] Implementare metriche componenti
- [ ] Calcolare DDI per ogni dossier
- [ ] Sensitivity analysis
- [ ] Interpretazione risultati

### Week 5: Documentation
- [ ] Scrivere metodi section
- [ ] Creare tabelle e figure
- [ ] Draft risultati preliminari
- [ ] Review con coautori

---

## 7. RISCHI E MITIGAZIONI

| Rischio | Probabilità | Mitigazione |
|---------|-------------|-------------|
| ParlaMint non copre dibattiti rilevanti | Media | Usare EUR-Lex diretto come backup |
| Topic modeling non convergente | Bassa | Tune hyperparameters, aumentare docs |
| Copertura temporale mismatch | Media | Allineare periodi, documentare gap |
| DDI non interpretabile | Media | Confronto con coding manuale |

---

## 8. SUCCESS CRITERIA

Il pilot è considerato riuscito se:
1. ✓ Otteniamo almeno 500 docs HYS e 100 interventi EP per ogni dossier
2. ✓ BERTopic produce topics interpretabili (coherence > 0.4)
3. ✓ DDI mostra variazione significativa tra dossier
4. ✓ Risultati passano sanity check con esperti dominio

---

## Appendice: Ares References per AIA/DMA/DSA

Da identificare nel database HYS:

```sql
-- Query per trovare iniziative AIA/DMA/DSA
SELECT id, reference, short_title
FROM initiatives
WHERE short_title LIKE '%Artificial Intelligence%'
   OR short_title LIKE '%Digital Markets%'
   OR short_title LIKE '%Digital Services%'
ORDER BY published_date;
```

**Nota**: Di Porto et al. hanno usato feedback da queste consultazioni specifiche. Dobbiamo identificare le stesse iniziative per comparabilità.
