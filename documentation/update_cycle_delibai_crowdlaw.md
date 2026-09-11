# Update cycle: source → DKG → semantic index → web interfaces

How DelibAI and CrowdLaw data are (re)imported, merged, indexed and deployed, and
how source, graph and index are kept consistent after updates, corrections or
authorised removals. All commands run from `/home/svagnoni/deliberation-knowledge-graph`
with the project virtualenv (`venv/bin/python3`).

## 0. Prerequisites

* `config/integration/delibai.local.json` (git-ignored) with the private
  `pseudonym_salt`. **Never change the salt**: pseudonyms would change and the
  re-import would create new participant URIs.
* `config/integration/crowdlaw.json` listing the documents to import.
* Access to the running `deliberative-postgres` container (DelibAI) and to
  `/home/svagnoni/portale-cittadino-mvp/backend/data/app.db` (CrowdLaw).

## 1. Export and import (idempotent)

```bash
# DelibAI: read-only export of the pilot tables (JSON, outside the repo)
scripts/integration/export_delibai_pilot.sh            # -> /home/svagnoni/delibai_analysis/dkg_export
venv/bin/python3 scripts/integration/import_delibai.py  # -> knowledge_graph/sources/delibai_pilot_kg.ttl
                                                        #    data/delibai/reconciliation_report.json
                                                        #    data/delibai/screening_report.json (exit code 1 if a text matches a personal-data pattern)

# CrowdLaw
venv/bin/python3 scripts/integration/import_crowdlaw.py # -> knowledge_graph/sources/crowdlaw_kg.ttl
                                                        #    data/crowdlaw/reconciliation_report.json
```

Both importers are deterministic: same snapshot → same triples. Check the
reconciliation reports (read / imported / excluded / failed per table, warnings)
before merging. Records that are incomplete or whose relations cannot be resolved
are listed under `warnings` and `exclusions`.

## 2. Merge into the main graph (with backup and explicit replacement)

```bash
venv/bin/python3 scripts/integration/merge_source_into_kg.py --source delibai  --file knowledge_graph/sources/delibai_pilot_kg.ttl
venv/bin/python3 scripts/integration/merge_source_into_kg.py --source crowdlaw --file knowledge_graph/sources/crowdlaw_kg.ttl
```

Several sources can be merged in one pass, loading and rewriting the 240 MB
graph only once (this is how the first deployment was done):

```bash
venv/bin/python3 scripts/integration/merge_source_into_kg.py \
  --source delibai    --file knowledge_graph/sources/delibai_pilot_kg.ttl \
  --source crowdlaw   --file knowledge_graph/sources/crowdlaw_kg.ttl \
  --source crosslinks --file knowledge_graph/sources/crosslinks_delibai_crowdlaw_kg.ttl
```

* A backup `knowledge_graph/backups/deliberation_kg_before_<sources>_<stamp>.ttl` is written first.
* If the source was merged before, the triples of the *previously merged version*
  (`knowledge_graph/sources/merged/<source>.ttl`) are removed before adding the new
  ones. This is the only deletion the pipeline performs; it is logged in
  `knowledge_graph/sources/merged/<source>.merge_log.json` and
  `merge_history.jsonl`, and the replaced version is archived under
  `knowledge_graph/sources/history/`.
* Re-merging an unchanged source is a no-op (`--dry-run` shows the counts).

Rollback: stop the servers, copy the backup file back to
`knowledge_graph/deliberation_kg.ttl`, restore the previous
`knowledge_graph/sources/merged/<source>.ttl` from `history/`, restart.

## 3. Cross-process links (after the sources, before the index)

```bash
venv/bin/python3 scripts/integration/infer_cross_links.py \
  --sources knowledge_graph/sources/delibai_pilot_kg.ttl knowledge_graph/sources/crowdlaw_kg.ttl \
  --index knowledge_graph/embeddings.pkl \
  --output knowledge_graph/sources/crosslinks_delibai_crowdlaw_kg.ttl
venv/bin/python3 scripts/integration/merge_source_into_kg.py --source crosslinks --file knowledge_graph/sources/crosslinks_delibai_crowdlaw_kg.ttl
```

Links are reified `del:ProcessLink` nodes with `del:linkType "inferred"`, method,
version, model and score; re-running replaces the previous link set.

## 4. Semantic index

```bash
venv/bin/python3 scripts/integration/update_embeddings_for_source.py --source delibai  --file knowledge_graph/sources/delibai_pilot_kg.ttl
venv/bin/python3 scripts/integration/update_embeddings_for_source.py --source crowdlaw --file knowledge_graph/sources/crowdlaw_kg.ttl
```

Each run drops every index entry with `metadata.source == <source>` and appends
the fresh documents (backup `knowledge_graph/embeddings_backup_before_<source>_<stamp>.pkl`).
Consequently the index never keeps documents for resources that were removed
from the graph, and every result keeps a stable `uri` that resolves in the graph.
Same model as production search (`paraphrase-multilingual-MiniLM-L12-v2`).

## 5. Deploy (restart the in-memory servers)

Both servers load `deliberation_kg.ttl` (and the citizen server also
`embeddings.pkl`) at start-up, so a restart publishes the new data:

```bash
# citizen.svagnoni.linkeddata.es (systemd unit citizen_interface.service, Restart=always)
pkill -f 'citizen_interface/backend/simple_server.py'   # systemd restarts it in 10 s; loading takes ~5-8 min
# dkg.svagnoni.linkeddata.es API (port 8085, no unit)
./start_dkg_server.sh
```

The static pages (`index.html`, `img/`) of dkg.svagnoni.linkeddata.es are served
directly by nginx from the repository checkout.

After a rewrite, check that no original triple was lost (full parse of backup
and new file, compare the non-blank-node triple sets); the first deployment's
check is recorded in `documentation/delibai_crowdlaw_reconciliation.md`.

## 6. Verify

```bash
venv/bin/python3 -m pytest tests/integration -q                 # mapping, counts, idempotency, reserved fields
venv/bin/python3 scripts/integration/verify_integration.py --base http://127.0.0.1:5001   # live API checks
node scripts/integration/browser_walkthrough.js https://citizen.svagnoni.linkeddata.es shots prod             # browser walk-through (puppeteer-core, 26 checks; evidence in documentation/evidence/)
```

## 7. Corrections and authorised removals

1. Fix or remove the record in the **source** (or add the exclusion rule to the
   importer/config with its reason), re-run the importer.
2. Re-run the merge (old version removed, new one added), the index update and
   the deploy. The graph, the index and the pages are rebuilt from the same
   source graph, so they cannot drift from each other.
3. Keep the backup and the `history/` copy; document the change in the
   reconciliation report notes if it is a data correction.

## 8. Order of operations (summary)

export → import → (tests) → merge sources → infer links → merge links →
update index → restart servers → verify in the browser.
