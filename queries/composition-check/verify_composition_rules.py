#!/usr/bin/env python3
"""Record-level check of the composition rules of Section 2.7.2 on the public
Deliberation Knowledge Graph (DelibAI pilot and CrowdLaw evaluation corpora).

Read-only SPARQL GET queries against https://dkg.svagnoni.linkeddata.es/sparql.
Each check states the rule it bears on, the query, and the expected value.
Usage: python3 verify_composition_rules.py [out.json]
"""
import json, sys, time, urllib.request, urllib.parse, datetime

ENDPOINT = 'https://dkg.svagnoni.linkeddata.es/sparql'
PREFIXES = """PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX res: <https://svagnoni.linkeddata.es/resource/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
CL = "VALUES ?pr { res:crowdlaw_consultation_doc7 res:crowdlaw_consultation_doc15 res:crowdlaw_consultation_doc16 } ?pr del:hasContribution ?c ."
DL = "res:delibai_pilot_2026 del:hasContribution ?c ."


def sparql(query, tries=4):
    url = ENDPOINT + '?' + urllib.parse.urlencode({'query': PREFIXES + query})
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/sparql-results+json'})
            data = json.load(urllib.request.urlopen(req, timeout=300))
            vars_ = data['head']['vars']
            return [{v: b.get(v, {}).get('value') for v in vars_} for b in data['results']['bindings']]
        except Exception as e:  # 502 under load: wait and retry
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


CHECKS = [
    # ---- Rule 1: reconstructible shared record
    *[(f'R1.cl.missing.{p.split(":")[1]}', 1, f'CrowdLaw contributions lacking {p}', '0',
       f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {CL} FILTER NOT EXISTS {{ ?c {p} ?x }} }}")
      for p in ['del:text', 'del:madeBy', 'del:timestamp', 'del:references', 'del:aboutProvision', 'del:hasAnchor',
                'del:hasTopic', 'del:pcaX', 'prov:wasGeneratedBy', 'del:sourceRecordId', 'del:identifier']],
    ('R1.cl.anchors_per_contribution', 1, 'distinct anchor methods per CrowdLaw contribution (expect 2 for all 146)', '2:146',
     f"SELECT ?n (COUNT(*) AS ?k) WHERE {{ SELECT ?c (COUNT(DISTINCT ?m) AS ?n) WHERE {{ {CL} ?c del:hasAnchor ?a . ?a del:anchorMethod ?m }} GROUP BY ?c }} GROUP BY ?n"),
    ('R1.cl.stance_methods_per_process', 1, 'stance annotations per process and method', None,
     f"SELECT ?pr ?m (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {CL} ?c del:hasAnnotation ?a . ?a a del:StanceAnnotation ; del:annotationMethod ?m }} GROUP BY ?pr ?m ORDER BY ?pr ?m"),
    ('R1.cl.without_model_stance', 1, 'CrowdLaw contributions with no model-produced stance label retained by the source', None,
     f"SELECT ?pr (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {CL} FILTER NOT EXISTS {{ ?c del:hasAnnotation ?a . ?a a del:StanceAnnotation ; a del:AutomatedAnnotation }} }} GROUP BY ?pr"),
    *[(f'R1.dl.missing.{p.split(":")[1]}', 1, f'DelibAI contributions lacking {p}', '0',
       f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {DL} FILTER NOT EXISTS {{ ?c {p} ?x }} }}")
      for p in ['del:text', 'del:madeBy', 'del:hasTopic', 'prov:wasGeneratedBy', 'del:identifier']],
    ('R1.dl.participant_missing_condition_or_time', 1, 'DelibAI participant contributions lacking condition or timestamp', '0',
     f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {DL} ?c del:sourceRecordId ?r FILTER NOT EXISTS {{ ?c del:experimentalCondition ?e ; del:timestamp ?t }} }}"),
    ('R1.dl.feedback_by_condition', 1, 'contributions and AI-feedback records per condition (feedback only when delibai_on)', None,
     f"SELECT ?cond (COUNT(DISTINCT ?c) AS ?n) (COUNT(DISTINCT ?f) AS ?fb) WHERE {{ {DL} ?c del:experimentalCondition ?cond OPTIONAL {{ ?f a del:AIFeedback ; del:annotates ?c }} }} GROUP BY ?cond"),
    ('R1.dl.draft_equals_final', 1, 'DelibAI contributions with a draft text, and how many drafts differ from the final text', None,
     f"SELECT (COUNT(DISTINCT ?c) AS ?withDraft) (SUM(IF(str(?d)!=str(?t),1,0)) AS ?differ) WHERE {{ {DL} ?c del:draftText ?d ; del:text ?t }}"),
    ('R1.dl.reviewed_equals_final', 1, 'AI-feedback records whose reviewed text differs from the final contribution text', None,
     "SELECT (COUNT(*) AS ?fb) (SUM(IF(str(?rt)!=str(?t),1,0)) AS ?differ) WHERE { ?f a del:AIFeedback ; del:reviewedText ?rt ; del:annotates ?c . ?c del:text ?t }"),
    # ---- Rule 2: provenance with the pertinent uncertainty measure
    ('R2.system_anchor_missing_confidence_or_model', 2, 'system-predicted anchors lacking similarity score or model', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?a a del:LegalResourceAnchor ; del:anchorMethod 'system_prediction' FILTER NOT EXISTS { ?a del:confidence ?x ; del:model ?m } }"),
    ('R2.nli_label_missing_confidence_or_model', 2, 'NLI stance labels lacking confidence or model', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?a a del:StanceAnnotation ; del:annotationMethod 'nli_cross_encoder_targeted_stance' FILTER NOT EXISTS { ?a del:confidence ?x ; del:model ?m } }"),
    ('R2.llm_label_fields', 2, 'fields of the single LLM-fallback stance label (model absence must be explicit)', None,
     "SELECT ?p ?o WHERE { ?a a del:StanceAnnotation ; del:annotationMethod 'llm_targeted_stance_openrouter' ; ?p ?o FILTER(?p IN (del:model, del:confidence, <http://www.w3.org/2000/01/rdf-schema#comment>)) }"),
    ('R2.feedback_missing_model_provider_run', 2, 'AI-feedback records lacking model, provider or model run', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?f a del:AIFeedback FILTER NOT EXISTS { ?f del:model ?m ; del:provider ?p ; del:hasModelRun ?r } }"),
    ('R2.modelrun_missing_latency_cost', 2, 'model runs lacking latency or cost', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?r a del:ModelRun FILTER NOT EXISTS { ?r del:latencyMs ?l ; del:inferenceCost ?k ; del:runSucceeded ?s } }"),
    ('R2.automated_missing_method', 2, 'automated annotations lacking a method', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?a a del:AutomatedAnnotation FILTER NOT EXISTS { ?a del:annotationMethod ?m } }"),
    ('R2.contributions_without_versioned_import', 2, 'contributions of both sources not generated by a versioned import activity', '0',
     f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {{ {CL} }} UNION {{ {DL} }} FILTER NOT EXISTS {{ ?c prov:wasGeneratedBy ?i . ?i a del:ImportActivity ; del:importVersion ?v ; del:mappingVersion ?mv }} }}"),
    # ---- Rule 3: versioned legal anchoring
    ('R3.anchor_missing_expression', 3, 'anchors without an identified FRBR expression', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?a a del:LegalResourceAnchor FILTER NOT EXISTS { ?a del:anchorExpression ?e . ?e a del:LegalExpression ; del:frbrExpressionUri ?u } }"),
    ('R3.anchor_expression_differs_from_reference', 3, 'anchors whose expression differs from the expression the contribution references', '0',
     f"SELECT (COUNT(*) AS ?n) WHERE {{ {CL} ?c del:hasAnchor ?a ; del:references ?e1 . ?a del:anchorExpression ?e2 FILTER(?e1 != ?e2) }}"),
    ('R3.provision_expression_mismatch', 3, 'anchors whose provision belongs to a different expression', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?a a del:LegalResourceAnchor ; del:anchorProvision ?pv ; del:anchorExpression ?e . ?pv del:partOfExpression ?e2 FILTER(?e != ?e2) }"),
    ('R3.expressions_per_work', 3, 'expressions per legal work (1 = cross-version mapping not testable)', None,
     "SELECT ?w (COUNT(DISTINCT ?e) AS ?n) WHERE { ?e a del:LegalExpression ; del:expressionOf ?w } GROUP BY ?w"),
    ('R3.anchor_agreement', 3, 'system vs author anchor agreement per process', None,
     f"SELECT ?pr ?ag (COUNT(*) AS ?n) WHERE {{ {CL} ?c del:hasAnchor ?a . ?a del:anchorMethod 'system_prediction' ; del:anchorsAgree ?ag }} GROUP BY ?pr ?ag ORDER BY ?pr ?ag"),
    # ---- Rule 4: confidence-gated escalation with declared thresholds
    ('R4.nli_confidence_vs_threshold', 4, 'NLI labels at or above vs below the declared 0.6 threshold, per process', None,
     f"SELECT ?pr ?b (COUNT(*) AS ?n) WHERE {{ {CL} ?c del:hasAnnotation ?a . ?a a del:StanceAnnotation ; del:annotationMethod 'nli_cross_encoder_targeted_stance' ; del:confidence ?x BIND(IF(xsd:decimal(?x) >= 0.6,'ge_0.6','lt_0.6') AS ?b) }} GROUP BY ?pr ?b ORDER BY ?pr ?b"),
    ('R4.llm_fallback_labels', 4, 'stance labels produced by the LLM fallback', None,
     "SELECT (COUNT(*) AS ?n) WHERE { ?a a del:StanceAnnotation ; del:annotationMethod 'llm_targeted_stance_openrouter' }"),
    ('R4.feedback_display_strategy', 4, 'DelibAI feedback: displayed model vs primary model', None,
     "SELECT ?pm ?m (COUNT(*) AS ?n) WHERE { ?f a del:AIFeedback ; del:primaryModel ?pm ; del:model ?m } GROUP BY ?pm ?m"),
    # ---- Rule 5: recorded correction
    ('R5.responses_by_action', 5, 'recorded responses by action and whether they point to the annotation they respond to', None,
     "SELECT ?a (COUNT(*) AS ?n) (COUNT(?t) AS ?withTarget) WHERE { ?r a del:AnnotationResponse ; del:actionType ?a OPTIONAL { ?r del:respondsToAnnotation ?t } } GROUP BY ?a"),
    ('R5.corrected_missing_new_label', 5, 'corrections lacking the corrected label', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?r a del:AnnotationResponse ; del:actionType 'corrected' FILTER NOT EXISTS { ?r del:correctedTo ?x } }"),
    ('R5.corrected_original_lost', 5, 'corrections whose original annotation no longer carries its label', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?r a del:AnnotationResponse ; del:actionType 'corrected' ; del:respondsToAnnotation ?t FILTER NOT EXISTS { ?t del:annotationLabel ?l } }"),
    ('R5.corrected_equal_to_original', 5, 'corrections whose new label equals the original', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?r a del:AnnotationResponse ; del:actionType 'corrected' ; del:respondsToAnnotation ?t ; del:correctedTo ?new . ?t del:identifiesFallacy ?old FILTER(?old = ?new) }"),
    ('R5.rejected_original_lost', 5, 'rejections whose original annotation no longer carries its label', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?r a del:AnnotationResponse ; del:actionType 'rejected' ; del:respondsToAnnotation ?t FILTER NOT EXISTS { ?t del:annotationLabel ?l } }"),
    ('R5.responses_missing_actor_or_time', 5, 'responses lacking actor or timestamp', '0',
     "SELECT (COUNT(*) AS ?n) WHERE { ?r a del:AnnotationResponse FILTER NOT EXISTS { ?r prov:wasAttributedTo ?p ; del:timestamp ?t } }"),
    ('R5.unmatched_responses', 5, 'responses that could not be matched to a contribution (attached to topic, as the reconciliation report states)', None,
     "SELECT ?r ?x WHERE { ?r a del:AnnotationResponse ; del:actionType 'ignored' ; del:annotates ?x }"),
    # ---- Decomposability of aggregates (reviewer test 3)
    ('AG.cluster_sizes', 1, 'clusters whose declared size equals the number of contributions linked to them', '18:18',
     "SELECT (COUNT(*) AS ?clusters) (SUM(IF(xsd:integer(?sz)=?cnt,1,0)) AS ?consistent) WHERE { SELECT ?cl ?sz (COUNT(DISTINCT ?c) AS ?cnt) WHERE { ?cl a del:Topic ; del:clusterKey ?k ; del:clusterSize ?sz OPTIONAL { ?c a del:Contribution ; del:hasTopic ?cl } } GROUP BY ?cl ?sz }"),
    ('AG.stored_metrics', 1, 'stored evaluation metrics per process', None,
     "SELECT ?pr ?name ?val WHERE { VALUES ?pr { res:crowdlaw_consultation_doc7 res:crowdlaw_consultation_doc15 res:crowdlaw_consultation_doc16 } ?pr del:hasAnnotation ?m . ?m del:metricName ?name ; del:metricValue ?val FILTER(?name IN ('anchoring_total','anchoring_top1_correct','stance_total','stance_correct','descriptive_n_comments','descriptive_n_clusters')) } ORDER BY ?pr ?name"),
    ('AG.recomputed_anchoring', 1, 'anchoring correct/total recomputed from the anchors', None,
     f"SELECT ?pr (COUNT(*) AS ?total) (SUM(IF(str(?ag)='true',1,0)) AS ?correct) WHERE {{ {CL} ?c del:hasAnchor ?a . ?a del:anchorMethod 'system_prediction' ; del:anchorsAgree ?ag }} GROUP BY ?pr ORDER BY ?pr"),
    ('AG.recomputed_stance', 1, 'stance correct/total recomputed from seed vs model labels', None,
     f"SELECT ?pr (COUNT(DISTINCT ?c) AS ?total) (SUM(IF(str(?gl)=str(?ml),1,0)) AS ?correct) WHERE {{ {CL} ?c del:hasAnnotation ?g , ?mo . ?g a del:StanceAnnotation ; del:annotationMethod 'seed_ground_truth' ; del:stanceLabel ?gl . ?mo a del:StanceAnnotation ; a del:AutomatedAnnotation ; del:stanceLabel ?ml }} GROUP BY ?pr ORDER BY ?pr"),
    ('AG.contributions_per_process', 1, 'contributions per process (to compare with reconciliation reports)', None,
     f"SELECT ?pr (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {CL} }} GROUP BY ?pr ORDER BY ?pr"),
    ('AG.delibai_by_source', 1, 'DelibAI contributions by source (195 participant + 20 seed)', None,
     f"SELECT ?s (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {DL} ?c del:contributionSource ?s }} GROUP BY ?s"),
    # ---- Nothing invented
    ('NI.crowdlaw_processes', 4, 'CrowdLaw processes in the graph (13 excluded documents must be absent)', '3',
     "SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p a del:DeliberationProcess ; del:platform 'CrowdLaw (Portale del Cittadino)' }"),
    ('NI.proposal_fields', 4, 'contributions with recovered proposed-change fields (only where the source supports them)', '32',
     f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ {CL} ?c del:proposesChangeTo ?x }}"),
    ('NI.delibai_reserved_predicates', 4, 'predicates in the DelibAI import mentioning survey, password or credential', '0',
     "SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?s prov:wasGeneratedBy res:delibai_import_delibai_import_1_0_0 ; ?p ?o FILTER(CONTAINS(LCASE(str(?p)),'survey') || CONTAINS(LCASE(str(?p)),'password') || CONTAINS(LCASE(str(?p)),'credential')) }"),
    ('NI.datasets', 4, 'source datasets with declared status and import version', None,
     "SELECT ?d ?st ?iv WHERE { ?d a dcat:Dataset ; del:datasetStatus ?st ; del:importVersion ?iv }"),
]


def main():
    out = {'endpoint': ENDPOINT, 'run_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'checks': []}
    for cid, rule, desc, expect, q in CHECKS:
        try:
            rows = sparql(q)
            status = 'ok'
        except Exception as e:
            rows, status = None, f'error: {e}'
        rec = {'id': cid, 'rule': rule, 'description': desc, 'expected': expect, 'rows': rows, 'status': status}
        out['checks'].append(rec)
        print(f"[{cid}] {desc}\n   -> {rows if rows is None or len(rows) <= 8 else rows[:8] + ['…']}")
    path = sys.argv[1] if len(sys.argv) > 1 else 'results/composition-check-' + datetime.date.today().isoformat() + '.json'
    json.dump(out, open(path, 'w'), indent=1, ensure_ascii=False)
    print('written', path)


if __name__ == '__main__':
    main()
