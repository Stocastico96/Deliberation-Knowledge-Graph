# Pilot Study Dataset: HYS-EP Deliberation Comparison

## 📊 Dataset Summary

**Created**: 2026-02-11
**Location**: `/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset/`
**Total Size**: 171 MB
**Period**: 2021-2025

---

## 🎯 Three Cases

### Case 1: COVID Certificate Extension
- **HYS Feedback**: 299,815
- **EP Speeches**: 1,185 (in 155 debates)
- **Size**: 169 MB
- **References**: COM(2022)50, COM(2022)55
- **Topic**: Health policy, emergency measures, digital certificates

### Case 2: Artificial Intelligence Act
- **HYS Feedback**: 1,349
- **EP Speeches**: 119 (in 60 debates)
- **Size**: 900 KB
- **References**: AIConsult2020, Ares(2020)3896535
- **Topic**: Technology regulation, AI ethics, innovation

### Case 3: Deforestation Regulation
- **HYS Feedback**: 202
- **EP Speeches**: 139 (in 66 debates)
- **Size**: 508 KB
- **References**: Ares(2018)6516782
- **Topic**: Environmental policy, supply chains, due diligence

---

## 📁 Dataset Structure

```
pilot_study_dataset/
├── case_1_covid/
│   ├── hys_feedback.json        (299,815 feedback)
│   ├── ep_debates.json          (155 debates, 1,185 speeches)
│   ├── metadata.json
│   └── README.md
├── case_2_ai/
│   ├── hys_feedback.json        (1,349 feedback)
│   ├── ep_debates.json          (60 debates, 119 speeches)
│   ├── metadata.json
│   └── README.md
├── case_3_deforestation/
│   ├── hys_feedback.json        (202 feedback)
│   ├── ep_debates.json          (66 debates, 139 speeches)
│   ├── metadata.json
│   └── README.md
├── summary.json
└── README.md
```

---

## 📈 Comparison Matrix

| Metric | COVID | AI | Deforestation |
|--------|-------|----|--------------|
| **HYS Feedback** | 299,815 | 1,349 | 202 |
| **EP Debates** | 155 | 60 | 66 |
| **EP Speeches** | 1,185 | 119 | 139 |
| **Ratio (HYS/EP)** | 253:1 | 11:1 | 1.5:1 |
| **Participation** | Mass | Stakeholder | Expert |
| **Salience** | Very High | High | Medium |

---

## 🔬 Research Questions Enabled

### 1. Topic Comparison (RQ1)
- Do HYS and EP discuss the same topics?
- **Method**: BERTopic on both corpora, topic alignment analysis

### 2. Stance Comparison (RQ2)
- Do citizens and legislators hold similar positions?
- **Method**: Stance detection, argument mining, DDI calculation

### 3. Actor Comparison (RQ3)
- Who participates in HYS vs EP?
- **Method**: Actor analysis (HYS user types vs EP speakers)

### 4. Temporal Analysis (RQ4)
- Who anticipates topics? HYS → EP or EP → HYS?
- **Method**: Temporal topic tracking, lag analysis

---

## 🛠️ Next Steps for Analysis

### Phase 1: Data Preparation
- [x] Extract HYS feedback
- [x] Extract EP debates
- [x] Match by topic and time
- [ ] Preprocess text (cleaning, language detection)
- [ ] Generate embeddings (SBERT)

### Phase 2: Topic Analysis
- [ ] Run BERTopic on each case
- [ ] Align topics across HYS-EP
- [ ] Calculate topic distance metrics

### Phase 3: Stance & Arguments
- [ ] Detect stances (pro/con/neutral)
- [ ] Extract arguments (claim-evidence)
- [ ] Compare position distribution

### Phase 4: Metrics & Visualization
- [ ] Calculate Deliberative Distance Index (DDI)
- [ ] Generate comparative visualizations
- [ ] Statistical tests

### Phase 5: Paper Writing
- [ ] Write methodology section
- [ ] Present results
- [ ] Discussion & limitations

---

## 📚 References & Comparability

### Compared to Di Porto et al. (2024):

| Aspect | Di Porto et al. | Our Study |
|--------|----------------|-----------|
| **Data source** | HYS only | HYS + EP |
| **Cases** | 3 (AIA, DMA, DSA) | 3 (COVID, AI, Deforestation) |
| **Responses** | 830 | 301,366 (HYS) + 1,443 (EP) |
| **Method** | NLP clustering | BERTopic + DDI + uptake analysis |
| **Innovation** | Topic extraction | **Cross-forum comparison** |
| **Output** | Clusters of topics | **Topics + stances + temporal alignment** |

### Our Contribution:
1. ✅ **Multi-forum**: Not just HYS, but HYS ↔ EP comparison
2. ✅ **Larger scale**: 301k feedback (vs 830)
3. ✅ **New metrics**: Deliberative Distance Index (DDI)
4. ✅ **Temporal**: Track topic evolution across forums
5. ✅ **Politically useful**: Shows if consultations influence legislation

---

## 💾 Data Sources

- **HYS Database**: `/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db`
- **EP Verbatim**: 178 HTML files → 178 JSON debates
- **Period**: 2021-2025
- **Languages**: Mainly EN, but multilingual in HYS

---

## ✅ Dataset Validation

- **HYS**: All feedback from closed consultations with reference IDs
- **EP**: All speeches from plenary debates mentioning topic keywords
- **Matching**: Temporal alignment (HYS before/during EP debates)
- **Quality**: Text fields non-empty, dates valid, speaker IDs present

---

## 🚀 Ready for Implementation!

The dataset is now ready for:
1. BERTopic analysis
2. Stance detection
3. Temporal analysis
4. DDI calculation
5. Paper writing

**Location**: `data/pilot_study_dataset/`
**Format**: JSON (easy to load with Python/pandas)
**Documentation**: README.md in each case folder

---

## 📧 Contact

For questions about this dataset or analysis:
- See `/home/svagnoni/deliberation-knowledge-graph/research/` for research plans
- Check `COMPARISON_PAPER_DESIGN.md` for methodology details
- Review `PILOT_STUDY_PLAN.md` for implementation timeline

---

**Generated**: 2026-02-11
**Status**: ✅ Ready for analysis
