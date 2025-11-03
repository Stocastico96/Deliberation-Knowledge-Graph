#!/usr/bin/env python3
"""
Script to process all available datasets and add them to the knowledge graph.
For large datasets, processes a representative sample.
"""

import os
import sys
import csv
import json
import argparse
from datetime import datetime
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
import uuid
import hashlib

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
BASE_URI = "https://w3id.org/deliberation/resource/"

def create_unified_graph():
    """Create a unified RDF graph"""
    g = Graph()
    g.bind("del", DEL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    return g

def process_eu_have_your_say(graph, feedback_csv, initiatives_csv, limit=1000):
    """Process EU Have Your Say feedback data"""
    print(f"Processing EU Have Your Say data (limit: {limit})...")

    # Load initiatives for metadata
    initiatives = {}
    with open(initiatives_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            initiatives[row['id']] = row

    # Process feedback
    with open(feedback_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0

        # Group by initiative
        initiative_groups = {}
        for row in reader:
            if count >= limit:
                break
            initiative_id = row.get('initiative_id', '')
            if initiative_id not in initiative_groups:
                initiative_groups[initiative_id] = []
            initiative_groups[initiative_id].append(row)
            count += 1

        # Create deliberation processes for each initiative
        for init_id, feedbacks in initiative_groups.items():
            if init_id not in initiatives:
                continue

            initiative = initiatives[init_id]
            process_id = f"euhys_{init_id}"
            process_uri = URIRef(BASE_URI + process_id)

            graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
            graph.add((process_uri, DEL.identifier, Literal(process_id)))
            graph.add((process_uri, DEL.name, Literal(f"EU Have Your Say: {initiative.get('shortTitle', f'Initiative {init_id}')}")))
            graph.add((process_uri, DEL.platform, Literal("EU Have Your Say")))

            # Add topic
            topic_id = f"euhys_topic_{init_id}"
            topic_uri = URIRef(BASE_URI + topic_id)
            graph.add((topic_uri, RDF.type, DEL.Topic))
            graph.add((topic_uri, DEL.identifier, Literal(topic_id)))
            graph.add((topic_uri, DEL.name, Literal(initiative.get('shortTitle', ''))))
            graph.add((process_uri, DEL.hasTopic, topic_uri))

            # Add participants and contributions
            for feedback in feedbacks:
                # Create participant
                participant_id = f"euhys_user_{feedback.get('id', uuid.uuid4())}"
                participant_uri = URIRef(BASE_URI + participant_id)
                graph.add((participant_uri, RDF.type, DEL.Participant))
                graph.add((participant_uri, DEL.identifier, Literal(participant_id)))

                # Use organization or construct anonymous name
                org = feedback.get('organization', '').strip()
                if org:
                    graph.add((participant_uri, DEL.name, Literal(org)))
                    # Add organization affiliation
                    org_uri = URIRef(BASE_URI + f"org_{hashlib.md5(org.encode()).hexdigest()[:8]}")
                    graph.add((org_uri, RDF.type, DEL.Organization))
                    graph.add((org_uri, DEL.name, Literal(org)))
                    graph.add((participant_uri, DEL.isAffiliatedWith, org_uri))
                else:
                    name_parts = []
                    if feedback.get('firstName'):
                        name_parts.append(feedback['firstName'])
                    if feedback.get('surname'):
                        name_parts.append(feedback['surname'])
                    if name_parts:
                        graph.add((participant_uri, DEL.name, Literal(' '.join(name_parts))))
                    else:
                        graph.add((participant_uri, DEL.name, Literal(f"Anonymous User")))

                graph.add((process_uri, DEL.hasParticipant, participant_uri))

                # Create contribution
                contrib_id = f"euhys_feedback_{feedback['id']}"
                contrib_uri = URIRef(BASE_URI + contrib_id)
                graph.add((contrib_uri, RDF.type, DEL.Contribution))
                graph.add((contrib_uri, DEL.identifier, Literal(contrib_id)))
                graph.add((contrib_uri, DEL.text, Literal(feedback.get('feedback', ''))))
                graph.add((contrib_uri, DEL.madeBy, participant_uri))

                # Add timestamp
                date_str = feedback.get('dateFeedback', '')
                if date_str:
                    try:
                        dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')
                        graph.add((contrib_uri, DEL.timestamp, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                    except:
                        pass

                graph.add((process_uri, DEL.hasContribution, contrib_uri))

    print(f"Processed {len(initiative_groups)} EU Have Your Say initiatives")
    return True

def process_decidim_barcelona(graph, proposals_csv, comments_csv, limit=500):
    """Process Decidim Barcelona proposals and comments"""
    print(f"Processing Decidim Barcelona data (limit: {limit})...")

    # First, collect all proposals
    proposals = {}
    with open(proposals_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0

        for row in reader:
            if count >= limit:
                break
            count += 1

            proposal_db_id = row['id']
            proposals[proposal_db_id] = row

            proposal_id = f"decidim_bcn_proposal_{proposal_db_id}"
            process_uri = URIRef(BASE_URI + proposal_id)

            graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
            graph.add((process_uri, DEL.identifier, Literal(proposal_id)))

            # Use Spanish title if Catalan not available
            title = row.get('title/ca', row.get('title/es', f'Proposal {proposal_db_id}'))
            graph.add((process_uri, DEL.name, Literal(title)))
            graph.add((process_uri, DEL.platform, Literal("Decidim Barcelona")))

            # Add published date
            pub_date = row.get('published_at', '')
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date, '%Y/%m/%d %H:%M')
                    graph.add((process_uri, DEL.startDate, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                except:
                    pass

            # Add topic/category
            category = row.get('category/name/ca', row.get('category/name/es', ''))
            if category:
                topic_id = f"decidim_bcn_topic_{hashlib.md5(category.encode()).hexdigest()[:8]}"
                topic_uri = URIRef(BASE_URI + topic_id)
                graph.add((topic_uri, RDF.type, DEL.Topic))
                graph.add((topic_uri, DEL.identifier, Literal(topic_id)))
                graph.add((topic_uri, DEL.name, Literal(category)))
                graph.add((process_uri, DEL.hasTopic, topic_uri))

            # Create author participant (anonymous since not in CSV)
            author_id = f"decidim_bcn_user_{hashlib.md5(f'proposal_author_{proposal_db_id}'.encode()).hexdigest()[:8]}"
            author_uri = URIRef(BASE_URI + author_id)
            graph.add((author_uri, RDF.type, DEL.Participant))
            graph.add((author_uri, DEL.identifier, Literal(author_id)))
            graph.add((author_uri, DEL.name, Literal(f"Participant {author_id[-8:]}")))
            graph.add((process_uri, DEL.hasParticipant, author_uri))

            # Create main proposal contribution
            contrib_id = f"decidim_bcn_contrib_{proposal_db_id}"
            contrib_uri = URIRef(BASE_URI + contrib_id)
            graph.add((contrib_uri, RDF.type, DEL.Contribution))
            graph.add((contrib_uri, DEL.identifier, Literal(contrib_id)))

            body = row.get('body/ca', row.get('body/es', ''))
            graph.add((contrib_uri, DEL.text, Literal(body)))
            graph.add((contrib_uri, DEL.madeBy, author_uri))

            if pub_date:
                try:
                    dt = datetime.strptime(pub_date, '%Y/%m/%d %H:%M')
                    graph.add((contrib_uri, DEL.timestamp, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                except:
                    pass

            graph.add((process_uri, DEL.hasContribution, contrib_uri))

    print(f"Processed {count} Decidim Barcelona proposals")

    # Now process comments for these proposals
    if os.path.exists(comments_csv):
        print(f"Processing comments for Decidim Barcelona proposals...")
        comment_count = 0

        with open(comments_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                # Only process comments for proposals we included
                commentable_id = row.get('commentable_id', '')
                commentable_type = row.get('commentable_type', '')

                # Only process if it's a proposal comment and we have the proposal
                if commentable_type != 'Decidim::Proposals::Proposal' or commentable_id not in proposals:
                    continue

                if comment_count >= limit * 2:  # Allow 2x comments as proposals
                    break

                comment_id = row.get('id', '')
                if not comment_id:
                    continue

                comment_count += 1

                # Use the actual commentable_id to link to the correct proposal
                process_id = f"decidim_bcn_proposal_{commentable_id}"
                process_uri = URIRef(BASE_URI + process_id)

                # Create comment author
                author_name = row.get('author/name', f'Anonymous_{comment_id}')
                author_id = f"decidim_bcn_user_{hashlib.md5(author_name.encode()).hexdigest()[:8]}"
                author_uri = URIRef(BASE_URI + author_id)
                graph.add((author_uri, RDF.type, DEL.Participant))
                graph.add((author_uri, DEL.identifier, Literal(author_id)))
                graph.add((author_uri, DEL.name, Literal(author_name)))
                graph.add((process_uri, DEL.hasParticipant, author_uri))

                # Create comment contribution
                comment_contrib_id = f"decidim_bcn_comment_{comment_id}"
                comment_uri = URIRef(BASE_URI + comment_contrib_id)
                graph.add((comment_uri, RDF.type, DEL.Contribution))
                graph.add((comment_uri, DEL.identifier, Literal(comment_contrib_id)))
                graph.add((comment_uri, DEL.text, Literal(row.get('body', ''))))
                graph.add((comment_uri, DEL.madeBy, author_uri))

                # Add timestamp
                created = row.get('created_at', '')
                if created:
                    try:
                        dt = datetime.strptime(created, '%Y-%m-%d %H:%M:%S UTC')
                        graph.add((comment_uri, DEL.timestamp, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                    except:
                        pass

                # Link comment as response to main proposal contribution
                main_contrib_uri = URIRef(BASE_URI + f"decidim_bcn_contrib_{commentable_id}")
                graph.add((comment_uri, DEL.responseTo, main_contrib_uri))

                graph.add((process_uri, DEL.hasContribution, comment_uri))

        print(f"Processed {comment_count} comments for Decidim Barcelona")

    return True

def process_decide_madrid(graph, debates_csv, comments_csv, limit=500):
    """Process Decide Madrid debates and comments"""
    print(f"Processing Decide Madrid data (limit: {limit})...")

    # First, collect all debates
    debates = {}
    with open(debates_csv, 'r', encoding='latin-1') as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0

        for row in reader:
            if count >= limit:
                break
            count += 1

            debate_id = row['id']
            debates[debate_id] = row

            process_id = f"decide_madrid_debate_{debate_id}"
            process_uri = URIRef(BASE_URI + process_id)

            graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
            graph.add((process_uri, DEL.identifier, Literal(process_id)))
            graph.add((process_uri, DEL.name, Literal(row.get('title', f'Debate {debate_id}'))))
            graph.add((process_uri, DEL.platform, Literal("Decide Madrid")))

            # Add created date
            created = row.get('created_at', '')
            if created:
                try:
                    dt = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
                    graph.add((process_uri, DEL.startDate, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                except:
                    pass

            # Create participant for debate author
            author = row.get('author_name', 'Anonymous')
            participant_id = f"decide_madrid_user_{hashlib.md5(author.encode()).hexdigest()[:8]}"
            participant_uri = URIRef(BASE_URI + participant_id)
            graph.add((participant_uri, RDF.type, DEL.Participant))
            graph.add((participant_uri, DEL.identifier, Literal(participant_id)))
            graph.add((participant_uri, DEL.name, Literal(author)))
            graph.add((process_uri, DEL.hasParticipant, participant_uri))

            # Create main debate contribution
            contrib_id = f"decide_madrid_contrib_{debate_id}"
            contrib_uri = URIRef(BASE_URI + contrib_id)
            graph.add((contrib_uri, RDF.type, DEL.Contribution))
            graph.add((contrib_uri, DEL.identifier, Literal(contrib_id)))
            graph.add((contrib_uri, DEL.text, Literal(row.get('description', ''))))
            graph.add((contrib_uri, DEL.madeBy, participant_uri))

            if created:
                try:
                    dt = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
                    graph.add((contrib_uri, DEL.timestamp, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                except:
                    pass

            graph.add((process_uri, DEL.hasContribution, contrib_uri))

    print(f"Processed {count} Decide Madrid debates")

    # Now process comments for these debates
    if os.path.exists(comments_csv):
        print(f"Processing comments for Decide Madrid debates...")
        comment_count = 0
        with open(comments_csv, 'r', encoding='latin-1') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                # Only process comments for debates we included
                commentable_id = row.get('commentable_id', '')
                commentable_type = row.get('commentable_type', '')

                if commentable_type == 'Debate' and commentable_id in debates:
                    comment_count += 1

                    process_id = f"decide_madrid_debate_{commentable_id}"
                    process_uri = URIRef(BASE_URI + process_id)

                    # Create comment author (anonymous since no author info in CSV)
                    comment_id = row.get('id', uuid.uuid4())
                    author_id = f"decide_madrid_user_{hashlib.md5(f'comment_author_{comment_id}'.encode()).hexdigest()[:8]}"
                    author_uri = URIRef(BASE_URI + author_id)
                    graph.add((author_uri, RDF.type, DEL.Participant))
                    graph.add((author_uri, DEL.identifier, Literal(author_id)))
                    graph.add((author_uri, DEL.name, Literal(f"Participant {author_id[-8:]}")))
                    graph.add((process_uri, DEL.hasParticipant, author_uri))

                    # Create comment contribution
                    comment_contrib_id = f"decide_madrid_comment_{comment_id}"
                    comment_uri = URIRef(BASE_URI + comment_contrib_id)
                    graph.add((comment_uri, RDF.type, DEL.Contribution))
                    graph.add((comment_uri, DEL.identifier, Literal(comment_contrib_id)))
                    graph.add((comment_uri, DEL.text, Literal(row.get('body', ''))))
                    graph.add((comment_uri, DEL.madeBy, author_uri))

                    # Add timestamp
                    created = row.get('created_at', '')
                    if created:
                        try:
                            # Handle format like "07/09/2015 08"
                            dt = datetime.strptime(created, '%d/%m/%Y %H')
                            graph.add((comment_uri, DEL.timestamp, Literal(dt.isoformat(), datatype=XSD.dateTime)))
                        except:
                            pass

                    # Link comment as response to main debate contribution
                    main_contrib_uri = URIRef(BASE_URI + f"decide_madrid_contrib_{commentable_id}")
                    graph.add((comment_uri, DEL.responseTo, main_contrib_uri))

                    graph.add((process_uri, DEL.hasContribution, comment_uri))

        print(f"Processed {comment_count} comments for Decide Madrid")

    return True

def main():
    parser = argparse.ArgumentParser(description='Process all deliberation datasets')
    parser.add_argument('--output', default='knowledge_graph/deliberation_kg_full.ttl', help='Output file path')
    parser.add_argument('--ep-limit', type=int, default=46, help='Number of EP debates to include (default: 46)')
    parser.add_argument('--euhys-limit', type=int, default=5346, help='EU Have Your Say feedback limit (default: 5346)')
    parser.add_argument('--decidim-limit', type=int, default=50000, help='Decidim Barcelona proposals limit (default: 50000)')
    parser.add_argument('--madrid-limit', type=int, default=30000, help='Decide Madrid debates limit (default: 30000)')

    args = parser.parse_args()

    # Create graph
    graph = create_unified_graph()

    # Import EP debates processing from create_knowledge_graph.py
    sys.path.insert(0, '/home/svagnoni/deliberation-knowledge-graph')
    from create_knowledge_graph import process_ep_debates

    # Process EU Parliament debates
    ep_debates = [
        # 2025 debates (from ep_debates folder)
        "data/EU_parliament_debates/ep_debates/debate_2025-03-10.json",
        "data/EU_parliament_debates/ep_debates/debate_2025-03-11.json",
        "data/EU_parliament_debates/ep_debates/debate_2025-03-12.json",
        "data/EU_parliament_debates/ep_debates/debate_2025-03-27.json",
        "data/EU_parliament_debates/ep_debates/debate_1_Competitiveness_Compass_(debat.json",
        # 2024 debates (from debates folder)
        "data/EU_parliament_debates/debates/debate_20240716.json",
        "data/EU_parliament_debates/debates/debate_20240717.json",
        "data/EU_parliament_debates/debates/debate_20240718.json",
        "data/EU_parliament_debates/debates/debate_20240916.json",
        "data/EU_parliament_debates/debates/debate_20240917.json",
        "data/EU_parliament_debates/debates/debate_20240918.json",
        "data/EU_parliament_debates/debates/debate_20241007.json",
        # 2024-2025 debates (newly downloaded)
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-09-16.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-09-17.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-09-18.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-09-19.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-10-21.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-10-22.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-10-23.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-10-24.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-11-25.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-11-26.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-11-27.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2024-11-28.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-05-21.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-05-22.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-06-16.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-06-17.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-06-18.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-06-19.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-07-07.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-07-08.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-07-09.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-07-10.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-09-08.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-09-09.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-09-10.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-09-11.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-06.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-07.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-08.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-09.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-20.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-21.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-22.json",
        "data/EU_parliament_debates/debates_2024_2025/verbatim_2025-10-23.json",
    ]

    for debate_file in ep_debates[:args.ep_limit]:
        if os.path.exists(debate_file):
            process_ep_debates(graph, debate_file)

    # Process EU Have Your Say
    if os.path.exists('data/EU_have_your_say/csv_export/feedback.csv'):
        process_eu_have_your_say(
            graph,
            'data/EU_have_your_say/csv_export/feedback.csv',
            'data/EU_have_your_say/csv_export/initiatives.csv',
            limit=args.euhys_limit
        )

    # Process Decidim Barcelona
    if os.path.exists('data/decidim_barcelona/data/www.decidim.barcelona-open-data-proposals.csv'):
        process_decidim_barcelona(
            graph,
            'data/decidim_barcelona/data/www.decidim.barcelona-open-data-proposals.csv',
            'data/decidim_barcelona/data/www.decidim.barcelona-open-data-proposal_comments.csv',
            limit=args.decidim_limit
        )

    # Process Decide Madrid
    if os.path.exists('data/decide_Madrid/data/debates.csv'):
        process_decide_madrid(
            graph,
            'data/decide_Madrid/data/debates.csv',
            'data/decide_Madrid/data/comments.csv',
            limit=args.madrid_limit
        )

    # Save graph
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    graph.serialize(destination=args.output, format="turtle")

    print(f"\nKnowledge graph created with {len(graph)} triples")
    print(f"Saved to {args.output}")

if __name__ == "__main__":
    main()
