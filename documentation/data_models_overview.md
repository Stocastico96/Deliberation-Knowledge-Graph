# Data Models and Ontologies in the Deliberation/Argumentation Domain

This document provides an overview of relevant data models and ontologies in the deliberation and argumentation domain, based on the Ontology Requirements Specification Document (ORSD) for the Deliberation Knowledge Graph.

## Existing Ontologies and Their Limitations

| Name | Description | Format | Application Area | Strengths | Limitations |
|------|-------------|--------|-----------------|-----------|-------------|
| DELIB Ontology | Models e-participation deliberation process with social media integration | OWL | E-participation, deliberative democracy | Explicitly supports dual e-participation (government and citizen-led); connects deliberation with social media content; comprehensive conceptualization of topic, claim, argument structure | Focused primarily on electronic participation; lacks detailed representation of legal frameworks; limited implementation examples |
| Deliberation Ontology | Supports public decision making in policy deliberations | OWL | Policy deliberation, legal information integration | Strong focus on legal information integration; connects arguments with legal sources; emphasizes bureaucratic process modeling | Government-centric approach; limited participant modeling; does not account for informal deliberation spaces |
| SIOC (Semantically Interlinked Online Communities) | Describes online discussion information structure | OWL/RDF | Online discussions, social media | Well-established standard; robust representation of online discussions; widely used in social media applications | Not specifically designed for deliberation; lacks political and legal conceptualization; no deliberation-specific reasoning capabilities |
| AIF (Argument Interchange Format) | Represents argument structure and relations | OWL/RDF | Computational argumentation, argument mining | Sophisticated argument modeling; captures support/attack relationships; strong theoretical foundation | Complex for non-expert users; focused only on argumentation, not broader deliberation processes; limited integration with other aspects of deliberation |
| LKIF (Legal Knowledge Interchange Format) | Facilitates communication between legal knowledge systems | OWL | Legal reasoning, legal knowledge representation | Comprehensive legal information modeling; supports complex legal reasoning; structured legal source representation | Highly specialized for legal domain; overly complex for general deliberation needs; lacks direct connection to civic participation concepts |
| IBIS (Issue-Based Information System) | Models issues, positions, and arguments | Various | Design rationale, collaborative problem-solving | Simple, intuitive structure; explicitly separates issues, positions, and arguments; widely used in design rationale | Limited expressivity for complex deliberations; no participant or process modeling; lacks temporal dimension |

## Why a New Deliberation Knowledge Graph is Needed

Despite the availability of multiple ontologies in related domains, a unified Deliberation Knowledge Graph is necessary for several reasons:

1. **Integration Gap**: None of the existing ontologies adequately bridges formal institutional deliberation with civic participation platforms. The del addresses this by creating mappings between these domains.

2. **Fallacy Detection Support**: Existing ontologies lack the specific structures required for computational identification of logical fallacies in deliberative discourse. The del explicitly models argument patterns needed for automated fallacy detection.

3. **Cross-Dataset Standardization**: Current deliberation data exists in heterogeneous formats across platforms. The del provides a common semantic framework to normalize and integrate these diverse datasets.

4. **Fragmentation**: Each existing ontology covers only part of the deliberation ecosystem. The del provides a comprehensive framework that connects process, participants, content, and information in a coherent structure.

5. **Interoperability Challenges**: Current solutions operate in silos, making cross-platform analysis difficult. The del establishes common semantics to enable data sharing across different deliberation environments.

6. **Multi-perspective Integration**: Existing approaches typically adopt either a government-centric or citizen-centric perspective. The del supports multiple viewpoints simultaneously.

7. **Technical Evolution**: New deliberation platforms and technologies emerge regularly. The del's modular approach allows extension to incorporate new deliberation forms while maintaining backward compatibility.

8. **Research-Practice Gap**: Current ontologies are either too theoretical or too implementation-specific. The del balances conceptual rigor with practical applicability.

## Purpose and Scope of the Deliberation Knowledge Graph

### Purpose
The purpose of the Deliberation Knowledge Graph is to create a comprehensive, interoperable data model that represents deliberative processes across different platforms and contexts. This knowledge graph aims to structure and connect the various elements of deliberations (participants, arguments, processes, and information) in a way that enables analysis, visualization, and comparison of deliberative activities across platforms, from formal parliamentary debates to citizen participation initiatives. The ontology specifically addresses requirements for logical fallacy detection in deliberative discourse and provides a unified representation of common elements across diverse deliberation datasets.

### Scope
The ontology covers the domain of deliberative processes in both institutional and civic contexts. It encompasses:

- Formal deliberation processes (e.g., parliamentary debates, legislative procedures)
- Participatory deliberation platforms (e.g., Decidim, civic consultation tools)
- Arguments and contributions exchanged during deliberations
- Participants and their roles in deliberative processes
- Information resources that inform or result from deliberations
- Temporal and thematic organization of deliberative content
- Logical fallacy patterns and classifications
- Common structures and fields across different deliberation platforms and datasets
- Standard argument components required for fallacy detection

The ontology explicitly excludes:
- Detailed representation of document content beyond what's relevant to deliberation
- Internal platform-specific technical details not related to deliberative processes
- Implementation details of fallacy detection algorithms (focusing instead on required data structures)

## Intended End-Users and Uses

### End-Users
1. Government officials and policy makers who need to analyze and understand deliberative processes
2. Civic participation platform administrators who want to integrate deliberative content across platforms
3. Researchers studying deliberative democracy and analyzing deliberative data
4. Developers creating applications that connect or visualize deliberative content from multiple sources
5. Citizens and civic organizations seeking to understand and participate in deliberative processes
6. Fallacy detection system developers who require structured argument data
7. Cross-platform data analysts who need to work with multiple deliberation datasets

### Intended Uses
1. Integration of deliberative content from multiple platforms and sources to create unified views of participation
2. Analysis of deliberative processes to understand participation patterns, argument flows, and information usage
3. Visualization of deliberation structures and their evolution over time
4. Importing/exporting deliberative content between different systems (e.g., from Decidim to parliamentary systems)
5. Creation of searchable repositories of deliberative content with rich semantic relationships
6. Enabling the development of tools to support more effective deliberation processes
7. Automated detection and flagging of logical fallacies in arguments
8. Standardized representation of deliberation data from heterogeneous sources
9. Training and validation of AI models for argument analysis

## Key Competency Questions

The Deliberation Knowledge Graph is designed to answer the following groups of competency questions:

### Deliberation Process Structure
- What are the stages of a specific deliberation process?
- When did a particular deliberation start and end?
- What deliberation processes exist on a particular topic?
- What are the participation rules for a deliberation process?
- Which organization or entity is responsible for a specific deliberation process?

### Participant Information
- Who are the participants in a specific deliberation?
- What is the role of a participant in a deliberation process?
- In which deliberations has a particular participant contributed?
- Which organizations are represented in a deliberation?
- How many participants were involved in a deliberation process?

### Contributions and Arguments
- What contributions were made in a specific deliberation?
- Who made a specific contribution or argument?
- Which arguments support or oppose a specific position?
- What is the thread structure of a deliberative conversation?
- Which contributions received the most responses or engagement?

### Information Resources
- What information sources are referenced in contributions?
- What legal documents are referenced in a deliberation?
- What information frameworks are relevant to a specific deliberation?
- What documents were produced as a result of a deliberation?
- How is legal information structured and referenced in deliberations?

### Fallacy Detection
- What logical fallacies can be identified in a specific argument?
- What are the premise-conclusion relationships in an argument?
- Which arguments contain ad hominem attacks?
- What patterns of circular reasoning exist in a deliberation?
- How can arguments be classified by fallacy type?
- What evidence is provided to support a claim?

### Cross-Dataset Integration
- What common fields exist across different deliberation platforms?
- How can participant identities be reconciled across platforms?
- What standard argument elements can be mapped across datasets?
- How are temporal aspects of deliberation represented consistently?
- What minimal data structure is required for cross-platform analysis?

## Core Concepts in the Deliberation Knowledge Graph

Based on the competency questions and the pre-glossary of terms, the Deliberation Knowledge Graph will model the following core concepts:

- **DeliberationProcess**: The overall deliberative activity, including its stages, timeline, and outcomes
- **Stage**: A distinct phase in a deliberation process with specific activities and goals
- **Participant**: Individuals or entities taking part in a deliberation process
- **Role**: The function or position a participant holds in a deliberation
- **Organization**: Formal entities represented in or responsible for deliberations
- **Contribution**: Any input provided by a participant in a deliberation
- **Argument**: A structured form of contribution with premises and conclusions
- **Position**: A stance or viewpoint on an issue under deliberation
- **Topic**: The subject matter of a deliberation
- **InformationResource**: External sources of information referenced in deliberations
- **LegalSource**: Legal documents, frameworks, or interpretations relevant to deliberations
- **FallacyType**: Classification of logical fallacies that can occur in arguments
- **ArgumentStructure**: The formal structure of an argument, including premises and conclusions
- **Evidence**: Supporting information for claims made in arguments
- **CrossPlatformIdentifier**: Mechanisms to link entities across different deliberation platforms
