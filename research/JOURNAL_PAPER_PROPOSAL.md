# Proposta Paper: Beyond Opinion Clustering - Tracing Deliberative Impact from Public Consultations to EU Legislation

## 1. Posizionamento rispetto a Di Porto et al. (2024)

### Cosa fa il paper esistente:
- Dataset: 830 risposte a 3 consultazioni (AIA, DMA, DSA)
- Metodo: NLP lessicale/semantico (unigrams, n-grams, Ruzicka, Jaccard, SBERT)
- Obiettivo: Verificare accuratezza clustering opinioni EC
- Contributo: Evidenzia misclustering (PMI ≠ grandi imprese, cittadini ≠ consumer orgs)

### Gap identificati:
1. **Scala limitata**: 830 documenti vs nostri ~3M feedback
2. **Snapshot statico**: Nessuna analisi temporale/longitudinale
3. **Nessun impact tracing**: Non collegano consultazioni → legislazione finale
4. **Nessun link istituzionale**: HYS isolato da EP e atti finali
5. **Solo similarity**: Non analizzano claim/argomentazioni specifiche
6. **No Knowledge Graph**: Dati non strutturati semanticamente

---

## 2. Proposta: "Deliberative Impact Tracing"

### Titolo provvisorio:
**"From Consultation to Legislation: Tracing the Deliberative Impact of Public Participation in EU Rulemaking through Knowledge Graphs and NLP"**

### Research Questions:

**RQ1 (Rappresentatività estesa)**: Come varia la rappresentatività delle consultazioni HYS su scala massiva (3M+ feedback, 4700+ iniziative) e nel tempo (2016-2025)?

**RQ2 (Deliberative Traceability)**: In che misura i temi, claim e argomentazioni emersi nelle consultazioni HYS sono rintracciabili nei:
- (a) dibattiti del Parlamento Europeo
- (b) testi legislativi finali (direttive, regolamenti)

**RQ3 (Differential Impact)**: Quali categorie di stakeholder (cittadini, PMI, grandi imprese, NGO, etc.) mostrano maggiore "impatto deliberativo" sul testo finale? Esistono bias sistematici?

**RQ4 (Knowledge Graph Utility)**: Un approccio basato su Knowledge Graph semantico migliora la tracciabilità rispetto a metodi puramente NLP?

---

## 3. Contributi Scientifici (Beyond State of Art)

### 3.1 Contributo Metodologico
| Aspetto | Di Porto et al. | Nostra proposta |
|---------|-----------------|-----------------|
| Scala | 830 docs, 3 consultazioni | 3M+ feedback, 4700+ iniziative |
| Periodo | Snapshot singolo | Longitudinale 2016-2025 |
| Linking | Nessuno | HYS → CELEX → EP debates |
| Rappresentazione | Bag-of-words/embeddings | Knowledge Graph semantico |
| Ontologia | Nessuna | Deliberation Ontology formale |
| Impact measure | Solo similarity clustering | Traceability score, causal inference |

### 3.2 Contributo Empirico
- Prima analisi su **scala completa** del dataset HYS
- Primo **linking sistematico** HYS → atti legislativi via Ares→CELEX
- Prima **analisi longitudinale** (9 anni) delle consultazioni EU
- Quantificazione del **differential impact** per categoria stakeholder

### 3.3 Contributo Teorico
- Framework **"Deliberative Traceability"**: metodologia replicabile
- Operazionalizzazione concetto di **"deliberative impact"**
- Test empirico teoria della **"corporate capture"** delle consultazioni

### 3.4 Contributo Policy
- Raccomandazioni evidence-based per migliorare Better Regulation Toolbox
- Identificazione bias sistematici nel processo consultivo EU
- Proposta di metriche automatiche per monitoraggio rappresentatività

---

## 4. Metodologia Proposta

### 4.1 Dataset

**A. EU Have Your Say (completo)**
- 4,744 iniziative (o ~3,835 nel DB disponibile)
- ~3 milioni di feedback
- Metadati: paese, user_type, organizzazione, Ares reference
- Periodo: 2016-2025

**B. EUR-Lex Legislative Acts**
- Proposte legislative (CELEX 5xxxx)
- Atti finali (CELEX 3xxxx)
- Testi strutturati: articoli, consideranda, emendamenti

**C. EP Debates**
- Trascrizioni dibattiti plenari
- Interventi per relatore/gruppo politico
- Link a dossier legislativi

**D. Deliberation Knowledge Graph**
- Ontologia formale (Deliberation Ontology v1.0)
- Entità: DeliberationProcess, Contribution, Participant, LegalSource
- Relazioni: hasContribution, references, isInformedBy

### 4.2 Pipeline Metodologica

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DELIBERATIVE IMPACT TRACING PIPELINE                  │
└─────────────────────────────────────────────────────────────────────────┘

FASE 1: DATA INTEGRATION
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  HYS DB     │───▶│  CSV Export │───▶│  RDF/KG     │
│  (3M+ fb)   │    │  + cleaning │    │  Integration│
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                         ┌──────────────────┼──────────────────┐
                         ▼                  ▼                  ▼
                   ┌──────────┐      ┌──────────┐      ┌──────────┐
                   │ Ares→    │      │ CELEX    │      │ EP       │
                   │ CELEX    │      │ Acts     │      │ Debates  │
                   │ Linking  │      │ Download │      │ Download │
                   └──────────┘      └──────────┘      └──────────┘
                         │                  │                  │
                         └──────────────────┼──────────────────┘
                                            ▼
                                   ┌─────────────────┐
                                   │  KNOWLEDGE      │
                                   │  GRAPH (DKG)    │
                                   └─────────────────┘

FASE 2: ANALYSIS
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │
│  │ REPRESENTAT.  │  │ TOPIC         │  │ ARGUMENT      │              │
│  │ ANALYSIS      │  │ MODELING      │  │ MINING        │              │
│  │               │  │               │  │               │              │
│  │ • Geographic  │  │ • LDA/BERTopic│  │ • Claim       │              │
│  │ • User type   │  │ • Temporal    │  │   extraction  │              │
│  │ • Gini coeff  │  │   evolution   │  │ • Stance      │              │
│  │ • Concentrat. │  │ • Cross-corpus│  │   detection   │              │
│  └───────────────┘  └───────────────┘  └───────────────┘              │
│         │                  │                  │                        │
│         └──────────────────┼──────────────────┘                        │
│                            ▼                                           │
│                   ┌─────────────────┐                                  │
│                   │ DELIBERATIVE    │                                  │
│                   │ IMPACT SCORING  │                                  │
│                   │                 │                                  │
│                   │ • Embedding     │                                  │
│                   │   similarity    │                                  │
│                   │ • Claim match   │                                  │
│                   │ • Topic overlap │                                  │
│                   └─────────────────┘                                  │
│                            │                                           │
│         ┌──────────────────┼──────────────────┐                        │
│         ▼                  ▼                  ▼                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │
│  │ HYS → EP      │  │ HYS → Act     │  │ DIFFERENTIAL  │              │
│  │ Traceability  │  │ Traceability  │  │ IMPACT        │              │
│  │ Score         │  │ Score         │  │ by Stakeholder│              │
│  └───────────────┘  └───────────────┘  └───────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

FASE 3: VALIDATION & OUTPUT
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │
│  │ CASE STUDIES  │  │ STATISTICAL   │  │ POLICY        │              │
│  │               │  │ VALIDATION    │  │ RECOMMENDATIONS│              │
│  │ • AIA         │  │               │  │               │              │
│  │ • DMA         │  │ • Regression  │  │ • Better Reg  │              │
│  │ • DSA         │  │ • Causal inf. │  │   Toolbox     │              │
│  │ • Green Deal  │  │ • Robustness  │  │ • Transparency│              │
│  └───────────────┘  └───────────────┘  └───────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Metriche Proposte

#### A. Representativity Metrics (estensione Di Porto)
- **Geographic Gini**: Concentrazione geografica feedback
- **Stakeholder Gini**: Concentrazione per tipo attore
- **Temporal Coverage**: Distribuzione feedback nel periodo consultazione
- **Response Rate**: % iniziative con feedback significativo

#### B. Deliberative Traceability Score (NUOVO)
```
DTS(feedback_i, act_j) = α * semantic_sim(emb_i, emb_j)
                        + β * topic_overlap(topics_i, topics_j)
                        + γ * claim_match(claims_i, text_j)
```

Dove:
- `semantic_sim`: Cosine similarity embeddings (SBERT/E5)
- `topic_overlap`: Jaccard sui topic BERTopic
- `claim_match`: Match claim estratti vs articoli/consideranda

#### C. Differential Impact Index (NUOVO)
```
DII(stakeholder_type) = mean(DTS) per tipo stakeholder
                        normalizzato per volume feedback
```

Permette di testare:
- Ipotesi "corporate capture": DII(large_companies) >> DII(citizens)?
- Bias geografici: DII(DEU) >> DII(altri)?
- Effetto organizzazione: DII(org) >> DII(individual)?

#### D. Knowledge Graph Advantage Score (NUOVO)
Confronto performance:
- Metodo KG-based (ontologia + SPARQL + reasoning)
- Metodo NLP-only (embeddings + clustering)
- Metodo Di Porto (Ruzicka + Jaccard + TF-IDF)

---

## 5. Esperimenti Proposti

### Esperimento 1: Representativity at Scale
**Obiettivo**: Replicare e estendere analisi Di Porto su scala massiva

**Metodo**:
1. Applicare metriche Di Porto (Ruzicka, Jaccard) su intero dataset HYS
2. Calcolare Gini coefficient per paese/user_type/organizzazione
3. Analisi temporale: come cambia rappresentatività 2016→2025?

**Output**:
- Tabelle rappresentatività per anno/tipo consultazione
- Heatmap similarity stakeholder (replica Di Porto su 3M feedback)
- Trend temporali

### Esperimento 2: HYS → EP Debate Traceability
**Obiettivo**: Misurare quanto i temi HYS appaiono nei dibattiti EP

**Metodo**:
1. Per ogni iniziativa HYS collegata a CELEX:
   - Estrarre topic/claim dai feedback
   - Scaricare dibattiti EP correlati
   - Calcolare topic overlap e semantic similarity
2. Aggregare per tipo stakeholder

**Output**:
- Traceability score HYS→EP per dossier
- Differential impact per stakeholder type
- Case studies: AIA, DMA, DSA, Green Deal

### Esperimento 3: HYS → Legislative Text Traceability
**Obiettivo**: Misurare quanto i feedback influenzano il testo finale

**Metodo**:
1. Per ogni iniziativa HYS con atto finale (CELEX 3xxxx):
   - Segmentare testo in articoli/consideranda
   - Calcolare similarity con feedback
   - Identificare claim "tracciabili" nel testo
2. Confrontare proposta iniziale vs testo finale

**Output**:
- Traceability score HYS→Act per dossier
- % claim HYS rintracciabili nel testo
- Differential impact per stakeholder

### Esperimento 4: Knowledge Graph vs NLP Comparison
**Obiettivo**: Valutare valore aggiunto del KG approach

**Metodo**:
1. Implementare tre pipeline:
   - KG-based (DKG + SPARQL + reasoning)
   - NLP-only (embeddings + BERTopic)
   - Di Porto method (Ruzicka + Jaccard)
2. Confrontare su metriche comuni
3. Valutare interpretabilità/spiegabilità

**Output**:
- Benchmark comparativo
- Analisi qualitativa interpretabilità
- Raccomandazioni metodologiche

### Esperimento 5: Causal Inference (avanzato)
**Obiettivo**: Stimare effetto causale consultazioni su legislazione

**Metodo**:
1. Design quasi-sperimentale:
   - Trattamento: iniziative con alta partecipazione HYS
   - Controllo: iniziative con bassa partecipazione
   - Outcome: modifiche proposta→atto finale
2. Matching su confounders (DG, tipo atto, periodo)
3. Difference-in-differences o regression discontinuity

**Output**:
- Stima effetto causale consultazione
- Heterogeneous effects per stakeholder type
- Policy implications

---

## 6. Timeline e Risorse

### Fase 1: Data Preparation (mesi 1-2)
- [x] Export completo HYS
- [x] Conversione RDF
- [ ] Linking Ares→CELEX (richiede tempo per rate limiting)
- [ ] Download atti legislativi
- [ ] Download dibattiti EP

### Fase 2: Analysis Implementation (mesi 3-4)
- [ ] Esperimento 1: Representativity at Scale
- [ ] Esperimento 2: HYS→EP Traceability
- [ ] Esperimento 3: HYS→Act Traceability

### Fase 3: Advanced Analysis (mesi 5-6)
- [ ] Esperimento 4: KG vs NLP Comparison
- [ ] Esperimento 5: Causal Inference (se fattibile)
- [ ] Validazione e robustness checks

### Fase 4: Writing (mesi 7-8)
- [ ] Draft paper
- [ ] Revisione
- [ ] Submission

### Risorse necessarie
- **Compute**: GPU per embeddings (SBERT/E5 su 3M testi)
- **Storage**: ~50GB per dati + embeddings
- **API access**: EUR-Lex (rate limiting da gestire)
- **Expertise**: NLP, KG, policy analysis

---

## 7. Target Journals

### Opzione 1: Artificial Intelligence and Law (Springer)
- **Pro**: Stesso journal di Di Porto, direct comparison
- **Contro**: Audience limitata

### Opzione 2: Journal of European Public Policy
- **Pro**: High impact, policy-relevant audience
- **Contro**: Meno focus su AI/NLP

### Opzione 3: Government Information Quarterly
- **Pro**: Buon fit per e-participation, high impact
- **Contro**: Review process lungo

### Opzione 4: PLOS ONE / Nature Scientific Reports
- **Pro**: Open access, ampia diffusione
- **Contro**: Meno prestigioso per law/policy

### Raccomandazione:
**Artificial Intelligence and Law** come prima scelta (direct engagement con Di Porto), con **Government Information Quarterly** come backup.

---

## 8. Impatto Atteso

### Scientifico
- Prima analisi su scala completa HYS
- Framework replicabile "Deliberative Traceability"
- Contributo metodologico KG + NLP

### Policy
- Evidence-based input per Better Regulation Toolbox
- Identificazione bias sistematici
- Raccomandazioni per EC su clustering e reporting

### Sociale
- Trasparenza processo legislativo EU
- Empowerment cittadini e società civile
- Accountability delle istituzioni

---

## 9. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Linking Ares→CELEX incompleto | Alta | Medio | Focus su subset major initiatives |
| Dibattiti EP non disponibili | Media | Alto | Usare solo atti finali per RQ2-3 |
| Causal inference non fattibile | Alta | Medio | Focus su correlational analysis |
| Confronto KG vs NLP non significativo | Media | Medio | Documentare comunque |
| Tempo/risorse insufficienti | Media | Alto | Prioritizzare Esp. 1-3 |

---

## 10. Next Steps Immediati

1. **Completare linking Ares→CELEX** per campione significativo (top 500 iniziative)
2. **Scaricare atti legislativi** corrispondenti
3. **Implementare BERTopic** per topic modeling
4. **Calcolare embedding similarity** HYS→Acts
5. **Produrre prime statistiche descrittive** per validare approccio

---

## Appendice: Differenze chiave vs Di Porto et al.

| Dimensione | Di Porto et al. (2024) | Nostra proposta |
|------------|------------------------|-----------------|
| **Scala** | 830 documenti | 3,000,000+ feedback |
| **Consultazioni** | 3 (AIA, DMA, DSA) | 4,700+ iniziative |
| **Periodo** | Snapshot | 2016-2025 longitudinale |
| **Linking** | Nessuno | HYS→CELEX→EP |
| **Impact measure** | Similarity clustering | Traceability score |
| **Causal claim** | Nessuno | Quasi-experimental |
| **KG** | No | Deliberation Ontology |
| **Replicabilità** | Limitata | Pipeline open source |
| **Policy output** | Generico | Specific Better Reg recommendations |

Questo posizionamento garantisce **novelty** rispetto allo stato dell'arte e **policy relevance** per le istituzioni EU.
