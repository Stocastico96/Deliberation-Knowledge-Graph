#!/usr/bin/env python3
"""
Integrate Have Your Say JSON-LD data into the Deliberation Knowledge Graph
"""

import json
import sys
import os
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
from datetime import datetime

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCT = Namespace("http://purl.org/dc/terms/")
BASE_URI = "https://svagnoni.linkeddata.es/resource/"

def load_existing_kg(kg_file):
    """Load existing knowledge graph"""
    g = Graph()

    # Bind namespaces
    g.bind("del", DEL)
    g.bind("foaf", FOAF)
    g.bind("dct", DCT)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    if kg_file and os.path.exists(kg_file):
        print(f"Loading existing KG from {kg_file}...")
        g.parse(kg_file, format='turtle')
        print(f"  Loaded {len(g)} triples")
    else:
        print(f"Creating new KG...")

    return g

def integrate_jsonld_file(graph, jsonld_file):
    """Integrate a JSON-LD file into the graph"""
    print(f"\nIntegrating: {jsonld_file}")

    with open(jsonld_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # If it's a graph with multiple processes
    if '@graph' in data:
        processes = data['@graph']
    else:
        processes = [data]

    for process_data in processes:
        if '@type' not in process_data or 'DeliberationProcess' not in process_data['@type']:
            continue

        # Get process URI
        process_uri = URIRef(process_data.get('@id', f"{BASE_URI}process/{process_data.get('del:identifier', 'unknown')}"))

        # Add process
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))

        # Add basic properties
        if 'del:identifier' in process_data:
            graph.add((process_uri, DEL.identifier, Literal(process_data['del:identifier'])))
        if 'del:name' in process_data:
            graph.add((process_uri, DEL.name, Literal(process_data['del:name'])))
        if 'del:platform' in process_data:
            graph.add((process_uri, DEL.platform, Literal(process_data['del:platform'])))
        if 'dct:source' in process_data:
            graph.add((process_uri, DCT.source, URIRef(process_data['dct:source'])))
        if 'dct:created' in process_data:
            graph.add((process_uri, DCT.created, Literal(process_data['dct:created'], datatype=XSD.dateTime)))
        if 'del:startDate' in process_data:
            graph.add((process_uri, DEL.startDate, Literal(process_data['del:startDate'], datatype=XSD.dateTime)))
        if 'del:endDate' in process_data:
            graph.add((process_uri, DEL.endDate, Literal(process_data['del:endDate'], datatype=XSD.dateTime)))

        # Add topics
        for topic_data in process_data.get('del:hasTopic', []):
            topic_uri = URIRef(topic_data.get('@id', f"{BASE_URI}topic/{topic_data.get('del:identifier', 'unknown')}"))
            graph.add((topic_uri, RDF.type, DEL.Topic))
            graph.add((topic_uri, DEL.identifier, Literal(topic_data.get('del:identifier', ''))))
            graph.add((topic_uri, DEL.name, Literal(topic_data.get('del:name', ''))))
            if 'del:description' in topic_data:
                graph.add((topic_uri, DEL.description, Literal(topic_data['del:description'])))
            graph.add((process_uri, DEL.hasTopic, topic_uri))

        # Add participants
        for participant_data in process_data.get('del:hasParticipant', []):
            participant_uri = URIRef(participant_data.get('@id', f"{BASE_URI}participant/{participant_data.get('del:identifier', 'unknown')}"))

            # Determine type
            ptype = participant_data.get('@type', 'del:Participant')
            if 'Organization' in ptype:
                graph.add((participant_uri, RDF.type, DEL.Organization))
            else:
                graph.add((participant_uri, RDF.type, DEL.Participant))

            graph.add((participant_uri, DEL.identifier, Literal(participant_data.get('del:identifier', ''))))
            graph.add((participant_uri, DEL.name, Literal(participant_data.get('del:name', ''))))

            if 'del:country' in participant_data:
                graph.add((participant_uri, DEL.country, Literal(participant_data['del:country'])))
            if 'foaf:name' in participant_data:
                graph.add((participant_uri, FOAF.name, Literal(participant_data['foaf:name'])))

            graph.add((process_uri, DEL.hasParticipant, participant_uri))

        # Add contributions
        for contrib_data in process_data.get('del:hasContribution', []):
            contrib_uri = URIRef(contrib_data.get('@id', f"{BASE_URI}contribution/{contrib_data.get('del:identifier', 'unknown')}"))
            graph.add((contrib_uri, RDF.type, DEL.Contribution))
            graph.add((contrib_uri, DEL.identifier, Literal(contrib_data.get('del:identifier', ''))))
            graph.add((contrib_uri, DEL.text, Literal(contrib_data.get('del:text', ''))))

            if 'dct:created' in contrib_data:
                graph.add((contrib_uri, DCT.created, Literal(contrib_data['dct:created'], datatype=XSD.dateTime)))

            # Link to participant
            if 'del:madeBy' in contrib_data:
                made_by_uri = URIRef(contrib_data['del:madeBy']['@id'])
                graph.add((contrib_uri, DEL.madeBy, made_by_uri))

            # Link to topic
            if 'del:hasTopic' in contrib_data:
                topic_uri = URIRef(contrib_data['del:hasTopic']['@id'])
                graph.add((contrib_uri, DEL.hasTopic, topic_uri))

            graph.add((process_uri, DEL.hasContribution, contrib_uri))

        print(f"  ✓ Integrated process: {process_data.get('del:name', 'N/A')[:80]}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python integrate_haveyoursay_to_kg.py <jsonld_dir> <output_kg_file>")
        print("\nExample:")
        print("  python integrate_haveyoursay_to_kg.py mapped_haveyoursay kg_with_haveyoursay.ttl")
        sys.exit(1)

    jsonld_dir = Path(sys.argv[1])
    output_file = sys.argv[2]

    if not jsonld_dir.exists():
        print(f"Error: Directory {jsonld_dir} does not exist")
        sys.exit(1)

    print(f"{'='*60}")
    print("Have Your Say -> Knowledge Graph Integration")
    print(f"{'='*60}")
    print(f"Input directory: {jsonld_dir}")
    print(f"Output file: {output_file}")
    print(f"{'='*60}\n")

    # Load or create knowledge graph
    graph = load_existing_kg(output_file if os.path.exists(output_file) else None)
    initial_size = len(graph)

    # Find all JSON-LD files
    jsonld_files = list(jsonld_dir.glob("*.jsonld"))

    if not jsonld_files:
        print(f"No JSON-LD files found in {jsonld_dir}")
        sys.exit(1)

    print(f"Found {len(jsonld_files)} JSON-LD files to integrate\n")

    # Integrate each file
    for jsonld_file in jsonld_files:
        try:
            integrate_jsonld_file(graph, jsonld_file)
        except Exception as e:
            print(f"  ✗ Error integrating {jsonld_file.name}: {e}")

    # Save the graph
    print(f"\n{'='*60}")
    print("Saving knowledge graph...")
    graph.serialize(destination=output_file, format='turtle')

    new_size = len(graph)
    added_triples = new_size - initial_size

    print(f"✓ Saved to {output_file}")
    print(f"{'='*60}")
    print(f"Initial triples: {initial_size}")
    print(f"Added triples: {added_triples}")
    print(f"Total triples: {new_size}")
    print(f"{'='*60}")

    # Save statistics
    stats = {
        'integration_date': datetime.now().isoformat(),
        'jsonld_files_processed': len(jsonld_files),
        'initial_triples': initial_size,
        'added_triples': added_triples,
        'total_triples': new_size,
        'output_file': output_file
    }

    stats_file = Path(output_file).parent / "integration_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

    print(f"\nStatistics saved to {stats_file}")


if __name__ == "__main__":
    main()