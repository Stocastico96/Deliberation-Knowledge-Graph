#!/usr/bin/env python3
"""
Convert only the latest 100 EU HYS initiatives to RDF
Much smaller dataset for faster processing
"""

import sqlite3
import json
from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal, RDF, DCTERMS, XSD
from tqdm import tqdm

# Namespaces
BASE_URI = 'http://data.cogenta.org/deliberation/'
DEL = Namespace('http://data.cogenta.org/ontology/')
SCHEMA = Namespace('http://schema.org/')

def convert_top100_hys_to_rdf():
    """Convert latest 100 HYS initiatives to RDF"""

    db_path = '/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db'
    output_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/hys_data.ttl'

    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get top 100 initiatives by feedback count
    print("Loading top 100 initiative IDs...")
    with open('/tmp/top100_init_ids.txt', 'r') as f:
        initiative_ids = [int(line.strip()) for line in f]

    print(f"Fetching {len(initiative_ids)} initiatives...")
    initiative_ids_str = ','.join(map(str, initiative_ids))

    initiatives = c.execute(f'''
        SELECT id, data
        FROM initiatives
        WHERE id IN ({initiative_ids_str})
    ''').fetchall()

    print(f"Found {len(initiatives)} initiatives")

    # Create RDF graph
    g = Graph()
    g.bind("del", DEL)
    g.bind("schema", SCHEMA)
    g.bind("dcterms", DCTERMS)

    # Process initiatives
    print("\nProcessing initiatives...")
    for init_id, init_data_str in tqdm(initiatives):
        init_data = json.loads(init_data_str)

        initiative_uri = URIRef(f"{BASE_URI}hys_initiative_{init_id}")

        g.add((initiative_uri, RDF.type, DEL.DeliberationProcess))
        g.add((initiative_uri, DEL.platform, Literal("EU Have Your Say")))

        if init_data.get('shortTitle'):
            g.add((initiative_uri, DCTERMS.title, Literal(init_data['shortTitle'], lang='en')))

        if init_data.get('reference'):
            g.add((initiative_uri, DEL.reference, Literal(init_data['reference'])))

        # Process publications
        for pub in init_data.get('publications', []):
            pub_id = pub.get('id')
            if not pub_id:
                continue

            pub_uri = URIRef(f"{BASE_URI}hys_publication_{pub_id}")
            g.add((pub_uri, RDF.type, DEL.Publication))
            g.add((initiative_uri, DEL.hasPublication, pub_uri))

            if pub.get('title'):
                g.add((pub_uri, DCTERMS.title, Literal(pub['title'], lang='en')))

            if pub.get('publicationDate'):
                try:
                    dt = datetime.strptime(pub['publicationDate'], '%Y/%m/%d %H:%M:%S')
                    g.add((pub_uri, DCTERMS.date, Literal(dt.date(), datatype=XSD.date)))
                except:
                    pass

            if pub.get('endDate'):
                try:
                    dt = datetime.strptime(pub['endDate'], '%Y/%m/%d %H:%M:%S')
                    g.add((pub_uri, DEL.endDate, Literal(dt.date(), datatype=XSD.date)))
                except:
                    pass

    # Get feedbacks for these initiatives
    print("\nCounting feedbacks...")
    feedback_count = c.execute(f'''
        SELECT COUNT(*)
        FROM feedback
        WHERE publication_id IN (
            SELECT DISTINCT json_extract(value, '$.id')
            FROM initiatives, json_each(json_extract(data, '$.publications'))
            WHERE initiatives.id IN ({initiative_ids_str})
        )
    ''').fetchone()[0]

    print(f"Processing {feedback_count:,} feedbacks...")

    # Process feedbacks in batches
    batch_size = 10000
    offset = 0

    while offset < feedback_count:
        feedbacks = c.execute(f'''
            SELECT f.id, f.publication_id, f.data
            FROM feedback f
            WHERE f.publication_id IN (
                SELECT DISTINCT json_extract(value, '$.id')
                FROM initiatives, json_each(json_extract(data, '$.publications'))
                WHERE initiatives.id IN ({initiative_ids_str})
            )
            LIMIT {batch_size} OFFSET {offset}
        ''').fetchall()

        for fb_id, pub_id, fb_data_str in tqdm(feedbacks, desc=f"Batch {offset//batch_size + 1}", leave=False):
            fb_data = json.loads(fb_data_str)

            feedback_uri = URIRef(f"{BASE_URI}hys_feedback_{fb_id}")
            pub_uri = URIRef(f"{BASE_URI}hys_publication_{pub_id}")

            g.add((feedback_uri, RDF.type, DEL.Contribution))
            g.add((pub_uri, DEL.hasContribution, feedback_uri))

            # Feedback text
            if fb_data.get('feedback'):
                g.add((feedback_uri, DEL.content, Literal(fb_data['feedback'], lang=fb_data.get('language', 'en').lower())))

            # Date
            if fb_data.get('dateFeedback'):
                try:
                    dt = datetime.strptime(fb_data['dateFeedback'], '%Y/%m/%d %H:%M:%S')
                    g.add((feedback_uri, DCTERMS.date, Literal(dt.date(), datatype=XSD.date)))
                except:
                    pass

            # Author metadata
            if fb_data.get('organization'):
                g.add((feedback_uri, DEL.organization, Literal(fb_data['organization'])))

            if fb_data.get('firstName') and fb_data.get('surname'):
                author_name = f"{fb_data['firstName']} {fb_data['surname']}"
                g.add((feedback_uri, DEL.author, Literal(author_name)))

            if fb_data.get('userType'):
                g.add((feedback_uri, DEL.userType, Literal(fb_data['userType'])))

            if fb_data.get('country'):
                g.add((feedback_uri, DEL.country, Literal(fb_data['country'])))

            if fb_data.get('language'):
                g.add((feedback_uri, DCTERMS.language, Literal(fb_data['language'])))

        offset += batch_size

    conn.close()

    # Save
    print(f"\nSaving to {output_file}...")
    g.serialize(destination=output_file, format='turtle')

    print(f"\n✓ Conversion complete!")
    print(f"  Initiatives: 100")
    print(f"  Feedbacks: {feedback_count:,}")
    print(f"  Total triples: {len(g):,}")
    print(f"  Output: {output_file}")

    return len(g)

if __name__ == '__main__':
    convert_top100_hys_to_rdf()
