#!/usr/bin/env python3
"""
Map real Have Your Say feedback data to Deliberation Knowledge Graph Ontology
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCT = Namespace("http://purl.org/dc/terms/")
BASE_URI = "https://svagnoni.linkeddata.es/resource/"

def create_knowledge_graph(db_path, output_file):
    """Convert feedback database to RDF knowledge graph"""

    print(f"Loading data from {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create graph
    g = Graph()
    g.bind("del", DEL)
    g.bind("foaf", FOAF)
    g.bind("dct", DCT)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    # Get all initiatives
    initiatives = c.execute("SELECT id, data FROM initiatives").fetchall()
    print(f"Found {len(initiatives)} initiatives")

    for init_id, init_data_json in initiatives:
        init_data = json.loads(init_data_json)

        # Create deliberation process
        process_uri = URIRef(f"{BASE_URI}process/eu_hys_{init_id}")
        g.add((process_uri, RDF.type, DEL.DeliberationProcess))
        g.add((process_uri, DEL.identifier, Literal(f"eu_hys_{init_id}")))
        g.add((process_uri, DEL.name, Literal(init_data.get('shortTitle', ''))))
        g.add((process_uri, DEL.platform, Literal("EU Have Your Say")))
        g.add((process_uri, DCT.source, URIRef(f"https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives/{init_id}")))

        # Add description
        if init_data.get('dossierSummary'):
            g.add((process_uri, DEL.description, Literal(init_data['dossierSummary'])))

        # Create main topic
        topic_uri = URIRef(f"{BASE_URI}topic/eu_hys_topic_{init_id}")
        g.add((topic_uri, RDF.type, DEL.Topic))
        g.add((topic_uri, DEL.identifier, Literal(f"eu_hys_topic_{init_id}")))
        g.add((topic_uri, DEL.name, Literal(init_data.get('shortTitle', ''))))
        if init_data.get('dossierSummary'):
            g.add((topic_uri, DEL.description, Literal(init_data['dossierSummary'])))
        g.add((process_uri, DEL.hasTopic, topic_uri))

        # Get feedback for this initiative
        feedback_rows = c.execute("""
            SELECT id, publication_id, data
            FROM feedback
            WHERE initiative_id = ?
        """, (init_id,)).fetchall()

        print(f"  Initiative {init_id}: {len(feedback_rows)} feedback items")

        # Track unique participants
        participants = {}

        for fb_id, pub_id, fb_data_json in feedback_rows:
            fb_data = json.loads(fb_data_json)

            # Create participant
            country = fb_data.get('country', 'UNKNOWN')
            user_type = fb_data.get('userType', 'UNKNOWN')
            org = fb_data.get('organization', '')
            first_name = fb_data.get('firstName', '')
            surname = fb_data.get('surname', '')

            # Participant identifier
            if org:
                participant_key = f"org_{org}_{country}"
                participant_name = org
                participant_type = DEL.Organization
            elif first_name or surname:
                participant_key = f"person_{first_name}_{surname}_{country}_{fb_id}"
                participant_name = f"{first_name} {surname}".strip() or "Anonymous"
                participant_type = DEL.Participant
            else:
                participant_key = f"anon_{country}_{user_type}_{fb_id}"
                participant_name = f"Participant from {country}"
                participant_type = DEL.Participant

            if participant_key not in participants:
                participant_uri = URIRef(f"{BASE_URI}participant/eu_hys_{init_id}_{len(participants)+1}")
                g.add((participant_uri, RDF.type, participant_type))
                g.add((participant_uri, DEL.name, Literal(participant_name)))

                if country and country != 'UNKNOWN':
                    g.add((participant_uri, DEL.country, Literal(country)))

                if user_type and user_type != 'UNKNOWN':
                    role_uri = URIRef(f"{BASE_URI}role/{user_type}")
                    g.add((role_uri, RDF.type, DEL.Role))
                    g.add((role_uri, DEL.name, Literal(user_type)))
                    g.add((participant_uri, DEL.hasRole, role_uri))

                if org:
                    g.add((participant_uri, FOAF.name, Literal(org)))

                g.add((process_uri, DEL.hasParticipant, participant_uri))
                participants[participant_key] = participant_uri

            participant_uri = participants[participant_key]

            # Create contribution
            contrib_uri = URIRef(f"{BASE_URI}contribution/eu_hys_fb_{fb_id}")
            g.add((contrib_uri, RDF.type, DEL.Contribution))
            g.add((contrib_uri, DEL.identifier, Literal(f"fb_{fb_id}")))

            # Add feedback text
            feedback_text = fb_data.get('feedback', '')
            if feedback_text:
                # Truncate very long texts for performance
                if len(feedback_text) > 10000:
                    feedback_text = feedback_text[:10000] + "..."
                g.add((contrib_uri, DEL.text, Literal(feedback_text)))

            # Add date
            date_feedback = fb_data.get('dateFeedback')
            if date_feedback:
                try:
                    # Try to parse and format date
                    g.add((contrib_uri, DCT.created, Literal(date_feedback, datatype=XSD.dateTime)))
                except:
                    g.add((contrib_uri, DCT.created, Literal(date_feedback)))

            # Link to participant
            g.add((contrib_uri, DEL.madeBy, participant_uri))

            # Link to topic
            g.add((contrib_uri, DEL.hasTopic, topic_uri))

            # Add language
            lang = fb_data.get('language')
            if lang:
                g.add((contrib_uri, DCT.language, Literal(lang)))

            # Link to process
            g.add((process_uri, DEL.hasContribution, contrib_uri))

    conn.close()

    # Save graph
    print(f"\nSaving knowledge graph to {output_file}...")
    g.serialize(destination=output_file, format='turtle')

    print(f"\n{'='*60}")
    print("KNOWLEDGE GRAPH CREATED")
    print(f"{'='*60}")
    print(f"Total triples: {len(g)}")
    print(f"Output file: {output_file}")
    print(f"{'='*60}")

    return g

def main():
    if len(sys.argv) < 2:
        print("Usage: python map_feedback_to_ontology.py <database.db> [output.ttl]")
        print("\nExample:")
        print("  python map_feedback_to_ontology.py eu_haveyoursay_specific.db haveyoursay_kg.ttl")
        sys.exit(1)

    db_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "haveyoursay_kg.ttl"

    if not Path(db_path).exists():
        print(f"Error: Database file '{db_path}' not found")
        sys.exit(1)

    create_knowledge_graph(db_path, output_file)

if __name__ == "__main__":
    main()