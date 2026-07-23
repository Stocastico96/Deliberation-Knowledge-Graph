# SPARQL Query Examples for Deliberation Knowledge Graph

This document provides a collection of SPARQL query examples for exploring the Deliberation Knowledge Graph. These queries can be executed using the SPARQL endpoint set up with `setup_sparql_endpoint.sh` or through the web interface at `sparql.html`.

## Basic Queries

### List all deliberation processes

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?process ?name
WHERE {
  ?process rdf:type del:DeliberationProcess ;
           del:name ?name .
}
LIMIT 10
```

### Find all contributions by a specific participant

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?contribution ?text
WHERE {
  ?contribution rdf:type del:Contribution ;
               del:text ?text ;
               del:madeBy ?participant .
  ?participant del:name "Iratxe García Pérez" .
}
LIMIT 10
```

### Find all topics discussed in European Parliament debates

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?topic ?name
WHERE {
  ?process rdf:type del:DeliberationProcess ;
           del:name ?processName ;
           del:hasTopic ?topic .
  ?topic del:name ?name .
  FILTER(CONTAINS(?processName, "European Parliament"))
}
LIMIT 20
```

### List participants and their organizations

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?participant ?name ?orgName
WHERE {
  ?participant rdf:type del:Participant ;
               del:name ?name ;
               del:isAffiliatedWith ?org .
  ?org del:name ?orgName .
}
LIMIT 20
```

### Find responses to contributions

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?contribution ?text ?responseTo
WHERE {
  ?contribution rdf:type del:Contribution ;
               del:text ?text ;
               del:responseTo ?responseTo .
}
LIMIT 10
```

## Advanced Queries

### Query all topics in a debate with their identifiers

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?topic_id ?topic_name
WHERE {
    ?topic rdf:type del:Topic ;
           del:identifier ?topic_id ;
           del:name ?topic_name .
}
ORDER BY ?topic_id
```

### Query all participants with their roles and organizations

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?name ?role ?organization
WHERE {
    ?participant rdf:type del:Participant ;
                del:name ?name .
    OPTIONAL {
        ?participant del:hasRole ?role_uri .
        ?role_uri del:name ?role .
    }
    OPTIONAL {
        ?participant del:isAffiliatedWith ?org_uri .
        ?org_uri del:name ?organization .
    }
}
ORDER BY ?name
```

### Query contributions by a participant with timestamps

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?timestamp ?text
WHERE {
    ?participant rdf:type del:Participant ;
                del:name ?name ;
                ^del:madeBy ?contribution .
    ?contribution del:timestamp ?timestamp ;
                 del:text ?text .
    FILTER(REGEX(?name, "García Pérez", "i"))
}
ORDER BY ?timestamp
```

### Query contributions related to a specific topic

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?topic_name ?participant_name ?timestamp ?text
WHERE {
    ?topic rdf:type del:Topic ;
          del:name ?topic_name .
    ?process del:hasTopic ?topic ;
            del:hasContribution ?contribution .
    ?contribution del:timestamp ?timestamp ;
                 del:text ?text ;
                 del:madeBy ?participant .
    ?participant del:name ?participant_name .
    FILTER(REGEX(?topic_name, "climate", "i") || REGEX(?text, "climate", "i"))
}
ORDER BY ?timestamp
```

## Cross-Dataset Queries

### Find similar topics across different deliberation processes

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?process1_name ?topic1_name ?process2_name ?topic2_name
WHERE {
    ?process1 rdf:type del:DeliberationProcess ;
             del:name ?process1_name ;
             del:hasTopic ?topic1 .
    ?topic1 del:name ?topic1_name .
    
    ?process2 rdf:type del:DeliberationProcess ;
             del:name ?process2_name ;
             del:hasTopic ?topic2 .
    ?topic2 del:name ?topic2_name .
    
    FILTER(?process1 != ?process2)
    FILTER(CONTAINS(LCASE(?topic1_name), LCASE(?topic2_name)) || 
           CONTAINS(LCASE(?topic2_name), LCASE(?topic1_name)))
}
LIMIT 20
```

### Find participants who contributed to multiple deliberation processes

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?participant_name (COUNT(DISTINCT ?process) AS ?process_count)
WHERE {
    ?participant rdf:type del:Participant ;
                del:name ?participant_name ;
                ^del:madeBy ?contribution .
    ?process del:hasContribution ?contribution ;
            rdf:type del:DeliberationProcess .
}
GROUP BY ?participant_name
HAVING (?process_count > 1)
ORDER BY DESC(?process_count)
LIMIT 20
```

### Find fallacies detected in contributions

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?contribution_text ?fallacy_type ?confidence
WHERE {
    ?contribution rdf:type del:Contribution ;
                 del:text ?contribution_text ;
                 del:containsFallacy ?fallacy .
    ?fallacy rdf:type del:FallacyType ;
            del:name ?fallacy_type ;
            del:confidence ?confidence .
}
ORDER BY DESC(?confidence)
LIMIT 20
```

## Using the SPARQL Endpoint

To use these queries with the SPARQL endpoint:

1. Start the SPARQL endpoint:
   ```bash
   cd fuseki/apache-jena-fuseki-4.10.0 && ./fuseki-server --config=config.ttl
   ```

2. Access the SPARQL interface at http://localhost:3030/deliberation

3. Copy and paste any of the queries above into the query editor

4. Click "Execute Query" to see the results

Alternatively, you can use the web interface provided in `sparql.html` which includes these example queries with a more user-friendly interface.

## Common Prefixes

These prefixes are commonly used in queries against the Deliberation Knowledge Graph:

```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX sioc: <http://rdfs.org/sioc/ns#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
