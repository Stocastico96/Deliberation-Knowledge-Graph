#!/usr/bin/env python3
"""
Map all public Pol.is conversations to RDF Knowledge Graph
Processes multiple Pol.is conversations from compdemocracy/openData repository
"""

import csv
import os
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS, FOAF
from datetime import datetime

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RESOURCE = Namespace("https://svagnoni.linkeddata.es/resource/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")
SCHEMA = Namespace("http://schema.org/")

# Initialize graph
g = Graph()
g.bind("del", DEL)
g.bind("resource", RESOURCE)
g.bind("rdfs", RDFS)
g.bind("dcterms", DCTERMS)
g.bind("foaf", FOAF)
g.bind("sioc", SIOC)
g.bind("schema", SCHEMA)

def clean_conversation_name(name):
    """Clean conversation name for URI"""
    return name.replace('.', '_').replace('-', '_')

def process_conversation(conv_dir, conv_name):
    """Process a single Pol.is conversation"""
    print(f"\nProcessing: {conv_name}")

    clean_name = clean_conversation_name(conv_name)

    # Read summary first to get conversation metadata
    summary_file = conv_dir / "summary.csv"
    if not summary_file.exists():
        print(f"  Warning: No summary.csv found, skipping")
        return 0

    # Parse summary (Pol.is CSV format is key-value pairs, one per line)
    summary = {}
    with open(summary_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key, value = parts
                    summary[key] = value

    if not summary:
        print(f"  Warning: Empty summary, skipping")
        return 0

    # Create deliberation process
    process_uri = RESOURCE[f"polis_{clean_name}"]
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))

    # Add title and description
    topic = summary.get('topic', conv_name)
    g.add((process_uri, RDFS.label, Literal(topic, lang="en")))

    description = summary.get('description', '')
    if description:
        g.add((process_uri, DCTERMS.description, Literal(description, lang="en")))

    # Add URL if available
    url = summary.get('url', '')
    if url:
        g.add((process_uri, SCHEMA.url, Literal(url, datatype=XSD.anyURI)))

    # Create forum/platform
    forum_uri = RESOURCE[f"polis_platform"]
    g.add((forum_uri, RDF.type, SIOC.Forum))
    g.add((forum_uri, SIOC.name, Literal("Pol.is")))
    g.add((process_uri, SIOC.has_host, forum_uri))

    # Process comments
    comments_file = conv_dir / "comments.csv"
    comment_count = 0

    if comments_file.exists():
        with open(comments_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                comment_id = row.get('comment-id')
                if not comment_id:
                    continue

                comment_count += 1

                # Create contribution
                contrib_uri = RESOURCE[f"polis_{clean_name}_comment_{comment_id}"]
                g.add((contrib_uri, RDF.type, DEL.Contribution))
                g.add((contrib_uri, DEL.isPartOf, process_uri))

                # Add comment text
                comment_body = row.get('comment-body', '')
                if comment_body:
                    g.add((contrib_uri, DEL.text, Literal(comment_body)))

                # Add timestamp
                timestamp = row.get('timestamp')
                if timestamp:
                    try:
                        dt = datetime.fromtimestamp(int(timestamp) / 1000)
                        g.add((contrib_uri, DCTERMS.created, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                    except:
                        pass

                # Add author
                author_id = row.get('author-id')
                if author_id:
                    participant_uri = RESOURCE[f"polis_{clean_name}_participant_{author_id}"]
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((contrib_uri, DEL.author, participant_uri))

                # Add vote counts
                agrees = row.get('agrees', '0')
                disagrees = row.get('disagrees', '0')

                if agrees:
                    g.add((contrib_uri, DEL.agreeCount, Literal(int(agrees), datatype=XSD.integer)))
                if disagrees:
                    g.add((contrib_uri, DEL.disagreeCount, Literal(int(disagrees), datatype=XSD.integer)))

    print(f"  ✓ Added {comment_count} comments from {conv_name}")
    return comment_count

def main():
    """Process all Pol.is conversations"""
    base_dir = Path("/home/svagnoni/deliberation-knowledge-graph/data/polis_public/openData")

    if not base_dir.exists():
        print(f"Error: Directory {base_dir} not found")
        return

    total_comments = 0
    conversations_processed = 0

    # Process each conversation directory
    for conv_dir in sorted(base_dir.iterdir()):
        if not conv_dir.is_dir():
            continue

        if conv_dir.name.startswith('.'):
            continue

        conv_name = conv_dir.name
        comments = process_conversation(conv_dir, conv_name)

        if comments > 0:
            conversations_processed += 1
            total_comments += comments

    # Save to file
    output_file = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/polis_public_kg.ttl"
    print(f"\n{'='*60}")
    print(f"Saving to {output_file}...")
    g.serialize(destination=output_file, format='turtle')

    triples_count = len(g)
    print(f"\n{'='*60}")
    print(f"POLIS PUBLIC DATA INTEGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"Conversations processed: {conversations_processed}")
    print(f"Total comments: {total_comments}")
    print(f"Total RDF triples: {triples_count:,}")
    print(f"Output file: {output_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
