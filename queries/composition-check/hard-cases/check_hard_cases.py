#!/usr/bin/env python3
"""Check the composition rules of Section 2.7.2 on the hard cases of Table 2.3,
using declared synthetic fixtures (fixtures/*.ttl), not live data.

Each case has a conforming fixture and a violating one. Every check is run on both,
together with fixtures/base.ttl, and compared with the count fixed in EXPECTED before
the run: 0 on the conforming fixture, and the number of planted defects on the
violating one. A check passes the demonstration when both counts match.
The live rule-3 query of verify_composition_rules.py is also run on case C, to show
why it is replaced by R3.target_without_matching_anchor.
Terms in the px: namespace are proposed for the demonstration and are not part of DEL.
Requires rdflib. Usage: python3 check_hard_cases.py [out.json]
"""
import datetime
import json
import sys
from pathlib import Path

import rdflib

HERE = Path(__file__).resolve().parent
PREFIXES = """PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX px: <urn:del:proposed#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
ROUTING = "'no_provision', 'uncertain_prediction', 'out_of_scope'"
ANCHOR_STATUS = "'confirmed', 'contested', 'not_applicable'"

# (id, rule, case, description, query); each query returns one row per offending record.
CHECKS = [
    # ---- Rule 1: the record keeps every contribution
    ('R1.contribution_outside_process', 1, 'A', 'contributions that no process record contains',
     "SELECT ?c WHERE { ?c a del:Contribution FILTER NOT EXISTS { ?pr del:hasContribution ?c } }"),
    # ---- Rule 3: zero, one or several anchors; citation recorded apart from the target
    ('R3.unanchored_without_human_routing', 3, 'A',
     'contributions with no anchor and no routing decision by a person into one of the three categories',
     f"SELECT ?c WHERE {{ ?c a del:Contribution FILTER NOT EXISTS {{ ?c del:hasAnchor ?a }} "
     f"FILTER NOT EXISTS {{ ?c px:hasRoutingDecision ?d . ?d px:routingCategory ?k ; prov:wasAttributedTo ?p . "
     f"?p a prov:Person FILTER(?k IN ({ROUTING})) }} }}"),
    ('R3.anchor_missing_method_or_status', 3, 'A,B',
     'anchors without a method or without their own status (confirmed, contested, not applicable)',
     f"SELECT ?a WHERE {{ ?a a del:LegalResourceAnchor FILTER NOT EXISTS {{ ?a del:anchorMethod ?m ; "
     f"px:anchorStatus ?s FILTER(?s IN ({ANCHOR_STATUS})) }} }}"),
    ('R3.target_without_matching_anchor', 3, 'B,C',
     'provisions a contribution is about or proposes to change that have no anchor naming them in their own expression',
     "SELECT ?c ?p WHERE { ?c a del:Contribution ; del:aboutProvision|del:proposesChangeTo ?p . "
     "?p del:partOfExpression ?e FILTER NOT EXISTS { ?c del:hasAnchor ?a . ?a del:anchorProvision ?p ; "
     "del:anchorExpression ?e } }"),
    ('R3.legacy_anchor_expression_differs_from_reference', 3, 'C',
     'live query of 15 October 2026: anchors whose expression differs from the expression the contribution references',
     "SELECT ?c ?a WHERE { ?pr del:hasContribution ?c . ?c del:hasAnchor ?a ; del:references ?e1 . "
     "?a del:anchorExpression ?e2 FILTER(?e1 != ?e2) }"),
    # ---- Rule 1: aggregates decompose into the contributions behind them
    ('AG.declared_count_mismatch', 1, 'D',
     'aggregates whose declared number of contributions differs from the contributions they are derived from',
     "SELECT ?g ?n ?k WHERE { { SELECT ?g ?n (COUNT(DISTINCT ?c) AS ?k) WHERE { ?g a px:Aggregate ; "
     "px:declaredCount ?n OPTIONAL { ?g prov:wasDerivedFrom ?c . ?c a del:Contribution } } GROUP BY ?g ?n } "
     "FILTER(?k != ?n) }"),
    ('AG.in_scope_not_covered', 1, 'D',
     'contributions on the provision an aggregate covers that are neither in the aggregate nor recorded as excluded',
     "SELECT ?g ?c WHERE { ?g a px:Aggregate ; px:aggregateScope ?p ; px:declaredCount ?n . "
     "?c a del:Contribution ; del:aboutProvision ?p FILTER NOT EXISTS { ?g prov:wasDerivedFrom ?c } "
     "FILTER NOT EXISTS { ?x a px:Exclusion ; px:excludes ?c ; px:fromAggregate ?g } }"),
    ('AG.exclusion_without_reason', 1, 'D', 'exclusions from an aggregate without a recorded reason',
     "SELECT ?x WHERE { ?x a px:Exclusion FILTER NOT EXISTS { ?x px:reason ?r } }"),
    # ---- Rule 5: recorded correction with propagation
    ('R5.correction_missing_affected_aggregate', 5, 'E',
     'corrections of a label that an aggregate is derived from, which do not name that aggregate',
     "SELECT ?r ?g WHERE { ?r a del:AnnotationResponse ; del:actionType 'corrected' ; del:respondsToAnnotation ?l . "
     "?g a px:Aggregate ; prov:wasDerivedFrom ?l FILTER NOT EXISTS { ?r px:affectsAggregate ?g } "
     "FILTER NOT EXISTS { ?g prov:wasDerivedFrom ?r } }"),
    ('R5.affected_aggregate_not_recomputed', 5, 'E',
     'aggregates named by a correction for which no revision derived from that correction exists',
     "SELECT ?r ?g WHERE { ?r a del:AnnotationResponse ; px:affectsAggregate ?g "
     "FILTER NOT EXISTS { ?g2 prov:wasRevisionOf ?g ; prov:wasDerivedFrom ?r } }"),
    # One correction per label in the fixtures; with several, the latest would have to be selected.
    ('R5.current_aggregate_inconsistent', 5, 'E',
     'current aggregates (not revised) whose value differs from a recount of their labels after corrections',
     "SELECT ?g ?v ?recount WHERE { ?g a px:Aggregate ; px:aggregateValue ?v "
     "FILTER NOT EXISTS { ?g2 prov:wasRevisionOf ?g } "
     "{ SELECT ?g (SUM(IF(?eff = ?lab, 1, 0)) AS ?recount) WHERE { ?g px:countsLabel ?lab ; prov:wasDerivedFrom ?l . "
     "?l a del:StanceAnnotation OPTIONAL { ?l del:stanceLabel ?orig } "
     "OPTIONAL { ?r a del:AnnotationResponse ; del:actionType 'corrected' ; del:respondsToAnnotation ?l ; del:correctedTo ?ct } "
     "BIND(COALESCE(?ct, ?orig) AS ?eff) } GROUP BY ?g } FILTER(?recount != ?v) }"),
    ('R5.corrected_original_lost', 5, 'E',
     'corrections whose original annotation no longer carries its label (stance, fallacy or generic label)',
     "SELECT ?r ?l WHERE { ?r a del:AnnotationResponse ; del:actionType 'corrected' ; del:respondsToAnnotation ?l "
     "FILTER NOT EXISTS { ?l del:stanceLabel|del:annotationLabel|del:identifiesFallacy ?x } }"),
    # ---- Rule 6: recorded institutional response
    ('R6.contribution_without_status', 6, 'F',
     'contributions with no recorded status, individually or as an enumerated member of a group',
     "SELECT ?c WHERE { ?pr del:hasContribution ?c FILTER NOT EXISTS { ?s a px:ContributionStatus "
     "{ ?s px:statusOf ?c } UNION { ?s px:statusOf ?grp . ?grp px:hasMember ?c } } }"),
    ('R6.group_without_members', 6, 'F', 'statuses recorded for a group that does not name its members',
     "SELECT ?s ?grp WHERE { ?s a px:ContributionStatus ; px:statusOf ?grp . ?grp a px:ContributionGroup "
     "FILTER NOT EXISTS { ?grp px:hasMember ?m } }"),
    ('R6.examined_missing_fields', 6, 'F',
     'examined statuses lacking who responds, outcome, reasons, date or procedural reference',
     "SELECT ?s WHERE { ?s a px:ContributionStatus ; px:status 'examined' FILTER NOT EXISTS { ?s "
     "prov:wasAttributedTo ?w ; px:outcome ?o ; px:reason ?r ; px:asOf ?d ; px:proceduralReference ?pr } }"),
    ('R6.excluded_without_reason', 6, 'F', 'exclusions without a recorded reason',
     "SELECT ?s WHERE { ?s a px:ContributionStatus ; px:status 'excluded' FILTER NOT EXISTS { ?s px:reason ?r } }"),
    ('R6.unanswered_without_date', 6, 'F', 'absences of response recorded without a date',
     "SELECT ?s WHERE { ?s a px:ContributionStatus ; px:status 'unanswered' FILTER NOT EXISTS { ?s px:asOf ?d } }"),
]

# Counts fixed before the run: (conforming fixture, violating fixture), per case.
EXPECTED = {
    ('R1.contribution_outside_process', 'A'): (0, 1),             # vA3
    ('R3.unanchored_without_human_routing', 'A'): (0, 3),         # vA1, vA3, vA4
    ('R3.anchor_missing_method_or_status', 'A'): (0, 1),          # vA2a (forced anchor)
    ('R3.anchor_missing_method_or_status', 'B'): (0, 2),          # vB2a, vB2b
    ('R3.target_without_matching_anchor', 'B'): (0, 1),           # vB1 / art2
    ('R3.target_without_matching_anchor', 'C'): (0, 1),           # vC1 / art3
    ('R3.legacy_anchor_expression_differs_from_reference', 'C'): (1, 0),  # false positive, then a miss
    ('AG.declared_count_mismatch', 'D'): (0, 1),                  # vsD
    ('AG.in_scope_not_covered', 'D'): (0, 1),                     # vD3
    ('AG.exclusion_without_reason', 'D'): (0, 1),                 # vxD4
    ('R5.correction_missing_affected_aggregate', 'E'): (0, 1),    # vE1r
    ('R5.affected_aggregate_not_recomputed', 'E'): (0, 1),        # vE2r
    ('R5.current_aggregate_inconsistent', 'E'): (0, 2),           # vE1agg, vE2agg
    ('R5.corrected_original_lost', 'E'): (0, 1),                  # vE3r
    ('R6.contribution_without_status', 'F'): (0, 2),              # vF1, vF5
    ('R6.group_without_members', 'F'): (0, 1),                    # vsF5
    ('R6.examined_missing_fields', 'F'): (0, 1),                  # vsF2
    ('R6.excluded_without_reason', 'F'): (0, 1),                  # vsF4
    ('R6.unanswered_without_date', 'F'): (0, 1),                  # vsF3
}

# Report-only query: an absence is relative to a date and, where declared, a deadline.
DEADLINE = ("SELECT ?c ?asOf ?deadline (?asOf > ?deadline AS ?deadlinePassed) WHERE { ?pr px:responseDeadline ?deadline ; "
            "del:hasContribution ?c . ?s a px:ContributionStatus ; px:status 'unanswered' ; px:asOf ?asOf "
            "{ ?s px:statusOf ?c } UNION { ?s px:statusOf ?grp . ?grp px:hasMember ?c } }")


def load(case, variant):
    g = rdflib.Graph()
    g.parse(HERE / 'fixtures' / 'base.ttl')
    g.parse(HERE / 'fixtures' / f'{case}-{variant}.ttl')
    return g


def short(term):
    s = str(term)
    return s.rsplit(':', 1)[-1] if s.startswith('urn:') else s


def run(g, query):
    return [[short(x) if x is not None else None for x in row] for row in g.query(PREFIXES + query)]


def main():
    queries = {cid: (rule, desc, q) for cid, rule, _, desc, q in CHECKS}
    out = {'run_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
           'rdflib': rdflib.__version__, 'checks': []}
    failures = 0
    for (cid, case), (exp_ok, exp_bad) in EXPECTED.items():
        rule, desc, q = queries[cid]
        ok_rows, bad_rows = run(load(case, 'conform'), q), run(load(case, 'violation'), q)
        match = len(ok_rows) == exp_ok and len(bad_rows) == exp_bad
        failures += not match
        out['checks'].append({'id': cid, 'rule': rule, 'case': case, 'description': desc, 'query': q,
                              'expected': [exp_ok, exp_bad], 'observed': [len(ok_rows), len(bad_rows)],
                              'conform_rows': ok_rows, 'violation_rows': bad_rows, 'match': match})
        print(f"[{'ok ' if match else 'BAD'}] {case} {cid}: conform {len(ok_rows)} (exp {exp_ok}), "
              f"violation {len(bad_rows)} (exp {exp_bad}) {bad_rows}")
    out['deadline_report'] = {v: run(load('F', v), DEADLINE) for v in ('conform', 'violation')}
    print('deadline report', out['deadline_report'])
    out['mismatches'] = failures
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'results' / f'hard-cases-{datetime.date.today().isoformat()}.json'
    path.parent.mkdir(exist_ok=True)
    json.dump(out, open(path, 'w'), indent=1, ensure_ascii=False)
    print('written', path, '| mismatches:', failures)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
