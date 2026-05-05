# DEL ActivityPub / JSON-LD Profile

This directory contains JSON-LD artifacts for using the Deliberation Ontology
with ActivityPub / ActivityStreams objects.

## Files

- `deliberation-context.jsonld`: JSON-LD context that exposes DEL classes and properties.
- `examples.jsonld`: example ActivityStreams objects extended with DEL terms.

## Usage

ActivityPub objects can include both ActivityStreams and DEL contexts:

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/deliberation/context.jsonld"
  ],
  "type": ["Note", "del:Argument"],
  "content": "An argument text",
  "supports": [{ "id": "https://example.org/positions/7" }]
}
```

The public deployment URL for `context.jsonld` still needs to be configured.

