# Visual evidence – DelibAI and CrowdLaw on the production sites

Captured on 2026-09-11 with headless Chrome 138 (puppeteer-core) against the
public sites after deployment. Screenshots are downscaled to 900 px wide
(390 px for mobile) and cut at 6000 px height. The full walk-through results
are in `browser_walkthrough_results.json`: 26 of 26 checks passed.

| File | Site and URL | What it shows |
|---|---|---|
| `citizen_01_home_platform_catalogue.jpg` | https://citizen.svagnoni.linkeddata.es/ | Platform catalogue with DelibAI (official logo) and CrowdLaw (fallback mark), computed counts, dates, languages, data status |
| `citizen_02_search_process_mode.jpg` | same, search "affordable housing and short-term rentals", platform DelibAI | Process-mode semantic search result for the DelibAI pilot |
| `citizen_03_search_items_typed_results.jpg` | same, "Individual contributions and documents" | Typed results (contribution, topic, legal provision) with platform, language, date, topic, condition badges, inspection and process links; AI feedback excluded by default |
| `citizen_04_search_ai_feedback_on_request.jpg` | same, content type "AI rewrite suggestions", AI feedback included | AI-generated documents only when requested, labelled with model and the note that they are not participants' opinions |
| `citizen_05_search_italian_legal_provisions.jpg` | same, language Italian, content type legal provision | Semantic search over the articles of the CrowdLaw bills |
| `citizen_06_delibai_process_page.jpg` | `/?process=https://svagnoni.linkeddata.es/resource/delibai_pilot_2026` | DelibAI process page: status notice, computed statistics, conditions, topics, paginated contributions, links, provenance |
| `citizen_07_delibai_contribution_ai_feedback.jpg` | same, contribution inspection | Participant text and draft, AI feedback (advice, rewrite, model, model runs, time shown), recorded response, peer evaluations and label responses with their human/automated origin |
| `citizen_08_crowdlaw_process_page.jpg` | `/?process=https://svagnoni.linkeddata.es/resource/crowdlaw_consultation_doc7` | CrowdLaw consultation page: synthetic-data notice, bill with FRBR expression and articles, clusters, contributions with anchors and stance, evaluation metrics |
| `citizen_09_crowdlaw_comment_anchors.jpg` | same, comment inspection | Author anchor vs system-resolved anchor on the exact version, method and score, stance label with method |
| `citizen_10_crowdlaw_anchor_to_provision.jpg` | same, anchor → provision | Navigation from an anchor to the legal provision (text, segments, key aspects, anchored contributions) |
| `citizen_11_mobile_crowdlaw.jpg` | CrowdLaw page at 390 px | Mobile layout without horizontal scrolling |
| `citizen_12_mobile_inspection.jpg` | inspection at 390 px | Mobile inspection dialog |
| `dkg_01_datasets_delibai_crowdlaw_cards.jpg` | https://dkg.svagnoni.linkeddata.es/#datasets | DelibAI and CrowdLaw dataset cards with logos, descriptions and deep links to the citizen interface |

Reproduce: `node scripts/integration/browser_walkthrough.js https://citizen.svagnoni.linkeddata.es <outdir> prod`
(requires `puppeteer-core`; see `documentation/update_cycle_delibai_crowdlaw.md`, section 6).
