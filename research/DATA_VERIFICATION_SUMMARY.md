# Data Verification Summary: HYS + EP for AIA/DMA/DSA

**Date**: 2026-01-06
**Status**: ✅ PILOT STUDY FEASIBLE

---

## 🎯 Objective

Verify availability of HYS feedback and EP debates for pilot study on 3 dossiers:
- Artificial Intelligence Act (AIA)
- Digital Markets Act (DMA)
- Digital Services Act (DSA)

---

## 📊 HYS FEEDBACK AVAILABILITY

### Total Feedback: **1,544**

| Initiative | Ref | Feedback | Top User Types | Top Countries |
|-----------|-----|----------|----------------|---------------|
| **AI White Paper** | AIConsult2020 | **1,216** | Unknown (38%), Company (12%), NGO (10%) | Unknown (38%), BEL (11%), DEU (10%) |
| **AI Requirements** | Ares(2020)3896535 | **133** | Business Assoc (38%), Company (19%), NGO (11%) | BEL (36%), Unknown (11%), DEU (10%) |
| **DMA Ex-Ante** | Ares(2020)2836174 | **85** | Company (29%), Business Assoc (20%), NGO (17%) | BEL (21%), Unknown (14%), USA (12%) |
| **DSA Deepening** | Ares(2020)2836155 | **110** | Business Assoc (34%), Company (23%), NGO (15%) | BEL (28%), Unknown (11%), DEU (8%) |
| AI Liability | Ares(2021)2230940 | **0** | - | - |
| DSA Implementing | Ares(2022)6252979 | **0** | - | - |

### Language Distribution

| Initiative | EN | DE | FR | Other |
|-----------|----|----|----|----|
| AI White Paper | 65% | 15% | 6% | 14% |
| AI Requirements | 91% | 3% | - | 6% |
| DMA | 89% | 2% | 6% | 3% |
| DSA | 90% | 4% | - | 6% |

**Note**: ~90% feedback in inglese → preprocessing semplificato

---

## 📚 EP DEBATES AVAILABILITY

### Source: EP Open Data API

**Endpoint**: `https://data.europarl.europa.eu/api/v2/speeches`

**Status**: ✅ API FUNZIONANTE (testata il 2026-01-06)

**Test Result**:
- 50 speeches scaricati per sitting-date=2024-07-17
- Formato: JSON-LD con full text
- Metadata: speaker, party, date, type

### Coverage Attesa (da verificare)

Periodo rilevante per i 3 dossier:

| Dossier | Periodo chiave dibattiti | Note |
|---------|--------------------------|------|
| **AIA** | 2020-2024 | White Paper → proposta → adozione |
| **DMA** | 2020-2022 | Inception → fast-track adoption |
| **DSA** | 2020-2022 | Parallel a DMA |

**Next Step**: Query API con filtri temporali e keywords per stimare volume dibattiti

---

## 🔍 Data Quality Assessment

### HYS Feedback

**Strengths**:
- ✅ Volume sufficiente (1,544 feedback)
- ✅ Distribuzione stakeholder variegata
- ✅ 90% in inglese (facilita NLP)
- ✅ AI White Paper ha massa critica (1,216 fb)

**Weaknesses**:
- ⚠️ 38% user type "Unknown" nel White Paper
- ⚠️ DMA/DSA hanno pochi feedback (<110 ciascuno)
- ⚠️ AI Liability e DSA Implementing: zero feedback
- ⚠️ Concentrazione geografica: BEL overrepresented

**Implication**: Focus su **AI White Paper** come case study principale, DMA/DSA come supplementari.

---

## 🎯 Revised Pilot Study Strategy

### Opzione A (Focused): AI White Paper only
- **1,216 feedback HYS**
- EP debates 2020-2024 su AI
- Robust topic modeling possibile
- Comparabile con Di Porto et al.

### Opzione B (Comprehensive): AIA + DMA + DSA
- **1,544 feedback HYS totali**
- EP debates multi-topic 2020-2024
- Analisi comparativa cross-dossier
- Più complesso ma più interessante

**Raccomandazione**: Iniziare con **Opzione A** (AI White Paper), estendere a B se tempo/risorse.

---

## 📋 Next Steps

### Step 1: Download EP Debates ⏳
```bash
# Query API per dibattiti AI 2020-2024
python3 scripts/eurlex/fetch_ep_debates.py \
  --start-date 2020-01-01 \
  --end-date 2024-12-31 \
  --keywords "artificial intelligence,AI act,AI regulation" \
  --output data/ep_debates/ai_debates.json
```

**Expected output**: 100-500 speeches (da verificare)

### Step 2: Export HYS Feedback ✅ (pipeline ready)
```bash
# Export AI White Paper feedback
python3 scripts/integrate_hys_full.py \
  --db /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db \
  --output /tmp/hys_export_ai \
  --filter-reference AIConsult2020
```

**Output**: CSV con 1,216 feedback

### Step 3: Preprocessing & Alignment
- Parse EP JSON-LD → extract text + metadata
- Clean HYS feedback (remove HTML, normalize)
- Align temporal coverage
- Filter EN only or translate?

### Step 4: Topic Modeling (BERTopic)
- Fit on combined corpus (HYS + EP)
- Extract topic distributions per forum
- Calculate topic overlap

### Step 5: DDI Calculation
- Implement metrics (topic, salience, temporal, actor)
- Compute DDI for AI White Paper
- Sensitivity analysis

---

## 🚧 Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| EP debates volume troppo basso | Media | Alto | Espandere a commissioni/Q&A |
| DMA/DSA feedback insufficienti | Alta | Medio | Focus solo su AIA |
| Topic modeling non converge | Bassa | Alto | Tune hyperparameters |
| Temporal mismatch HYS↔EP | Media | Medio | Documentare gap, analisi qualitativa |

---

## 📊 Comparison with Di Porto et al.

| Aspect | Di Porto | Nostro Pilot |
|--------|----------|--------------|
| Dataset | 830 docs (AIA+DMA+DSA) | 1,544 feedback (focus AIA) |
| EP Debates | NO | YES |
| Temporal | Snapshot | 2020-2024 |
| Metrics | Similarity clustering | DDI (multi-dimensional) |
| Scale | Limited | Larger + EP comparison |

**Key differentiator**: Noi aggiungiamo **EP debates** e dimensione **temporale**.

---

## ✅ PILOT STUDY: GO/NO-GO Decision

**GO ✅**

**Rationale**:
1. ✅ Sufficient HYS feedback (1,544 total, 1,216 for main case)
2. ✅ EP API working and accessible
3. ✅ Infrastructure ready (scripts, pipeline)
4. ✅ Clear differentiation from Di Porto et al.
5. ✅ Manageable scope (4-6 weeks for Option A)

**Approval for**: Proceed with Step 1 (download EP debates) to verify coverage.

---

## 📁 Files Generated

- `DATA_VERIFICATION_SUMMARY.md` (this file)
- `COMPARISON_PAPER_DESIGN.md` (methodology)
- `PILOT_STUDY_PLAN.md` (detailed implementation)
- `JOURNAL_PAPER_PROPOSAL.md` (research design)

---

**Next Meeting Discussion**:
1. Approve Option A (AI only) vs Option B (AIA+DMA+DSA)?
2. EP debates: sufficient coverage after download?
3. Timeline for pilot: 4 weeks realistic?
4. Co-authors assignments?
