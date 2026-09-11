# DelibAI pilot (May 2026) in the Deliberation Knowledge Graph

DelibAI is a research prototype for *contestable* AI feedback in civic
deliberation, implemented as a pilot mode of a research fork of Your Priorities
(CIRSFID, University of Bologna). Before submitting a comment, participants may
receive advice, a rewrite suggestion and possible argumentation-fallacy flags;
the system never edits their text and every suggestion can be ignored, rejected
or corrected. Participants also evaluate other comments (peer flags).

## What is in the graph

| Entity | Count | Notes |
|---|---|---|
| Process | 1 (`res:delibai_pilot_2026`) | 4 topics, protocol `delibai-pilot-v2-postpilot-hardened-2026-09-01` |
| Participants | 34 pseudonymised + research team | salted-hash pseudonyms; no personal data |
| Contributions | 195 participant texts + 20 seed comments | first-level comments, agreeing / disagreeing replies |
| AI feedback | 99 (`del:AIFeedback`) | advice, rewrite suggestion, model, provider, model runs; 7 fallacy flags |
| Displayed labels on seeds | 16 | fixed by the study design, marked as such |
| Peer evaluations | 275 | problem / no problem, category, withdrawals |
| Recorded responses to AI labels or feedback | 280 | confirmed / corrected / rejected / accepted / ignored |

Exact counts, exclusions and warnings: `reconciliation_report.json`.
Personal-data screening of every free text: `screening_report.json`.

## Not published (reserved)

* questionnaires (`pilot_survey_responses`),
* participant credentials (`pilot_participants.metadata`),
* behavioural logs (thread views, sessions, disclosure acknowledgements),
* original participant codes,
* post-pilot test sessions (after 2026-05-31).

## Files

* `search_documents.json` – the documents indexed for semantic search (types: contribution, seed_contribution, topic, process, ai_feedback, ai_rewrite).
* Source graph: `knowledge_graph/sources/delibai_pilot_kg.ttl` (not versioned; regenerate with the importer).
* Mapping: `documentation/delibai_crowdlaw_integration.md`.

## Browse

* Citizen interface: https://citizen.svagnoni.linkeddata.es/?process=https%3A%2F%2Fsvagnoni.linkeddata.es%2Fresource%2Fdelibai_pilot_2026
* Linked-data URI: https://svagnoni.linkeddata.es/resource/delibai_pilot_2026
* SPARQL examples: `queries/integration/delibai_*.rq`

## Licence and attribution

Derived, pseudonymised data released under CC BY 4.0 (Vagnoni, DelibAI pilot
2026; data controller: University of Bologna). Cite the DelibAI paper
(CERCA 2026 workshop / AI & Law journal submission) when reusing.
