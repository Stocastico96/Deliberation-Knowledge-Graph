# TODO: Estensioni Ontologia DEL

Basato su analisi dei dati HYS (5,340 feedbacks, 100 initiatives)

## 1. ESTENSIONI ESSENZIALI (Priorità ALTA)

### 1.1 Participant.country
**Occorrenze**: 5,340 feedbacks (100%)
**Uso**: Analisi geografica partecipazione

```turtle
:country rdf:type owl:DatatypeProperty ;
    rdfs:domain :Participant ;
    rdfs:range xsd:string ;
    rdfs:comment "The country of origin of a participant (ISO 3166-1 alpha-3 code)."@en ;
    rdfs:label "country"@en .
```

### 1.2 Participant.participantType
**Occorrenze**: 5,340 feedbacks (100%)
**Valori**: EU_CITIZEN (73.5%), NON_EU_CITIZEN (8.9%), BUSINESS_ASSOCIATION (6.7%), COMPANY (6.4%), NGO, PUBLIC_AUTHORITY, etc.
**Uso**: Stakeholder analysis, distinguish citizens from organizations

```turtle
:participantType rdf:type owl:DatatypeProperty ;
    rdfs:domain :Participant ;
    rdfs:range xsd:string ;
    rdfs:comment "The type or status of participant (e.g., EU_CITIZEN, COMPANY, NGO, PUBLIC_AUTHORITY)."@en ;
    rdfs:label "participant type"@en .
```

**ALTERNATIVA**: Creare sottoclassi di Participant
```turtle
:Citizen rdfs:subClassOf :Participant .
:OrganizationalParticipant rdfs:subClassOf :Participant .
```

### 1.3 DeliberationProcess.platform
**Occorrenze**: 100 processes (100%)
**Valori**: "EU Have Your Say", "Decidim Barcelona", "Decide Madrid", "European Parliament"
**Uso**: Cross-platform analysis

```turtle
:platform rdf:type owl:DatatypeProperty ;
    rdfs:domain :DeliberationProcess ;
    rdfs:range xsd:string ;
    rdfs:comment "The name of the deliberation platform hosting the process."@en ;
    rdfs:label "platform"@en .
```

**ALTERNATIVA**: Creare classe Platform
```turtle
:Platform rdf:type owl:Class ;
    rdfs:comment "A deliberation platform or system."@en ;
    rdfs:label "Platform"@en .

:hostedOn rdf:type owl:ObjectProperty ;
    rdfs:domain :DeliberationProcess ;
    rdfs:range :Platform ;
    rdfs:comment "Relates a process to the platform hosting it."@en ;
    rdfs:label "hosted on"@en .
```

## 2. ESTENSIONI MEDIE (Priorità MEDIA)

### 2.1 Organization.organizationType
**Occorrenze**: 943 feedbacks (17.7%)
**Valori**: NGO, COMPANY, BUSINESS_ASSOCIATION, PUBLIC_AUTHORITY, ACADEMIC_RESEARCH_INSTITUTION, etc.

```turtle
:organizationType rdf:type owl:DatatypeProperty ;
    rdfs:domain :Organization ;
    rdfs:range xsd:string ;
    rdfs:comment "The type of organization (e.g., NGO, COMPANY, PUBLIC_AUTHORITY)."@en ;
    rdfs:label "organization type"@en .
```

**ALTERNATIVA MIGLIORE**: Sottoclassi di Organization
```turtle
:NonGovernmentalOrganization rdfs:subClassOf :Organization .
:Company rdfs:subClassOf :Organization .
:PublicAuthority rdfs:subClassOf :Organization .
:AcademicInstitution rdfs:subClassOf :Organization .
:BusinessAssociation rdfs:subClassOf :Organization .
:TradeUnion rdfs:subClassOf :Organization .
:ConsumerOrganization rdfs:subClassOf :Organization .
:EnvironmentalOrganization rdfs:subClassOf :NonGovernmentalOrganization .
```

### 2.2 Organization.size
**Occorrenze**: 943 feedbacks (17.7%)
**Valori**: MICRO, SMALL, MEDIUM, LARGE (company size categories)

```turtle
:organizationSize rdf:type owl:DatatypeProperty ;
    rdfs:domain :Organization ;
    rdfs:range xsd:string ;
    rdfs:comment "The size category of an organization (e.g., MICRO, SMALL, MEDIUM, LARGE)."@en ;
    rdfs:label "organization size"@en .
```

### 2.3 Contribution.sourceUrl
**Occorrenze**: Potenzialmente tutte le contribution
**Uso**: Tracciabilità, link alla contribution originale

```turtle
:sourceUrl rdf:type owl:DatatypeProperty ;
    rdfs:domain :Contribution ;
    rdfs:range xsd:anyURI ;
    rdfs:comment "The URL of the contribution on the original platform."@en ;
    rdfs:label "source URL"@en .
```

**NOTA**: Potrebbe già essere coperto da `del:references → InformationResource`

## 3. ESTENSIONI GENERALI (Priorità BASSA)

### 3.1 DeliberationProcess.description
**Occorrenze**: Molti processes hanno descrizione
**Status**: Già coperto da `dcterms:description`

### 3.2 Entity.identifier proprietà generiche
**Status**: Già esiste `del:identifier` generico

### 3.3 Participant.affiliation (literal)
**Occorrenze**: 943 feedbacks hanno organization name
**Uso**: Quando non si vuole creare Organization entity

```turtle
:affiliationName rdf:type owl:DatatypeProperty ;
    rdfs:domain :Participant ;
    rdfs:range xsd:string ;
    rdfs:comment "The name of participant's affiliated organization as literal (when not creating Organization entity)."@en ;
    rdfs:label "affiliation name"@en .
```

## 4. DECISIONI ARCHITETTURALI

### Approccio 1: Datatype Properties (Veloce)
- ✅ PRO: Semplice, veloce da implementare
- ✅ PRO: Non richiede creazione massiva di entities
- ❌ CONTRO: Meno semanticamente ricco
- ❌ CONTRO: Non permette query SPARQL complesse su tipi

### Approccio 2: Sottoclassi + Object Properties (Semantico)
- ✅ PRO: Semanticamente corretto e ricco
- ✅ PRO: Permette reasoning e query avanzate
- ✅ PRO: Allineato con best practices ontologie
- ❌ CONTRO: Più complesso da implementare
- ❌ CONTRO: Richiede creazione di più entities

### Approccio 3: Ibrido (Raccomandato)
**Datatype per metadati semplici**:
- `del:country` (Participant)
- `del:platform` (DeliberationProcess)
- `del:organizationSize` (Organization)

**Sottoclassi per tipologie**:
- Organization sottoclassi (NGO, Company, PublicAuthority, etc.)
- Opzionale: Participant sottoclassi (Citizen vs OrganizationalParticipant)

**Reasoning**: Participant.participantType potrebbe essere inferito:
```sparql
# Se Participant ha isAffiliatedWith → OrganizationalParticipant
# Se Participant non ha isAffiliatedWith → Citizen
```

## 5. ROADMAP IMPLEMENTAZIONE

### Fase 1: Fix Immediati (ORA)
1. ✅ Correggere `del:content` → `del:text` in HYS
2. ✅ Rimuovere predicati inventati (author, country, userType, etc.)
3. ⏳ Creare mapping base HYS conforme DEL attuale

### Fase 2: Estensioni Minime (PROSSIMO)
1. Aggiungere 3 proprietà essenziali all'ontologia:
   - `del:country`
   - `del:participantType`
   - `del:platform`
2. Re-processare HYS con nuove proprietà
3. Aggiornare server query per usare nuove proprietà

### Fase 3: Estensioni Complete (FUTURO)
1. Creare sottoclassi Organization
2. Creare Participant entities con metadati completi
3. Aggiungere `del:organizationSize`
4. Linking cross-platform (se applicabile)

## 6. IMPATTO SU QUERY E SERVER

### Query che cambieranno:
**Citizen Interface Server** (`simple_server.py`):
- Query contributions: aggiungere OPTIONAL per `del:country`, `del:participantType`
- Query processes: aggiungere OPTIONAL per `del:platform`
- Filtri geografici/stakeholder se richiesti

**Semantic Search**:
- Embeddings già contengono process_name, aggiungere metadata se necessario

### Backward Compatibility:
- Tutte le nuove proprietà saranno OPTIONAL
- Dati esistenti (Decidim, EP debates) continueranno a funzionare
- Solo HYS avrà country/participantType completi

## 7. CHECKLIST FINALE

Estensioni da implementare:
- [ ] `del:country` (ALTA priorità, 100% coverage)
- [ ] `del:participantType` (ALTA priorità, 100% coverage)
- [ ] `del:platform` (ALTA priorità, multi-platform analysis)
- [ ] Organization sottoclassi (MEDIA priorità, semantic richness)
- [ ] `del:organizationSize` (MEDIA priorità, 17.7% coverage)
- [ ] `del:sourceUrl` (BASSA priorità, tracciabilità)

Modifiche file:
- [ ] Aggiornare ontologia TTL in `/ontologies/deliberation.owl`
- [ ] Ri-generare documentazione OnToology
- [ ] Aggiornare `convert_hys_to_rdf.py` per usare proprietà corrette
- [ ] Aggiornare `simple_server.py` queries
- [ ] Aggiornare frontend per visualizzare metadati geografici/stakeholder
- [ ] Testare con SPARQL endpoint

Timeline stimata:
- Fase 1 (fix immediati): 2-3 ore
- Fase 2 (estensioni minime): 3-4 ore
- Fase 3 (estensioni complete): 8-10 ore
