#!/usr/bin/env python3
"""
Map Collective Intelligence Project (CIP) Global Dialogue data to the Deliberation Knowledge Graph.

This script processes the Global Dialogue datasets and creates RDF triples following
the deliberation ontology structure.
"""

import csv
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
from datetime import datetime
import hashlib

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RESOURCE = Namespace("https://svagnoni.linkeddata.es/resource/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")

def create_uri_hash(text):
    """Create a unique URI from text using hash."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]

def parse_global_dialogue_2024(data_dir):
    """Parse Global Dialogue 2024 dataset."""
    g = Graph()

    # Bind namespaces
    g.bind("del", DEL)
    g.bind("resource", RESOURCE)
    g.bind("foaf", FOAF)
    g.bind("sioc", SIOC)
    g.bind("dcterms", DCTERMS)

    # Create the deliberation process
    process_uri = RESOURCE["cip_global_dialogue_2024"]
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, RDFS.label, Literal("Global Dialogue 2024 - What future do you want?", lang="en")))
    g.add((process_uri, DEL.platform, Literal("Collective Intelligence Project")))
    g.add((process_uri, DCTERMS.date, Literal("2024-09-04", datatype=XSD.date)))
    g.add((process_uri, DEL.participantCount, Literal(1502, datatype=XSD.integer)))

    # Create main topic
    topic_uri = RESOURCE["cip_topic_global_dialogue_2024"]
    g.add((topic_uri, RDF.type, DEL.Topic))
    g.add((topic_uri, RDFS.label, Literal("What future do you want?", lang="en")))
    g.add((topic_uri, DEL.description, Literal("Global dialogue on future visions and AI governance", lang="en")))
    g.add((process_uri, DEL.hasTopic, topic_uri))

    # Parse verbatim map (contributions)
    verbatim_file = data_dir / "verbatim_map.csv"
    if verbatim_file.exists():
        print(f"Processing {verbatim_file}...")
        with open(verbatim_file, 'r', encoding='utf-8') as f:
            # Skip metadata header rows (8 lines)
            for i in range(8):
                next(f)

            # Now create DictReader from remaining content
            reader = csv.DictReader(f)

            count = 0
            for row in reader:
                if not row.get('Thought ID'):
                    continue

                # Create contribution
                contrib_id = row['Thought ID']
                contrib_uri = RESOURCE[f"cip_contribution_{contrib_id}"]

                g.add((contrib_uri, RDF.type, DEL.Contribution))
                g.add((contrib_uri, DEL.text, Literal(row['Thought Text'], lang="en")))
                g.add((contrib_uri, DEL.contributionID, Literal(contrib_id)))

                # Link to process and topic
                g.add((process_uri, DEL.hasContribution, contrib_uri))

                # Create question as subtopic if needed
                question_id = row['Question ID']
                question_uri = RESOURCE[f"cip_question_{question_id}"]
                g.add((question_uri, RDF.type, DEL.Topic))
                g.add((question_uri, RDFS.label, Literal(row['Question Text'], lang="en")))
                g.add((topic_uri, DEL.hasSubtopic, question_uri))
                g.add((contrib_uri, DEL.addresses, question_uri))

                # Create participant
                participant_id = row['Participant ID']
                participant_uri = RESOURCE[f"cip_participant_{participant_id}"]
                g.add((participant_uri, RDF.type, DEL.Participant))
                g.add((participant_uri, RDF.type, FOAF.Person))
                g.add((participant_uri, DEL.participantID, Literal(participant_id)))
                g.add((contrib_uri, DEL.hasAuthor, participant_uri))
                g.add((process_uri, DEL.hasParticipant, participant_uri))

                count += 1
                if count % 1000 == 0:
                    print(f"  Processed {count} contributions...")

            print(f"  Total contributions: {count}")

    # Parse agreement data
    agreement_file = data_dir / "agreement.csv"
    if agreement_file.exists():
        print(f"Processing {agreement_file}...")
        with open(agreement_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Skip header
            for i in range(8):
                next(reader, None)

            count = 0
            for row in reader:
                if not row.get('Thought ID'):
                    continue

                contrib_id = row['Thought ID']
                contrib_uri = RESOURCE[f"cip_contribution_{contrib_id}"]

                # Add agreement score
                if 'Agreement' in row and row['Agreement']:
                    try:
                        agreement = float(row['Agreement'])
                        g.add((contrib_uri, DEL.agreementScore, Literal(agreement, datatype=XSD.float)))
                    except ValueError:
                        pass

                count += 1
                if count % 1000 == 0:
                    print(f"  Processed {count} agreement scores...")

            print(f"  Total agreement scores: {count}")

    return g

def parse_global_dialogue_march_2025(data_dir):
    """Parse Global Dialogue March 2025 dataset."""
    g = Graph()

    # Bind namespaces
    g.bind("del", DEL)
    g.bind("resource", RESOURCE)
    g.bind("foaf", FOAF)
    g.bind("sioc", SIOC)
    g.bind("dcterms", DCTERMS)

    # Create the deliberation process
    process_uri = RESOURCE["cip_global_dialogue_march_2025"]
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, RDFS.label, Literal("Global Dialogue March 2025", lang="en")))
    g.add((process_uri, DEL.platform, Literal("Collective Intelligence Project")))
    g.add((process_uri, DCTERMS.date, Literal("2025-03", datatype=XSD.gYearMonth)))

    # Similar processing for March 2025 data...
    # (Structure is similar, can be extracted to common function)

    return g

def main():
    """Main execution function."""
    print("=" * 60)
    print("Mapping Collective Intelligence Project to Knowledge Graph")
    print("=" * 60)

    base_dir = Path("data/collective_intelligence_project/global dialogue data")

    # Process 2024 Global Dialogue
    print("\n[1/2] Processing Global Dialogue 2024...")
    gd_2024_dir = base_dir / "2024 GD1"
    if gd_2024_dir.exists():
        g_2024 = parse_global_dialogue_2024(gd_2024_dir)

        # Save to RDF file
        output_file = Path("knowledge_graph") / "cip_global_dialogue_2024.ttl"
        output_file.parent.mkdir(exist_ok=True)

        print(f"\nSaving to {output_file}...")
        g_2024.serialize(destination=str(output_file), format='turtle')
        print(f"✓ Saved {len(g_2024)} triples")
    else:
        print(f"⚠ Directory not found: {gd_2024_dir}")

    # Process March 2025 Global Dialogue
    print("\n[2/2] Processing Global Dialogue March 2025...")
    gd_march_dir = base_dir / "march 2025 GD"
    if gd_march_dir.exists():
        g_march = parse_global_dialogue_march_2025(gd_march_dir)

        output_file = Path("knowledge_graph") / "cip_global_dialogue_march_2025.ttl"
        print(f"\nSaving to {output_file}...")
        g_march.serialize(destination=str(output_file), format='turtle')
        print(f"✓ Saved {len(g_march)} triples")
    else:
        print(f"⚠ Directory not found: {gd_march_dir}")

    print("\n" + "=" * 60)
    print("✓ Mapping complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review generated .ttl files in knowledge_graph/")
    print("2. Merge with main KG: python merge_cip_to_main_kg.py")
    print("3. Test with SPARQL queries")

if __name__ == "__main__":
    main()
