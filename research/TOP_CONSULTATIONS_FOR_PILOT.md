# Top Consultations for Pilot Study

**Date**: 2026-02-04
**Purpose**: Select 3 completed consultations with EP debates for HYS-EP comparison

---

## Selection Criteria

1. ✅ Consultation completed (stage=ADOPTION or status=CLOSED)
2. ✅ High feedback volume (>1,000 preferred for robust NLP)
3. ✅ Legislative relevance (likely EP debates)
4. ✅ Thematic diversity (different policy domains)
5. ✅ Recent period (2018-2022 = better EP coverage)

---

## Top 20 Completed Consultations (by feedback count)

| Rank | Title | Feedback | Reference | Status | Year |
|------|-------|----------|-----------|--------|------|
| 1 | EU COVID-19 certificate - Extension | 296,600 | Ares(2021)7905561 | CLOSED | 2021 |
| 2 | Evaluation of the Tobacco Products Directive | 23,762 | Ares(2021)1275054 | CLOSED | 2021 |
| 3 | Passenger name record data - tracing | 12,046 | Ares(2021)1291046 | CLOSED | 2021 |
| 4 | EU Climate Pact | 3,510 | Ares(2020)4600977 | CLOSED | 2020 |
| 5 | Common fisheries policy - technical measures | 1,941 | Ares(2021)1273962 | CLOSED | 2021 |
| 6 | Trans fats in food | 1,634 | Ares(2022)1336682 | CLOSED | 2022 |
| 7 | Deforestation and forest degradation | 1,456 | Ares(2021)1411682 | CLOSED | 2021 |
| 8 | Artificial intelligence - White Paper | 1,216 | AIConsult2020 | CLOSED | 2020 |
| 9 | Terrorist content online | 1,041 | Ares(2018)4721409 | CLOSED | 2018 |
| 10 | Copyright - Directive implementation | 967 | Ares(2022)1336698 | CLOSED | 2022 |
| 11 | Machinery products - safety requirements | 958 | Ares(2021)1411692 | CLOSED | 2021 |
| 12 | Machinery products safety (follow-up) | 927 | Ares(2021)1411691 | CLOSED | 2021 |
| 13 | Circular economy - greening SMEs | 831 | Ares(2021)1340704 | CLOSED | 2021 |
| 14 | Sustainable finance - Environmental taxonomy | 742 | Ares(2020)2801218 | CLOSED | 2020 |
| 15 | Cross-border parcel delivery services | 737 | Ares(2021)1267844 | CLOSED | 2021 |
| 16 | Taxation - crypto-assets | 727 | Ares(2021)6723321 | CLOSED | 2021 |
| 17 | Animal welfare - animals in captivity | 722 | Ares(2022)1336680 | CLOSED | 2022 |
| 18 | Health Technology Assessment | 712 | Ares(2018)5943859 | CLOSED | 2018 |
| 19 | Pesticides - maximum residue levels | 700 | Ares(2021)1267840 | CLOSED | 2021 |
| 20 | Mediation in civil and commercial matters | 697 | Ares(2021)1291052 | CLOSED | 2021 |

---

## 🎯 Recommended 3 Cases

### Option A: Maximum Contrast

| # | Case | Feedback | Domain | Rationale |
|---|------|----------|--------|-----------|
| 1 | **COVID Certificate** | 296,600 | Health/Rights | Extreme volume, high political salience |
| 2 | **AI White Paper** | 1,216 | Technology | Technical, stakeholder-rich, comparable to Di Porto |
| 3 | **Deforestation** | 1,456 | Environment | Moderate volume, different policy domain |

**Strengths**: Maximum thematic diversity, includes extreme case (COVID)
**Weaknesses**: Volume imbalance may affect comparison

### Option B: Balanced Volume

| # | Case | Feedback | Domain | Rationale |
|---|------|----------|--------|-----------|
| 1 | **Tobacco Directive** | 23,762 | Health | High volume, health policy |
| 2 | **Deforestation** | 1,456 | Environment | Moderate volume, environmental policy |
| 3 | **AI White Paper** | 1,216 | Technology | Technical, comparable to Di Porto |

**Strengths**: More balanced feedback volumes, all >1k
**Weaknesses**: Less extreme contrast

### Option C: Legislative Focus

| # | Case | Feedback | Domain | Rationale |
|---|------|----------|--------|-----------|
| 1 | **AI White Paper** | 1,216 | Technology | Led to AI Act |
| 2 | **Deforestation** | 1,456 | Environment | Due Diligence Regulation |
| 3 | **Tobacco Directive** | 23,762 | Health | Directive evaluation/update |

**Strengths**: All led to legislation, clear EP debate linkage
**Weaknesses**: Similar to Option B

---

## ⏭️ Next Steps

### Step 1: Verify EP Debates Availability

For each candidate case, query EP API:

```bash
# Test COVID Certificate debates
curl "https://data.europarl.europa.eu/api/v2/speeches?filter=sitting-date:ge:2021-01-01,sitting-date:le:2022-12-31&query=COVID+certificate"

# Test AI debates
curl "https://data.europarl.europa.eu/api/v2/speeches?filter=sitting-date:ge:2020-01-01,sitting-date:le:2024-12-31&query=artificial+intelligence"

# Test Deforestation debates
curl "https://data.europarl.europa.eu/api/v2/speeches?filter=sitting-date:ge:2021-01-01,sitting-date:le:2023-12-31&query=deforestation"

# Test Tobacco debates
curl "https://data.europarl.europa.eu/api/v2/speeches?filter=sitting-date:ge:2021-01-01,sitting-date:le:2023-12-31&query=tobacco"
```

**Expected output**: Count of speeches per topic to confirm sufficient EP debate coverage

### Step 2: Export HYS Feedback

```bash
# Export feedback for selected cases
python3 scripts/integrate_hys_full.py \
  --db /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db \
  --output /tmp/hys_export_pilot \
  --filter-reference "Ares(2021)7905561,AIConsult2020,Ares(2021)1411682"
```

### Step 3: Compare Temporal Coverage

Ensure HYS consultation period overlaps with EP debate period:

| Case | HYS Period | EP Debate Period (expected) | Overlap |
|------|------------|----------------------------|---------|
| COVID Certificate | 2021 | 2021-2022 | ✓ |
| AI White Paper | 2020 | 2020-2024 | ✓ |
| Deforestation | 2021 | 2021-2023 | ✓ |

---

## 📊 Decision Criteria

Select **Option A, B, or C** based on:

1. **EP debate volume**: After Step 1 verification
2. **Research question**: What contrast do we want to study?
   - Option A: Extreme vs moderate participation
   - Option B: Balanced comparison across domains
   - Option C: Legislative impact focus
3. **Workload**: Option A requires handling 296k COVID feedback (computational cost)
4. **Comparability**: Option B/C more balanced for statistical analysis

---

## 🚦 GO/NO-GO After EP Verification

Each case needs **minimum 50 EP speeches** to proceed.

If any case fails EP verification:
- Replace with next candidate from Top 20 list
- Consider extending temporal range for EP query
- Consider searching EP committee debates (not just plenary)

---

**Recommendation**: Start with **Option B** (Tobacco, Deforestation, AI) for balanced volume, verify EP debates, adjust if needed.

---

**Next Meeting Decision**:
1. Approve Option A, B, or C?
2. After EP verification, confirm final 3 cases
3. Timeline: 2 weeks for data acquisition + EP verification?
