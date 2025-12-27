#!/usr/bin/env python3
"""
Converte CSV HYS in RDF conforme all'ontologia DEL estesa
https://w3id.org/deliberation/ontology# (v1.0.1 - 2025-12-22)

Nuove proprietà e classi:
- del:country (Participant datatype property)
- del:participantType (Participant datatype property)
- del:Forum (classe)
- del:takesPlaceIn (DeliberationProcess → Forum object property)
"""

import csv
import json
import sqlite3
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
from datetime import datetime
from collections import defaultdict

# Namespaces
BASE = Namespace("https://svagnoni.linkeddata.es/resource/")
DEL = Namespace("https://w3id.org/deliberation/ontology#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

# Initialize graph
g = Graph()
g.bind("del", DEL)
g.bind("dcterms", DCTERMS)
g.bind("foaf", FOAF)
g.bind("", BASE)

print("=== Converting HYS CSV to DEL RDF ===\n")

# Load initiatives from database
print("Loading initiatives from database...")
conn = sqlite3.connect('eu_haveyoursay_with_feedbacks.db')
cursor = conn.cursor()
cursor.execute("SELECT id, data FROM initiatives")

initiatives = {}
for row in cursor.fetchall():
    init_id = row[0]
    data = json.loads(row[1])
    initiatives[init_id] = data

print(f"Loaded {len(initiatives)} initiatives")

# Process feedbacks from CSV
print("\nProcessing feedbacks from CSV...")
feedback_count = 0
participant_cache = {}  # Cache to avoid duplicate participants

with open('csv_export/feedback.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for row in reader:
        feedback_id = row['id']
        initiative_id = int(row['initiative_id'])

        # URIs
        feedback_uri = BASE[f"hys_feedback_{feedback_id}"]
        initiative_uri = BASE[f"hys_initiative_{initiative_id}"]

        # Create initiative if first time
        if initiative_id not in initiatives:
            print(f"WARNING: Initiative {initiative_id} not found in database")
            continue

        if (initiative_uri, RDF.type, DEL.DeliberationProcess) not in g:
            init_data = initiatives[initiative_id]
            g.add((initiative_uri, RDF.type, DEL.DeliberationProcess))

            # Title
            title = init_data.get('shortTitle', 'Untitled')
            g.add((initiative_uri, DCTERMS.title, Literal(title, lang='en')))

            # Forum - create EU Have Your Say forum entity
            forum_uri = BASE["forum_eu_have_your_say"]
            if (forum_uri, RDF.type, DEL.Forum) not in g:
                g.add((forum_uri, RDF.type, DEL.Forum))
                g.add((forum_uri, DEL.name, Literal("EU Have Your Say")))
                g.add((forum_uri, DCTERMS.description, Literal("European Commission public consultation platform", lang='en')))
            g.add((initiative_uri, DEL.takesPlaceIn, forum_uri))

            # Date if available
            if init_data.get('publishedDate'):
                try:
                    date_str = init_data['publishedDate']
                    g.add((initiative_uri, DCTERMS.date, Literal(date_str)))
                except:
                    pass

        # Create Contribution
        g.add((feedback_uri, RDF.type, DEL.Contribution))
        g.add((initiative_uri, DEL.hasContribution, feedback_uri))

        # Text
        if row['feedback'] and row['feedback'].strip():
            g.add((feedback_uri, DEL.text, Literal(row['feedback'], lang=row['language'].lower() if row['language'] else 'en')))

        # Timestamp
        if row['dateFeedback']:
            try:
                # Parse: 2025/09/30 12:19:18
                dt = datetime.strptime(row['dateFeedback'], '%Y/%m/%d %H:%M:%S')
                g.add((feedback_uri, DEL.timestamp, Literal(dt, datatype=XSD.dateTime)))
            except:
                pass

        # Language
        if row['language']:
            g.add((feedback_uri, DCTERMS.language, Literal(row['language'])))

        # Create Participant if has name or org
        create_participant = (row['firstName'] or row['surname'] or
                             row['country'] or row['userType'] or row['organization'])

        if create_participant:
            # Create participant URI based on name or anonymous
            if row['firstName'] or row['surname']:
                name = f"{row['firstName']}_{row['surname']}".strip('_').replace(' ', '_')
                participant_key = f"{name}_{row['country']}_{row['userType']}"
            else:
                participant_key = f"anon_{row['country']}_{row['userType']}_{feedback_id}"

            # Check cache to reuse participant entities
            if participant_key in participant_cache:
                participant_uri = participant_cache[participant_key]
            else:
                participant_uri = BASE[f"hys_participant_{hash(participant_key) % 1000000}"]
                participant_cache[participant_key] = participant_uri

                g.add((participant_uri, RDF.type, DEL.Participant))

                # Name
                if row['firstName'] or row['surname']:
                    full_name = f"{row['firstName']} {row['surname']}".strip()
                    g.add((participant_uri, FOAF.name, Literal(full_name)))

                # Country (NEW)
                if row['country']:
                    g.add((participant_uri, DEL.country, Literal(row['country'])))

                # ParticipantType (NEW)
                if row['userType']:
                    g.add((participant_uri, DEL.participantType, Literal(row['userType'])))

                # Organization affiliation
                if row['organization']:
                    org_uri = BASE[f"hys_org_{hash(row['organization']) % 1000000}"]
                    g.add((org_uri, RDF.type, DEL.Organization))
                    g.add((org_uri, DEL.name, Literal(row['organization'])))
                    g.add((participant_uri, DEL.isAffiliatedWith, org_uri))

                    # Company size if available
                    if row['companySize']:
                        # NOTE: No del:organizationSize in ontology yet (TODO)
                        # For now, use rdfs:comment or skip
                        pass

            # Link contribution to participant
            g.add((feedback_uri, DEL.madeBy, participant_uri))

        feedback_count += 1
        if feedback_count % 1000 == 0:
            print(f"  Processed {feedback_count} feedbacks...")

print(f"\n✅ Processed {feedback_count} feedbacks")
print(f"   Created {len(participant_cache)} unique participants")
print(f"   Total triples: {len(g)}")

# Save to file
output_file = "eu_have_your_say_FULL_DEL_ONTOLOGY.ttl"
print(f"\nSaving to {output_file}...")
g.serialize(destination=output_file, format='turtle')
print(f"✅ Done! File size: {len(open(output_file).read()) / 1024 / 1024:.1f} MB")

# Verification
print("\n=== VERIFICATION ===")
print(f"Initiatives: {len([s for s in g.subjects(RDF.type, DEL.DeliberationProcess)])}")
print(f"Contributions: {len([s for s in g.subjects(RDF.type, DEL.Contribution)])}")
print(f"Participants: {len([s for s in g.subjects(RDF.type, DEL.Participant)])}")
print(f"Organizations: {len([s for s in g.subjects(RDF.type, DEL.Organization)])}")

# Check new properties and classes
country_count = len(list(g.triples((None, DEL.country, None))))
ptype_count = len(list(g.triples((None, DEL.participantType, None))))
forum_count = len([s for s in g.subjects(RDF.type, DEL.Forum)])
takes_place_count = len(list(g.triples((None, DEL.takesPlaceIn, None))))

print(f"\n✅ New ontology properties:")
print(f"   del:country: {country_count} uses")
print(f"   del:participantType: {ptype_count} uses")
print(f"   del:Forum entities: {forum_count}")
print(f"   del:takesPlaceIn: {takes_place_count} uses")
