#!/usr/bin/env python3
"""
Integrate Have Your Say knowledge graph into main DKG
"""

import sys
from pathlib import Path
from rdflib import Graph
from datetime import datetime

def integrate_graphs(hys_kg_file, main_kg_file, output_file):
    """Integrate HYS KG into main KG"""

    print(f"Loading Have Your Say KG from {hys_kg_file}...")
    hys_graph = Graph()
    hys_graph.parse(hys_kg_file, format='turtle')
    print(f"  Loaded {len(hys_graph)} triples")

    print(f"\nLoading main KG from {main_kg_file}...")
    main_graph = Graph()
    main_graph.parse(main_kg_file, format='turtle')
    initial_size = len(main_graph)
    print(f"  Loaded {initial_size} triples")

    print(f"\nIntegrating graphs...")
    # Add all triples from HYS graph to main graph
    for triple in hys_graph:
        main_graph.add(triple)

    final_size = len(main_graph)
    added_triples = final_size - initial_size

    print(f"\nSaving integrated graph to {output_file}...")
    main_graph.serialize(destination=output_file, format='turtle')

    # Also save as RDF/XML for compatibility
    rdf_output = str(output_file).replace('.ttl', '.rdf')
    main_graph.serialize(destination=rdf_output, format='xml')

    # And JSON-LD
    jsonld_output = str(output_file).replace('.ttl', '.jsonld')
    main_graph.serialize(destination=jsonld_output, format='json-ld')

    print(f"\n{'='*60}")
    print("INTEGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"Initial triples:  {initial_size:,}")
    print(f"HYS triples:      {len(hys_graph):,}")
    print(f"Added triples:    {added_triples:,}")
    print(f"Final triples:    {final_size:,}")
    print(f"\nOutput files:")
    print(f"  Turtle:   {output_file}")
    print(f"  RDF/XML:  {rdf_output}")
    print(f"  JSON-LD:  {jsonld_output}")
    print(f"{'='*60}")

    return main_graph

def main():
    if len(sys.argv) < 3:
        print("Usage: python integrate_to_main_kg.py <hys_kg.ttl> <main_kg.ttl> [output.ttl]")
        print("\nExample:")
        print("  python integrate_to_main_kg.py haveyoursay_kg.ttl /path/to/deliberation_kg.ttl deliberation_kg_with_hys.ttl")
        sys.exit(1)

    hys_kg = sys.argv[1]
    main_kg = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else "deliberation_kg_integrated.ttl"

    for f in [hys_kg, main_kg]:
        if not Path(f).exists():
            print(f"Error: File '{f}' not found")
            sys.exit(1)

    integrate_graphs(hys_kg, main_kg, output)

if __name__ == "__main__":
    main()