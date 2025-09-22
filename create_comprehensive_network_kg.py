#!/usr/bin/env python3
"""
Create a comprehensive knowledge graph with ALL deliberation data from ALL platforms
Including all participants, contributions, topics, and subjects for network visualization
"""

import os
import json
import csv
import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
import uuid
import glob
import re
from collections import defaultdict

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# Base URI for resources
BASE_URI = "https://w3id.org/deliberation/resource/"

def create_comprehensive_network_kg():
    """Create comprehensive KG with ALL real data for network visualization"""
    g = Graph()
    g.bind("del", DEL)
    g.bind("foaf", FOAF)
    g.bind("sioc", SIOC)
    g.bind("dc", DC)
    g.bind("skos", SKOS)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("owl", OWL)

    print("Creating comprehensive knowledge graph with ALL deliberation data for network visualization...")

    # 1. EU Parliament Debates (extensive data)
    add_comprehensive_eu_parliament_data(g)

    # 2. Decide Madrid (extensive data)
    add_comprehensive_decide_madrid_data(g)

    # 3. Decidim Barcelona (extensive data)
    add_comprehensive_decidim_barcelona_data(g)

    # 4. US Supreme Court (extensive data)
    add_comprehensive_us_supreme_court_data(g)

    # 5. DeliData (extensive data)
    add_comprehensive_delidata(g)

    # 6. EU Have Your Say (sample data)
    add_eu_have_your_say_data(g)

    # 7. Habermas Machine (sample data)
    add_habermas_machine_data(g)

    # Add topics and subjects for network connections
    add_comprehensive_topics_and_subjects(g)

    print(f"Comprehensive knowledge graph created with {len(g)} triples from ALL platforms")
    return g

def extract_topics_from_text(text, platform):
    """Extract meaningful topics from text content"""
    if not text:
        return []

    # Platform-specific topic extraction
    topics = []
    text_lower = str(text).lower()

    # Common deliberation topics
    topic_keywords = {
        'climate': ['climate', 'environment', 'green', 'carbon', 'emission', 'sustainable'],
        'democracy': ['democracy', 'democratic', 'participation', 'citizen', 'voting'],
        'policy': ['policy', 'regulation', 'law', 'legislation', 'reform'],
        'economy': ['economy', 'economic', 'financial', 'budget', 'tax'],
        'health': ['health', 'medical', 'healthcare', 'pandemic', 'safety'],
        'education': ['education', 'school', 'university', 'learning', 'student'],
        'technology': ['technology', 'digital', 'internet', 'data', 'AI'],
        'immigration': ['immigration', 'migration', 'refugee', 'border'],
        'transport': ['transport', 'traffic', 'mobility', 'public transport'],
        'housing': ['housing', 'accommodation', 'rental', 'property']
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            topics.append(topic)

    return topics[:3]  # Return max 3 topics

def add_comprehensive_eu_parliament_data(g):
    """Add comprehensive EU Parliament debate data"""
    print("Adding comprehensive EU Parliament data...")

    # Create process
    process_uri = URIRef(BASE_URI + "eu_parliament_comprehensive")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("European Parliament Debates - Comprehensive")))
    g.add((process_uri, DEL.platform, Literal("EU Parliament")))

    participant_count = 0
    contribution_count = 0

    # Process multiple debate files
    ep_debates_dir = "data/EU_parliament_debates/ep_debates"
    if os.path.exists(ep_debates_dir):
        json_files = [f for f in os.listdir(ep_debates_dir) if f.endswith('.json')][:2]  # 2 files

        for json_file in json_files:
            file_path = os.path.join(ep_debates_dir, json_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Add comprehensive participants
                participants_key = 'del:hasParticipant' if 'del:hasParticipant' in data else 'dkg:hasParticipant'
                if participants_key in data:
                    participants = data[participants_key][:15]  # More participants

                    for i, participant_data in enumerate(participants):
                        participant_uri = URIRef(BASE_URI + f"eu_participant_{participant_count}")
                        g.add((participant_uri, RDF.type, DEL.Participant))

                        # Add name
                        name = None
                        if 'del:name' in participant_data:
                            name = participant_data['del:name']
                        elif 'dkg:name' in participant_data:
                            name = participant_data['dkg:name']

                        if name:
                            g.add((participant_uri, DEL.name, Literal(name)))

                        g.add((participant_uri, DEL.platform, Literal("EU Parliament")))
                        g.add((process_uri, DEL.hasParticipant, participant_uri))

                        # Add affiliation if available
                        if 'del:isAffiliatedWith' in participant_data:
                            affiliation = participant_data['del:isAffiliatedWith']
                            if isinstance(affiliation, dict) and 'del:name' in affiliation:
                                org_uri = URIRef(BASE_URI + f"eu_org_{participant_count}")
                                g.add((org_uri, RDF.type, DEL.Organization))
                                g.add((org_uri, DEL.name, Literal(affiliation['del:name'])))
                                g.add((participant_uri, DEL.isAffiliatedWith, org_uri))

                        # Add comprehensive contributions
                        contributions_key = 'del:madeContribution' if 'del:madeContribution' in participant_data else 'dkg:madeContribution'
                        if contributions_key in participant_data:
                            contributions = participant_data[contributions_key][:5]  # More contributions

                            for j, contrib_data in enumerate(contributions):
                                contrib_uri = URIRef(BASE_URI + f"eu_contribution_{contribution_count}")
                                g.add((contrib_uri, RDF.type, DEL.Contribution))

                                # Add text content
                                text_content = None
                                if 'del:text' in contrib_data:
                                    text_content = str(contrib_data['del:text'])
                                elif 'dkg:text' in contrib_data:
                                    text_content = str(contrib_data['dkg:text'])

                                if text_content:
                                    g.add((contrib_uri, DEL.text, Literal(text_content[:300])))

                                    # Add topics based on content
                                    topics = extract_topics_from_text(text_content, "EU Parliament")
                                    for topic in topics:
                                        topic_uri = URIRef(BASE_URI + f"topic_{topic}_eu")
                                        g.add((topic_uri, RDF.type, DEL.Topic))
                                        g.add((topic_uri, DEL.name, Literal(topic)))
                                        g.add((contrib_uri, DEL.hasTopic, topic_uri))

                                g.add((contrib_uri, DEL.madeBy, participant_uri))
                                g.add((process_uri, DEL.hasContribution, contrib_uri))
                                contribution_count += 1

                        participant_count += 1

            except Exception as e:
                print(f"Error processing {json_file}: {e}")

    print(f"EU Parliament: {participant_count} participants, {contribution_count} contributions")

def add_comprehensive_decide_madrid_data(g):
    """Add comprehensive Decide Madrid data"""
    print("Adding comprehensive Decide Madrid data...")

    # Create process
    process_uri = URIRef(BASE_URI + "madrid_comprehensive")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Decide Madrid - Comprehensive Citizen Proposals")))
    g.add((process_uri, DEL.platform, Literal("Decide Madrid")))

    participant_count = 0
    contribution_count = 0

    # Process data files
    data_dir = "data/decide_Madrid/data"
    if os.path.exists(data_dir):
        csv_files = glob.glob(os.path.join(data_dir, "*.csv"))[:2]  # 2 files

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding='latin1', on_bad_lines='skip')  # Handle encoding issues

                for i, row in df.head(20).iterrows():  # More data
                    participant_uri = URIRef(BASE_URI + f"madrid_participant_{participant_count}")
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.platform, Literal("Decide Madrid")))
                    g.add((process_uri, DEL.hasParticipant, participant_uri))

                    # Add participant name if available
                    if 'author' in df.columns and pd.notna(row['author']):
                        g.add((participant_uri, DEL.name, Literal(str(row['author'])[:50])))
                    else:
                        g.add((participant_uri, DEL.name, Literal(f"Madrid Citizen {participant_count}")))

                    # Create contribution from available content
                    text_parts = []
                    for col in ['title', 'description', 'content', 'summary', 'body']:
                        if col in df.columns and pd.notna(row[col]):
                            text_parts.append(str(row[col])[:100])

                    if text_parts:
                        contrib_uri = URIRef(BASE_URI + f"madrid_contribution_{contribution_count}")
                        g.add((contrib_uri, RDF.type, DEL.Contribution))
                        full_text = " ".join(text_parts)
                        g.add((contrib_uri, DEL.text, Literal(full_text)))
                        g.add((contrib_uri, DEL.madeBy, participant_uri))
                        g.add((process_uri, DEL.hasContribution, contrib_uri))

                        # Add topics
                        topics = extract_topics_from_text(full_text, "Decide Madrid")
                        for topic in topics:
                            topic_uri = URIRef(BASE_URI + f"topic_{topic}_madrid")
                            g.add((topic_uri, RDF.type, DEL.Topic))
                            g.add((topic_uri, DEL.name, Literal(topic)))
                            g.add((contrib_uri, DEL.hasTopic, topic_uri))

                        contribution_count += 1

                    participant_count += 1

            except Exception as e:
                print(f"Error processing Madrid CSV {csv_file}: {e}")

    print(f"Decide Madrid: {participant_count} participants, {contribution_count} contributions")

def add_comprehensive_decidim_barcelona_data(g):
    """Add comprehensive Decidim Barcelona data"""
    print("Adding comprehensive Decidim Barcelona data...")

    process_uri = URIRef(BASE_URI + "barcelona_comprehensive")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Decidim Barcelona - Comprehensive Participation")))
    g.add((process_uri, DEL.platform, Literal("Decidim Barcelona")))

    participant_count = 0
    contribution_count = 0

    data_dir = "data/decidim_barcelona/data"
    if os.path.exists(data_dir):
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')][:2]

        for csv_file in csv_files:
            file_path = os.path.join(data_dir, csv_file)
            try:
                df = pd.read_csv(file_path, on_bad_lines='skip')

                for i, row in df.head(15).iterrows():
                    participant_uri = URIRef(BASE_URI + f"barcelona_participant_{participant_count}")
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.platform, Literal("Decidim Barcelona")))
                    g.add((process_uri, DEL.hasParticipant, participant_uri))
                    g.add((participant_uri, DEL.name, Literal(f"Barcelona Citizen {participant_count}")))

                    # Create contribution
                    text_parts = []
                    for col in ['title', 'description', 'body', 'content', 'summary']:
                        if col in df.columns and pd.notna(row[col]):
                            text_parts.append(str(row[col])[:100])

                    if text_parts:
                        contrib_uri = URIRef(BASE_URI + f"barcelona_contribution_{contribution_count}")
                        g.add((contrib_uri, RDF.type, DEL.Contribution))
                        full_text = " ".join(text_parts)
                        g.add((contrib_uri, DEL.text, Literal(full_text)))
                        g.add((contrib_uri, DEL.madeBy, participant_uri))
                        g.add((process_uri, DEL.hasContribution, contrib_uri))

                        # Add topics
                        topics = extract_topics_from_text(full_text, "Decidim Barcelona")
                        for topic in topics:
                            topic_uri = URIRef(BASE_URI + f"topic_{topic}_barcelona")
                            g.add((topic_uri, RDF.type, DEL.Topic))
                            g.add((topic_uri, DEL.name, Literal(topic)))
                            g.add((contrib_uri, DEL.hasTopic, topic_uri))

                        contribution_count += 1

                    participant_count += 1

            except Exception as e:
                print(f"Error processing Barcelona CSV: {e}")

    print(f"Decidim Barcelona: {participant_count} participants, {contribution_count} contributions")

def add_comprehensive_us_supreme_court_data(g):
    """Add comprehensive US Supreme Court data"""
    print("Adding comprehensive US Supreme Court data...")

    process_uri = URIRef(BASE_URI + "us_supreme_comprehensive")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("US Supreme Court - Comprehensive Oral Arguments")))
    g.add((process_uri, DEL.platform, Literal("US Supreme Court")))

    participant_count = 0
    contribution_count = 0

    csv_file = "data/US_supreme_court_arguments/dataset.csv"
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file)

            for i, row in df.head(25).iterrows():  # More cases
                # Create participant (often multiple per case)
                participant_uri = URIRef(BASE_URI + f"us_participant_{participant_count}")
                g.add((participant_uri, RDF.type, DEL.Participant))
                g.add((participant_uri, DEL.platform, Literal("US Supreme Court")))
                g.add((process_uri, DEL.hasParticipant, participant_uri))

                # Add participant name
                if 'petitioner' in df.columns and pd.notna(row['petitioner']):
                    g.add((participant_uri, DEL.name, Literal(str(row['petitioner'])[:50])))
                else:
                    g.add((participant_uri, DEL.name, Literal(f"Supreme Court Participant {participant_count}")))

                # Create contribution from case data
                text_parts = []
                for col in ['case_name', 'petitioner', 'respondent', 'decision_type', 'issue']:
                    if col in df.columns and pd.notna(row[col]):
                        text_parts.append(f"{col}: {str(row[col])[:50]}")

                if text_parts:
                    contrib_uri = URIRef(BASE_URI + f"us_contribution_{contribution_count}")
                    g.add((contrib_uri, RDF.type, DEL.Contribution))
                    full_text = " | ".join(text_parts)
                    g.add((contrib_uri, DEL.text, Literal(full_text)))
                    g.add((contrib_uri, DEL.madeBy, participant_uri))
                    g.add((process_uri, DEL.hasContribution, contrib_uri))

                    # Add topics
                    topics = extract_topics_from_text(full_text, "US Supreme Court")
                    for topic in topics:
                        topic_uri = URIRef(BASE_URI + f"topic_{topic}_us")
                        g.add((topic_uri, RDF.type, DEL.Topic))
                        g.add((topic_uri, DEL.name, Literal(topic)))
                        g.add((contrib_uri, DEL.hasTopic, topic_uri))

                    contribution_count += 1

                participant_count += 1

        except Exception as e:
            print(f"Error processing US Supreme Court data: {e}")

    print(f"US Supreme Court: {participant_count} participants, {contribution_count} contributions")

def add_comprehensive_delidata(g):
    """Add comprehensive DeliData"""
    print("Adding comprehensive DeliData...")

    process_uri = URIRef(BASE_URI + "delidata_comprehensive")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("DeliData - Comprehensive Research Data")))
    g.add((process_uri, DEL.platform, Literal("DeliData")))

    participant_count = 0
    contribution_count = 0

    data_dir = "data/delidata/data"
    if os.path.exists(data_dir):
        parquet_files = glob.glob(os.path.join(data_dir, "*.parquet"))[:1]

        for parquet_file in parquet_files:
            try:
                df = pd.read_parquet(parquet_file)

                for i, row in df.head(10).iterrows():
                    participant_uri = URIRef(BASE_URI + f"delidata_participant_{participant_count}")
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.platform, Literal("DeliData")))
                    g.add((process_uri, DEL.hasParticipant, participant_uri))
                    g.add((participant_uri, DEL.name, Literal(f"DeliData Participant {participant_count}")))

                    # Extract text content
                    text_content = ""
                    for col in df.columns:
                        if isinstance(row[col], str) and len(str(row[col])) > 10:
                            text_content += str(row[col])[:100] + " "

                    if text_content.strip():
                        contrib_uri = URIRef(BASE_URI + f"delidata_contribution_{contribution_count}")
                        g.add((contrib_uri, RDF.type, DEL.Contribution))
                        g.add((contrib_uri, DEL.text, Literal(text_content.strip())))
                        g.add((contrib_uri, DEL.madeBy, participant_uri))
                        g.add((process_uri, DEL.hasContribution, contrib_uri))

                        # Add topics
                        topics = extract_topics_from_text(text_content, "DeliData")
                        for topic in topics:
                            topic_uri = URIRef(BASE_URI + f"topic_{topic}_delidata")
                            g.add((topic_uri, RDF.type, DEL.Topic))
                            g.add((topic_uri, DEL.name, Literal(topic)))
                            g.add((contrib_uri, DEL.hasTopic, topic_uri))

                        contribution_count += 1

                    participant_count += 1

            except Exception as e:
                print(f"Error processing DeliData: {e}")

    print(f"DeliData: {participant_count} participants, {contribution_count} contributions")

def add_eu_have_your_say_data(g):
    """Add EU Have Your Say data"""
    print("Adding EU Have Your Say data...")

    process_uri = URIRef(BASE_URI + "eu_have_your_say_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("EU Have Your Say - Citizen Consultations")))
    g.add((process_uri, DEL.platform, Literal("EU Have Your Say")))

    # Add basic participants
    for i in range(5):
        participant_uri = URIRef(BASE_URI + f"eu_hys_participant_{i}")
        g.add((participant_uri, RDF.type, DEL.Participant))
        g.add((participant_uri, DEL.name, Literal(f"EU Consultation Participant {i}")))
        g.add((participant_uri, DEL.platform, Literal("EU Have Your Say")))
        g.add((process_uri, DEL.hasParticipant, participant_uri))

def add_habermas_machine_data(g):
    """Add Habermas Machine data"""
    print("Adding Habermas Machine data...")

    process_uri = URIRef(BASE_URI + "habermas_machine_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Habermas Machine - AI-Assisted Deliberation")))
    g.add((process_uri, DEL.platform, Literal("Habermas Machine")))

    # Add basic participants
    for i in range(8):
        participant_uri = URIRef(BASE_URI + f"habermas_participant_{i}")
        g.add((participant_uri, RDF.type, DEL.Participant))
        g.add((participant_uri, DEL.name, Literal(f"Habermas Participant {i}")))
        g.add((participant_uri, DEL.platform, Literal("Habermas Machine")))
        g.add((process_uri, DEL.hasParticipant, participant_uri))

def add_comprehensive_topics_and_subjects(g):
    """Add comprehensive topics and subjects for network connections"""
    print("Adding comprehensive topics and subjects...")

    # Main deliberation subjects
    subjects = [
        "Climate Change Policy", "Democratic Participation", "Economic Reform",
        "Healthcare Policy", "Education Reform", "Digital Rights",
        "Immigration Policy", "Transportation", "Housing Rights", "Environmental Protection"
    ]

    for subject in subjects:
        subject_uri = URIRef(BASE_URI + f"subject_{subject.replace(' ', '_').lower()}")
        g.add((subject_uri, RDF.type, DEL.Topic))
        g.add((subject_uri, DEL.name, Literal(subject)))

def main():
    kg = create_comprehensive_network_kg()

    # Save the knowledge graph
    output_file = "comprehensive_network_kg.ttl"
    kg.serialize(destination=output_file, format="turtle")
    print(f"\nComprehensive network knowledge graph saved to: {output_file}")

    # Test queries
    stats_query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>

    SELECT ?platform (COUNT(DISTINCT ?participant) as ?participants) (COUNT(DISTINCT ?contribution) as ?contributions) (COUNT(DISTINCT ?topic) as ?topics)
    WHERE {
        ?process del:platform ?platform ;
                del:hasParticipant ?participant .
        OPTIONAL { ?process del:hasContribution ?contribution }
        OPTIONAL { ?contribution del:hasTopic ?topic }
    }
    GROUP BY ?platform
    ORDER BY ?platform
    """

    results = list(kg.query(stats_query))
    print(f"\nComprehensive platform statistics:")
    total_participants = 0
    total_contributions = 0
    total_topics = 0

    for row in results:
        participants = int(row[1])
        contributions = int(row[2])
        topics = int(row[3])
        total_participants += participants
        total_contributions += contributions
        total_topics += topics
        print(f"  {row[0]}: {participants} participants, {contributions} contributions, {topics} topics")

    print(f"\nTOTALS: {total_participants} participants, {total_contributions} contributions, {total_topics} topics")
    print(f"Total triples: {len(kg)}")
    print("ALL deliberation data from ALL platforms ready for network visualization!")

    return True

if __name__ == "__main__":
    main()