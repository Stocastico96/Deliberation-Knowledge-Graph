# Record-level check of the composition rules

`verify_composition_rules.py` checks the six composition rules of the
participation-to-legislation framework (Vagnoni, PhD thesis, Section 2.7.2) on the
DelibAI pilot and CrowdLaw evaluation records imported into the public
Deliberation Knowledge Graph.

- 55 read-only SPARQL `GET` queries against <https://dkg.svagnoni.linkeddata.es/sparql>
- each check states the rule it bears on, the query, and the expected value
- no dependencies beyond the Python 3 standard library

```
python3 verify_composition_rules.py results/out.json
```

`results/composition-check-2026-10-18.json` is the run reported in the thesis
(Section 6.5.2, Table 6.2). It differs from the run of 15 October 2026
(`results/composition-check-2026-10-15.json`) in two checks:

- `R3.anchor_expression_differs_from_reference` is replaced by
  `R3.target_without_matching_anchor`. The old query compared each anchor with the
  document the contribution references, but a cited source need not be the target;
  on synthetic records (`hard-cases/`, case C) it flags a correct record and misses a
  wrong one.
- `AG.cluster_sizes` completed on the endpoint (18 of 18 clusters consistent); on
  15 October it was partial because the endpoint returned HTTP 502 under load.

Scope: the check tests the data integration on the published snapshot. Rule 4
(confidence-gated escalation) cannot be checked there, because the snapshot holds
the stance labels of the NLI configuration and not the hybrid run; rule 6 has no
records, because no institution has responded through the framework.

`hard-cases/` checks the rules on synthetic records for the difficult cases of the
thesis (Table 2.3); see its README.
