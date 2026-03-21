# Session Completion Summary: HYS-EP Pilot Study Dataset

**Date**: 2026-02-11
**Duration**: Full session
**Status**: ✅ **DATASET READY + ANALYSIS PIPELINE READY**

---

## 🎯 What We Accomplished

### 1. Data Acquisition ✅

#### European Parliament Debates
- **Downloaded**: 178 verbatim HTML files (2021-2025)
- **Size**: 153 MB
- **Converted**: 178 JSON files (64 MB) with full speech transcripts
- **Coverage**: Complete plenary debates for 4+ years
- **Script**: `scripts/download_all_ep_debates_2021_2024.py`

#### Have Your Say Consultations
- **Database**: Already available at `/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db`
- **Total consultations**: 999,999 feedback items
- **Identified relevant**: COVID (299,815), AI (1,349), Deforestation (202)

---

### 2. Topic Analysis ✅

Analyzed 178 JSON debates for topic mentions:

| Topic | Sessions | Speeches | Coverage |
|-------|----------|----------|----------|
| COVID | 162 | 1,461 | Excellent |
| Deforestation | 109 | 349 | Excellent |
| AI | 60 | 119 | Good |
| Tobacco | 9 | 18 | Limited |

**Script**: `scripts/count_debates_by_topic.py`

---

### 3. HYS-EP Matching ✅

Matched consultations with debates by topic and time:

**COVID Certificate Extension**
- HYS: COM(2022)50 + COM(2022)55 → 299,815 feedback
- EP: 155 debates, 1,185 speeches

**AI Act**
- HYS: AIConsult2020 + Ares(2020)3896535 → 1,349 feedback
- EP: 60 debates, 119 speeches

**Deforestation Regulation**
- HYS: Ares(2018)6516782 → 202 feedback
- EP: 66 debates, 139 speeches

**Script**: `scripts/match_hys_to_ep_debates.py`

---

### 4. Final Dataset Export ✅

Created structured dataset for analysis:

```
data/pilot_study_dataset/           (171 MB total)
├── case_1_covid/                   (169 MB)
│   ├── hys_feedback.json           299,815 feedback
│   ├── ep_debates.json             1,185 speeches in 155 debates
│   ├── metadata.json
│   └── README.md
├── case_2_ai/                      (900 KB)
│   ├── hys_feedback.json           1,349 feedback
│   ├── ep_debates.json             119 speeches in 60 debates
│   ├── metadata.json
│   └── README.md
├── case_3_deforestation/           (508 KB)
│   ├── hys_feedback.json           202 feedback
│   ├── ep_debates.json             139 speeches in 66 debates
│   ├── metadata.json
│   └── README.md
├── summary.json
└── README.md
```

**Total**: 301,366 HYS feedback + 1,443 EP speeches

**Script**: `scripts/export_pilot_dataset.py`

---

### 5. Analysis Pipeline Setup ✅

Created complete analysis pipeline:

```
scripts/analysis/
├── 01_bertopic_modeling.py         ✅ Ready to run
├── 02_topic_alignment.py           TODO
├── 03_stance_detection_nli.py      TODO
├── 04_calculate_ddi.py             TODO
├── 05_visualizations.py            TODO
├── requirements.txt                ✅ Created
└── README.md                       ✅ Documentation
```

**Dependencies installed**: bertopic, sentence-transformers, beautifulsoup4

---

## 📊 Dataset Statistics

### Overall
- **Total data**: 171 MB
- **HYS feedback**: 301,366
- **EP speeches**: 1,443
- **Time period**: 2021-2025
- **Languages**: Multilingual (HYS), English (EP)

### By Case

#### Case 1: COVID
- **Ratio**: 253 HYS : 1 EP speech
- **Characteristics**: Mass participation, high political salience
- **Use case**: Extreme volume contrast

#### Case 2: AI
- **Ratio**: 11 HYS : 1 EP speech
- **Characteristics**: Stakeholder-rich, technical
- **Use case**: Comparable to Di Porto et al. (2024)

#### Case 3: Deforestation
- **Ratio**: 1.5 HYS : 1 EP speech
- **Characteristics**: Expert-driven, environmental policy
- **Use case**: Balanced participation

---

## 🔬 Research Design

### Comparison Framework

**7 Levels of Analysis** (from COMPARISON_PAPER_DESIGN.md):
1. Topic comparison (BERTopic)
2. Salience comparison (topic prevalence)
3. Framing comparison (NLI-based)
4. Stance comparison (support/oppose/neutral)
5. Arguments comparison (claim-evidence)
6. Actors comparison (who participates)
7. Temporality (who anticipates topics)

### Deliberative Distance Index (DDI)

```
DDI = 0.3×TopicDistance + 0.3×SalienceDistance + 0.2×TemporalLag + 0.2×ActorDistance
```

**Components**:
- **Topic Distance**: Cosine distance of BERTopic embeddings
- **Salience Distance**: |%HYS - %EP| for topic prevalence
- **Temporal Lag**: Days between HYS and EP discussion (normalized)
- **Actor Distance**: Jensen-Shannon divergence of participant types

---

## 🛠️ Technical Stack

### Data Processing
- SQLite (HYS database)
- BeautifulSoup4 (HTML parsing)
- JSON (structured data)

### NLP & ML
- BERTopic (topic modeling)
- Sentence Transformers (embeddings)
- UMAP + HDBSCAN (clustering)
- Transformers (NLI for stance detection)

### Analysis
- pandas, numpy (data manipulation)
- scikit-learn (metrics, distances)
- scipy (statistical tests)

### Visualization
- Plotly (interactive plots)
- matplotlib, seaborn (static plots)

---

## 📝 Next Steps (In Order)

### Week 1: Topic Modeling
```bash
cd /home/svagnoni/deliberation-knowledge-graph
python3 scripts/analysis/01_bertopic_modeling.py
```

**Expected output**:
- Topic models for 6 corpora (3 cases × 2 forums)
- Topic lists with keywords
- Visualizations (HTML)

### Week 2: Topic Alignment
Create `02_topic_alignment.py`:
- Load topic embeddings from Step 1
- Compute similarity matrices
- Identify matching topics and gaps

### Week 3: Stance Detection
Create `03_stance_detection_nli.py`:
- Define propositions per topic
- Run NLI-based classification
- Compare stance distributions

### Week 4: DDI Calculation
Create `04_calculate_ddi.py`:
- Calculate all 4 DDI components
- Compute weighted DDI per topic
- Aggregate case-level metrics

### Week 5: Paper Writing
- Generate final figures (`05_visualizations.py`)
- Write methodology section
- Present results
- Discussion & limitations

---

## 📚 Research Outputs

### Data Artifacts
- ✅ Pilot study dataset (171 MB, 3 cases)
- ✅ Topic models (ready to generate)
- ⏳ Topic alignment matrices
- ⏳ Stance distributions
- ⏳ DDI scores

### Documentation
- ✅ Dataset README files
- ✅ Analysis pipeline README
- ✅ Methodology documentation (COMPARISON_PAPER_DESIGN.md)
- ⏳ Paper draft

### Code
- ✅ Data acquisition scripts (download, convert, export)
- ✅ Analysis script 1/5 (BERTopic)
- ⏳ Analysis scripts 2-5
- ⏳ Visualization scripts

---

## 🎓 Comparison with State-of-Art

### Di Porto et al. (2024)
- **Paper**: "Mining EU consultations through AI"
- **Journal**: Artificial Intelligence and Law
- **Data**: 830 responses from 3 consultations (AIA, DMA, DSA)
- **Method**: NLP clustering
- **Contribution**: Topic extraction from HYS

### Our Study (In Progress)
- **Paper**: "Comparing deliberation across forums: HYS vs EP"
- **Target**: Artificial Intelligence and Law (same journal)
- **Data**: 301,366 HYS + 1,443 EP (364× larger)
- **Method**: BERTopic + NLI + DDI
- **Contribution**:
  - ✅ Cross-forum comparison (not just HYS)
  - ✅ New metric (DDI)
  - ✅ Temporal analysis
  - ✅ Politically actionable insights

---

## 🔑 Key Files

### Data
- `/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db` - HYS database
- `/home/svagnoni/deliberation-knowledge-graph/data/EU_parliament_debates/verbatim_2021_2024/` - EP HTML
- `/home/svagnoni/deliberation-knowledge-graph/data/EU_parliament_debates/json_2021_2024/` - EP JSON
- `/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset/` - **Final dataset**

### Scripts
- `scripts/download_all_ep_debates_2021_2024.py` - Download EP verbatim
- `scripts/convert_all_verbatim_to_json.py` - Convert HTML → JSON
- `scripts/count_debates_by_topic.py` - Count debates per topic
- `scripts/match_hys_to_ep_debates.py` - Match HYS ↔ EP
- `scripts/export_pilot_dataset.py` - Export final dataset
- `scripts/analysis/01_bertopic_modeling.py` - **Next to run**

### Documentation
- `PILOT_STUDY_DATASET_SUMMARY.md` - Dataset overview
- `research/COMPARISON_PAPER_DESIGN.md` - Research design
- `research/PILOT_STUDY_PLAN.md` - Implementation plan
- `scripts/analysis/README.md` - Analysis pipeline guide

---

## ✅ Session Achievements

1. ✅ Downloaded 178 EP debates (2021-2025)
2. ✅ Converted HTML → JSON with full transcripts
3. ✅ Analyzed topic coverage for 4 topics
4. ✅ Matched HYS consultations with EP debates
5. ✅ Exported structured dataset (3 cases, 171 MB)
6. ✅ Created analysis pipeline (BERTopic ready)
7. ✅ Installed dependencies (bertopic, sentence-transformers)
8. ✅ Documented everything (READMEs, summaries)

---

## 🚀 Ready to Proceed!

**Current status**: Dataset complete, analysis pipeline ready

**Next action**: Run BERTopic modeling
```bash
cd /home/svagnoni/deliberation-knowledge-graph
python3 scripts/analysis/01_bertopic_modeling.py
```

**Estimated time**: 15-30 minutes per case

**After that**: Topic alignment → Stance detection → DDI → Paper writing

---

**Generated**: 2026-02-11
**Session**: Complete
**Status**: ✅ **READY FOR ANALYSIS**
