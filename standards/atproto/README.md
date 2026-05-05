# DEL ATProto Lexicons

This directory contains AT Protocol Lexicon documents generated from the
Deliberation Ontology.

## Individual Lexicons

The deployable Lexicon files are in:

```text
lexicons/org/deliberation/
```

Each file corresponds to one Lexicon NSID:

```text
lexicons/org/deliberation/argument.json
  -> org.deliberation.argument

lexicons/org/deliberation/deliberationProcess.json
  -> org.deliberation.deliberationProcess
```

## Convenience Bundle

`dist/deliberation.lexicon.collection.json` is a map of Lexicon ID to Lexicon
document. It is useful for browsing and tooling, but individual files are the
preferred form for ATProto Lexicon consumption.

## DDS Relationship

These are DEL Lexicons, not official DDS Lexicons. They can be referenced from
DDS records or mapped into future `org.dds.module.*` / `org.dds.ref.*`
schemas.

