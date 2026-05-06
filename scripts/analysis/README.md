# Pilot Study Analysis Scripts

Pipeline for analyzing HYS-EP deliberation comparison across 3 cases.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Or use system packages
pip3 install bertopic sentence-transformers umap-learn hdbscan transformers torch --break-system-packages
```

## Pipeline

### Step 1: Topic Modeling (BERTopic)

```bash
python3 01_bertopic_modeling.py
```

**What it does**:
- Loads HYS feedback and EP speeches for 3 cases
- Runs BERTopic separately on HYS and EP
- Extracts topics, keywords, representative documents
- Generates visualizations (topic maps, barcharts)

**Output**:
- `data/analysis_results/models/{case}_hys_model/` - Trained BERTopic models
- `data/analysis_results/models/{case}_ep_model/`
- `data/analysis_results/results/{case}_topics.json` - Topic info per case
- `data/analysis_results/results/visualizations/` - HTML plots

**Time estimate**: 10-30 min per case (depends on dataset size)

---

### Step 2: Topic Alignment (TODO)

```bash
python3 02_topic_alignment.py
```

**What it does**:
- Loads topic embeddings from Step 1
- Computes cosine similarity between HYS and EP topics
- Creates alignment matrix (which HYS topics match which EP topics)
- Identifies gaps (topics only in HYS or only in EP)

**Output**:
- `data/analysis_results/results/{case}_topic_alignment.json`
- Similarity matrices
- Gap analysis

---

### Step 3: Stance Detection (TODO)

```bash
python3 03_stance_detection_nli.py
```

**What it does**:
- Uses NLI model (BART-MNLI) for zero-shot stance detection
- For each topic, defines propositions
- Classifies each HYS feedback and EP speech as support/oppose/neutral
- Compares stance distributions across forums

**Output**:
- `data/analysis_results/results/{case}_stances.json`
- Stance distributions per topic

---

### Step 4: DDI Calculation (TODO)

```bash
python3 04_calculate_ddi.py
```

**What it does**:
- Calculates Deliberative Distance Index components:
  - Topic Distance (cosine distance of embeddings)
  - Salience Distance (topic prevalence difference)
  - Temporal Lag (time between HYS and EP discussion)
  - Actor Distance (participant type distribution)
- Computes weighted DDI score

**Output**:
- `data/analysis_results/results/{case}_ddi.json`
- DDI scores per topic and overall

---

### Step 5: Visualizations (TODO)

```bash
python3 05_visualizations.py
```

**What it does**:
- Creates publication-ready figures for paper
- Topic alignment heatmaps
- Stance distribution charts
- DDI spider plots
- Temporal evolution graphs

**Output**:
- `data/analysis_results/figures/` - PNG/PDF plots for paper

---

## Current Status

- [x] Step 1: BERTopic modeling (script ready)
- [ ] Step 2: Topic alignment
- [ ] Step 3: Stance detection
- [ ] Step 4: DDI calculation
- [ ] Step 5: Visualizations

## Data Flow

```
pilot_study_dataset/
  └─> 01_bertopic_modeling.py
        └─> analysis_results/models/
        └─> analysis_results/results/{case}_topics.json
              └─> 02_topic_alignment.py
                    └─> results/{case}_topic_alignment.json
                          └─> 03_stance_detection_nli.py
                                └─> results/{case}_stances.json
                                      └─> 04_calculate_ddi.py
                                            └─> results/{case}_ddi.json
                                                  └─> 05_visualizations.py
                                                        └─> figures/
```

## Notes

- BERTopic uses multilingual sentence transformers for HYS (mixed languages)
- EP speeches are mostly English
- Min topic size = 10 (adjustable based on dataset size)
- Visualizations are interactive HTML (Plotly)

## Next Steps After Pipeline

1. Review topic quality (manual inspection)
2. Refine propositions for stance detection
3. Validate DDI weights (sensitivity analysis)
4. Write paper sections:
   - Methodology
   - Results
   - Discussion

## References

- BERTopic: https://maartengr.github.io/BERTopic/
- Sentence Transformers: https://www.sbert.net/
- NLI for stance: Yin & Roth (2018)
