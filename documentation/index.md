# Deliberation Knowledge Graph Documentation

Welcome to the documentation for the Deliberation Knowledge Graph project. This documentation provides detailed information about the project structure, components, and how to use the knowledge graph.

## Documentation Index

- [Project Structure](project_structure.md) - Overview of the project components and how they work together
- [Data Models Overview](data_models_overview.md) - Overview of the data models used in the project
- [SPARQL Examples](guides/SPARQL_examples.md) - Collection of SPARQL query examples for exploring the knowledge graph
- [Fallacy Analysis](guides/fallacy_analysis_README.md) - Documentation for the fallacy analysis component
- [Integration Guide](guides/README_INTEGRAZIONE.md) - Notes on integrating data into the DEL ontology

## Interoperability Standards

- [Standards Index](../standards/README.md) - ATProto Lexicons, ActivityPub JSON-LD context, and DEL interoperability notes
- [DEL ATProto Lexicons](../standards/atproto/README.md) - Machine-readable Lexicons under `org.deliberation.*`
- [DEL ActivityPub / JSON-LD Profile](../standards/activitypub/README.md) - JSON-LD context and examples
- [DEL-DDS Interoperability Roadmap](../standards/docs/dds-interoperability-roadmap.md) - Roadmap for DDS-compatible interoperability

## Dataset Documentation

Each dataset has its own documentation:

- [EU Parliament Debates](../data/EU_parliament_debates/README.md) - Documentation for the EU Parliament debates dataset
- [Decide Madrid](../data/decide_Madrid/readme.txt) - Documentation for the Decide Madrid dataset
- [DeliData](../data/delidata/readme.txt) - Documentation for the DeliData dataset
- [EU Have Your Say](../data/EU_have_your_say/readme.txt) - Documentation for the EU Have Your Say dataset
- [Habermas Machine](../data/habermas_machine/readme.txt) - Documentation for the Habermas Machine dataset
- [Decidim Barcelona](../data/decidim_barcelona/readme.txt) - Documentation for the Decidim Barcelona dataset
- [US Supreme Court Arguments](../data/US_supreme_court_arguments/readme.txt) - Documentation for the US Supreme Court arguments dataset

## Ontology Documentation

- [Deliberation Ontology](../ontologies/deliberation.owl) - The main deliberation ontology in OWL format
- [Ontology Mappings](../ontologies/mappings.owl) - Mappings between the deliberation ontology and other standard ontologies

## Web Interfaces

- [Main Website](../index.html) - Main project website
- [SPARQL Interface](../sparql.html) - SPARQL query interface
- [Knowledge Graph Visualization](../visualize_kg.html) - Knowledge graph visualization interface

## Scripts

- [Create Knowledge Graph](../create_knowledge_graph.py) - Script to create the knowledge graph
- [Create Unified Knowledge Graph](../create_unified_kg.py) - Script to unify all datasets
- [Setup SPARQL Endpoint](../setup_sparql_endpoint.sh) - Script to set up the SPARQL endpoint
- [Run EP Fallacy Analysis](../run_ep_fallacy_analysis.py) - Script to run fallacy analysis on EU Parliament debates

## Deployment and Operations

- [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
- [Linked Data Deployment Guide](deployment/DEPLOYMENT_GUIDE_LINKEDDATA.md)
- [Manual Apache Configuration](deployment/MANUAL_APACHE_CONFIG.md)
- [Manual Nginx Instructions](deployment/MANUAL_NGINX_INSTRUCTIONS.md)
- [Subdomain Configuration Guide](deployment/SUBDOMAIN_CONFIGURATION_GUIDE.md)

## Reports and Research Material

- [Status Reports](reports/status/)
- [Legacy Runtime Logs](reports/logs/legacy/)
- [Research and ORSD Material](research/)
