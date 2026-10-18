# Composition rules on the hard cases (synthetic records)

The public graph contains none of the hard cases of Table 2.3 of the thesis: every
CrowdLaw comment has an anchor, no contribution has an institutional status, and no
aggregate has been recomputed after a correction. This folder checks whether the
composition rules of Section 2.7.2 can be tested on such cases, using records written
for the purpose.

- `fixtures/base.ttl`: a synthetic process, bill, cited constitution, reviewer and committee,
  and the list of proposed terms.
- `fixtures/<case>-conform.ttl`: records that follow the rules.
- `fixtures/<case>-violation.ttl`: records with defects planted on purpose; the header of each
  file lists them.
- `check_hard_cases.py`: 19 SPARQL checks, each run on the conforming and the violating
  records of its case and compared with counts fixed in `EXPECTED` before the run.
- `results/`: the output of each run.

| Case | Table 2.3 case | Rules |
|---|---|---|
| A | a proposal that concerns no article | 1, 3 |
| B | a comment that concerns several provisions | 3 |
| C | a comment that cites one text and targets another (Section 4.5) | 3 |
| D | a synthesis that omits a minority position (structural part only) | 1 |
| E | a correction that changes aggregates already computed | 5 |
| F | an institution that does not respond | 6 |

Terms with the `px:` prefix (`urn:del:proposed#`) are proposed for this test and are not
part of DEL: anchor status, routing decisions, aggregates and exclusions, institutional
status and contribution groups. Everything else uses DEL 1.1.1 / annotations 1.2.0-draft
and PROV-O.

What the result shows: each rule can be stated as a query that separates the planted
defects from conforming records. What it does not show: that the queries catch every way
a rule can be broken (records and queries have the same author), or that any platform
meets the rules. Case D checks that an aggregate decomposes into its contributions; whether
a textual summary keeps a minority reason is a human audit (thesis, Section 6.2(d)).

Case C also tests the rule-3 query used on the live graph until 15 October 2026, which
compared the anchor with the document the contribution references. It flags the
conforming record and misses the violating one, so `verify_composition_rules.py` now uses
`R3.target_without_matching_anchor` instead.

Run: `python3 check_hard_cases.py` (requires `rdflib`).
