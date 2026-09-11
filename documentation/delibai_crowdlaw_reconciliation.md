# Reconciliation report – DelibAI and CrowdLaw integration

Generated from the importer reports (`data/*/reconciliation_report.json`), the
merge logs (`knowledge_graph/sources/merged/*.merge_log.json`) and the search
documents. Every source table satisfies **read = imported + excluded + failed**
(enforced by `tests/integration/test_importers.py`).

## DelibAI pilot

Import `delibai-import-1.0.0`, mapping `delibai-del-mapping-1.0.0`; source snapshot of
the `pilot_*` tables taken on 2026-09-11T08:43:57Z; pilot window
2026-05-07 → 2026-05-31.

| Source table | Read | Imported | Excluded | Failed |
|---|---:|---:|---:|---:|
| pilot_survey_responses | 41 | 0 | 41 | 0 |
| seed_comments | 20 | 20 | 0 | 0 |
| pilot_participants | 36 | 34 | 2 | 0 |
| pilot_task_responses | 195 | 195 | 0 | 0 |
| ai_feedback | 99 | 99 | 0 | 0 |
| ai_fallacy_flags | 7 | 7 | 0 | 0 |
| pilot_peer_flags | 454 | 453 | 1 | 0 |
| pilot_events | 2024 | 203 | 1821 | 0 |

Exclusions:

| Table | Reason | Records |
|---|---|---:|
| pilot_survey_responses | questionnaires are reserved - never exported to the graph | 41 |
| pilot_participants | created outside the pilot window (post-pilot session) | 2 |
| pilot_peer_flags | created outside the pilot window | 1 |
| pilot_events | session log - not published | 50 |
| pilot_events | behavioural log (thread views) - not published | 550 |
| pilot_events | consent/disclosure log - kept private (counted) | 36 |
| pilot_events | survey - reserved | 40 |
| pilot_events | experimental timing detail - captured as controlDelayMs on the contribution | 97 |
| pilot_events | redundant with the task record | 195 |
| pilot_events | redundant with the flag record | 417 |
| pilot_events | redundant with the flag record (aiAgreement=ai_confirmed) | 109 |
| pilot_events | redundant with delibai_analysis.modelComparison | 121 |
| pilot_events | redundant with the flag record (action=cleared) | 36 |
| pilot_events | redundant with the flag record (aiAgreement=ai_corrected) | 118 |
| pilot_events | 'Suggestion Shown' without a submitted contribution (text edited or abandoned) | 20 |
| pilot_events | redundant with the flag record (aiAgreement=ai_rejected) | 11 |
| pilot_events | created outside the pilot window | 21 |

Warnings: 3 – event 233 (DelibAI Suggestion Ignored): no matching contribution; attached to topic; event 527 (DelibAI Suggestion Ignored): no matching contribution; attached to topic; event 1152 (DelibAI Suggestion Ignored): no matching contribution; attached to topic.
`DelibAI Suggestion Shown` events matched to a stored feedback (→ `del:presentedAt`): 101.
Personal-data screening: 195 participant texts plus all AI texts screened, 0 flagged.

Source graph: 16522 triples.

| Entity type | Count |
|---|---:|
| dcat:Dataset | 1 |
| del:AIFeedback | 99 |
| del:AnnotationResponse | 280 |
| del:ArtificialAgent | 3 |
| del:AutomatedAnnotation | 106 |
| del:Contribution | 215 |
| del:DeliberationProcess | 1 |
| del:Facilitator | 1 |
| del:FallacyAnnotation | 83 |
| del:FallacyType | 6 |
| del:Forum | 1 |
| del:HumanAnnotation | 571 |
| del:ImportActivity | 1 |
| del:ModelRun | 99 |
| del:Participant | 35 |
| del:PeerEvaluation | 275 |
| del:Topic | 4 |
| prov:Activity | 1 |

## CrowdLaw / Portale del Cittadino

Import `crowdlaw-import-1.0.0`, mapping `crowdlaw-del-mapping-1.0.0`; documents imported: 7, 15, 16.
Proposal columns present in the historical database: False (proposal/motivation parsed from the platform's composed content where present).

| Source table | Read | Imported | Excluded | Failed |
|---|---:|---:|---:|---:|
| documents | 16 | 3 | 13 | 0 |
| articles | 39 | 39 | 0 | 0 |
| article_aspects | 24 | 17 | 7 | 0 |
| segment_aspects | 47 | 37 | 10 | 0 |
| clusters | 18 | 18 | 0 | 0 |
| ground_truth | 146 | 146 | 0 | 0 |
| comments | 194 | 146 | 48 | 0 |
| anchors_user | 0 | 146 | 0 | 0 |
| anchors_system | 0 | 146 | 0 | 0 |
| stance_annotations | 0 | 146 | 0 | 0 |
| proposal_fields_parsed_from_content | 0 | 32 | 0 | 0 |

Exclusions:

| Table | Reason | Records |
|---|---|---:|
| documents | developer test document or duplicate upload (not an evaluation corpus) | 13 |
| article_aspects | empty aspect list or unknown article | 7 |
| segment_aspects | empty aspect list or unknown article | 10 |
| comments | belongs to an excluded document (developer test data) | 48 |

Warnings: 0.
Evaluation metrics attached: doc7 33, doc15 53, doc16 57.

Source graph: 11993 triples.

| Entity type | Count |
|---|---:|
| dcat:Dataset | 1 |
| del:AspectAnnotation | 54 |
| del:AutomatedAnnotation | 131 |
| del:Contribution | 146 |
| del:DeliberationProcess | 3 |
| del:Facilitator | 1 |
| del:Forum | 1 |
| del:HumanAnnotation | 146 |
| del:ImportActivity | 1 |
| del:InformationResource | 143 |
| del:LegalExpression | 3 |
| del:LegalProvision | 177 |
| del:LegalResourceAnchor | 292 |
| del:LegalSource | 45 |
| del:LegalWork | 3 |
| del:Participant | 104 |
| del:StanceAnnotation | 223 |
| del:Topic | 18 |
| prov:Activity | 1 |

## Merge into the main graph

Backup before merge: `/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/backups/deliberation_kg_before_delibai+crowdlaw+crosslinks_20260911_150259.ttl`.

| Source | Triples in source | Removed (previous version) | Added | Graph after |
|---|---:|---:|---:|---:|
| delibai | 16522 | 0 | 16522 | 2200971 |
| crowdlaw | 11993 | 0 | 11993 | 2212964 |
| crosslinks | 191 | 0 | 191 | 2213155 |

Integrity check after rewriting the file (full parse of backup and new file):
2,184,449 original triples, 0 lost, 28,706 added, 0 blank-node triples, the 11
pre-existing ill-typed `xsd:float` literals of the legacy fallacy annotations
preserved unchanged.

## Semantic index

| Source | Documents indexed | By type |
|---|---:|---|
| delibai | 339 | {'process': 1, 'topic': 4, 'contribution': 195, 'ai_feedback': 99, 'ai_rewrite': 20, 'seed_contribution': 20} |
| crowdlaw | 188 | {'process': 3, 'contribution': 146, 'legal_provision': 39} |

Index total after update: 85,456 documents (84,929 before); backups
`knowledge_graph/embeddings_backup_before_delibai_20260911_150323.pkl` and
`…_before_crowdlaw_20260911_150343.pkl`.
