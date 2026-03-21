# Comparison Paper: Cross-Forum Deliberative Analysis

## Core Research Question

**"How distant are legislators from citizens in what they discuss and how they position themselves?"**

---

## 0. THEORETICAL GROUNDING: Congruence vs Distance

### 0.1 Existing Literature on Congruence Measurement

Il concetto di "distanza deliberativa" non esiste come tale in letteratura. Esistono invece:

**A. Policy Congruence (Political Science)**
- **Golder & Stramski (2010)**: Distinguono tra:
  - *One-to-one*: singolo cittadino ↔ suo rappresentante
  - *Many-to-one*: popolazione ↔ singolo rappresentante
  - *Many-to-many*: tutti i cittadini ↔ tutto il parlamento
- **Metodo**: Confronto distribuzioni preferenze su scale ideologiche (left-right)
- Ref: [Measuring Agreement: How to Arrive at Reliable Measures of Opinion Congruence](https://www.tandfonline.com/doi/full/10.1080/00344893.2021.1998208)

**B. Uptake/Congruency Approach (Participatory Democracy)**
- **Vrydagh (2022)**: "Measuring the impact of consultative citizen participation"
- Tre approcci:
  1. *Binary Impact*: idea cittadina presente/assente nel documento
  2. *Plural Impact*: uptake completo / parziale / assente
  3. *Sequential Impact Matrix (SIM)*: integra preferenze iniziali decision-maker
- Ref: [PMC Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC8869347/)

**C. Deliberative Quality Measurement (Deliberative Democracy)**
- **Bächtiger et al.**: Discourse Quality Index (DQI) - misura qualità argomentativa
- **V-Dem Institute**: Deliberative Democracy Index (macro-level)
- Ref: [Measuring Deliberation - Harvard](https://ash.harvard.edu/wp-content/uploads/2024/02/baechtiger_0.pdf)

### 0.2 Nostro Contributo: Deliberative Distance Index (DDI)

Il DDI è una **nuova proposta metodologica** che:
- Combina elementi di policy congruence e uptake measurement
- Aggiunge dimensione **temporale** (chi anticipa chi)
- Opera su **testi naturali** (non scale ideologiche predefinite)
- Usa **NLP/embeddings** per scalabilità
- È **multi-dimensionale** (topics, stance, salience)

**Differenza chiave**:
| Approccio esistente | DDI |
|---------------------|-----|
| Scale ideologiche fisse | Topic modeling dinamico |
| Survey-based | Text-based |
| Manuale/qualitativo | Automatizzato/scalabile |
| Singola dimensione | Multi-dimensionale |
| Snapshot | Temporale |

---

## 1. DATA SOURCES INVENTORY

### 1.1 Parliamentary Data

| Source | Coverage | Content | Access | Status |
|--------|----------|---------|--------|--------|
| **EUR-Lex EP Debates** | EU | Plenary transcripts, votes | API/SPARQL | ✅ Accessible |
| **EP Open Data Portal** | EU | MEP info, votes, amendments | API | ✅ Accessible |
| **Parlamento Italiano** | IT | Stenografici, DDL | Scraping | ⚠️ Requires work |
| **Congreso de los Diputados** | ES | Diario de Sesiones | Scraping | ⚠️ Requires work |
| **ParlaMint Corpus** | Multi-EU | Annotated parliamentary corpora | Download | ✅ Available |

**ParlaMint** è particolarmente interessante: corpus annotato di dibattiti parlamentari in 29 paesi, formato TEI-XML, già con POS tagging e named entities.

**ParlaMint Details** (da [CLARIN](https://www.clarin.eu/parlamint)):
- **Versione attuale**: 5.0 (2024)
- **Copertura**: 29 parlamenti europei
- **Volume**: ~500 milioni di parole
- **Formato**: TEI-XML con annotazioni UD (Universal Dependencies)
- **Metadati**: 11,000+ speaker con partito, genere, ruolo
- **Varianti**:
  - Plain text
  - Annotated (.ana) con NER, POS, lemmi
  - English MT version
- **Download**: [CLARIN.SI Repository](https://www.clarin.si/repository/xmlui/handle/11356/2004)
- **GitHub**: [clarin-eric/ParlaMint](https://github.com/clarin-eric/ParlaMint)

### 1.2 Public Consultation Data (Educated Citizens + Stakeholders)

| Source | Coverage | Content | Volume | Status |
|--------|----------|---------|--------|--------|
| **EU Have Your Say** | EU | Feedback consultazioni | 3M+ feedback | ✅ Abbiamo DB |
| **Consultazioni.gov.it** | IT | Consultazioni pubbliche | ~50k? | ⚠️ Da verificare |
| **Decidim Barcelona** | ES/CAT | Partecipazione locale | Variable | ⚠️ API available |

### 1.3 Social Media Data

| Source | Coverage | Content | Issues | Status |
|--------|----------|---------|--------|--------|
| **Twitter/X Institucional ES** | ES | 1.5M tweets istituzioni | Filtered by platform | 📁 Disponibile |
| **Twitter Academic API** | Global | Historical tweets | Costly, limited | ❌ Difficile |
| **Reddit** | Global | Subreddits EU politics | Self-selected users | ⚠️ Possibile |
| **Mastodon/Fediverse** | EU-focused | Public posts | Small but unfiltered | ⚠️ Interessante |

### 1.4 Institutional/Executive Data

| Source | Coverage | Content | Access | Status |
|--------|----------|---------|--------|--------|
| **EUR-Lex Legislation** | EU | Proposte EC, atti finali | API/SPARQL | ✅ Accessibile |
| **EC Press Releases** | EU | Comunicazioni ufficiali | Scraping | ⚠️ Fattibile |
| **BOE/Gazzetta Ufficiale** | ES/IT | Leggi e decreti | Scraping | ⚠️ Fattibile |

### 1.5 Argument Databases (External)

| Source | Content | Format | Access |
|--------|---------|--------|--------|
| **Kialo** | Structured debates | Tree structure | Export + Scraping |
| **args.me** | Argument search engine | API | ✅ Available |
| **IBM Debater Dataset** | Arguments + evidence | Download | ✅ Available |

**Kialo Details** (da ricerca):
- **Struttura**: Debate trees con pro/con sotto tesi principali
- **Export**: CSV nativo dalla piattaforma
- **Scraping**: Possibile con tool terzi:
  - [Kialo-Parser](https://github.com/edoguido/Kialo-Parser) - converte export in JSON strutturato
  - [Kialo-Scraper](https://github.com/AndreP-git/Kialo-Scraper) - scarica struttura completa
- **Limitazioni**: No API pubblica, no dati sui voti/impact
- **Uso in ricerca**: Dataset usato per training argument generation models
- **Nota**: Non ha dati politici EU specifici - utile solo come reference per struttura argomentativa

---

## 2. WHAT TO COMPARE: Beyond Semantic Similarity

### 2.1 Livelli di Confronto

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LIVELLI DI ANALISI COMPARATIVA                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LIVELLO 1: TOPICS (Cosa si discute)                                   │
│  ─────────────────────────────────────                                 │
│  • Topic modeling (LDA, BERTopic)                                      │
│  • Keyword extraction                                                   │
│  • Named Entity Recognition                                             │
│  → Metrica: Topic Overlap Score                                        │
│                                                                         │
│  LIVELLO 2: SALIENCE (Quanto è importante)                             │
│  ─────────────────────────────────────────                             │
│  • Topic prominence over time                                          │
│  • Agenda-setting analysis                                             │
│  • Attention allocation                                                │
│  → Metrica: Salience Divergence Index                                  │
│                                                                         │
│  LIVELLO 3: FRAMING (Come si presenta)                                 │
│  ────────────────────────────────────                                  │
│  • Frame detection (economic, moral, legal, etc.)                      │
│  • Metaphor analysis                                                   │
│  • Sentiment/emotion                                                   │
│  → Metrica: Frame Alignment Score                                      │
│                                                                         │
│  LIVELLO 4: STANCE/POSITION (Pro o contro)                             │
│  ─────────────────────────────────────────                             │
│  • Stance detection (favor/against/neutral)                            │
│  • Opinion mining                                                      │
│  • Polarization measures                                               │
│  → Metrica: Stance Congruence Index                                    │
│                                                                         │
│  LIVELLO 5: ARGUMENTS (Perché)                                         │
│  ────────────────────────────────                                      │
│  • Argument mining (claim + premise)                                   │
│  • Argumentation schemes                                               │
│  • Evidence types                                                      │
│  → Metrica: Argument Alignment Score                                   │
│                                                                         │
│  LIVELLO 6: ACTORS (Chi parla)                                         │
│  ───────────────────────────────                                       │
│  • Stakeholder mapping                                                 │
│  • Influence networks                                                  │
│  • Coalition detection                                                 │
│  → Metrica: Actor Representation Index                                 │
│                                                                         │
│  LIVELLO 7: TEMPORALITY (Quando)                                       │
│  ─────────────────────────────────                                     │
│  • Agenda dynamics                                                     │
│  • Lead-lag analysis (chi anticipa chi?)                               │
│  • Event detection                                                     │
│  → Metrica: Temporal Alignment Score                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Perché il Knowledge Graph Aggiunge Valore

Il punto di Victor è cruciale. Ecco dove il KG fa la differenza:

| Analisi | Solo NLP | Con Knowledge Graph |
|---------|----------|---------------------|
| **Chi parla di cosa** | Difficile linking | Relazioni esplicite Actor→Topic |
| **Evoluzione posizioni** | Embeddings temporali | Query SPARQL su timeline |
| **Cross-forum linking** | Nessuno | URI condivisi per entità |
| **Spiegabilità** | Black box | Tracciabile via ontologia |
| **Aggregazione** | Ad-hoc | Query strutturate |
| **Interoperabilità** | Nessuna | Linked Data standards |

**Esempio concreto**:
```sparql
# Con KG: "Chi ha parlato di AI regulation prima che diventasse mainstream in EP?"
SELECT ?actor ?date ?forum
WHERE {
  ?contribution del:hasTopic :AI_Regulation ;
                del:madeBy ?actor ;
                del:timestamp ?date ;
                del:partOf ?process .
  ?process del:takesPlaceIn ?forum .
  FILTER (?date < "2020-01-01"^^xsd:date)
}
ORDER BY ?date
```

Questo tipo di query è impossibile con solo NLP/embeddings.

---

## 3. PROPOSED METHODOLOGY

### 3.1 Multi-Forum Comparison Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                        DELIBERATIVE FORUM A                             │
│                     (e.g., EU Parliament)                               │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    KNOWLEDGE GRAPH                               │   │
│  │                                                                  │   │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐                 │   │
│  │   │ Topics   │────│ Stances  │────│ Arguments│                 │   │
│  │   └──────────┘    └──────────┘    └──────────┘                 │   │
│  │        │               │               │                        │   │
│  │        └───────────────┼───────────────┘                        │   │
│  │                        │                                        │   │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐                 │   │
│  │   │ Actors   │────│ Time     │────│ Forum    │                 │   │
│  │   └──────────┘    └──────────┘    └──────────┘                 │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ▲                                          │
│                              │                                          │
│                        DELIBERATIVE FORUM B                             │
│                     (e.g., Have Your Say)                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

                    COMPARISON METRICS
                    ──────────────────

    Topic Overlap    Salience Gap    Stance Congruence    Temporal Lag
         │               │                  │                  │
         └───────────────┴──────────────────┴──────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  DELIBERATIVE DISTANCE  │
                    │       INDEX (DDI)       │
                    └─────────────────────────┘
```

### 3.2 Deliberative Distance Index (DDI)

**Definizione formale**:

```
DDI(Forum_A, Forum_B) = Σ wᵢ × Distanceᵢ(A, B)

Dove:
  w₁ × TopicDistance        # Differenza nei temi trattati
+ w₂ × SalienceDistance     # Differenza nell'importanza data
+ w₃ × FrameDistance        # Differenza nel framing
+ w₄ × StanceDistance       # Differenza nelle posizioni
+ w₅ × ArgumentDistance     # Differenza nelle argomentazioni
+ w₆ × TemporalLag          # Ritardo temporale
```

I pesi wᵢ possono essere:
- Uniformi (baseline)
- Learned (da annotazioni gold standard)
- Domain-specific (diversi per policy area)

### 3.3 Componenti Metodologiche

#### A. Topic Analysis
- **Metodo**: BERTopic (meglio di LDA per testi brevi)
- **Output**: Topic distribution per documento
- **Confronto**: Jensen-Shannon divergence tra distribuzioni

#### B. Stance Detection
- **Metodo**: Fine-tuned BERT per stance (es. su SemEval dataset)
- **Output**: favor/against/neutral per topic
- **Confronto**: Agreement rate, Krippendorff's alpha

#### C. Argument Mining (se fattibile)
- **Metodo**:
  - Claim detection (classificatore binario)
  - Premise identification
  - Argumentation scheme classification
- **Output**: Claim-premise pairs con tipo
- **Confronto**: Argument overlap, scheme distribution

#### D. Actor Analysis
- **Metodo**: NER + linking a KG
- **Output**: Actor→Topic→Stance mapping
- **Confronto**: Who speaks for whom? Representation gaps

#### E. Temporal Analysis
- **Metodo**: Dynamic topic models, Granger causality
- **Output**: Lead-lag relationships
- **Confronto**: Chi anticipa le discussioni?

---

## 4. PAPER STRUCTURE PROPOSAL

### Titolo:
**"Measuring Deliberative Distance: A Multi-Forum Comparison of Legislative and Public Discourse in EU Policymaking"**

### Abstract (150 parole)
[Da scrivere]

### Struttura (stile simile a Di Porto, ~35-40 pagine):

1. **Introduction** (4 pp)
   - Gap between legislators and citizens
   - Why comparison matters for democracy
   - Research questions

2. **Background** (5 pp)
   - Deliberative democracy theory
   - Computational approaches to deliberation
   - Related work (Di Porto et al., etc.)

3. **Data Sources** (5 pp)
   - Parliamentary data
   - Public consultations (HYS)
   - [Optional: Social media, institutional]
   - Deliberation Knowledge Graph

4. **Methodology** (8 pp)
   - Multi-level comparison framework
   - Topic modeling (BERTopic)
   - Stance detection
   - [Optional: Argument mining]
   - Deliberative Distance Index

5. **Results** (10 pp)
   - Topic overlap analysis
   - Salience comparison
   - Stance congruence
   - Actor representation
   - Temporal dynamics
   - Case studies (AIA, DMA, DSA)

6. **Discussion** (5 pp)
   - How distant are legislators from citizens?
   - Role of stakeholders as intermediaries
   - Knowledge Graph advantages
   - Limitations

7. **Conclusions & Policy Implications** (3 pp)
   - Summary of findings
   - Recommendations for Better Regulation
   - Future work

---

## 5. WHAT MAKES THIS PAPER PUBLISHABLE IN AI & LAW

### 5.1 Contributo AI/Computational
- **Novel metric**: Deliberative Distance Index (multi-dimensional)
- **Method**: Multi-forum comparison framework
- **Tool**: Knowledge Graph-based analysis (vs pure NLP)
- **Scale**: 3M+ documents across forums

### 5.2 Contributo Law/Policy
- **Empirical**: First large-scale comparison EU Parliament ↔ HYS
- **Normative**: What should deliberative distance look like?
- **Practical**: Recommendations for consultation design

### 5.3 Differenziazione da Di Porto et al.
| Di Porto | Nostro paper |
|----------|--------------|
| Solo HYS | HYS + Parliament + [altri] |
| Similarity clustering | Multi-level comparison |
| Snapshot | Temporal dynamics |
| NLP only | Knowledge Graph |
| 830 docs | 3M+ docs |
| Descriptive | Distance metrics |

---

## 6. FEASIBILITY ASSESSMENT

### 6.1 Cosa abbiamo già
- ✅ HYS database completo (3M feedback)
- ✅ Pipeline export/RDF funzionante
- ✅ Deliberation Ontology
- ✅ Script EUR-Lex linking

### 6.2 Cosa serve implementare

| Componente | Effort | Priority |
|------------|--------|----------|
| EP debates download | Medio | Alta |
| BERTopic pipeline | Basso | Alta |
| Stance detection | Medio | Media |
| Argument mining | Alto | Bassa (opzionale) |
| DDI calculation | Medio | Alta |
| Temporal analysis | Medio | Media |

### 6.3 Scelte strategiche

**Opzione A: Paper Focused (fattibile in 4-6 mesi)**
- Solo HYS vs EP debates
- Topic + Salience + Actor analysis
- No argument mining (troppo complesso)
- DDI semplificato

**Opzione B: Paper Ambitious (6-12 mesi)**
- HYS + EP + Executive data
- Full multi-level analysis
- Basic argument mining
- DDI completo

**Raccomandazione**: Iniziare con Opzione A, estendere se tempo/risorse permettono.

---

## 7. IMMEDIATE NEXT STEPS

1. **Decidere scope**: Opzione A o B?
2. **Acquisire EP debates**: ParlaMint o EUR-Lex?
3. **Pilot study**:
   - Selezionare 3 dossier (AIA, DMA, DSA)
   - Applicare BERTopic a entrambi i corpora
   - Calcolare topic overlap preliminare
4. **Validare DDI**: Test su caso noto per verificare sensatezza

---

## 8. OPEN QUESTIONS

1. **Social media**: Includerli o no? (Pro: completezza; Contro: bias piattaforma)
2. **Argument mining**: È realistico? (Pro: differenziazione; Contro: effort alto)
3. **Causalità**: Possiamo dire qualcosa su chi influenza chi?
4. **Multilingua**: Come gestire 24 lingue EU?
5. **Ground truth**: Come validare DDI senza gold standard?

---

## Appendice: Ontology Extensions Needed

Per supportare comparison cross-forum, la Deliberation Ontology potrebbe aver bisogno di:

```turtle
# Nuove proprietà per comparison
del:discussesSameTopic rdfs:domain del:DeliberationProcess ;
                       rdfs:range del:DeliberationProcess .

del:temporallyRelatedTo rdfs:domain del:Contribution ;
                        rdfs:range del:Contribution .

del:hasStance rdfs:domain del:Contribution ;
              rdfs:range del:Stance .

# Nuove classi
del:Stance a owl:Class ;
    rdfs:comment "Position (favor/against/neutral) on a topic" .

del:Claim a owl:Class ;
    rdfs:subClassOf del:Contribution ;
    rdfs:comment "An assertion that can be supported or attacked" .
```

Queste estensioni permetterebbero query SPARQL come:
```sparql
# Trova contributi che hanno stance opposta sullo stesso topic
SELECT ?contrib_a ?contrib_b ?topic
WHERE {
  ?contrib_a del:hasTopic ?topic ; del:hasStance del:Favor .
  ?contrib_b del:hasTopic ?topic ; del:hasStance del:Against .
  ?contrib_a del:partOf ?process_a .
  ?contrib_b del:partOf ?process_b .
  FILTER (?process_a != ?process_b)  # Forum diversi
}
```
