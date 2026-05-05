# Deliberation Interoperability Standards

This directory contains machine-readable interoperability artifacts for the
Deliberation Ontology (DEL).

## Contents

- `atproto/lexicons/`: AT Protocol Lexicon documents for DEL classes.
- `atproto/dist/deliberation.lexicon.collection.json`: convenience bundle keyed by Lexicon ID.
- `activitypub/deliberation-context.jsonld`: JSON-LD context for ActivityPub/ActivityStreams extensions.
- `activitypub/examples.jsonld`: example ActivityPub objects using DEL terms.
- `docs/`: mapping and feasibility notes.

## Namespace Position

DEL terms remain under:

```text
https://w3id.org/deliberation/ontology#
```

The ATProto Lexicons currently use:

```text
org.deliberation.*
```

These files are not official DDS (`org.dds.*`) Lexicons. They are intended as
an interoperability layer that lets DEL/RDF deliberation data be consumed by
ATProto/DDS-style applications.

If DDS adopts or references these schemas, the expected integration path is via
`org.dds.ref.*`, a DDS product/module Lexicon, or an explicit DEL-DDS
interoperability profile.

