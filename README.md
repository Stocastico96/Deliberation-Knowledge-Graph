# Deliberation Knowledge Graph

A comprehensive knowledge graph connecting various deliberative process datasets and ontologies for enhanced analysis and understanding.

## Overview

The Deliberation Knowledge Graph project aims to connect various deliberative process datasets and ontologies into a comprehensive knowledge graph. This project provides a unified framework for analyzing deliberative processes across different platforms and contexts, from formal parliamentary debates to citizen participation initiatives.

By integrating diverse datasets and ontologies, the Deliberation Knowledge Graph enables researchers, policymakers, and citizens to explore the connections between different deliberative processes, identify patterns, and gain insights into how deliberation works across various contexts.

## Documentation

The project documentation is organized as follows:

- [Documentation Index](documentation/index.md) - Main documentation index with links to all documentation files
- [Project Structure](documentation/project_structure.md) - Detailed overview of the project components and how they work together
- [SPARQL Examples](SPARQL_examples.md) - Collection of SPARQL query examples for exploring the knowledge graph
- [Fallacy Analysis](fallacy_analysis_README.md) - Documentation for the fallacy analysis component

## Repository Structure

```
Deliberation-Knowledge-Graph/
├── css/                          # CSS stylesheets
├── data/                         # Dataset directories
│   ├── decide_Madrid/            # Decide Madrid dataset
│   ├── decidim_barcelona/        # Decidim Barcelona dataset
│   ├── delidata/                 # DeliData dataset
│   ├── EU_have_your_say/         # EU Have Your Say dataset
│   ├── EU_parliament_debates/    # EU Parliament debates dataset
│   ├── habermas_machine/         # Habermas Machine dataset
│   └── US_supreme_court_arguments/ # US Supreme Court arguments dataset
├── documentation/                # Project documentation
├── js/                           # JavaScript files
├── knowledge_graph/              # Generated knowledge graph files
│   └── rdf/                      # RDF files for each dataset
├── ontologies/                   # Ontology files and documentation
│   ├── deliberation.owl          # Main deliberation ontology
│   └── mappings.owl              # Ontology mappings
├── visualizations/               # Knowledge graph visualizations
├── create_knowledge_graph.py     # Script to create the knowledge graph
├── create_unified_kg.py          # Script to unify all datasets
├── index.html                    # Main project website
├── setup_sparql_endpoint.sh      # Script to set up SPARQL endpoint
├── sparql.html                   # SPARQL query interface
└── visualize_kg.html             # Knowledge graph visualization interface
```

## Datasets

The project integrates several datasets related to deliberative processes:

1. **European Parliament Debates** - Structured representations of plenary session debates
2. **Decide Madrid** - Citizen proposals and comments from Madrid's participatory democracy platform
3. **DeliData** - Dataset for deliberation in multi-party problem solving
4. **EU Have Your Say** - Feedback from the European Commission's public consultation platform
5. **Habermas Machine** - Data from a deliberative democracy experiment
6. **Decidim Barcelona** - Data from Barcelona's participatory democracy platform
7. **US Supreme Court Arguments** - Transcripts of oral arguments before the US Supreme Court

## Ontologies

The project uses a core deliberation ontology that integrates concepts from several standard ontologies:

- **DELIB Ontology** - For capturing deliberative processes
- **Argument Interchange Format (AIF)** - For representing argument structures
- **SIOC Ontology** - For online community activities
- **FOAF Ontology** - For describing persons and their relations
- **Dublin Core** - For metadata
- **LKIF Ontology** - For legal knowledge
- **IBIS Model** - For issue-based information systems

## SPARQL Queries

The repository includes several example SPARQL queries for exploring the knowledge graph. These can be found in the [SPARQL Examples](SPARQL_examples.md) document, which includes:

- Basic queries for listing deliberation processes, contributions, and topics
- Advanced queries for exploring relationships between participants, topics, and contributions
- Cross-dataset queries for finding connections between different deliberation processes
- Fallacy analysis queries for exploring detected logical fallacies

Example SPARQL query interfaces:

1. **sparql.html** - A web interface with interactive query examples
2. **data/EU_parliament_debates/query_rdf_data.py** - Python script with example queries
3. **setup_sparql_endpoint.sh** - Shell script with example queries

### Example SPARQL Query

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

For more examples, see the [SPARQL Examples](SPARQL_examples.md) document.

## Fallacy Analysis

The project includes tools for analyzing logical fallacies in deliberative processes:

- **ep_debates_fallacy_analysis.py** - Main script for fallacy detection
- **run_ep_fallacy_analysis.py** - Script to run fallacy analysis on existing JSON debate files

The system detects various fallacy types including Ad Hominem, Straw Man, False Dilemma, Appeal to Authority, and many others.

## Getting Started

### Setting up the SPARQL Endpoint

```bash
# Run the setup script
./setup_sparql_endpoint.sh

# Start the SPARQL endpoint
cd fuseki/apache-jena-fuseki-4.10.0 && ./fuseki-server --config=config.ttl
```

The SPARQL endpoint will be available at http://localhost:3030/deliberation

### Creating the Knowledge Graph

```bash
# Create the knowledge graph
python create_knowledge_graph.py

# Create a unified knowledge graph from all datasets
python create_unified_kg.py
```

### Running Fallacy Analysis

```bash
# Process a debate HTML file
python ep_debates_fallacy_analysis.py process data/EU_parliament_debates/ep_debates/verbatim_2025-03-10.html

# Generate a fallacy report
python ep_debates_fallacy_analysis.py report ep_debate_20250310 --output fallacy_report.json
```

## Web Interfaces

The project includes several web interfaces:

- **index.html** - Main project website
- **sparql.html** - SPARQL query interface
- **visualize_kg.html** - Knowledge graph visualization interface

## Author

Simone Vagnoni, CIRSFID, University of Bologna - OEG, Universidad Politecnica de Madrid
