<!-- Generated: 2026-04-28 10:20:15 UTC; DEL ontology version: 1.0.0; DEL commit: e4037519f1a5b5adb3679443c54ff71a310fcb0e; Assumptions: analysis based on local ontologies/deliberation.owl and imported mappings.owl plus metagov/ontology commit e5d3312aa0da481429ef4545ac172b668ead5f55. -->

# Feasibility Report

## Fase 0 - Inventario DEL

- Ontologia principale: `/home/svagnoni/deliberation-knowledge-graph/ontologies/deliberation.owl`
- Base URI: `https://w3id.org/deliberation/ontology`
- Namespace DEL: `https://w3id.org/deliberation/ontology#`
- Versione: `1.0.0`; modified: `2025-12-22`
- Import: https://w3id.org/deliberation/mappings
- Classi OWL (19): `Argument`, `ArgumentStructure`, `Conclusion`, `Consensus`, `Contribution`, `CrossPlatformIdentifier`, `DeliberationProcess`, `Evidence`, `FallacyType`, `Forum`, `InformationResource`, `LegalSource`, `Organization`, `Participant`, `Position`, `Premise`, `Role`, `Stage`, `Topic`
- Object properties (17): `attacks`, `containsFallacy`, `hasArgument`, `hasConclusion`, `hasContribution`, `hasEvidence`, `hasParticipant`, `hasPremise`, `hasRole`, `hasStage`, `hasTopic`, `isAffiliatedWith`, `madeBy`, `references`, `responseTo`, `supports`, `takesPlaceIn`
- Data properties (10): `country`, `endDate`, `identifier`, `name`, `participantType`, `platformIdentifier`, `startDate`, `text`, `timestamp`, `url`

`mappings.owl` aggiunge allineamenti SKOS verso FOAF, Dublin Core, SIOC, SIOC Argue, AIF e LKIF. Questi mapping sono utili per ActivityPub/JSON-LD, ma non forniscono cardinalità o trasformazioni operative verso Lexicon.

## A. Fattibilità Generale

La mappatura a JSON-LD/ActivityPub è fattibile con perdita bassa perché DEL è già RDF/OWL e ActivityPub accetta estensioni JSON-LD. La mappatura a ATProto Lexicon è fattibile come schema applicativo, ma non senza perdita semantica: Lexicon non rappresenta inferenza OWL, `rdfs:subClassOf`, `owl:unionOf`, import ontologici, proprietà aperte, assiomi SKOS o semantica RDF completa.

Concetti che si mappano bene: `Contribution`/`Argument` come contenuti tipo `as:Note`, `Participant` come actor/profile, `Organization` come `as:Organization`, `InformationResource`/`LegalSource` come documenti o link, `DeliberationProcess` come collection/context, proprietà testuali e temporali come literal.

Concetti problematici: `ArgumentStructure`, `Premise`, `Conclusion`, `supports`, `attacks` e `containsFallacy` richiedono estensioni DEL perché ActivityStreams non ha un modello argomentativo. `Consensus` è un outcome deliberativo ma non equivale a `Decision`: l’ontologia locale non dichiara classi `Decision` o `Outcome`. `Forum` può essere `Place`, `Collection` o endpoint/piattaforma, a seconda del caso.

Concetti senza equivalente diretto: `FallacyType`, `CrossPlatformIdentifier`, `Role`, `Stage` come fase processuale deliberativa, e le relazioni argomentative formali. Vanno mantenuti come termini `del:`.

## B. Cosa Serve - Lexicon (ATProto)

Serve un set di Lexicon record con NSID sotto `org.deliberation.*`. Le classi OWL diventano record, le object property diventano campi `ref`, `array` o `union`, e le data property diventano primitive (`string`, `datetime`, `integer`, `boolean`). Poiché l’OWL locale non contiene `owl:minCardinality` o restrizioni cardinali, il campo `required` resta vuoto.

Tool necessari: validatore/CLI `lex` o tooling ATProto equivalente, specifica JSON Lexicon, e idealmente un generatore RDF/OWL -> Lexicon che oggi non è presente nel repo Metagov. I record generati qui sono conservativi e devono essere validati nel toolchain ATProto prima della pubblicazione.

## C. Cosa Serve - ActivityPub / ActivityStreams

Serve un documento `@context` pubblico, per esempio `https://w3id.org/deliberation/context.jsonld`, che esponga prefisso `del` e termini per classi/proprietà. Le classi DEL vengono usate in array `type`, insieme a tipi ActivityStreams quando semanticamente vicini: `Note`, `Collection`, `Profile`, `Organization`, `Document`, `Place`, `Event`, `Object`. La gerarchia di classi va preservata con `@type` multipli negli oggetti o pubblicando l’OWL/RDFS separato; il solo `@context` JSON-LD non esprime `rdfs:subClassOf`.

ActivityStreams riutilizzabili: `Note` per contributi/argomenti, `Collection` per processi o insiemi, `Profile`/Actor per partecipanti, `Organization`, `Document` per risorse, `Place` per forum fisici, `Event` per stage quando temporali, `Object` per consensus/outcome generici. Relazioni come `supports`, `attacks`, `hasPremise` restano estensioni DEL.

## D. Ruolo del Tool Metagov

Il repository `metagov/ontology` contiene un sistema Rust con data model e macro: `data_model_rdf`/`data_model_rdf_macros` esportano istanze annotate in JSON-LD e costruiscono context; `data_model_atproto`/`data_model_atproto_macros` generano Lexicon da struct Rust annotate; `ontology/data` definisce entità come `Person`, `Project`, `Statement`, `Stakeholder`, `Location`; `adaptors` contiene connettori Polis, HeyForm e Talk to the City.

Input richiesto: tipi Rust compilati con attributi `#[rdf(...)]` e `#[atproto(...)]`, non un file OWL/RDF esterno. Output: JSON-LD di istanze Rust, JSON Schema via `schemars`, e Lexicon JSON per i tipi annotati. Limitazioni: la macro ATProto tratta i campi non saltati sostanzialmente come stringhe; molti field complessi del data model sono `skip`; non esiste un parser OWL né un convertitore DEL OWL -> Lexicon/ActivityPub.

Il tool copre concettualmente parte del lavoro, perché mostra come produrre JSON-LD e Lexicon da un modello deliberativo, ma non è usabile direttamente su `ontologies/deliberation.owl` senza scrivere un importatore RDF/OWL o riscrivere DEL come struct Rust annotate.

## E. Gap e Rischi

- Mancano cardinalità, vincoli di obbligatorietà e shape SHACL: rischio di Lexicon troppo permissivo.
- `owl:unionOf` è approssimato come union/ref e non conserva pienamente la semantica OWL.
- Lexicon è schema JSON chiuso rispetto al modello RDF aperto: perdita di inferenza, subclassing e mapping SKOS.
- ActivityPub accetta JSON-LD esteso, ma server ActivityPub possono ignorare termini custom.
- L’ontologia DEL non ha `Decision`/`Outcome`; mappare `Consensus` come outcome è un’approssimazione dichiarata.
- Lavoro manuale residuo stimato: 1-2 giorni per validazione Lexicon e naming NSID; 2-4 giorni se si vuole un convertitore automatico OWL -> Lexicon robusto; 1-2 giorni per pubblicare e testare il context JSON-LD su w3id.
