#!/bin/bash
# Script to set up a SPARQL endpoint using Apache Jena Fuseki

# Configuration
FUSEKI_VERSION="4.10.0"
FUSEKI_DOWNLOAD_URL="https://dlcdn.apache.org/jena/binaries/apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz"
FUSEKI_DIR="apache-jena-fuseki-${FUSEKI_VERSION}"
DATASET_NAME="deliberation"
PORT=3030

# Create knowledge graph if it doesn't exist
if [ ! -d "knowledge_graph" ] || [ ! -f "knowledge_graph/deliberation_kg.ttl" ]; then
    echo "Knowledge graph not found. Creating it now..."
    python3 create_knowledge_graph.py
    
    if [ ! -f "knowledge_graph/deliberation_kg.ttl" ]; then
        echo "Failed to create knowledge graph. Please check the create_knowledge_graph.py script."
        exit 1
    fi
fi

# Create a directory for Fuseki if it doesn't exist
mkdir -p fuseki

# Download Fuseki if not already downloaded
if [ ! -f "fuseki/${FUSEKI_DIR}.tar.gz" ]; then
    echo "Downloading Apache Jena Fuseki..."
    curl -L ${FUSEKI_DOWNLOAD_URL} -o "fuseki/${FUSEKI_DIR}.tar.gz"
    
    if [ $? -ne 0 ]; then
        echo "Failed to download Fuseki. Please check your internet connection."
        exit 1
    fi
fi

# Extract Fuseki if not already extracted
if [ ! -d "fuseki/${FUSEKI_DIR}" ]; then
    echo "Extracting Fuseki..."
    tar -xzf "fuseki/${FUSEKI_DIR}.tar.gz" -C fuseki
    
    if [ $? -ne 0 ]; then
        echo "Failed to extract Fuseki."
        exit 1
    fi
fi

# Create a configuration file for Fuseki
cat > "fuseki/${FUSEKI_DIR}/config.ttl" << EOL
@prefix :      <#> .
@prefix fuseki: <http://jena.apache.org/fuseki#> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix tdb:   <http://jena.hpl.hp.com/2008/tdb#> .
@prefix ja:    <http://jena.hpl.hp.com/2005/11/Assembler#> .

[] rdf:type fuseki:Server ;
   fuseki:services (
     <#service_${DATASET_NAME}>
   ) .

<#service_${DATASET_NAME}> rdf:type fuseki:Service ;
    fuseki:name                       "${DATASET_NAME}" ;
    fuseki:serviceQuery               "query" ;
    fuseki:serviceQuery               "sparql" ;
    fuseki:serviceUpdate              "update" ;
    fuseki:serviceUpload              "upload" ;
    fuseki:serviceReadWriteGraphStore "data" ;
    fuseki:serviceReadGraphStore      "get" ;
    fuseki:dataset                    <#dataset_${DATASET_NAME}> ;
    .

<#dataset_${DATASET_NAME}> rdf:type ja:MemoryDataset ;
    ja:data [ ja:graph <file:../../../knowledge_graph/deliberation_kg.ttl> ] ;
    .
EOL

# Make the Fuseki start script executable
chmod +x "fuseki/${FUSEKI_DIR}/fuseki-server"

echo "SPARQL endpoint setup complete!"
echo "To start the SPARQL endpoint, run:"
echo "cd fuseki/${FUSEKI_DIR} && ./fuseki-server --config=config.ttl"
echo ""
echo "Once started, you can access the SPARQL endpoint at:"
echo "http://localhost:${PORT}/"
echo ""
echo "The SPARQL query interface will be available at:"
echo "http://localhost:${PORT}/${DATASET_NAME}"
echo ""
echo "Example SPARQL queries:"
echo ""
echo "# Query 1: List all deliberation processes"
echo "PREFIX del: <https://w3id.org/deliberation/ontology#>"
echo ""
echo "SELECT ?process ?name"
echo "WHERE {"
echo "    ?process a del:DeliberationProcess ;"
echo "             del:name ?name ."
echo "}"
echo ""
echo "# Query 2: Find all contributions by a specific participant"
echo "PREFIX del: <https://w3id.org/deliberation/ontology#>"
echo ""
echo "SELECT ?contribution ?text"
echo "WHERE {"
echo "    ?contribution a del:Contribution ;"
echo "                 del:text ?text ;"
echo "                 del:madeBy ?participant ."
echo "    ?participant del:name \"Iratxe García Pérez\" ."
echo "}"
echo ""
echo "# Query 3: Find all topics discussed in European Parliament debates"
echo "PREFIX del: <https://w3id.org/deliberation/ontology#>"
echo ""
echo "SELECT ?topic ?name"
echo "WHERE {"
echo "    ?process a del:DeliberationProcess ;"
echo "             del:name ?processName ;"
echo "             del:hasTopic ?topic ."
echo "    ?topic del:name ?name ."
echo "    FILTER(CONTAINS(?processName, \"European Parliament\"))"
echo "}"
