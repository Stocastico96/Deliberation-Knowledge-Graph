#!/usr/bin/env python3
"""
Convert EU Have Your Say data to RDF format
"""
import sqlite3
import json
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
from datetime import datetime
from tqdm import tqdm

# Namespaces
BASE_URI = "http://data.cogenta.org/deliberation/"
DEL = Namespace(BASE_URI)
SCHEMA = Namespace("http://schema.org/")

def convert_hys_to_rdf():
    """Convert HYS database to RDF"""
    
    db_path = '/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db'
    output_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/hys_data.ttl'
    
    print("Loading data from database...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create graph
    g = Graph()
    g.bind("del", DEL)
    g.bind("schema", SCHEMA)
    g.bind("dcterms", DCTERMS)
    
    # Get all initiatives
    initiatives = []
    for row in c.execute('SELECT id, data FROM initiatives WHERE data IS NOT NULL'):
        initiatives.append((row[0], json.loads(row[1])))
    
    print(f"Converting {len(initiatives)} initiatives...")
    
    for init_id, init_data in tqdm(initiatives, desc="Processing initiatives"):
        # Create initiative URI
        initiative_uri = URIRef(f"{BASE_URI}hys_initiative_{init_id}")
        
        # Basic properties
        g.add((initiative_uri, RDF.type, DEL.DeliberationProcess))
        g.add((initiative_uri, DEL.platform, Literal("EU Have Your Say")))
        
        # Title
        if init_data.get('shortTitle'):
            g.add((initiative_uri, DCTERMS.title, Literal(init_data['shortTitle'], lang='en')))
        
        # Description
        if init_data.get('description'):
            g.add((initiative_uri, DCTERMS.description, Literal(init_data['description'], lang='en')))
        
        # Reference number
        if init_data.get('referenceNumber'):
            g.add((initiative_uri, DEL.referenceNumber, Literal(init_data['referenceNumber'])))
        
        # Process publications
        for pub in init_data.get('publications', []):
            pub_id = pub.get('id')
            pub_uri = URIRef(f"{BASE_URI}hys_publication_{pub_id}")
            
            g.add((pub_uri, RDF.type, DEL.Publication))
            g.add((initiative_uri, DEL.hasPublication, pub_uri))
            
            # Publication metadata
            if pub.get('title'):
                g.add((pub_uri, DCTERMS.title, Literal(pub['title'], lang='en')))
            
            if pub.get('reference'):
                g.add((pub_uri, DEL.reference, Literal(pub['reference'])))
            
            # Publication date
            if pub.get('date'):
                try:
                    dt = datetime.fromisoformat(pub['date'].replace('Z', '+00:00'))
                    g.add((pub_uri, DCTERMS.date, Literal(dt.date(), datatype=XSD.date)))
                except:
                    pass
            
            # Total feedback count
            if pub.get('totalFeedback'):
                g.add((pub_uri, DEL.feedbackCount, Literal(pub['totalFeedback'], datatype=XSD.integer)))
    
    print("\nProcessing feedbacks...")
    
    # Get all feedbacks
    feedback_count = c.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
    print(f"Converting {feedback_count:,} feedbacks...")
    
    batch_size = 10000
    offset = 0
    
    while offset < feedback_count:
        feedbacks = c.execute(f'SELECT id, publication_id, data FROM feedback LIMIT {batch_size} OFFSET {offset}').fetchall()
        
        for fb_id, pub_id, fb_data_str in tqdm(feedbacks, desc=f"Batch {offset//batch_size + 1}", leave=False):
            fb_data = json.loads(fb_data_str)
            
            # Create feedback URI
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
            
            # User type
            if fb_data.get('userType'):
                g.add((feedback_uri, DEL.userType, Literal(fb_data['userType'])))
            
            # Country
            if fb_data.get('country'):
                g.add((feedback_uri, DEL.country, Literal(fb_data['country'])))
            
            # Language
            if fb_data.get('language'):
                g.add((feedback_uri, DCTERMS.language, Literal(fb_data['language'])))
        
        offset += batch_size
        
        # Save periodically
        if offset % 100000 == 0:
            print(f"\nSaving intermediate results... ({offset:,} feedbacks processed)")
            g.serialize(destination=output_file, format='turtle')
    
    conn.close()
    
    # Final save
    print(f"\nSaving to {output_file}...")
    g.serialize(destination=output_file, format='turtle')
    
    print(f"\n✓ Conversion complete!")
    print(f"  Total triples: {len(g):,}")
    print(f"  Output file: {output_file}")
    
    return len(g)

if __name__ == '__main__':
    convert_hys_to_rdf()
