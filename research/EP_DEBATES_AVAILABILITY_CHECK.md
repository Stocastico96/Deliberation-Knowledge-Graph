# EP Debates Availability Check

**Date**: 2026-02-10
**Task**: Verify if EP debates exist for HYS consultation topics

---

## Problem Identified

The EP API `/speeches` endpoint has limitations:
1. **Full-text search doesn't work well**: Query parameter finds very few matches (e.g., "COVID" finds only 2/802 speeches with "COVID" in title)
2. **API returns max 1000 results**: All queries return exactly 1000 speeches (API limit)
3. **Speech ≠ Debate**: 1000 speeches ≠ 1000 debates. Each debate (sitting date) has multiple speeches

## What We Know

### EP API Limitations
- Query `?query=COVID&filter=sitting-date:ge:2021-01-01` returns 1000+ speeches
- But only ~2 speeches actually have "COVID" in their title
- The API seems to do fuzzy/broad matching, not precise keyword search

### Alternative Approach Needed

Instead of relying on API keyword search, we should:

**Option 1: Download by Date Range**
- Identify when specific legislation was discussed (from EUR-Lex or EP legislative tracker)
- Download ALL debates from that period
- Filter locally by content

**Option 2: Use Legislative Procedure References**
- Find EP procedure numbers for each topic (e.g., COD/2021/0106 for AI Act)
- Query EP API by procedure reference
- This is more reliable than keyword search

**Option 3: Use Existing Downloaded Debates**
- Check if we already have relevant debates in `data/EU_parliament_debates/`
- Parse them to see if they cover our topics

---

## Recommended Next Steps

### Step 1: Map HYS Consultations → EP Procedures

For each top HYS consultation, find the corresponding EP legislative procedure:

| HYS Consultation | Reference | Feedback | EP Procedure | Legislative Act |
|------------------|-----------|----------|--------------|-----------------|
| AI White Paper | AIConsult2020 | 1,216 | COD/2021/0106 | AI Act (32024R1689) |
| Deforestation | Ares(2018)6516782 | 202 | COD/2021/0366 | Deforestation Regulation (32023R1115) |
| Tobacco | ? | 7,324? | ? | Tobacco Products Directive |
| COVID Certificate | ? | ? | ? | Digital COVID Certificate |

**TODO**: Verify these procedure numbers and CELEX identifiers

### Step 2: Query EP API by Procedure

Example:
```bash
curl "https://data.europarl.europa.eu/api/v2/speeches?filter=procedure-reference:eq:COD/2021/0106"
```

This should give us ALL speeches related to the AI Act procedure.

### Step 3: Download and Parse

Use existing scripts:
1. `download_ep_debates.py` - download verbatim HTML
2. `convert_verbatim_to_json.py` - parse to JSON
3. `convert_json_to_rdf.py` - convert to RDF

---

## Current Status

✅ **HYS data available**: Confirmed consultations with significant feedback
✅ **EP API working**: Can download speeches
❌ **Keyword search unreliable**: Need procedure-based approach
⏸️ **Procedure mapping**: Need to link HYS consultations to EP procedures

---

## Questions for User

1. Should we focus on finding EP procedure numbers first?
2. Or should we download debates by date range and filter locally?
3. Do you have access to EP legislative tracker or EUR-Lex to find procedure references?

---

## Technical Note

The background task counting feedback references is still running. Once complete, we'll have a full mapping of:
- Feedback reference → Initiative title
- This will help identify the exact HYS consultations to use

