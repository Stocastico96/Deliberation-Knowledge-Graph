# Deliberation Knowledge Graph - Project Structure

This document provides an overview of the Deliberation Knowledge Graph project structure, explaining how the different components work together.

## Project Overview

The Deliberation Knowledge Graph project aims to connect various deliberative process datasets and ontologies into a comprehensive knowledge graph. The project follows a modular architecture with the following main components:

1. **Data Collection and Conversion** - Scripts to collect and convert data from various sources
2. **Ontology Development** - Development of the deliberation ontology and mappings
3. **Knowledge Graph Creation** - Scripts to create and unify the knowledge graph
4. **SPARQL Endpoint** - Setup and configuration of the SPARQL endpoint
5. **Web Interfaces** - HTML interfaces for exploring the knowledge graph
6. **Fallacy Analysis** - Tools for analyzing logical fallacies in deliberative processes

## Directory Structure

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

## Component Details

### 1. Data Collection and Conversion

Each dataset directory under `data/` contains:

- `convert_to_rdf.py` - Script to convert the dataset to RDF format
- `readme.txt` - Documentation for the dataset
- `sample/` - Sample data files
- `data/` - Full dataset files (may be downloaded separately)

The conversion process follows these steps:

1. Parse the source data (CSV, JSON, XML, etc.)
2. Map the data to the deliberation ontology structure
3. Generate RDF/XML output compatible with the knowledge graph

Example conversion script structure:

```python
# Example from data/EU_parliament_debates/convert_json_to_rdf.py
def convert_json_to_rdf(json_file, rdf_file):
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Create RDF graph
    g = Graph()
    
    # Add namespaces
    DEL = Namespace("https://w3id.org/deliberation/ontology#")
    g.bind("del", DEL)
    
    # Create deliberation process
    process_uri = URIRef(f"https://w3id.org/deliberation/resource/{data['del:identifier']}")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.identifier, Literal(data["del:identifier"])))
    g.add((process_uri, DEL.name, Literal(data["del:name"])))
    
    # Add topics, participants, contributions, etc.
    # ...
    
    # Serialize to RDF/XML
    g.serialize(destination=rdf_file, format="xml")
```

### 2. Ontology Development

The `ontologies/` directory contains:

- `deliberation.owl` - The main deliberation ontology in OWL format
- `mappings.owl` - Mappings between the deliberation ontology and other standard ontologies
- Various HTML documentation files generated from the ontology

The deliberation ontology defines the following main classes:

- `DeliberationProcess` - A deliberative process (e.g., a debate, consultation)
- `Participant` - A person or organization participating in the process
- `Contribution` - A contribution made by a participant (e.g., a speech, comment)
- `Topic` - A topic discussed in the process
- `Argument` - An argument made in a contribution
- `FallacyType` - A type of logical fallacy that may be detected in a contribution

### 3. Knowledge Graph Creation

The knowledge graph creation process is handled by:

- `create_knowledge_graph.py` - Creates the knowledge graph from individual datasets
- `create_unified_kg.py` - Unifies all datasets into a single knowledge graph

The process follows these steps:

1. Load all RDF files from the `knowledge_graph/rdf/` directory
2. Merge them into a single graph
3. Apply ontology mappings to ensure consistency
4. Save the unified graph in various formats (RDF/XML, Turtle, JSON-LD)

### 4. SPARQL Endpoint

The SPARQL endpoint is set up using Apache Jena Fuseki:

- `setup_sparql_endpoint.sh` - Downloads and configures Fuseki
- Configuration files are created to load the knowledge graph
- The endpoint is accessible at http://localhost:3030/deliberation

### 5. Web Interfaces

The project includes several web interfaces:

- `index.html` - Main project website with information about the project
- `sparql.html` - SPARQL query interface with example queries
- `visualize_kg.html` - Knowledge graph visualization interface

These interfaces use:

- D3.js for visualizations
- Mermaid.js for diagrams
- CSS for styling

### 6. Fallacy Analysis

The fallacy analysis component includes:

- `ep_debates_fallacy_analysis.py` - Main script for fallacy detection
- `run_ep_fallacy_analysis.py` - Script to run fallacy analysis on existing JSON debate files

The fallacy detection process uses the Deepseek AI model via OpenRouter to analyze contributions for logical fallacies.

## Data Flow

The overall data flow in the project is as follows:

1. **Data Collection**: Raw data is collected from various sources (EU Parliament, Decide Madrid, etc.)
2. **Data Conversion**: Raw data is converted to JSON format aligned with the deliberation ontology
3. **RDF Conversion**: JSON data is converted to RDF/XML format
4. **Knowledge Graph Creation**: RDF data is merged into a unified knowledge graph
5. **Fallacy Analysis**: Contributions in the knowledge graph are analyzed for logical fallacies
6. **SPARQL Endpoint**: The knowledge graph is loaded into a SPARQL endpoint for querying
7. **Web Interfaces**: The knowledge graph is visualized and explored through web interfaces

## Integration Points

The project has several integration points:

1. **Ontology Mappings**: The `mappings.owl` file defines mappings between the deliberation ontology and other standard ontologies (FOAF, SIOC, etc.)
2. **Cross-Dataset Queries**: SPARQL queries can be used to explore connections between different datasets
3. **Fallacy Analysis Integration**: Fallacy analysis results are integrated into the knowledge graph
4. **Visualization Integration**: The knowledge graph is visualized through web interfaces

## Extension Points

The project can be extended in several ways:

1. **Adding New Datasets**: New datasets can be added by creating conversion scripts in the `data/` directory
2. **Extending the Ontology**: The deliberation ontology can be extended with new classes and properties
3. **Adding New Analysis Tools**: New analysis tools can be added to extract insights from the knowledge graph
4. **Creating New Visualizations**: New visualizations can be created to explore the knowledge graph

## Conclusion

The Deliberation Knowledge Graph project provides a comprehensive framework for analyzing deliberative processes across different platforms and contexts. By integrating diverse datasets and ontologies, it enables researchers, policymakers, and citizens to explore the connections between different deliberative processes, identify patterns, and gain insights into how deliberation works across various contexts.
