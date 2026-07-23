<!-- Generated: 2026-04-28 10:20:15 UTC; DEL ontology version: 1.0.0; DEL commit: e4037519f1a5b5adb3679443c54ff71a310fcb0e; Assumptions: conservative mapping from local OWL; no cardinality axioms found. -->

| OWL Entity | Type | Lexicon NSID | AP JSON-LD key | Notes / Losses |
|---|---|---|---|---|
| del:Argument | owl:Class | `org.deliberation.argument` | `argument` / `@type: del:Argument` | as:Note; subclassOf Contribution not native in Lexicon |
| del:ArgumentStructure | owl:Class | `org.deliberation.argumentStructure` | `argumentStructure` / `@type: del:ArgumentStructure` | DEL extension only |
| del:Conclusion | owl:Class | `org.deliberation.conclusion` | `conclusion` / `@type: del:Conclusion` | DEL extension only; subclassOf ArgumentStructure not native in Lexicon |
| del:Consensus | owl:Class | `org.deliberation.consensus` | `consensus` / `@type: del:Consensus` | as:Object |
| del:Contribution | owl:Class | `org.deliberation.contribution` | `contribution` / `@type: del:Contribution` | as:Note |
| del:CrossPlatformIdentifier | owl:Class | `org.deliberation.crossPlatformIdentifier` | `crossPlatformIdentifier` / `@type: del:CrossPlatformIdentifier` | DEL extension only |
| del:DeliberationProcess | owl:Class | `org.deliberation.deliberationProcess` | `deliberationProcess` / `@type: del:DeliberationProcess` | as:Collection / as:Activity context |
| del:Evidence | owl:Class | `org.deliberation.evidence` | `evidence` / `@type: del:Evidence` | DEL extension only |
| del:FallacyType | owl:Class | `org.deliberation.fallacyType` | `fallacyType` / `@type: del:FallacyType` | DEL extension only |
| del:Forum | owl:Class | `org.deliberation.forum` | `forum` / `@type: del:Forum` | as:Place or as:Collection |
| del:InformationResource | owl:Class | `org.deliberation.informationResource` | `informationResource` / `@type: del:InformationResource` | as:Document |
| del:LegalSource | owl:Class | `org.deliberation.legalSource` | `legalSource` / `@type: del:LegalSource` | as:Document; subclassOf InformationResource not native in Lexicon |
| del:Organization | owl:Class | `org.deliberation.organization` | `organization` / `@type: del:Organization` | as:Organization |
| del:Participant | owl:Class | `org.deliberation.participant` | `participant` / `@type: del:Participant` | as:Profile / as:Actor |
| del:Position | owl:Class | `org.deliberation.position` | `position` / `@type: del:Position` | DEL extension only |
| del:Premise | owl:Class | `org.deliberation.premise` | `premise` / `@type: del:Premise` | DEL extension only; subclassOf ArgumentStructure not native in Lexicon |
| del:Role | owl:Class | `org.deliberation.role` | `role` / `@type: del:Role` | DEL extension only |
| del:Stage | owl:Class | `org.deliberation.stage` | `stage` / `@type: del:Stage` | as:Event approximation |
| del:Topic | owl:Class | `org.deliberation.topic` | `topic` / `@type: del:Topic` | as:Topic approximation |
| del:attacks | owl:ObjectProperty | field on domain records | `attacks` | range del:Argument or del:Position; multi-valued @set; union range loses OWL class-expression semantics in Lexicon; Indicates that an argument attacks another argument or position. |
| del:containsFallacy | owl:ObjectProperty | field on domain records | `containsFallacy` | range del:FallacyType; multi-valued @set; Indicates that an argument contains a specific type of logical fallacy. |
| del:hasArgument | owl:ObjectProperty | field on domain records | `hasArgument` | range del:Argument; multi-valued @set; Relates a deliberation process to arguments made within it. |
| del:hasConclusion | owl:ObjectProperty | field on domain records | `hasConclusion` | range del:Conclusion; multi-valued @set; Relates an argument to its conclusion. |
| del:hasContribution | owl:ObjectProperty | field on domain records | `hasContribution` | range del:Contribution; multi-valued @set; Relates a deliberation process to contributions made within it. |
| del:hasEvidence | owl:ObjectProperty | field on domain records | `hasEvidence` | range del:Evidence; multi-valued @set; Relates an argument or premise to supporting evidence. |
| del:hasParticipant | owl:ObjectProperty | field on domain records | `hasParticipant` | range del:Participant; multi-valued @set; Relates a deliberation process to its participants. |
| del:hasPremise | owl:ObjectProperty | field on domain records | `hasPremise` | range del:Premise; multi-valued @set; Relates an argument to its premises. |
| del:hasRole | owl:ObjectProperty | field on domain records | `hasRole` | range del:Role; multi-valued @set; Relates a participant to their role in a deliberation. |
| del:hasStage | owl:ObjectProperty | field on domain records | `hasStage` | range del:Stage; multi-valued @set; Relates a deliberation process to its stages. |
| del:hasTopic | owl:ObjectProperty | field on domain records | `hasTopic` | range del:Topic; multi-valued @set; Relates a deliberation process to its topic. |
| del:isAffiliatedWith | owl:ObjectProperty | field on domain records | `isAffiliatedWith` | range del:Organization; multi-valued @set; Relates a participant to organizations they are affiliated with. |
| del:madeBy | owl:ObjectProperty | field on domain records | `madeBy` | range del:Participant; multi-valued @set; Relates a contribution to the participant who made it. |
| del:references | owl:ObjectProperty | field on domain records | `references` | range del:InformationResource; multi-valued @set; Relates a contribution or argument to information resources it references. |
| del:responseTo | owl:ObjectProperty | field on domain records | `responseTo` | range del:Contribution; multi-valued @set; Relates a contribution to another contribution it responds to. |
| del:supports | owl:ObjectProperty | field on domain records | `supports` | range del:Argument or del:Position; multi-valued @set; union range loses OWL class-expression semantics in Lexicon; Indicates that an argument supports another argument or position. |
| del:takesPlaceIn | owl:ObjectProperty | field on domain records | `takesPlaceIn` | range del:Forum; multi-valued @set; Relates a deliberation process to the forum where it takes place. |
| del:country | owl:DatatypeProperty | field on domain records | `country` | range xsd:string; literal datatype preserved approximately; The country of origin of a participant (ISO 3166-1 alpha-3 code). |
| del:endDate | owl:DatatypeProperty | field on domain records | `endDate` | range xsd:dateTime; literal datatype preserved approximately; The end date and time of a deliberation process or stage. |
| del:identifier | owl:DatatypeProperty | field on domain records | `identifier` | range xsd:string; literal datatype preserved approximately; A unique identifier for an entity. |
| del:name | owl:DatatypeProperty | field on domain records | `name` | range xsd:string; literal datatype preserved approximately; The name of an entity. |
| del:participantType | owl:DatatypeProperty | field on domain records | `participantType` | range xsd:string; literal datatype preserved approximately; The type or status of participant (e.g., EU_CITIZEN, NON_EU_CITIZEN, COMPANY, NGO, PUBLIC_AUTHORITY, ACADEMIC_RESEARCH_INSTITUTION). |
| del:platformIdentifier | owl:DatatypeProperty | field on domain records | `platformIdentifier` | range xsd:string; literal datatype preserved approximately; An identifier specific to a particular platform. |
| del:startDate | owl:DatatypeProperty | field on domain records | `startDate` | range xsd:dateTime; literal datatype preserved approximately; The start date and time of a deliberation process or stage. |
| del:text | owl:DatatypeProperty | field on domain records | `text` | range xsd:string; literal datatype preserved approximately; The textual content of a contribution, argument, position, premise, or conclusion. |
| del:timestamp | owl:DatatypeProperty | field on domain records | `timestamp` | range xsd:dateTime; literal datatype preserved approximately; The date and time when a contribution was made. |
| del:url | owl:DatatypeProperty | field on domain records | `url` | range xsd:anyURI; xsd:anyURI represented as string in Lexicon; @id in JSON-LD; The URL of an information resource. |
