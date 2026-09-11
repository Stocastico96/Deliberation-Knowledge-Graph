# DelibAI and CrowdLaw in the Deliberation Knowledge Graph

Integration of two research platforms into the DEL/DKG infrastructure, the
semantic search engine and the two web interfaces
(https://dkg.svagnoni.linkeddata.es and https://citizen.svagnoni.linkeddata.es).

* **DelibAI** – contestable AI feedback in civic deliberation (pilot mode of a
  research fork of Your Priorities). Source: `/home/svagnoni/your-priorities-app`
  (PostgreSQL tables `pilot_*`).
* **CrowdLaw / Portale del Cittadino** – comments anchored to Akoma Ntoso
  passages of Italian bills. Source: `/home/svagnoni/portale-cittadino-mvp`
  (SQLite `backend/data/app.db`, AKN XML, evaluation ground truth).

Related files

| Purpose | Path |
|---|---|
| Ontology extension (DEL 1.2 draft) | `ontologies/deliberation-annotations.ttl` |
| Importers | `scripts/integration/import_delibai.py`, `scripts/integration/import_crowdlaw.py` |
| Source export helper | `scripts/integration/export_delibai_pilot.sh` |
| Merge into the main graph | `scripts/integration/merge_source_into_kg.py` |
| Semantic index update | `scripts/integration/update_embeddings_for_source.py` |
| Cross-process links | `scripts/integration/infer_cross_links.py` |
| Verification | `scripts/integration/verify_integration.py`, `tests/integration/` |
| Configuration (no secrets) | `config/integration/delibai.example.json`, `config/integration/crowdlaw.json` |
| Reconciliation reports | `data/delibai/reconciliation_report.json`, `data/crowdlaw/reconciliation_report.json` |
| Update cycle | `documentation/update_cycle_delibai_crowdlaw.md` |
| SPARQL queries | `queries/integration/*.rq` |

## 1. Modelling decisions

### 1.1 Structure

| Level | DelibAI | CrowdLaw |
|---|---|---|
| Platform | `res:forum_delibai` (`del:Forum`) | `res:forum_crowdlaw` (`del:Forum`) |
| Process | `res:delibai_pilot_2026` – the May 2026 pilot | one `del:DeliberationProcess` per consultation document: `res:crowdlaw_consultation_doc{7,15,16}` |
| Theme / task | 4 `del:Topic` (housing, citizenship, maternity & paternity, minimum income) with the discussion question as `dct:description` | clusters as `del:Topic` (automatic, `del:annotationMethod`) |
| Thread | replies via `del:responseTo` (parent = seed or peer comment), `del:replyRelation` agree/disagree | n/a (flat comments per document) |
| Contribution | one per pilot task (`res:delibai_contribution_<taskId>`) + 20 seed comments (`res:delibai_seed_*`) | one per comment (`res:crowdlaw_comment_<id>`) |
| Legal resources | – | `del:LegalWork` → `del:LegalExpression` (FRBR) → `del:LegalProvision` (articles and paragraph segments) |
| Experimental condition | `del:experimentalCondition` on each contribution; per-participant `del:conditionAssignment` | – |

Every node carries `prov:wasGeneratedBy` → `del:ImportActivity`; each source has a
`dcat:Dataset` with `del:datasetStatus`, `del:importVersion`, `del:mappingVersion`,
`del:sourceSnapshotDate`.

### 1.2 What stays separate

| Layer | Class(es) | Attribution |
|---|---|---|
| Participant text | `del:Contribution` (`del:text`, `del:draftText`) | `del:madeBy` participant |
| AI feedback | `del:AIFeedback` ⊑ `del:AutomatedAnnotation` (+ `del:FallacyAnnotation` per flag, `del:ModelRun` per model) | `prov:wasAttributedTo` `del:ArtificialAgent` (model) |
| Displayed label fixed by the study design (DelibAI seeds) | `del:FallacyAnnotation` + `del:HumanAnnotation`, `del:annotationMethod "study_design_displayed_label"` | research team |
| Research annotation (CrowdLaw ground truth) | `del:StanceAnnotation` + `del:HumanAnnotation`, method `seed_ground_truth` | research team |
| Model annotation (CrowdLaw NLI stance, aspects, clusters) | `del:StanceAnnotation`/`del:AspectAnnotation`/`del:Topic` + `del:AutomatedAnnotation`, `del:model` | – |
| Evaluation by another participant | `del:PeerEvaluation` ⊑ `del:HumanAnnotation` | `prov:wasAttributedTo` evaluating participant |
| Recorded response to an annotation | `del:AnnotationResponse` (`del:actionType` accepted/ignored/confirmed/corrected/rejected/cleared) | acting participant |

The absence of a response is never turned into acceptance or rejection: only
logged actions are imported.

### 1.3 Legal anchoring (CrowdLaw)

* `del:references` → the `del:LegalExpression` (resource cited / consulted).
* `del:aboutProvision` → the provision an opinion is about (user-selected or user-declared article).
* `del:proposesChangeTo` → only when a change was recorded (`del:proposedOperation` modify/remove, `del:proposedText`, `del:motivation`). A negative stance never produces a removal request.
* `del:hasAnchor` → `del:LegalResourceAnchor` with `del:anchorMethod` = `user_selection` (passage selected in the UI, `del:anchorText`, `del:anchorKind range`), `user_declared` (article chosen without a text selection) or `system_prediction` (`del:model`, `del:confidence` = cosine similarity, `del:anchorsAgree`). Every anchor carries `del:anchorExpression` → the exact FRBR expression; nothing is transferred to later versions.

### 1.4 Links between processes

`del:ProcessLink` with `del:linkType` ∈ {explicit, human, inferred}. Historical
data contain **no** explicit DelibAI–CrowdLaw link, so none is asserted.
`scripts/integration/infer_cross_links.py` adds inferred links (thematic
similarity to other processes; EuroVoc candidates from the vocabulary built by
the HYS–EP pipeline), each with method, version, model, similarity and rank, and
an explicit note that similarity is not evidence of influence.

## 2. Field inventory and mapping – DelibAI

Source: PostgreSQL `your_priorities_dev`, exported by
`scripts/integration/export_delibai_pilot.sh` (read-only). Pilot window used for
the import: 2026‑05‑07 → 2026‑05‑31 (post‑pilot sessions are excluded and counted).
Visibility: **P** = public in graph/API/search, **R** = reserved (never exported),
**D** = derived into another field, **X** = excluded with reason.

### pilot_participants

| Field | Meaning | DEL target | Transformation | Vis. |
|---|---|---|---|---|
| id | row id | – | not needed (code is the key) | X |
| participant_code | pseudonymous login code | `del:identifier`, `del:name "Pilot participant <6 chars>"` on `res:delibai_participant_<hash12>` | salted SHA‑256 (`config/integration/delibai.local.json`, git‑ignored) – re‑pseudonymised as required by `delibai_analysis/provenance/PROVENANCE.md` | P (hash only) |
| status | flow status (pre_completed…) | – | tied to surveys; not published | X |
| assigned_topics (JSONB) | topic order + condition | `del:conditionAssignment "topic:condition"` | one literal per assignment (order dropped) | P |
| metadata (JSONB) | password hash/salt | – | **never read** | R |
| started_at / completed_at | session times | `del:startDate` / `del:endDate` | xsd:dateTime | P |
| created_at | row creation | pilot-window filter | – | D |

### pilot_task_responses (contributions)

| Field | Meaning | DEL target | Transformation | Vis. |
|---|---|---|---|---|
| id | task id | `res:delibai_contribution_<id>`, `del:sourceRecordId`, `del:identifier task-<id>` | – | P |
| participant_code | author | `del:madeBy` | via pseudonym | P |
| topic_id | topic | `del:hasTopic res:delibai_topic_<id>` | – | P |
| condition | delibai_on/off | `del:experimentalCondition` | – | P |
| position_value | (always null) | – | absent in data | X |
| comment_text / response_text | first-level text / reply text | `del:text` (via final_text fallback) | – | P |
| selected_seed_id | reply target (`seed-*`, `peer-<taskId>`) | `del:responseTo` | resolved to seed or contribution URI | P |
| draft_text | text before AI review | `del:draftText` | – | P |
| final_text | submitted text | `del:text` (@en) | screened for personal data (`data/delibai/screening_report.json`) | P |
| word_count | words | `del:wordCount` | – | P |
| delibai_analysis (JSONB) | AI feedback | `res:delibai_feedback_<id>` `del:AIFeedback`: `del:advice`, `del:rewriteSuggestion`, `del:model`, `del:provider`, `del:responseStrategy`, `del:primaryModel`, `del:pendingModel`, `del:annotationLabel shouldBlock=…`; `.fallacies[i]` → `res:delibai_feedback_<id>_fallacy_<i>` `del:FallacyAnnotation` (`del:identifiesFallacy`, `del:confidence`=score, `del:rationale`); `.modelComparison.models[i]` → `del:ModelRun` (model, role, ok, latency, tokens, cost, labels) | only for delibai_on tasks | P |
| metrics (JSONB) | instrumentation | `del:contributionKind` (kind), `del:replyRelation` (relation), `del:reviewDurationMs`, `del:controlDelayMs` (delibai_off), `del:reviewedText` (on the feedback), `del:annotationMethodVersion` (protocol/instrumentation version) | remaining derived metrics (lengths, exact-match flags) are recomputable and omitted | P/D |
| completed_at / created_at | times | `del:timestamp`, `dct:created` | – | P |

### pilot_peer_flags

| Field | Meaning | DEL target | Transformation | Vis. |
|---|---|---|---|---|
| id | flag id | `res:delibai_evaluation_<id>` | – | P |
| flagger_participant_code | evaluator | `prov:wasAttributedTo` | pseudonym | P |
| target_participant_code | author of target | – | recoverable from the target contribution | D |
| target_comment_id | `seed-x`, `peer-<id>`, or `…::ai-fallacy-<n>` | `del:annotates` (contribution); with `::ai-fallacy` → `del:respondsToAnnotation` (displayed label) | parsed | P |
| topic_id / condition | context | `del:experimentalCondition` | – | P |
| has_problem | judgement | `del:hasProblem` | – | P |
| taxonomy_id | fallacy category | `del:identifiesFallacy res:delibai_fallacy_type_<id>`, `del:annotationLabel` | – | P |
| free_text | rationale | `del:rationale` | empty in data | P |
| flagger_position / target_author_position | ideology positions | – | null in data | X |
| metadata.action | endorsed / cleared | `del:actionType no_problem` / `cleared` | – | P |
| metadata.aiAgreement | ai_confirmed / ai_corrected / ai_rejected / peer_flagged | class `del:AnnotationResponse` + `del:actionType confirmed/corrected/rejected`; `peer_flagged` → `del:PeerEvaluation` `problem_flagged` | – | P |
| metadata.correctedTaxonomyId | corrected label | `del:correctedTo` | – | P |
| metadata.protocolVersion | version | `del:annotationMethodVersion` | – | P |
| created_at | time | `del:timestamp` | – | P |

### pilot_events

| Event | DEL target | Notes |
|---|---|---|
| DelibAI Suggestion Accepted / Ignored | `res:delibai_response_<id>` `del:AnnotationResponse` (`del:actionType`, `del:actionReason`, `del:reviewDurationMs`), `del:respondsToAnnotation` the task's feedback | matched to the task by participant, topic, kind and text |
| DelibAI Suggestion Shown | `del:presentedAt` on the matched `del:AIFeedback` | matched on the reviewed text; unmatched shown events (edited/abandoned texts) counted |
| Confirmed / Corrected / Rejected, Peer Flag Submitted / Cleared, Topic Task Completed, Model Monitor Completed | – | redundant with flags / tasks (counted as excluded) |
| Comment Thread Viewed, Pilot Participant Started, Control Delay Applied, AI Disclosure Accepted, Pre/Post Survey Completed | – | behavioural / consent / survey logs: reserved (counted) |

### pilot_survey_responses – **reserved**, never exported.

### Pilot configuration (Your Priorities repo)

`delibaiPilotConfig.cjs` → topics (`del:Topic` with question, `del:containsFallacy`
expected by design, political axes as `del:annotationLabel`), fallacy taxonomy
(`del:FallacyType` with label, macro/fine category, question, example,
`del:taxonomyVersion`), study versions, disclosure text (`del:rationale` on the
process). `yp-delibai-pilot-forum.ts` → 20 seed comments (`del:contributionSource
"seed"`, author = research team with a `del:Facilitator` role) and their
displayed labels.

## 3. Field inventory and mapping – CrowdLaw

Source: `backend/data/app.db` (read-only) + `backend/scripts/ground_truth_doc*.json`,
`eval_results_doc*.json`. Only documents 7, 15, 16 (the evaluation corpora of the
paper) are imported; the other 13 rows (duplicate uploads and developer tests,
48 comments such as "commaaaa") are excluded and counted.

| Table.field | Meaning | DEL target | Transformation | Vis. |
|---|---|---|---|---|
| documents.id | upload id | `res:crowdlaw_consultation_doc<id>` (process), `del:sourceRecordId` | – | P |
| documents.filename | AKN file | `del:sourceFilename` on the expression | – | P |
| documents.title | bill title | `del:name`/`rdfs:label` of work and expression | – | P |
| documents.uploaded_at | upload time | `dct:created` on the process | – | P |
| documents.raw_xml | AKN XML | FRBR identifiers → `del:LegalWork` (`del:frbrWorkUri`), `del:LegalExpression` (`del:frbrExpressionUri`, `del:frbrManifestationUri`, `dct:language it`); `<article>/<p>` → paragraph segments `del:LegalProvision` with `del:segmentIndex` | raw XML itself not copied (bills are public; source archive linked) | P/D |
| articles.* | article rows | `res:crowdlaw_provision_<expr>_<eId>` `del:LegalProvision` (`del:eId`, `del:articleNumber`, `del:heading`, `del:text`, `del:partOfExpression`) | URI keyed on expression + eId, so duplicate uploads would share provisions | P |
| comments.id | comment id | `res:crowdlaw_comment_<id>` | – | P |
| comments.author | pseudonym (`anon-NN`, `eval-NNN`) | `del:madeBy res:crowdlaw_participant_<slug>` (`del:participantType SYNTHETIC_EVALUATION_AUTHOR`) | synthetic authors, no identity | P |
| comments.content | text | `del:text` (@it); when in the platform's composed format also `del:proposedText`, `del:motivation`, `del:proposedOperation` | parsed with the platform's own markers ("Proposta di modifica:", "Motivazione:", "Richiesta di rimozione…") | P |
| comments.article_id | article declared by the author | user anchor (`user_declared`), `del:aboutProvision` | – | P |
| comments.selection_article_id / selection_text / selection_kind | passage selected by the author | user anchor (`user_selection`, `del:anchorText`, `del:anchorKind`) | partial→range, full→article | P |
| comments.predicted_article_id / similarity | SBERT argmax | system anchor (`system_prediction`, `del:model`, `del:confidence`, `del:anchorsAgree`) | – | P |
| comments.sentiment / sentiment_conf / sentiment_method | stance label | `del:StanceAnnotation` (`del:stanceLabel`, `del:confidence`); method manual→`seed_ground_truth` (human), nli→`nli_cross_encoder_targeted_stance` (model recorded), targeted→`llm_targeted_stance_openrouter` (model not recorded by the source) | `del:annotationTarget` = anchored provision | P |
| comments.cluster_id | cluster | `del:hasTopic res:crowdlaw_cluster_doc<id>_<key>` | only clusters with `cluster_key` (older rows lack it → counted) | P |
| comments.pca_x / pca_y | 2‑D PCA coordinates | `del:pcaX`, `del:pcaY` | rounded | P |
| comments.created_at | time | `del:timestamp`; process start/end computed from data | – | P |
| stance / stance_conf / stance_method, author_id/author_role, proposed_change_text, motivation_text, removal_requested | newer schema columns | same targets as above | **absent in the historical database** – reported | – |
| clusters.* | KMeans clusters | `del:Topic` (`del:topicWords`, `del:clusterKey`, `del:clusterSize`, method, model) | – | P |
| article_aspects / segment_aspects | key phrases | `del:AspectAnnotation` (`del:annotationLabel` ×n, method from `aspects_meta`: deterministic / llm) | empty lists skipped and counted | P |
| segment_frames / frames_meta | value frames | – | empty tables | X |
| users / sessions | accounts | – | absent in the historical DB; would be reserved | R |
| ground_truth_doc*.json | seeded labels | `del:StanceAnnotation` + `del:HumanAnnotation` `seed_ground_truth` (only when not already the stored manual label) | – | P |
| eval_results_doc*.json | anchoring / stance accuracy | `del:InformationResource` metrics (`del:metricName/Value/Type evaluation`) attached to the process | scalar values only | P |

## 4. Publishability

* DelibAI: conditions in `delibai_analysis/provenance/PROVENANCE.md` are applied —
  password material never read; questionnaires reserved; behavioural logs reserved;
  codes re‑pseudonymised with a private salt; all free texts (comments, drafts,
  advice, rewrites, rationales) screened for personal-data patterns
  (`data/delibai/screening_report.json`, 0 hits; the only proper name found is a
  published author cited in a comment). Participants were told data would be
  analysed in aggregate and pseudonymised form; the graph publishes pseudonymised
  contribution texts, as foreseen by the paper's data-availability statement
  ("free-text contributions … after screening for accidental personal data").
* CrowdLaw: synthetic evaluation data with pseudonymous generated authors; bills
  are public parliamentary documents from the GenAI4Lex archive (source terms
  apply to redistribution of the archive; only article texts needed for
  anchoring are reproduced).
* The same restrictions apply to graph, API, search index, snippets and exports
  because all of them are built from the source graphs only.

## 5. Identity and idempotency

URIs are deterministic functions of source identifiers (see the helper functions
in each importer), so re-running an importer on the same snapshot produces the
same graph and merging twice adds no triples. Participant identities are never
unified across platforms.
