#!/usr/bin/env python3
"""
Convert eu_have_your_say_export.json to RDF and add to main knowledge graph
Uses the same ontology as the rest of the project
"""

import json
import sys
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, DCTERMS, XSD, FOAF
from datetime import datetime
import hashlib

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
SCHEMA = Namespace("http://schema.org/")
BASE_URI = "https://svagnoni.linkeddata.es/resource/"

def slugify(text):
    """Create a URL-friendly slug"""
    import re
    text = str(text).lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text[:50]

def create_uri(prefix, identifier):
    """Create a URI for a resource"""
    return URIRef(BASE_URI + prefix + "_" + str(identifier))

def convert_to_rdf(json_path, output_path):
    """Convert JSON export to RDF"""
    print(f"Loading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        initiatives = json.load(f)

    print(f"Creating RDF graph for {len(initiatives)} initiatives...")

    g = Graph()
    g.bind("del", DEL)
    g.bind("dcterms", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("schema", SCHEMA)

    total_contributions = 0
    total_participants = 0

    for initiative in initiatives:
        init_id = initiative['id']
        init_data = initiative['data']
        feedbacks = initiative['feedbacks']

        # Create DeliberationProcess
        process_uri = create_uri("hys_process", init_id)
        g.add((process_uri, RDF.type, DEL.DeliberationProcess))

        # Add process metadata
        short_title = init_data.get('shortTitle', f'Have Your Say Initiative {init_id}')
        g.add((process_uri, DEL.name, Literal(short_title, lang='en')))
        g.add((process_uri, DEL.identifier, Literal(f"hys_{init_id}")))
        g.add((process_uri, DEL.platform, Literal("EU Have Your Say")))

        if init_data.get('dossierSummary'):
            g.add((process_uri, RDFS.comment, Literal(init_data['dossierSummary'], lang='en')))

        # Source URL
        if init_data.get('reference'):
            source_url = f"https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives/{init_id}"
            g.add((process_uri, DCTERMS.source, Literal(source_url)))

        # Track unique participants
        participants = {}

        print(f"  Initiative {init_id}: {len(feedbacks)} feedbacks")

        # Process feedbacks as contributions
        for idx, feedback in enumerate(feedbacks):
            fb_id = feedback.get('id', f"{init_id}_{idx}")

            # Create Contribution
            contrib_uri = create_uri("hys_contrib", fb_id)
            g.add((contrib_uri, RDF.type, DEL.Contribution))
            g.add((contrib_uri, DEL.identifier, Literal(f"hys_contrib_{fb_id}")))

            # Link to process
            g.add((process_uri, DEL.hasContribution, contrib_uri))

            # Contribution text
            text = feedback.get('feedback', '')
            if text and len(text.strip()) > 0:
                g.add((contrib_uri, DEL.text, Literal(text)))
                g.add((contrib_uri, RDFS.comment, Literal(text)))
                total_contributions += 1

            # Timestamp
            date_feedback = feedback.get('dateFeedback')
            if date_feedback:
                try:
                    # Parse ISO date
                    dt = datetime.fromisoformat(date_feedback.replace('Z', '+00:00'))
                    g.add((contrib_uri, DEL.timestamp, Literal(dt, datatype=XSD.dateTime)))
                    g.add((contrib_uri, DCTERMS.created, Literal(dt, datatype=XSD.dateTime)))
                except:
                    pass

            # Language
            language = feedback.get('language')
            if language:
                g.add((contrib_uri, DEL.language, Literal(language)))

            # Create Participant
            # Use organization name or create anonymous ID
            org_name = feedback.get('organization', '').strip()
            first_name = feedback.get('firstName', '').strip()
            surname = feedback.get('surname', '').strip()
            user_type = feedback.get('userType', 'individual')

            if org_name:
                # Organization participant
                participant_id = f"hys_org_{slugify(org_name)}_{hashlib.md5(org_name.encode()).hexdigest()[:8]}"
                participant_uri = create_uri("hys_participant", participant_id)

                if participant_id not in participants:
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, RDF.type, FOAF.Organization))
                    g.add((participant_uri, FOAF.name, Literal(org_name)))
                    g.add((participant_uri, DEL.name, Literal(org_name)))
                    g.add((participant_uri, DEL.identifier, Literal(participant_id)))

                    # Add to process
                    g.add((process_uri, DEL.hasParticipant, participant_uri))
                    participants[participant_id] = True
                    total_participants += 1

            elif first_name or surname:
                # Individual participant
                full_name = f"{first_name} {surname}".strip()
                participant_id = f"hys_person_{slugify(full_name)}_{hashlib.md5(full_name.encode()).hexdigest()[:8]}"
                participant_uri = create_uri("hys_participant", participant_id)

                if participant_id not in participants:
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, RDF.type, FOAF.Person))
                    g.add((participant_uri, FOAF.name, Literal(full_name)))
                    g.add((participant_uri, DEL.name, Literal(full_name)))
                    g.add((participant_uri, DEL.identifier, Literal(participant_id)))

                    if first_name:
                        g.add((participant_uri, FOAF.givenName, Literal(first_name)))
                    if surname:
                        g.add((participant_uri, FOAF.familyName, Literal(surname)))

                    # Add to process
                    g.add((process_uri, DEL.hasParticipant, participant_uri))
                    participants[participant_id] = True
                    total_participants += 1

            else:
                # Anonymous participant
                participant_id = f"hys_anon_{fb_id}"
                participant_uri = create_uri("hys_participant", participant_id)

            # Link contribution to participant
            g.add((contrib_uri, DEL.madeBy, participant_uri))

            # Country
            country = feedback.get('country')
            if country:
                g.add((participant_uri, SCHEMA.addressCountry, Literal(country)))

        # Create Topic for the initiative
        if init_data.get('shortTitle'):
            topic_uri = create_uri("hys_topic", init_id)
            g.add((topic_uri, RDF.type, DEL.Topic))
            g.add((topic_uri, RDFS.label, Literal(init_data['shortTitle'], lang='en')))
            g.add((topic_uri, DEL.identifier, Literal(f"hys_topic_{init_id}")))
            g.add((process_uri, DEL.hasTopic, topic_uri))

    # Save to file
    print(f"\nSaving RDF graph...")
    print(f"  Total triples: {len(g)}")
    print(f"  Total contributions: {total_contributions}")
    print(f"  Total unique participants: {total_participants}")

    g.serialize(destination=output_path, format='turtle')
    print(f"✓ Saved to {output_path}")

    return len(g), total_contributions, total_participants


def merge_with_main_kg(hys_ttl, main_kg_path, output_path):
    """Merge Have Your Say data with main knowledge graph"""
    print(f"\nMerging with main knowledge graph...")
    print(f"  Loading {main_kg_path}...")

    main_g = Graph()
    main_g.parse(main_kg_path, format='turtle')
    print(f"  Main KG: {len(main_g)} triples")

    print(f"  Loading {hys_ttl}...")
    hys_g = Graph()
    hys_g.parse(hys_ttl, format='turtle')
    print(f"  HYS data: {len(hys_g)} triples")

    # Merge
    print(f"  Merging...")
    for triple in hys_g:
        main_g.add(triple)

    print(f"  Merged KG: {len(main_g)} triples")

    # Save
    print(f"  Saving to {output_path}...")
    main_g.serialize(destination=output_path, format='turtle')
    print(f"✓ Done!")

    return len(main_g)


if __name__ == "__main__":
    json_path = "eu_have_your_say_export.json"
    hys_ttl = "eu_have_your_say.ttl"
    main_kg = "../../knowledge_graph/deliberation_kg.ttl"
    merged_kg = "../../knowledge_graph/deliberation_kg_with_hys.ttl"

    # Convert JSON to RDF
    triples, contribs, participants = convert_to_rdf(json_path, hys_ttl)

    # Merge with main KG
    print(f"\n{'='*60}")
    total_triples = merge_with_main_kg(hys_ttl, main_kg, merged_kg)

    print(f"\n{'='*60}")
    print("CONVERSION COMPLETE")
    print(f"{'='*60}")
    print(f"Have Your Say data:")
    print(f"  - 10 initiatives")
    print(f"  - {contribs} contributions")
    print(f"  - {participants} unique participants")
    print(f"\nMerged knowledge graph:")
    print(f"  - {total_triples} total triples")
    print(f"  - Output: {merged_kg}")
    print(f"{'='*60}")
