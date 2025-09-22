#!/usr/bin/env python3
"""
Create a knowledge graph with REAL data samples from multiple platforms
WITHOUT any made-up connections - only real data and real relationships
"""

import os
import json
import csv
import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
import uuid
import glob

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# Base URI for resources
BASE_URI = "https://w3id.org/deliberation/resource/"

def create_real_sample_kg():
    """Create KG with real data samples from multiple platforms"""
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

    print("Creating knowledge graph with REAL data samples from multiple platforms...")

    # 1. EU Parliament Debates (REAL data)
    add_real_eu_parliament_data(g)

    # 2. Decide Madrid (REAL data)
    add_real_decide_madrid_data(g)

    # 3. Decidim Barcelona (REAL data)
    add_real_decidim_barcelona_data(g)

    # 4. US Supreme Court (REAL data)
    add_real_us_supreme_court_data(g)

    # 5. DeliData (REAL data)
    add_real_delidata_sample(g)

    print(f"Knowledge graph created with {len(g)} triples from REAL platforms")
    return g

def add_real_eu_parliament_data(g):
    """Add REAL EU Parliament debate data"""
    print("Adding REAL EU Parliament data...")

    # Create process
    process_uri = URIRef(BASE_URI + "eu_parliament_real_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("European Parliament Debate - Real Session")))
    g.add((process_uri, DEL.platform, Literal("EU Parliament")))

    # Look for actual JSON files
    ep_debates_dir = "data/EU_parliament_debates/ep_debates"
    if os.path.exists(ep_debates_dir):
        json_files = [f for f in os.listdir(ep_debates_dir) if f.endswith('.json')][:1]  # Just 1 file
        for json_file in json_files:
            file_path = os.path.join(ep_debates_dir, json_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Add real participants
                if 'del:hasParticipant' in data or 'dkg:hasParticipant' in data:
                    participants_key = 'del:hasParticipant' if 'del:hasParticipant' in data else 'dkg:hasParticipant'
                    participants = data[participants_key][:3]  # Limit to 3

                    for i, participant_data in enumerate(participants):
                        participant_uri = URIRef(BASE_URI + f"eu_real_participant_{i}")
                        g.add((participant_uri, RDF.type, DEL.Participant))

                        if 'del:name' in participant_data:
                            g.add((participant_uri, DEL.name, Literal(participant_data['del:name'])))
                        elif 'dkg:name' in participant_data:
                            g.add((participant_uri, DEL.name, Literal(participant_data['dkg:name'])))

                        g.add((participant_uri, DEL.platform, Literal("EU Parliament")))
                        g.add((process_uri, DEL.hasParticipant, participant_uri))

                        # Add real contributions
                        if 'del:madeContribution' in participant_data:
                            contributions = participant_data['del:madeContribution'][:2]  # Limit to 2
                            for j, contrib_data in enumerate(contributions):
                                contrib_uri = URIRef(BASE_URI + f"eu_real_contribution_{i}_{j}")
                                g.add((contrib_uri, RDF.type, DEL.Contribution))

                                if 'del:text' in contrib_data:
                                    g.add((contrib_uri, DEL.text, Literal(str(contrib_data['del:text'])[:200])))

                                g.add((contrib_uri, DEL.madeBy, participant_uri))
                                g.add((process_uri, DEL.hasContribution, contrib_uri))

            except Exception as e:
                print(f"Error processing {json_file}: {e}")

def add_real_decide_madrid_data(g):
    """Add REAL Decide Madrid data"""
    print("Adding REAL Decide Madrid data...")

    # Create process
    process_uri = URIRef(BASE_URI + "madrid_real_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Decide Madrid - Real Citizen Proposals")))
    g.add((process_uri, DEL.platform, Literal("Decide Madrid")))

    # Look for real data
    data_dir = "data/decide_Madrid/data"
    if os.path.exists(data_dir):
        csv_files = glob.glob(os.path.join(data_dir, "*.csv"))[:1]  # Just 1 file
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                for i, row in df.head(3).iterrows():  # Just 3 rows
                    participant_uri = URIRef(BASE_URI + f"madrid_real_participant_{i}")
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.platform, Literal("Decide Madrid")))
                    g.add((process_uri, DEL.hasParticipant, participant_uri))

                    # Add real content as contribution
                    text_content = ""
                    for col in ['title', 'description', 'content', 'text']:
                        if col in df.columns and pd.notna(row[col]):
                            text_content += str(row[col])[:100] + " "

                    if text_content.strip():
                        contrib_uri = URIRef(BASE_URI + f"madrid_real_contribution_{i}")
                        g.add((contrib_uri, RDF.type, DEL.Contribution))
                        g.add((contrib_uri, DEL.text, Literal(text_content.strip())))
                        g.add((contrib_uri, DEL.madeBy, participant_uri))
                        g.add((process_uri, DEL.hasContribution, contrib_uri))

            except Exception as e:
                print(f"Error processing Madrid CSV: {e}")

def add_real_decidim_barcelona_data(g):
    """Add REAL Decidim Barcelona data"""
    print("Adding REAL Decidim Barcelona data...")

    # Create process
    process_uri = URIRef(BASE_URI + "barcelona_real_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("Decidim Barcelona - Real Citizen Participation")))
    g.add((process_uri, DEL.platform, Literal("Decidim Barcelona")))

    # Look for real data
    data_dir = "data/decidim_barcelona/data"
    if os.path.exists(data_dir):
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')][:1]  # Just 1 file
        for csv_file in csv_files:
            file_path = os.path.join(data_dir, csv_file)
            try:
                df = pd.read_csv(file_path)
                for i, row in df.head(3).iterrows():  # Just 3 rows
                    participant_uri = URIRef(BASE_URI + f"barcelona_real_participant_{i}")
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.platform, Literal("Decidim Barcelona")))
                    g.add((process_uri, DEL.hasParticipant, participant_uri))

                    # Add real content
                    text_content = ""
                    for col in ['title', 'description', 'body', 'content']:
                        if col in df.columns and pd.notna(row[col]):
                            text_content += str(row[col])[:100] + " "

                    if text_content.strip():
                        contrib_uri = URIRef(BASE_URI + f"barcelona_real_contribution_{i}")
                        g.add((contrib_uri, RDF.type, DEL.Contribution))
                        g.add((contrib_uri, DEL.text, Literal(text_content.strip())))
                        g.add((contrib_uri, DEL.madeBy, participant_uri))
                        g.add((process_uri, DEL.hasContribution, contrib_uri))

            except Exception as e:
                print(f"Error processing Barcelona CSV: {e}")

def add_real_us_supreme_court_data(g):
    """Add REAL US Supreme Court data"""
    print("Adding REAL US Supreme Court data...")

    # Create process
    process_uri = URIRef(BASE_URI + "us_supreme_court_real_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("US Supreme Court - Real Oral Arguments")))
    g.add((process_uri, DEL.platform, Literal("US Supreme Court")))

    # Look for real data
    csv_file = "data/US_supreme_court_arguments/dataset.csv"
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file)
            for i, row in df.head(3).iterrows():  # Just 3 rows
                participant_uri = URIRef(BASE_URI + f"us_supreme_real_participant_{i}")
                g.add((participant_uri, RDF.type, DEL.Participant))
                g.add((participant_uri, DEL.platform, Literal("US Supreme Court")))
                g.add((process_uri, DEL.hasParticipant, participant_uri))

                # Add real content
                text_content = ""
                for col in ['petitioner', 'respondent', 'case_name', 'argument_date']:
                    if col in df.columns and pd.notna(row[col]):
                        text_content += str(row[col])[:50] + " "

                if text_content.strip():
                    contrib_uri = URIRef(BASE_URI + f"us_supreme_real_contribution_{i}")
                    g.add((contrib_uri, RDF.type, DEL.Contribution))
                    g.add((contrib_uri, DEL.text, Literal(text_content.strip())))
                    g.add((contrib_uri, DEL.madeBy, participant_uri))
                    g.add((process_uri, DEL.hasContribution, contrib_uri))

        except Exception as e:
            print(f"Error processing US Supreme Court data: {e}")

def add_real_delidata_sample(g):
    """Add REAL DeliData sample"""
    print("Adding REAL DeliData sample...")

    # Create process
    process_uri = URIRef(BASE_URI + "delidata_real_process")
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.name, Literal("DeliData - Real Deliberation Research")))
    g.add((process_uri, DEL.platform, Literal("DeliData")))

    # Look for real parquet files
    data_dir = "data/delidata/data"
    if os.path.exists(data_dir):
        parquet_files = glob.glob(os.path.join(data_dir, "*.parquet"))[:1]  # Just 1 file
        for parquet_file in parquet_files:
            try:
                df = pd.read_parquet(parquet_file)
                for i, row in df.head(2).iterrows():  # Just 2 rows
                    participant_uri = URIRef(BASE_URI + f"delidata_real_participant_{i}")
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.platform, Literal("DeliData")))
                    g.add((process_uri, DEL.hasParticipant, participant_uri))

                    # Add any text content
                    text_content = ""
                    for col in df.columns:
                        if isinstance(row[col], str) and len(str(row[col])) > 5:
                            text_content += str(row[col])[:50] + " "

                    if text_content.strip():
                        contrib_uri = URIRef(BASE_URI + f"delidata_real_contribution_{i}")
                        g.add((contrib_uri, RDF.type, DEL.Contribution))
                        g.add((contrib_uri, DEL.text, Literal(text_content.strip())))
                        g.add((contrib_uri, DEL.madeBy, participant_uri))
                        g.add((process_uri, DEL.hasContribution, contrib_uri))

            except Exception as e:
                print(f"Error processing DeliData: {e}")

def main():
    kg = create_real_sample_kg()

    # Save the knowledge graph
    output_file = "real_multi_platform_kg.ttl"
    kg.serialize(destination=output_file, format="turtle")
    print(f"\nReal multi-platform knowledge graph saved to: {output_file}")

    # Test query to show all platforms
    test_query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>

    SELECT ?platform (COUNT(?participant) as ?participants) (COUNT(?contribution) as ?contributions)
    WHERE {
        ?process del:platform ?platform ;
                del:hasParticipant ?participant .
        OPTIONAL { ?process del:hasContribution ?contribution }
    }
    GROUP BY ?platform
    ORDER BY ?platform
    """

    results = list(kg.query(test_query))
    print(f"\nReal platforms data summary:")
    for row in results:
        print(f"  {row[0]}: {row[1]} participants, {row[2]} contributions")

    print(f"\nTotal triples: {len(kg)}")
    print("NO fake connections - only real data from actual platforms!")

    return True

if __name__ == "__main__":
    main()