#!/usr/bin/env python3
"""
Add remaining platforms to the knowledge graph:
- Collective Intelligence Project (Global Dialogue)
- Habermas Machine
- US Supreme Court Arguments
"""

import json
import csv
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, DCTERMS, XSD, FOAF
from datetime import datetime
import hashlib
import re

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
SCHEMA = Namespace("http://schema.org/")
BASE_URI = "https://svagnoni.linkeddata.es/resource/"

def slugify(text):
    """Create URL-friendly slug"""
    text = str(text).lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text[:50]

def create_uri(prefix, identifier):
    """Create a URI for a resource"""
    return URIRef(BASE_URI + prefix + "_" + str(identifier))


def add_collective_intelligence(g):
    """Add Collective Intelligence Project - Global Dialogue data"""
    print("\n" + "="*60)
    print("COLLECTIVE INTELLIGENCE PROJECT - GLOBAL DIALOGUE")
    print("="*60)

    # Use participants CSV which is more manageable
    participants_file = Path("data/collective_intelligence_project/global dialogue data/2024 GD1/particpants.csv")

    if not participants_file.exists():
        print(f"⚠️  File not found: {participants_file}")
        return 0, 0

    print(f"Loading {participants_file}...")

    # Create DeliberationProcess
    process_uri = create_uri("cip_gd", "2024_gd1")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Global Dialogue 2024 - What future do you want?", lang='en')))
    g.add((process_uri, DEL.identifier, Literal("cip_gd_2024_gd1")))
    g.add((process_uri, DEL.platform, Literal("Collective Intelligence Project")))

    # Add topic
    topic_uri = create_uri("cip_topic", "global_dialogue_2024")
    g.add((topic_uri, RDF.type, DEL.Topic))
    g.add((topic_uri, RDFS.label, Literal("Global Dialogue on AI Governance", lang='en')))
    g.add((process_uri, DEL.hasTopic, topic_uri))

    contrib_count = 0
    participant_set = set()

    # Read participant contributions from CSV (sample first 500 rows)
    with open(participants_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)[:500]  # Sample 500 participants

    for row in rows:
        participant_id = row.get('Participant Id', '')

        if not participant_id:
            continue

        # Create participant
        if participant_id not in participant_set:
            participant_uri = create_uri("cip_participant", slugify(participant_id))
            g.add((participant_uri, RDF.type, DEL.Participant))
            g.add((participant_uri, DEL.identifier, Literal(f"cip_participant_{slugify(participant_id)}")))
            g.add((process_uri, DEL.hasParticipant, participant_uri))
            participant_set.add(participant_id)

        # Extract text contributions from various question columns
        for key, value in row.items():
            # Look for question response columns that contain actual text
            if '(English)' in key or '(Original)' in key:
                text = value

                if not text or len(str(text).strip()) < 20:
                    continue

                # Create contribution
                question_slug = slugify(key[:30])
                contrib_uri = create_uri("cip_contrib", f"{slugify(participant_id)}_{question_slug}")
                g.add((contrib_uri, RDF.type, DEL.Contribution))
                g.add((contrib_uri, DEL.identifier, Literal(f"cip_contrib_{slugify(participant_id)}_{question_slug}")))
                g.add((contrib_uri, DEL.text, Literal(str(text))))
                g.add((contrib_uri, RDFS.comment, Literal(str(text))))
                g.add((process_uri, DEL.hasContribution, contrib_uri))
                g.add((contrib_uri, DEL.madeBy, participant_uri))
                contrib_count += 1

    print(f"✓ Added {contrib_count} contributions from {len(participant_set)} participants")
    return contrib_count, len(participant_set)


def add_habermas_machine(g):
    """Add Habermas Machine data"""
    print("\n" + "="*60)
    print("HABERMAS MACHINE")
    print("="*60)

    data_dir = Path("data/habermas_machine/data")

    if not data_dir.exists():
        print(f"⚠️  Directory not found: {data_dir}")
        return 0, 0

    # Use position statement ratings parquet (smaller file)
    parquet_file = data_dir / "hm_all_position_statement_ratings.parquet"

    if not parquet_file.exists():
        print(f"⚠️  File not found: {parquet_file}")
        return 0, 0

    print(f"Loading {parquet_file}...")

    try:
        import pandas as pd
        df = pd.read_parquet(parquet_file)
    except Exception as e:
        print(f"⚠️  Error loading parquet: {e}")
        return 0, 0

    # Sample first 1000 rows
    df = df.head(1000)

    print(f"Processing {len(df)} position statement ratings...")

    # Create DeliberationProcess
    process_uri = create_uri("habermas", "position_statements")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Habermas Machine Position Statement Ratings", lang='en')))
    g.add((process_uri, DEL.identifier, Literal("habermas_position_statements")))
    g.add((process_uri, DEL.platform, Literal("Habermas Machine")))

    # Add topic
    topic_uri = create_uri("habermas_topic", "deliberative_polling")
    g.add((topic_uri, RDF.type, DEL.Topic))
    g.add((topic_uri, RDFS.label, Literal("Deliberative Polling Position Statements", lang='en')))
    g.add((process_uri, DEL.hasTopic, topic_uri))

    contrib_count = 0
    participants = set()

    for idx, row in df.iterrows():
        participant_id = row.get('metadata.participant_id', f'participant_{idx}')

        # Get the statement text from question fields
        question_text = row.get('question.text', '') or row.get('question.affirming_statement', '') or row.get('question.negating_statement', '')

        if not question_text or len(str(question_text).strip()) < 20:
            continue

        # Create participant
        if participant_id not in participants:
            participant_uri = create_uri("habermas_participant", slugify(str(participant_id)))
            g.add((participant_uri, RDF.type, DEL.Participant))
            g.add((participant_uri, DEL.identifier, Literal(f"habermas_participant_{slugify(str(participant_id))}")))
            g.add((process_uri, DEL.hasParticipant, participant_uri))
            participants.add(participant_id)

        # Create contribution (statement + rating as context)
        rating = row.get('ratings.agreement', 'unknown')
        text = f"{question_text} [Rating: {rating}]"

        contrib_uri = create_uri("habermas_contrib", f"statement_{idx}")
        g.add((contrib_uri, RDF.type, DEL.Contribution))
        g.add((contrib_uri, DEL.identifier, Literal(f"habermas_contrib_statement_{idx}")))
        g.add((contrib_uri, DEL.text, Literal(text)))
        g.add((contrib_uri, RDFS.comment, Literal(str(question_text))))
        g.add((process_uri, DEL.hasContribution, contrib_uri))

        participant_uri = create_uri("habermas_participant", slugify(str(participant_id)))
        g.add((contrib_uri, DEL.madeBy, participant_uri))

        contrib_count += 1

    print(f"✓ Added {contrib_count} contributions from {len(participants)} participants")
    return contrib_count, len(participants)


def add_supreme_court(g):
    """Add US Supreme Court Arguments"""
    print("\n" + "="*60)
    print("US SUPREME COURT ARGUMENTS")
    print("="*60)

    csv_file = Path("data/US_supreme_court_arguments/dataset.csv")

    if not csv_file.exists():
        print(f"⚠️  File not found: {csv_file}")
        return 0, 0

    print(f"Loading {csv_file}...")

    # Read CSV with actual column names: speaker, text, case
    with open(csv_file, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} rows")

    # Group by case
    cases = {}
    for row in rows[:2000]:  # Process first 2000 as sample
        case_id = row.get('case', 'Unknown')

        if case_id not in cases:
            cases[case_id] = []
        cases[case_id].append(row)

    total_contrib = 0
    total_participants = 0

    for case_id, arguments in list(cases.items())[:100]:  # First 100 cases
        process_id = slugify(case_id)
        process_uri = create_uri("scotus", process_id)

        g.add((process_uri, RDF.type, DEL.DeliberationProcess))
        g.add((process_uri, DEL.name, Literal(f"US Supreme Court Case: {case_id}", lang='en')))
        g.add((process_uri, DEL.identifier, Literal(f"scotus_{process_id}")))
        g.add((process_uri, DEL.platform, Literal("US Supreme Court")))

        # Add topic
        topic_uri = create_uri("scotus_topic", process_id)
        g.add((topic_uri, RDF.type, DEL.Topic))
        g.add((topic_uri, RDFS.label, Literal(case_id, lang='en')))
        g.add((process_uri, DEL.hasTopic, topic_uri))

        participants = set()

        for idx, arg in enumerate(arguments):
            text = arg.get('text', '')
            speaker = arg.get('speaker', 'Speaker')

            if not text or len(text.strip()) < 20:
                continue

            # Create contribution
            contrib_uri = create_uri("scotus_contrib", f"{process_id}_{idx}")
            g.add((contrib_uri, RDF.type, DEL.Contribution))
            g.add((contrib_uri, DEL.identifier, Literal(f"scotus_contrib_{process_id}_{idx}")))
            g.add((contrib_uri, DEL.text, Literal(text)))
            g.add((contrib_uri, RDFS.comment, Literal(text)))
            g.add((process_uri, DEL.hasContribution, contrib_uri))

            # Create participant
            participant_id = f"{process_id}_{slugify(speaker)}"
            if participant_id not in participants:
                participant_uri = create_uri("scotus_participant", participant_id)
                g.add((participant_uri, RDF.type, DEL.Participant))
                g.add((participant_uri, DEL.name, Literal(speaker)))
                g.add((participant_uri, DEL.identifier, Literal(participant_id)))
                g.add((process_uri, DEL.hasParticipant, participant_uri))
                participants.add(participant_id)

            participant_uri = create_uri("scotus_participant", participant_id)
            g.add((contrib_uri, DEL.madeBy, participant_uri))

            total_contrib += 1

        total_participants += len(participants)

    print(f"✓ Added {total_contrib} contributions from {total_participants} participants")
    return total_contrib, total_participants


def main():
    print("="*60)
    print("ADDING REMAINING PLATFORMS TO KNOWLEDGE GRAPH")
    print("="*60)

    # Load existing KG
    print("\nLoading existing knowledge graph...")
    main_kg_path = "knowledge_graph/deliberation_kg_with_hys.ttl"

    g = Graph()
    g.parse(main_kg_path, format='turtle')
    print(f"✓ Loaded {len(g)} triples")

    # Bind namespaces
    g.bind("del", DEL)
    g.bind("dcterms", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("schema", SCHEMA)

    # Add each platform
    stats = {}

    # Collective Intelligence Project
    contrib, participants = add_collective_intelligence(g)
    stats['Collective Intelligence Project'] = {'contributions': contrib, 'participants': participants}

    # Habermas Machine
    contrib, participants = add_habermas_machine(g)
    stats['Habermas Machine'] = {'contributions': contrib, 'participants': participants}

    # US Supreme Court
    contrib, participants = add_supreme_court(g)
    stats['US Supreme Court'] = {'contributions': contrib, 'participants': participants}

    # Save updated graph
    output_path = "knowledge_graph/deliberation_kg_all_platforms.ttl"
    print(f"\n{'='*60}")
    print("SAVING UPDATED KNOWLEDGE GRAPH")
    print(f"{'='*60}")
    print(f"Total triples: {len(g)}")
    print(f"Output: {output_path}")

    g.serialize(destination=output_path, format='turtle')
    print("✓ Saved!")

    # Print final statistics
    print(f"\n{'='*60}")
    print("PLATFORM ADDITION SUMMARY")
    print(f"{'='*60}")

    total_new_contrib = 0
    total_new_participants = 0

    for platform, data in stats.items():
        print(f"\n{platform}:")
        print(f"  Contributions: {data['contributions']}")
        print(f"  Participants: {data['participants']}")
        total_new_contrib += data['contributions']
        total_new_participants += data['participants']

    print(f"\n{'='*60}")
    print(f"TOTAL NEW DATA:")
    print(f"  +{total_new_contrib} contributions")
    print(f"  +{total_new_participants} participants")
    print(f"\nFinal KG: {len(g)} triples")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
