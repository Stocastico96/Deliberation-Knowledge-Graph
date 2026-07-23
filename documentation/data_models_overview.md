# Deliberation Knowledge Graph - Data Models Overview

This document provides an overview of the data models used in the Deliberation Knowledge Graph project, focusing on the core ontology classes and their relationships.

## Core Ontology Classes

The Deliberation Knowledge Graph is built around the following core classes:

### DeliberationProcess

Represents a deliberative process, such as a debate, consultation, or participatory decision-making process.

**Properties:**
- `del:identifier` - Unique identifier for the process
- `del:name` - Name of the process
- `del:startDate` - Start date of the process
- `del:endDate` - End date of the process
- `del:hasTopic` - Topics discussed in the process
- `del:hasParticipant` - Participants in the process
- `del:hasContribution` - Contributions made during the process
- `del:hasStage` - Stages of the process

### Participant

Represents a person or organization participating in a deliberative process.

**Properties:**
- `del:identifier` - Unique identifier for the participant
- `del:name` - Name of the participant
- `del:hasRole` - Role of the participant in the process
- `del:isAffiliatedWith` - Organization the participant is affiliated with

### Contribution

Represents a contribution made by a participant during a deliberative process, such as a speech, comment, or proposal.

**Properties:**
- `del:identifier` - Unique identifier for the contribution
- `del:text` - Text of the contribution
- `del:timestamp` - Time when the contribution was made
- `del:madeBy` - Participant who made the contribution
- `del:responseTo` - Another contribution this contribution responds to
- `del:hasArgument` - Arguments contained in the contribution
- `del:containsFallacy` - Fallacies detected in the contribution

### Topic

Represents a topic discussed in a deliberative process.

**Properties:**
- `del:identifier` - Unique identifier for the topic
- `del:name` - Name of the topic

### Argument

Represents an argument made in a contribution.

**Properties:**
- `del:identifier` - Unique identifier for the argument
- `del:text` - Text of the argument
- `del:hasPremise` - Premises of the argument
- `del:hasConclusion` - Conclusion of the argument
- `del:supports` - Another argument this argument supports
- `del:attacks` - Another argument this argument attacks

### FallacyType

Represents a type of logical fallacy that may be detected in a contribution.

**Properties:**
- `del:identifier` - Unique identifier for the fallacy type
- `del:name` - Name of the fallacy type
- `del:confidence` - Confidence score of the fallacy detection

### ArtificialAgent *(since 1.1.0)*

Subclass of `del:Participant` for non-human participants: AI systems, bots, and algorithms (moderation systems, clustering models, LLM summarizers). Attributing machine-generated contributions and classifications to an `ArtificialAgent` keeps them distinguishable from human input. Aligned with `prov:SoftwareAgent`.

### Facilitator *(since 1.1.0)*

Subclass of `del:Role` for the role of hosting, guiding, or moderating a deliberation. A facilitating entity (individual, organization, or artificial agent) is modeled as a `Participant` with `del:hasRole` pointing to a `Facilitator` role.

### Reaction *(since 1.1.0)*

Subclass of `del:Contribution` for lightweight evaluative contributions: votes, ratings, endorsements.

**Properties:**
- `del:responseTo` - The contribution being reacted to
- `del:reactionType` - Kind of reaction (AGREE, DISAGREE, NEUTRAL, SCORE, QUADRATIC_VOTE)
- `del:reactionValue` - Numeric strength, where applicable

Aggregate counts published by source platforms are captured on the target contribution with `del:agreeCount` / `del:disagreeCount`.

## Class Relationships

The following diagram illustrates the relationships between the core classes:

```
DeliberationProcess
  |
  |-- hasTopic --> Topic
  |
  |-- hasParticipant --> Participant
  |     |
  |     |-- hasRole --> Role
  |     |
  |     |-- isAffiliatedWith --> Organization
  |
  |-- hasContribution --> Contribution
  |     |
  |     |-- madeBy --> Participant
  |     |
  |     |-- responseTo --> Contribution
  |     |
  |     |-- hasArgument --> Argument
  |     |     |
  |     |     |-- hasPremise --> Premise
  |     |     |
  |     |     |-- hasConclusion --> Conclusion
  |     |     |
  |     |     |-- supports --> Argument
  |     |     |
  |     |     |-- attacks --> Argument
  |     |
  |     |-- containsFallacy --> FallacyType
  |
  |-- hasStage --> Stage
```

## Dataset-Specific Models

Each dataset in the Deliberation Knowledge Graph project has its own specific data model, which is mapped to the core ontology. Here's an overview of the dataset-specific models:

### EU Parliament Debates

The EU Parliament debates dataset represents plenary session debates with the following structure:

- Each debate is a `DeliberationProcess`
- Speakers are `Participant` instances with roles (e.g., MEP, President)
- Political groups are `Organization` instances
- Speeches are `Contribution` instances
- Debate topics are `Topic` instances

### Decide Madrid

The Decide Madrid dataset represents citizen proposals and comments with the following structure:

- Each proposal is a `DeliberationProcess`
- Citizens are `Participant` instances
- Proposals are `Contribution` instances
- Comments are `Contribution` instances with `responseTo` relationships
- Categories are `Topic` instances

### DeliData

The DeliData dataset represents multi-party problem-solving conversations with the following structure:

- Each conversation is a `DeliberationProcess`
- Participants are `Participant` instances
- Messages are `Contribution` instances
- Issues are `Topic` instances

### EU Have Your Say

The EU Have Your Say dataset represents public consultations with the following structure:

- Each consultation is a `DeliberationProcess`
- Citizens and organizations are `Participant` instances
- Feedback items are `Contribution` instances
- Policy areas are `Topic` instances

### Habermas Machine

The Habermas Machine dataset represents deliberative democracy experiments with the following structure:

- Each experiment is a `DeliberationProcess`
- Participants are `Participant` instances
- Messages are `Contribution` instances
- Discussion topics are `Topic` instances

### Decidim Barcelona

The Decidim Barcelona dataset represents participatory democracy processes with the following structure:

- Each process is a `DeliberationProcess`
- Citizens are `Participant` instances
- Proposals and comments are `Contribution` instances
- Categories are `Topic` instances

### US Supreme Court Arguments

The US Supreme Court arguments dataset represents oral arguments with the following structure:

- Each case is a `DeliberationProcess`
- Justices and attorneys are `Participant` instances with roles
- Utterances are `Contribution` instances
- Legal issues are `Topic` instances

## Ontology Mappings

The Deliberation Knowledge Graph ontology is mapped to several standard ontologies:

### FOAF Mappings

- `del:Participant` ↔ `foaf:Person`
- `del:Organization` ↔ `foaf:Organization`
- `del:Group` ↔ `foaf:Group`

### SIOC Mappings

- `del:Contribution` ↔ `sioc:Post`
- `del:DeliberationProcess` ↔ `sioc:Forum`
- `del:Participant` ↔ `sioc:UserAccount`
- `del:Topic` ↔ `sioc:Topic`

### Dublin Core Mappings

- `del:title` ↔ `dc:title`
- `del:description` ↔ `dc:description`
- `del:creator` ↔ `dc:creator`
- `del:date` ↔ `dc:date`

### AIF Mappings

- `del:Argument` ↔ `aif:Argument`
- `del:Premise` ↔ `aif:Premise`
- `del:Conclusion` ↔ `aif:Conclusion`
- `del:supports` ↔ `aif:supports`
- `del:attacks` ↔ `aif:attacks`

### Metagov Deliberation Interoperability Project (DIP) Mappings

The [Metagov Deliberation Interoperability Project](https://github.com/metagov/ontology) defines a platform-neutral data model (with RDF, JSON Schema and AT Protocol `org.deliberation.*` lexicon exports) for civic deliberation platforms such as Polis, HeyForm and Talk to the City. DEL aligns to the URIs its RDF export currently emits (DIP is pre-release; mappings will be revisited once it publishes stable identifiers):

- `del:Contribution` ↔ DIP `Statement` (`org.deliberation.statement`)
- `del:Participant` ↔ DIP `Person` (`org.deliberation.person`, exported as `schema:Person`)
- `del:DeliberationProcess` ↔ DIP `Project` (`org.deliberation.project`)
- `del:Forum` ↔ DIP `Location` (`org.deliberation.location`)
- `del:responseTo` ↔ DIP `inResponseTo`; `del:text` ↔ DIP `content`; `del:madeBy` ↔ DIP `madeBy`

Complementary coverage: DIP models moderation and algorithmic grouping; DEL models argument structure (premises, conclusions, support/attack, fallacies) and legal sources. Since DEL 1.1.0, both models cover reactions/voting and machine attribution: `del:Reaction` (with `reactionType`/`reactionValue`, plus aggregate `agreeCount`/`disagreeCount`) corresponds to DIP `Reaction`, `del:ArtificialAgent` to DIP's `Generator::Algorithm` attribution, and `del:Facilitator` to DIP's `Generator::Host`. See also the [W3C Decentralized Deliberation Stack (DDS) Community Group](https://www.w3.org/community/dds/), where the relationship between DEL and the DDS specification is under discussion ([dds-wg/dds#20](https://github.com/dds-wg/dds/issues/20)).

## Data Conversion Process

The data conversion process for each dataset follows these steps:

1. **Data Extraction**: Extract data from the source format (CSV, JSON, XML, etc.)
2. **Data Cleaning**: Clean and normalize the data
3. **Data Mapping**: Map the data to the deliberation ontology structure
4. **RDF Generation**: Generate RDF/XML output compatible with the knowledge graph
5. **Validation**: Validate the RDF output against the ontology

## Example Data Instance

Here's an example of a data instance in JSON-LD format:

```json
{
  "@context": {
    "del": "https://w3id.org/deliberation/ontology#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@type": "del:DeliberationProcess",
  "del:identifier": "ep_debate_20250310",
  "del:name": "European Parliament Debate - 2025-03-10",
  "del:startDate": "2025-03-10T09:00:00Z",
  "del:endDate": "2025-03-10T18:00:00Z",
  "del:hasTopic": [
    {
      "@type": "del:Topic",
      "del:identifier": "topic_1",
      "del:name": "Climate Change"
    }
  ],
  "del:hasParticipant": [
    {
      "@type": "del:Participant",
      "del:identifier": "participant_1",
      "del:name": "Iratxe García Pérez",
      "del:hasRole": {
        "@type": "del:Role",
        "del:name": "Member of European Parliament"
      },
      "del:isAffiliatedWith": {
        "@type": "del:Organization",
        "del:name": "S&D"
      }
    }
  ],
  "del:hasContribution": [
    {
      "@type": "del:Contribution",
      "del:identifier": "contribution_1",
      "del:text": "We must take immediate action on climate change.",
      "del:timestamp": "2025-03-10T09:15:00Z",
      "del:madeBy": {"@id": "participant_1"}
    }
  ]
}
```

## Conclusion

The Deliberation Knowledge Graph data models provide a flexible and extensible framework for representing deliberative processes across different platforms and contexts. By mapping diverse datasets to a common ontology, the project enables cross-dataset analysis and insights into deliberative processes.
