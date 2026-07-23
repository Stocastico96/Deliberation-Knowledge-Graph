# DEL to Democracy Data Space - Interoperability Roadmap

Generated: 2026-04-29 UTC

Ontology used: DEL `1.0.0`, repository commit `e4037519f1a5b5adb3679443c54ff71a310fcb0e`

Assumptions:

- `dds.xyz` was not reachable from available web sources on 2026-04-29.
- The roadmap therefore uses the local DEL ontology plus public data-space principles from DSSC, IDSA, Dataspace Protocol, ActivityPub, and ATProto.
- The goal is not only publishing an ontology, but enabling practical interoperability among deliberation platforms.

## 1. Problem Statement

The core problem is not "convert RDF to JSON".

The real problem is:

> different democratic platforms produce similar civic objects, but with different identifiers, schemas, semantics, APIs, provenance models, permissions, and trust assumptions.

Examples:

- a Decidim proposal;
- a Polis statement;
- a Your Priorities point;
- an EU Have Your Say feedback item;
- a parliamentary intervention;
- a Talk to the City claim.

All may be "contributions", but they are not interoperable unless we define:

- shared meanings;
- shared identifiers;
- shared payloads;
- shared provenance;
- shared access/usage rules;
- shared publication and federation mechanisms.

## 2. What We Already Have

### DEL Ontology

The DEL ontology already gives us a semantic core:

- `DeliberationProcess`
- `Contribution`
- `Argument`
- `Position`
- `Participant`
- `Topic`
- `Evidence`
- `InformationResource`
- `Consensus`
- `Stage`
- `Forum`

It also provides deliberative relations:

- `supports`
- `attacks`
- `hasEvidence`
- `hasPremise`
- `hasConclusion`
- `madeBy`
- `responseTo`
- `hasTopic`

### ActivityPub / JSON-LD Mapping

Generated file:

- `/home/svagnoni/output/deliberation-context.jsonld`

Use:

- ActivityPub carries civic objects across federated servers.
- DEL terms keep deliberative semantics.

### ATProto Lexicon Mapping

Generated files:

- `/home/svagnoni/output/deliberation.lexicon.json`
- `/home/svagnoni/output/lexicons/*.json`

Use:

- ATProto validates structured civic records.
- DEL classes become ATProto record types.

### Rust Generator

Generated project:

- `/home/svagnoni/del_ontology_export`

Use:

```bash
cd /home/svagnoni/del_ontology_export
/home/svagnoni/.cargo/bin/cargo run
```

This uses Metagov's Rust `data_model_atproto` builder to generate Lexicon files.

## 3. Main Criticalities

### 3.1 Governance Criticality

If `dds.xyz` is meant to become the public identity of the project, it must be stable and reachable.

Needed:

- working website;
- public documentation;
- stable namespace policy;
- versioned ontology;
- published JSON-LD context;
- governance page explaining who maintains schemas and under which process.

### 3.2 Semantic Criticality

DEL lacks some classes needed for a full Democracy Data Space:

- `Decision`
- `Outcome`
- `Proposal`
- `Vote`
- `Reaction`
- `ModerationAction`
- `Platform`
- `Dataset`
- `DataService`
- `UsagePolicy`
- `ProvenanceRecord`

Without these, DEL models deliberation well but not yet the whole data-space lifecycle.

### 3.3 Protocol Criticality

ActivityPub, ATProto, RDF/SPARQL, and Dataspace Protocol solve different layers.

They should not be treated as alternatives:

- RDF/OWL: semantic model.
- JSON-LD: linked-data payloads.
- ActivityPub: federation of civic activities and objects.
- ATProto: signed/replicated structured records.
- Dataspace Protocol: catalog, contract negotiation, access, usage policies.
- SPARQL/API: query and reuse.

### 3.4 Identity Criticality

Democratic data needs actor identity:

- citizen;
- organization;
- institution;
- platform;
- moderator;
- algorithmic agent.

Needed:

- actor URI;
- DID or ActivityPub actor ID;
- ATProto DID/handle when available;
- optional verifiable credential;
- provenance relation between actor, platform, contribution, and process.

### 3.5 Trust and Usage Criticality

A data space is not just open data. It needs rules:

- who can access;
- under what licence;
- for what purpose;
- with what consent;
- with what retention policy;
- with what auditability.

DEL currently has limited support for this.

## 4. Interoperability Architecture

Target architecture:

```text
Platform adapters
  Decidim / Polis / Your Priorities / HYS / Parliament / TTTC
        |
        v
DEL Canonical Model
  RDF/OWL + JSON-LD profile + validation shapes
        |
        +--> ActivityPub federation
        +--> ATProto Lexicon records
        +--> SPARQL / Knowledge Graph
        +--> Dataspace catalog and contract layer
        +--> Research exports
```

The key principle:

> every platform-specific object must become a DEL canonical object before it is exported to protocols.

## 5. Required Profiles

### 5.1 DDS Core Profile

Minimum interoperable democratic object set:

- `Process`
- `Actor`
- `Contribution`
- `Argument`
- `Position`
- `Topic`
- `Evidence`
- `Decision/Outcome`
- `Provenance`
- `Policy`

### 5.2 DDS ActivityPub Profile

Defines how DEL objects travel in ActivityPub:

- `DeliberationProcess` -> `Collection`
- `Contribution` -> `Note`
- `Argument` -> `Note + del:Argument`
- `Participant` -> `Actor/Profile`
- `Evidence` -> `Document`
- `Consensus/Decision` -> `Object` or custom `Activity`

### 5.3 DDS ATProto Profile

Defines record families:

- `xyz.dds.deliberation.process`
- `xyz.dds.deliberation.argument`
- `xyz.dds.deliberation.contribution`
- `xyz.dds.deliberation.position`
- `xyz.dds.deliberation.participant`
- `xyz.dds.deliberation.evidence`
- `xyz.dds.deliberation.outcome`

Current generated NSIDs are under `org.deliberation.*`; they should be renamed if `dds.xyz` is the intended public namespace.

### 5.4 DDS Dataspace Profile

Defines data-space-level metadata:

- dataset catalog entry;
- provider;
- consumer;
- access policy;
- usage policy;
- licence;
- provenance;
- audit trail;
- connector/API endpoint.

## 6. Step-by-Step Plan

### Step 1 - Stabilize Public Namespace

Decision:

- use `https://w3id.org/deliberation/` for ontology terms;
- use `https://dds.xyz/` or `https://w3id.org/dds/` for data-space profiles;
- use ATProto NSIDs derived from the chosen domain.

Deliverables:

- public ontology URL;
- public context URL;
- public profile documentation.

### Step 2 - Extend DEL for Data Space Needs

Add classes/properties for:

- `Decision`
- `Outcome`
- `Proposal`
- `Vote`
- `Reaction`
- `Platform`
- `Dataset`
- `DataService`
- `UsagePolicy`
- `ProvenanceRecord`

Deliverables:

- updated OWL;
- changelog;
- migration notes;
- updated Lexicons and JSON-LD context.

### Step 3 - Add Validation Shapes

OWL describes meaning, but we also need validation.

Add SHACL shapes for:

- required fields;
- cardinalities;
- valid ranges;
- date formats;
- URI requirements;
- required provenance.

Deliverables:

- `deliberation-shapes.ttl`;
- validation script;
- CI check.

### Step 4 - Build Platform Adapters

Start with one real source.

Recommended first adapter:

- Your Priorities or Polis, because deliberative statements and votes map clearly to DEL.

Adapter output:

- DEL JSON-LD;
- RDF triples;
- ActivityPub object;
- ATProto record.

Deliverables:

- `adapter_yp_to_del`;
- sample dataset;
- mapping report;
- validation results.

### Step 5 - Build the DDS Catalog Layer

Every dataset/process should be discoverable.

Catalog object should include:

- dataset ID;
- title;
- provider;
- licence;
- access URL;
- API URL;
- SPARQL URL;
- temporal coverage;
- topics;
- usage policy;
- provenance.

Deliverables:

- `dds-catalog.jsonld`;
- catalog API;
- dataset examples.

### Step 6 - Add Federation

ActivityPub:

- expose process outbox;
- publish `Create`, `Update`, `Announce` for deliberation objects;
- accept replies or references from trusted actors.

ATProto:

- publish Lexicon package;
- create records for arguments, positions, topics, evidence;
- resolve DIDs/handles for actors.

Deliverables:

- ActivityPub payload examples;
- ATProto record examples;
- federation test report.

### Step 7 - Add Trust and Policy

Introduce:

- actor identity;
- organization identity;
- provenance;
- usage policy;
- consent/visibility level;
- moderation metadata;
- audit trail.

Deliverables:

- trust model;
- policy vocabulary;
- examples for public/open/restricted deliberation data.

## 7. Immediate Next Sprint

Recommended next 5 tasks:

1. Rename or decide final ATProto namespace: `org.deliberation.*` vs `xyz.dds.*`.
2. Add `Decision`, `Outcome`, `Proposal`, `Vote`, `Reaction`, `Platform`, `Dataset`, `UsagePolicy` to DEL.
3. Create SHACL shapes for the DDS Core Profile.
4. Build one working adapter from a real local dataset to DEL JSON-LD.
5. Publish a small static DDS catalog with 2-3 deliberation processes.

## 8. Success Criteria

The first usable Democracy Data Space exists when:

- a dataset from one platform is converted to DEL JSON-LD;
- it validates against SHACL;
- it is queryable as RDF/SPARQL;
- it has a catalog entry;
- it can be exported as ActivityPub object;
- it can be exported as ATProto record;
- its provenance and usage policy are explicit.

