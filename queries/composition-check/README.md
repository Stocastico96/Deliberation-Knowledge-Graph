# Record-level check of the composition rules

`verify_composition_rules.py` checks the five composition rules of the
participation-to-legislation framework (Vagnoni, PhD thesis, Section 2.7.2) on the
DelibAI pilot and CrowdLaw evaluation records imported into the public
Deliberation Knowledge Graph.

- 55 read-only SPARQL `GET` queries against <https://dkg.svagnoni.linkeddata.es/sparql>
- each check states the rule it bears on, the query, and the expected value
- no dependencies beyond the Python 3 standard library

```
python3 verify_composition_rules.py results/out.json
```

`results/composition-check-2026-10-15.json` is the run reported in the thesis
(Section 6.5.2, Table 6.2). Two rows were not reproducible on the re-run because
the endpoint returned HTTP 502 under load; their `status` field says so
(`AG.cluster_sizes`: partial; `AG.recomputed_stance`: values from the first run).

Scope: the check tests the data integration on the published snapshot. Rule 4
(confidence-gated escalation) cannot be checked there, because the snapshot holds
the stance labels of the NLI configuration and not the hybrid run.
