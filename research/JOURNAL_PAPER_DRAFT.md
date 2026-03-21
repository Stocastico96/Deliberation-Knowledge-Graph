# Journal Paper Draft (AI and Law) - HYS vs EP Pilot Study

## Table of Contents
1. Abstract
2. Keywords
3. Introduction
4. Related Work
5. Data and Case Selection
6. Methods
7. Results (Planned)
8. Discussion and Policy Implications
9. Limitations and Ethics
10. Conclusions and Future Work
11. Reproducibility and Data Availability

---

## Abstract
This paper proposes a multi-forum framework to measure the distance between public consultation feedback and parliamentary debate in EU policymaking. We build a pilot dataset that links European Commission Have Your Say (HYS) consultations with European Parliament (EP) plenary debates across three policy dossiers: COVID Digital Certificate extension, the AI Act, and the Deforestation Regulation. The dataset includes 301,366 HYS feedback items and 1,443 EP speeches (2021-2025). We introduce a Deliberative Distance Index (DDI) that combines topic distance, salience gap, temporal lag, and actor distance to quantify alignment between citizen input and legislative discourse. Our analysis pipeline applies BERTopic for topic modeling, cross-forum topic alignment, stance detection, and distance metrics. This draft reports dataset construction, methodological choices, and the analysis plan; quantitative results will be inserted after topic modeling and alignment are completed. The goal is to provide a reproducible, scalable method for auditing deliberative alignment and to inform better consultation design in EU lawmaking.

## Keywords
Deliberative distance, public consultation, European Parliament, topic modeling, BERTopic, stance detection, knowledge graph, EU lawmaking

## 1. Introduction
Public consultations are intended to inform EU policymaking, yet the relationship between citizen feedback and parliamentary debate remains largely unmeasured. Existing studies focus on clustering consultation responses, but they rarely connect consultation discourse to subsequent legislative deliberation. This paper addresses that gap by linking HYS consultations to EP plenary debates and by proposing a metric that quantifies how closely the two forums align in topics, salience, timing, and participation.

We present a pilot study with three policy cases covering health, technology regulation, and environmental policy. The pilot provides a concrete testbed for measuring deliberative distance at scale and for validating a pipeline that can be extended to additional dossiers and legislative sources.

Contributions:
- A curated HYS-EP pilot dataset with three matched cases and transparent selection criteria.
- A multi-level comparison framework for cross-forum deliberation analysis.
- A Deliberative Distance Index (DDI) that operationalizes alignment across forums.
- A reproducible analysis pipeline (topic modeling, alignment, stance detection, distance metrics).

## 2. Related Work
Research on computational analysis of public consultations has highlighted misalignment between clustered opinions and stakeholder categories, but typically focuses on single-forum data. In contrast, cross-forum deliberation analysis is still rare. This work builds on prior NLP-based studies of consultation feedback while extending the scope to include parliamentary debate. We also connect to literature on deliberative democracy, argumentation mining, and policy traceability, and align with the emerging use of knowledge graphs to integrate heterogeneous civic participation data.

## 3. Data and Case Selection
### 3.1 Sources
- HYS feedback database (2016-2025) with structured metadata, including stakeholder categories and consultation references.
- EP plenary debate transcripts (verbatim HTML) for 2021-2025, converted into JSON with full speech texts.

### 3.2 Pilot Cases
Case 1: COVID Digital Certificate extension
- HYS feedback: 299,815 items
- EP speeches: 1,185 speeches in 155 debates
- References: COM(2022)50, COM(2022)55

Case 2: AI Act
- HYS feedback: 1,349 items
- EP speeches: 119 speeches in 60 debates
- References: AIConsult2020, Ares(2020)3896535

Case 3: Deforestation Regulation
- HYS feedback: 202 items
- EP speeches: 139 speeches in 66 debates
- References: Ares(2018)6516782

### 3.3 Dataset Structure
The dataset is exported as JSON with per-case folders containing HYS feedback, EP debates, and metadata. Total size is 171 MB. The dataset enables direct loading into Python for analysis and topic modeling.

### 3.4 Matching Logic
HYS consultations were matched to EP debates by topic keywords and temporal overlap. The pilot yields three high-quality matches with clear policy references.

## 4. Methods
### 4.1 Overview
The pipeline consists of four stages:
- Topic modeling (BERTopic) per forum and case.
- Topic alignment across HYS and EP corpora.
- Stance detection on aligned topics.
- Deliberative Distance Index computation.

### 4.2 Topic Modeling
We use BERTopic to generate topic distributions for each forum and case. This is suitable for short texts and supports interpretable topic keywords. Outputs include topic lists, topic prevalence, and interactive visualizations.

### 4.3 Topic Alignment
Aligned topics are identified via cosine similarity between topic embeddings. The alignment produces a correspondence matrix that supports comparison of topic coverage and salience across forums.

### 4.4 Stance Detection
We plan to apply NLI-based stance classification on topic-relevant propositions, producing distributions of favor, against, and neutral positions by topic and forum.

### 4.5 Deliberative Distance Index (DDI)
We define DDI as a weighted combination of four measurable components in the pilot phase:

DDI = 0.3 * TopicDistance + 0.3 * SalienceDistance + 0.2 * TemporalLag + 0.2 * ActorDistance

Where:
- TopicDistance is the cosine distance between aligned topic embeddings.
- SalienceDistance is the absolute difference in topic prevalence.
- TemporalLag measures time differences between HYS and EP discussion peaks.
- ActorDistance captures divergence in participant types (e.g., citizen vs institutional speakers).

A full version of DDI can incorporate framing and argumentation distances in future work.

## 5. Results (Planned)
This section will be populated after completing topic modeling and alignment.

Planned outputs:
- Table: topic overlap and salience gaps by case.
- Figure: aligned topic maps for HYS vs EP.
- Table: stance distributions by forum and topic.
- DDI scores per case with sensitivity analysis on weights.

## 6. Discussion and Policy Implications
The proposed framework enables a systematic audit of deliberative alignment between citizen input and legislative debate. For EU policymaking, this provides evidence for whether consultations anticipate or diverge from parliamentary discourse, and whether specific stakeholder categories have disproportionate influence. The DDI can inform Better Regulation practices by identifying consultations that are substantively disconnected from legislative deliberation.

## 7. Limitations and Ethics
- The pilot focuses on EP plenary debates and excludes committee work and final legal text.
- HYS feedback is multilingual, while EP debates are largely in English; this may introduce language bias.
- Stance detection is sensitive to proposition formulation and model bias.
- Privacy is respected by using publicly available data and aggregated results only.

## 8. Conclusions and Future Work
We present a pilot dataset and a measurable framework for cross-forum deliberation analysis in EU policymaking. The next steps include completing BERTopic modeling, topic alignment, stance detection, and DDI computation, followed by expansion to additional dossiers and legislative stages (e.g., final acts). This work aims to provide a scalable method to assess deliberative alignment and to support transparency in EU lawmaking.

## 9. Reproducibility and Data Availability
- Dataset path: `data/pilot_study_dataset/`
- Analysis scripts: `scripts/analysis/`
- Key script to run: `scripts/analysis/01_bertopic_modeling.py`

