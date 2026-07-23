# Repository Structure

This repository contains code, data, ontology artifacts, public web assets, and
interoperability standards for the Deliberation Knowledge Graph.

## Main Entry Points

- `README.md` - project overview.
- `index.html` - public project website.
- `standards/` - ATProto Lexicons, ActivityPub JSON-LD context, and mapping notes.
- `ontologies/` - DEL ontology files and generated ontology documentation.
- `documentation/` - guides, deployment notes, reports, and research material.
- `knowledge_graph/` - generated RDF/JSON-LD/Turtle knowledge graph artifacts.
- `data/` - source and processed datasets.
- `citizen_interface/` - citizen-facing exploration interface.
- `scripts/` - data processing, download, and analysis scripts.

## Standards Layout

```text
standards/
  atproto/
    lexicons/org/deliberation/*.json
    dist/deliberation.lexicon.collection.json
  activitypub/
    deliberation-context.jsonld
    examples.jsonld
  docs/
    mapping-table.md
    feasibility-report.md
    dds-interoperability-roadmap.md
```

## Documentation Layout

```text
documentation/
  index.md
  project_structure.md
  data_models_overview.md
  guides/
  deployment/
  reports/status/
  research/
```

## Repository Hygiene

- Do not commit local credentials, tokens, `.env` files, cache folders, logs, or virtual environments.
- Large generated KG files and backups should be kept outside Git unless explicitly needed for a release.
- Public interoperability artifacts should live under `standards/`.
- Core ontology artifacts should live under `ontologies/`.

