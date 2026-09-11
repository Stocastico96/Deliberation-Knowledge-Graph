# CrowdLaw / Portale del Cittadino in the Deliberation Knowledge Graph

The Citizen Portal is a research prototype for public consultation on bills
encoded in Akoma Ntoso: citizens anchor comments to specific passages of a
specific version of the text, propose changes with a separate rationale, and the
analytics pipeline produces traceable stance labels, clusters and semantic
distance views (Vagnoni et al., *Enabling Traceable eParticipation in
Legislative Processes Using Akoma Ntoso*, ICEDEG 2026). It follows the
*crowdlaw* paradigm of technology-supported lawmaking.

## What is in the graph

The three **evaluation corpora** of the paper (synthetic comments seeded by the
research team with pseudonymous authors and ground-truth labels). They are not a
real public consultation and are marked `del:datasetStatus "synthetic-evaluation"`.

| Consultation | Bill | Articles | Comments |
|---|---|---|---|
| `res:crowdlaw_consultation_doc7` | Regolamentazione legale della cannabis (A.C. 18PDL0001140) | 17 | 74 |
| `res:crowdlaw_consultation_doc15` | Limiti agli emolumenti dei top manager (A.C. 18PDL0001060) | 7 | 38 |
| `res:crowdlaw_consultation_doc16` | Conflitto di interessi dei titolari di cariche di governo (A.C. 18PDL0014950) | 15 | 34 |

For every comment: author-chosen anchor (selected passage or declared article),
system-resolved anchor (SBERT cosine, with score and agreement flag), the exact
FRBR expression, stance label with method (seed ground truth / NLI model / LLM
fallback), cluster, PCA coordinates, and, when recorded in the platform's
composed format, the proposed change and its motivation. Bills are represented
as FRBR work → expression → provisions (articles and paragraph segments) with
automatic key aspects.

Excluded (counted in `reconciliation_report.json`): 13 duplicate-upload or
developer-test documents with 48 test comments; clusters without a stable key.

## Files

* `search_documents.json` – documents indexed for semantic search (contribution, legal_provision, process).
* Source graph: `knowledge_graph/sources/crowdlaw_kg.ttl` (regenerate with the importer).
* Mapping: `documentation/delibai_crowdlaw_integration.md`.

## Browse

* Citizen interface: https://citizen.svagnoni.linkeddata.es/?process=https%3A%2F%2Fsvagnoni.linkeddata.es%2Fresource%2Fcrowdlaw_consultation_doc7
* SPARQL examples: `queries/integration/crowdlaw_*.rq`

## Sources and licences

* Bills: CIRSFID GenAI4Lex Camera-Bill AKN collection (check upstream terms before redistributing the archive).
* Comments and annotations: research artefacts of the Citizen Portal repository (https://gitlab.com/CIRSFID/cititen-portal), CC BY 4.0 as part of this graph.
* No official logo exists for the prototype; the graph and the sites use a brand mark rendered from the application's CSS as a temporary fallback.
