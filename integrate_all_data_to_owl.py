#!/usr/bin/env python3
"""
Script completo per integrare tutti i dati dei dataset nel formato OWL
nell'ontologia DEL e creare un knowledge graph unificato.
"""

import os
import json
import csv
import sys
import argparse
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
import uuid
from datetime import datetime
import pandas as pd
import re
import glob
from collections import defaultdict

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# Base URI for resources
BASE_URI = "https://w3id.org/deliberation/resource/"

def create_unified_graph():
    """Crea un grafo RDF unificato con tutti i namespace"""
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
    return g

def load_ontology(graph, ontology_path):
    """Carica l'ontologia DEL nel grafo"""
    if os.path.exists(ontology_path):
        if os.path.isdir(ontology_path):
            # Se è una directory, cerca il file ontology.owl dentro
            actual_path = os.path.join(ontology_path, "documentation", "ontology.owl")
            if not os.path.exists(actual_path):
                actual_path = os.path.join(ontology_path, "ontology.owl")
            if not os.path.exists(actual_path):
                print(f"Attenzione: File ontologia non trovato in {ontology_path}")
                return
            ontology_path = actual_path

        print(f"Caricamento ontologia da {ontology_path}")
        try:
            # Prova diversi formati
            if ontology_path.endswith('.owl'):
                graph.parse(ontology_path, format="xml")
            elif ontology_path.endswith('.ttl'):
                graph.parse(ontology_path, format="turtle")
            elif ontology_path.endswith('.jsonld'):
                graph.parse(ontology_path, format="json-ld")
            else:
                # Prova a rilevare automaticamente
                graph.parse(ontology_path)
            print(f"Ontologia caricata: {len(graph)} triple")
        except Exception as e:
            print(f"Errore nel caricare l'ontologia: {e}")
    else:
        print(f"Attenzione: File ontologia {ontology_path} non trovato")

def process_ep_debates(graph, file_path):
    """Processa i dati dei dibattiti del Parlamento Europeo"""
    print(f"Processando dibattiti Parlamento Europeo da {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Aggiungi processo deliberativo
        process_uri = URIRef(BASE_URI + data.get("del:identifier", data.get("dkg:identifier", f"ep_debate_{uuid.uuid4()}")))
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        
        # Aggiungi proprietà di base
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}identifier" in data:
                graph.add((process_uri, DEL.identifier, Literal(data[f"{prefix}identifier"])))
            if f"{prefix}name" in data:
                graph.add((process_uri, DEL.name, Literal(data[f"{prefix}name"])))
            if f"{prefix}startDate" in data:
                graph.add((process_uri, DEL.startDate, Literal(data[f"{prefix}startDate"], datatype=XSD.dateTime)))
            if f"{prefix}endDate" in data:
                graph.add((process_uri, DEL.endDate, Literal(data[f"{prefix}endDate"], datatype=XSD.dateTime)))
        
        # Processa topic
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}hasTopic" in data:
                for topic in data[f"{prefix}hasTopic"]:
                    topic_id = topic.get(f"{prefix}identifier", f"topic_{uuid.uuid4()}")
                    topic_uri = URIRef(BASE_URI + topic_id)
                    graph.add((topic_uri, RDF.type, DEL.Topic))
                    graph.add((topic_uri, DEL.identifier, Literal(topic_id)))
                    graph.add((topic_uri, DEL.name, Literal(topic.get(f"{prefix}name", ""))))
                    graph.add((process_uri, DEL.hasTopic, topic_uri))
        
        # Processa partecipanti
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}hasParticipant" in data:
                for participant in data[f"{prefix}hasParticipant"]:
                    participant_id = participant.get(f"{prefix}identifier", f"participant_{uuid.uuid4()}")
                    participant_uri = URIRef(BASE_URI + participant_id)
                    graph.add((participant_uri, RDF.type, DEL.Participant))
                    graph.add((participant_uri, DEL.identifier, Literal(participant_id)))
                    graph.add((participant_uri, DEL.name, Literal(participant.get(f"{prefix}name", ""))))
                    graph.add((participant_uri, DEL.platform, Literal("EU Parliament")))
                    
                    # Aggiungi ruolo se disponibile
                    if f"{prefix}hasRole" in participant:
                        role = participant[f"{prefix}hasRole"]
                        role_uri = URIRef(BASE_URI + f"role_{participant_id}")
                        graph.add((role_uri, RDF.type, DEL.Role))
                        graph.add((role_uri, DEL.name, Literal(role.get(f"{prefix}name", ""))))
                        graph.add((participant_uri, DEL.hasRole, role_uri))
                    
                    # Aggiungi affiliazione se disponibile
                    if f"{prefix}isAffiliatedWith" in participant:
                        org = participant[f"{prefix}isAffiliatedWith"]
                        org_name = org.get(f"{prefix}name", "")
                        org_uri = URIRef(BASE_URI + f"org_{org_name.replace(' ', '_').replace('/', '_')}")
                        graph.add((org_uri, RDF.type, DEL.Organization))
                        graph.add((org_uri, DEL.name, Literal(org_name)))
                        graph.add((participant_uri, DEL.isAffiliatedWith, org_uri))
                    
                    graph.add((process_uri, DEL.hasParticipant, participant_uri))
        
        # Processa contributi
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}hasContribution" in data:
                for contribution in data[f"{prefix}hasContribution"]:
                    contribution_id = contribution.get(f"{prefix}identifier", f"contribution_{uuid.uuid4()}")
                    contribution_uri = URIRef(BASE_URI + contribution_id)
                    graph.add((contribution_uri, RDF.type, DEL.Contribution))
                    graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
                    graph.add((contribution_uri, DEL.text, Literal(contribution.get(f"{prefix}text", ""))))
                    
                    # Aggiungi timestamp se disponibile
                    if f"{prefix}timestamp" in contribution:
                        graph.add((contribution_uri, DEL.timestamp, 
                                  Literal(contribution[f"{prefix}timestamp"], datatype=XSD.dateTime)))
                    
                    # Collega al partecipante
                    if f"{prefix}madeBy" in contribution and "@id" in contribution[f"{prefix}madeBy"]:
                        participant_id = contribution[f"{prefix}madeBy"]["@id"]
                        participant_uri = URIRef(BASE_URI + participant_id)
                        graph.add((contribution_uri, DEL.madeBy, participant_uri))
                    
                    # Collega contributo al processo
                    graph.add((process_uri, DEL.hasContribution, contribution_uri))
        
        print(f"Dibattiti Parlamento Europeo processati con successo")
        return True
    
    except Exception as e:
        print(f"Errore nel processare dibattiti Parlamento Europeo: {str(e)}")
        return False

def process_decide_madrid(graph, file_path):
    """Processa i dati di Decide Madrid"""
    print(f"Processando dati Decide Madrid da {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Crea processo deliberativo per la piattaforma
        process_uri = URIRef(BASE_URI + "decide_madrid_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("decide_madrid_process")))
        graph.add((process_uri, DEL.name, Literal("Decide Madrid Participatory Democracy Platform")))
        
        # Processa proposte
        if "proposals" in data:
            for proposal in data["proposals"]:
                proposal_id = str(proposal.get("id", uuid.uuid4()))
                topic_uri = URIRef(BASE_URI + f"madrid_topic_{proposal_id}")
                graph.add((topic_uri, RDF.type, DEL.Topic))
                graph.add((topic_uri, DEL.identifier, Literal(f"madrid_topic_{proposal_id}")))
                graph.add((topic_uri, DEL.name, Literal(proposal.get("title", ""))))
                graph.add((process_uri, DEL.hasTopic, topic_uri))
                
                # Crea contributo per il contenuto della proposta
                contribution_uri = URIRef(BASE_URI + f"madrid_proposal_{proposal_id}")
                graph.add((contribution_uri, RDF.type, DEL.Contribution))
                graph.add((contribution_uri, DEL.identifier, Literal(f"madrid_proposal_{proposal_id}")))
                graph.add((contribution_uri, DEL.text, Literal(proposal.get("summary", ""))))
                graph.add((contribution_uri, DEL.hasTopic, topic_uri))
                graph.add((process_uri, DEL.hasContribution, contribution_uri))
        
        print(f"Dati Decide Madrid processati con successo")
        return True
    
    except Exception as e:
        print(f"Errore nel processare dati Decide Madrid: {str(e)}")
        return False

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', str(text))
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def create_participant_uri(name, platform=""):
    """Create normalized participant URI for cross-platform linking"""
    if not name:
        return URIRef(BASE_URI + f"participant_{uuid.uuid4()}")

    # Normalize name for URI creation
    normalized_name = re.sub(r'[^a-zA-Z0-9\s]', '', str(name))
    normalized_name = re.sub(r'\s+', '_', normalized_name.strip()).lower()

    if platform:
        return URIRef(BASE_URI + f"participant_{platform}_{normalized_name}")
    else:
        return URIRef(BASE_URI + f"participant_{normalized_name}")

def process_decidim_barcelona(graph, data_dir):
    """Process Decidim Barcelona dataset"""
    print(f"Processing Decidim Barcelona data from {data_dir}")

    try:
        # Find CSV files
        csv_files = glob.glob(os.path.join(data_dir, "data", "*.csv"))
        if not csv_files:
            print("No CSV files found in Decidim Barcelona data directory")
            return False

        # Create main process
        process_uri = URIRef(BASE_URI + "decidim_barcelona_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("decidim_barcelona_process")))
        graph.add((process_uri, DEL.name, Literal("Decidim Barcelona Participatory Democracy Platform")))
        graph.add((process_uri, DEL.platform, Literal("Decidim Barcelona")))

        participants = {}
        topics = {}

        for csv_file in csv_files:
            file_name = os.path.basename(csv_file)
            print(f"  Processing {file_name}")

            try:
                df = pd.read_csv(csv_file, encoding='utf-8')

                if 'proposals' in file_name:
                    process_proposals(graph, df, process_uri, participants, topics, "decidim_barcelona")
                elif 'comments' in file_name:
                    process_comments(graph, df, process_uri, participants, topics, "decidim_barcelona")
                elif 'results' in file_name:
                    process_results(graph, df, process_uri, participants, topics, "decidim_barcelona")

            except Exception as e:
                print(f"    Error processing {file_name}: {e}")
                continue

        print(f"Decidim Barcelona processed successfully")
        return True

    except Exception as e:
        print(f"Error processing Decidim Barcelona: {e}")
        return False

def process_proposals(graph, df, process_uri, participants, topics, platform):
    """Process proposals data"""
    for _, row in df.iterrows():
        # Create topic
        topic_id = f"{platform}_topic_{row.get('id', uuid.uuid4())}"
        topic_uri = URIRef(BASE_URI + topic_id)
        graph.add((topic_uri, RDF.type, DEL.Topic))
        graph.add((topic_uri, DEL.identifier, Literal(topic_id)))
        graph.add((topic_uri, DEL.name, Literal(clean_text(row.get('title', '')))))
        graph.add((process_uri, DEL.hasTopic, topic_uri))

        # Create contribution
        contribution_id = f"{platform}_proposal_{row.get('id', uuid.uuid4())}"
        contribution_uri = URIRef(BASE_URI + contribution_id)
        graph.add((contribution_uri, RDF.type, DEL.Contribution))
        graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
        graph.add((contribution_uri, DEL.text, Literal(clean_text(row.get('body', '')))))
        graph.add((contribution_uri, DEL.hasTopic, topic_uri))
        graph.add((process_uri, DEL.hasContribution, contribution_uri))

        # Add participant if available
        author = row.get('author_nickname', '') or row.get('author_name', '')
        if author:
            participant_uri = create_participant_uri(author, platform)
            if participant_uri not in participants:
                graph.add((participant_uri, RDF.type, DEL.Participant))
                graph.add((participant_uri, DEL.name, Literal(str(author))))
                graph.add((participant_uri, DEL.platform, Literal(platform)))
                participants[participant_uri] = True
                graph.add((process_uri, DEL.hasParticipant, participant_uri))

            graph.add((contribution_uri, DEL.madeBy, participant_uri))

def process_comments(graph, df, process_uri, participants, topics, platform):
    """Process comments data"""
    for _, row in df.iterrows():
        # Create contribution for comment
        contribution_id = f"{platform}_comment_{row.get('id', uuid.uuid4())}"
        contribution_uri = URIRef(BASE_URI + contribution_id)
        graph.add((contribution_uri, RDF.type, DEL.Contribution))
        graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
        graph.add((contribution_uri, DEL.text, Literal(clean_text(row.get('body', '')))))
        graph.add((process_uri, DEL.hasContribution, contribution_uri))

        # Link to parent if available
        parent_id = row.get('commentable_id', '')
        if parent_id:
            parent_uri = URIRef(BASE_URI + f"{platform}_proposal_{parent_id}")
            graph.add((contribution_uri, DEL.respondsTo, parent_uri))

        # Add participant
        author = row.get('author_nickname', '') or row.get('author_name', '')
        if author:
            participant_uri = create_participant_uri(author, platform)
            if participant_uri not in participants:
                graph.add((participant_uri, RDF.type, DEL.Participant))
                graph.add((participant_uri, DEL.name, Literal(str(author))))
                graph.add((participant_uri, DEL.platform, Literal(platform)))
                participants[participant_uri] = True
                graph.add((process_uri, DEL.hasParticipant, participant_uri))

            graph.add((contribution_uri, DEL.madeBy, participant_uri))

def process_results(graph, df, process_uri, participants, topics, platform):
    """Process results data"""
    for _, row in df.iterrows():
        # Create topic for result
        topic_id = f"{platform}_result_topic_{row.get('id', uuid.uuid4())}"
        topic_uri = URIRef(BASE_URI + topic_id)
        graph.add((topic_uri, RDF.type, DEL.Topic))
        graph.add((topic_uri, DEL.identifier, Literal(topic_id)))
        graph.add((topic_uri, DEL.name, Literal(clean_text(row.get('title', '')))))
        graph.add((process_uri, DEL.hasTopic, topic_uri))

def process_delidata(graph, data_dir):
    """Process DeliData dataset"""
    print(f"Processing DeliData from {data_dir}")

    try:
        # Look for data files
        data_files = glob.glob(os.path.join(data_dir, "data", "*"))
        if not data_files:
            # Try sample file
            sample_file = os.path.join(data_dir, "sample", "sample.json")
            if os.path.exists(sample_file):
                data_files = [sample_file]

        if not data_files:
            print("No DeliData files found")
            return False

        # Create main process
        process_uri = URIRef(BASE_URI + "delidata_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("delidata_process")))
        graph.add((process_uri, DEL.name, Literal("DeliData Conversations")))
        graph.add((process_uri, DEL.platform, Literal("DeliData")))

        for data_file in data_files[:5]:  # Limit to first 5 files
            try:
                if data_file.endswith('.json'):
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    process_delidata_json(graph, data, process_uri)
                else:
                    # Try as TSV/CSV
                    df = pd.read_csv(data_file, delimiter='\t', encoding='utf-8', errors='replace')
                    process_delidata_csv(graph, df, process_uri, os.path.basename(data_file))
            except Exception as e:
                print(f"    Error processing {data_file}: {e}")
                continue

        print("DeliData processed successfully")
        return True

    except Exception as e:
        print(f"Error processing DeliData: {e}")
        return False

def process_delidata_json(graph, data, process_uri):
    """Process DeliData JSON format"""
    if "del:hasContribution" in data:
        for contribution in data["del:hasContribution"]:
            contribution_id = contribution.get("del:identifier", f"delidata_contrib_{uuid.uuid4()}")
            contribution_uri = URIRef(BASE_URI + contribution_id)
            graph.add((contribution_uri, RDF.type, DEL.Contribution))
            graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
            graph.add((contribution_uri, DEL.text, Literal(contribution.get("del:text", ""))))
            graph.add((process_uri, DEL.hasContribution, contribution_uri))

def process_delidata_csv(graph, df, process_uri, file_name):
    """Process DeliData CSV format"""
    participants = {}

    for _, row in df.iterrows():
        # Skip system messages
        if row.get('origin') == 'SYSTEM':
            continue

        # Create contribution
        message_id = row.get('message_id', '') or f"msg_{uuid.uuid4()}"
        contribution_id = f"delidata_{file_name}_{message_id}"
        contribution_uri = URIRef(BASE_URI + contribution_id)
        graph.add((contribution_uri, RDF.type, DEL.Contribution))
        graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))

        text = row.get('clean_text', '') or row.get('original_text', '')
        graph.add((contribution_uri, DEL.text, Literal(clean_text(text))))
        graph.add((process_uri, DEL.hasContribution, contribution_uri))

        # Add participant
        participant_name = row.get('origin', '')
        if participant_name and participant_name != 'SYSTEM':
            participant_uri = create_participant_uri(participant_name, "delidata")
            if participant_uri not in participants:
                graph.add((participant_uri, RDF.type, DEL.Participant))
                graph.add((participant_uri, DEL.name, Literal(str(participant_name))))
                graph.add((participant_uri, DEL.platform, Literal("DeliData")))
                participants[participant_uri] = True
                graph.add((process_uri, DEL.hasParticipant, participant_uri))

            graph.add((contribution_uri, DEL.madeBy, participant_uri))

def process_us_supreme_court(graph, data_dir):
    """Process US Supreme Court arguments dataset"""
    print(f"Processing US Supreme Court data from {data_dir}")

    try:
        csv_file = os.path.join(data_dir, "dataset.csv")
        if not os.path.exists(csv_file):
            print("US Supreme Court dataset.csv not found")
            return False

        df = pd.read_csv(csv_file)

        # Create main process
        process_uri = URIRef(BASE_URI + "us_supreme_court_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("us_supreme_court_process")))
        graph.add((process_uri, DEL.name, Literal("US Supreme Court Oral Arguments")))
        graph.add((process_uri, DEL.platform, Literal("US Supreme Court")))

        participants = {}

        for _, row in df.iterrows():
            # Create contribution for each argument statement
            contribution_id = f"us_supreme_{row.get('id', uuid.uuid4())}"
            contribution_uri = URIRef(BASE_URI + contribution_id)
            graph.add((contribution_uri, RDF.type, DEL.Contribution))
            graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
            graph.add((contribution_uri, DEL.text, Literal(clean_text(row.get('text', '')))))
            graph.add((process_uri, DEL.hasContribution, contribution_uri))

            # Add participant (speaker)
            speaker = row.get('speaker', '')
            if speaker:
                participant_uri = create_participant_uri(speaker, "us_supreme_court")
                if participant_uri not in participants:
                    graph.add((participant_uri, RDF.type, DEL.Participant))
                    graph.add((participant_uri, DEL.name, Literal(str(speaker))))
                    graph.add((participant_uri, DEL.platform, Literal("US Supreme Court")))

                    # Add role if available
                    role = row.get('speaker_role', '')
                    if role:
                        role_uri = URIRef(BASE_URI + f"role_us_supreme_{role}")
                        graph.add((role_uri, RDF.type, DEL.Role))
                        graph.add((role_uri, DEL.name, Literal(role)))
                        graph.add((participant_uri, DEL.hasRole, role_uri))

                    participants[participant_uri] = True
                    graph.add((process_uri, DEL.hasParticipant, participant_uri))

                graph.add((contribution_uri, DEL.madeBy, participant_uri))

        print("US Supreme Court processed successfully")
        return True

    except Exception as e:
        print(f"Error processing US Supreme Court: {e}")
        return False

def process_eu_have_your_say(graph, data_dir):
    """Process EU Have Your Say data"""
    print(f"Processing EU Have Your Say data from {data_dir}")

    # Create main process
    process_uri = URIRef(BASE_URI + f"eu_have_your_say_process_{uuid.uuid4()}")
    graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
    graph.add((process_uri, DEL.name, Literal("EU Have Your Say - Citizen Consultation Platform")))
    graph.add((process_uri, DEL.platform, Literal("EU Have Your Say")))

    # Look for data files
    sample_dir = os.path.join(data_dir, "sample")
    if os.path.exists(sample_dir):
        for file_path in glob.glob(os.path.join(sample_dir, "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Process consultations
                if isinstance(data, list):
                    for item in data:
                        add_eu_consultation_data(graph, item, process_uri)
                else:
                    add_eu_consultation_data(graph, data, process_uri)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    print("EU Have Your Say data processed successfully")

def add_eu_consultation_data(graph, data, process_uri):
    """Add EU consultation data to graph"""
    if 'title' in data:
        contrib_uri = URIRef(BASE_URI + f"eu_consultation_{uuid.uuid4()}")
        graph.add((contrib_uri, RDF.type, DEL.Contribution))
        graph.add((contrib_uri, DEL.text, Literal(str(data['title']))))
        graph.add((process_uri, DEL.hasContribution, contrib_uri))

def process_habermas_machine(graph, data_dir):
    """Process Habermas Machine data"""
    print(f"Processing Habermas Machine data from {data_dir}")

    # Create main process
    process_uri = URIRef(BASE_URI + f"habermas_machine_process_{uuid.uuid4()}")
    graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
    graph.add((process_uri, DEL.name, Literal("Habermas Machine - AI-Assisted Deliberation")))
    graph.add((process_uri, DEL.platform, Literal("Habermas Machine")))

    # Look for data files
    data_data_dir = os.path.join(data_dir, "data")
    if os.path.exists(data_data_dir):
        # Process parquet files
        for file_path in glob.glob(os.path.join(data_data_dir, "*.parquet")):
            try:
                df = pd.read_parquet(file_path)
                add_habermas_data(graph, df, process_uri, os.path.basename(file_path))
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    print("Habermas Machine data processed successfully")

def add_habermas_data(graph, df, process_uri, file_name):
    """Add Habermas Machine data to graph"""
    for idx, row in df.head(10).iterrows():  # Limit to first 10 rows
        participant_id = f"habermas_participant_{uuid.uuid4()}"
        participant_uri = URIRef(BASE_URI + participant_id)

        graph.add((participant_uri, RDF.type, DEL.Participant))
        graph.add((participant_uri, DEL.platform, Literal("Habermas Machine")))
        graph.add((process_uri, DEL.hasParticipant, participant_uri))

        # Add any text content as contributions
        for col in df.columns:
            if isinstance(row[col], str) and len(str(row[col])) > 10:
                contrib_uri = URIRef(BASE_URI + f"habermas_contrib_{uuid.uuid4()}")
                graph.add((contrib_uri, RDF.type, DEL.Contribution))
                graph.add((contrib_uri, DEL.text, Literal(str(row[col])[:500])))  # Limit text length
                graph.add((contrib_uri, DEL.madeBy, participant_uri))
                graph.add((process_uri, DEL.hasContribution, contrib_uri))

def process_dataset_incrementally(graph, dataset_info, max_files_per_type=3):
    """Process a single dataset with limits for performance"""
    name = dataset_info["name"]
    function = dataset_info["function"]
    paths = dataset_info["paths"]

    print(f"\nProcessing {name}...")

    if name in ["Decidim Barcelona", "DeliData", "US Supreme Court"]:
        # These functions take directory paths
        for path in paths:
            if os.path.exists(path):
                try:
                    if function(graph, path):
                        return True
                except Exception as e:
                    print(f"Error processing {name}: {e}")
                    return False
            else:
                print(f"Warning: Directory {path} does not exist. Skipping.")
    else:
        # File-based datasets - limit number of files for performance
        processed_files = 0
        for path in paths:
            if os.path.exists(path) and processed_files < max_files_per_type:
                try:
                    if function(graph, path):
                        processed_files += 1
                        print(f"  Processed file: {os.path.basename(path)}")
                except Exception as e:
                    print(f"  Error processing {path}: {e}")
                    continue

        if processed_files > 0:
            print(f"  Successfully processed {processed_files} files for {name}")
            return True
        else:
            print(f"Warning: No valid files found for {name}. Skipping.")

    return False

def discover_available_datasets(data_dir):
    """Dynamically discover available datasets"""
    datasets = []
    print(f"Discovering datasets in: {data_dir}")

    # EU Parliament Debates
    ep_debates_dir = os.path.join(data_dir, "EU_parliament_debates/ep_debates")
    print(f"Checking EU Parliament: {ep_debates_dir} - exists: {os.path.exists(ep_debates_dir)}")
    if os.path.exists(ep_debates_dir):
        json_files = [f for f in os.listdir(ep_debates_dir) if f.endswith('.json')][:3]  # Limit to 3 files
        print(f"Found {len(json_files)} JSON files")
        if json_files:
            datasets.append({
                "name": "European Parliament Debates",
                "function": process_ep_debates,
                "paths": [os.path.join(ep_debates_dir, f) for f in json_files]
            })

    # Decide Madrid
    madrid_sample = os.path.join(data_dir, "decide_Madrid/sample/sample.json")
    print(f"Checking Decide Madrid: {madrid_sample} - exists: {os.path.exists(madrid_sample)}")
    if os.path.exists(madrid_sample):
        datasets.append({
            "name": "Decide Madrid",
            "function": process_decide_madrid,
            "paths": [madrid_sample]
        })

    # Decidim Barcelona
    barcelona_dir = os.path.join(data_dir, "decidim_barcelona")
    print(f"Checking Decidim Barcelona: {barcelona_dir} - exists: {os.path.exists(barcelona_dir)}")
    if os.path.exists(barcelona_dir):
        datasets.append({
            "name": "Decidim Barcelona",
            "function": process_decidim_barcelona,
            "paths": [barcelona_dir]
        })

    # DeliData
    delidata_dir = os.path.join(data_dir, "delidata")
    print(f"Checking DeliData: {delidata_dir} - exists: {os.path.exists(delidata_dir)}")
    if os.path.exists(delidata_dir):
        datasets.append({
            "name": "DeliData",
            "function": process_delidata,
            "paths": [delidata_dir]
        })

    # US Supreme Court
    supreme_court_dir = os.path.join(data_dir, "US_supreme_court_arguments")
    print(f"Checking US Supreme Court: {supreme_court_dir} - exists: {os.path.exists(supreme_court_dir)}")
    if os.path.exists(supreme_court_dir):
        datasets.append({
            "name": "US Supreme Court",
            "function": process_us_supreme_court,
            "paths": [supreme_court_dir]
        })

    # EU Have Your Say
    eu_have_your_say_dir = os.path.join(data_dir, "EU_have_your_say")
    print(f"Checking EU Have Your Say: {eu_have_your_say_dir} - exists: {os.path.exists(eu_have_your_say_dir)}")
    if os.path.exists(eu_have_your_say_dir):
        datasets.append({
            "name": "EU Have Your Say",
            "function": process_eu_have_your_say,
            "paths": [eu_have_your_say_dir]
        })

    # Habermas Machine
    habermas_dir = os.path.join(data_dir, "habermas_machine")
    print(f"Checking Habermas Machine: {habermas_dir} - exists: {os.path.exists(habermas_dir)}")
    if os.path.exists(habermas_dir):
        datasets.append({
            "name": "Habermas Machine",
            "function": process_habermas_machine,
            "paths": [habermas_dir]
        })

    print(f"Total datasets discovered: {len(datasets)}")
    for dataset in datasets:
        print(f"  - {dataset['name']}")

    return datasets

def process_all_datasets(graph, data_dir, max_datasets=None):
    """Process all available datasets with performance optimizations"""
    datasets = discover_available_datasets(data_dir)

    if max_datasets:
        datasets = datasets[:max_datasets]

    print(f"Found {len(datasets)} available datasets")

    processed_count = 0
    for dataset in datasets:
        try:
            if process_dataset_incrementally(graph, dataset):
                processed_count += 1
        except Exception as e:
            print(f"Critical error processing {dataset['name']}: {e}")
            continue

        # Memory management - print current graph size
        print(f"  Current graph size: {len(graph)} triples")

    # Add cross-platform connections only if we have data
    if processed_count > 0:
        print(f"\nProcessed {processed_count} datasets successfully")
        add_cross_platform_connections(graph)
    else:
        print("No datasets processed successfully")

    return processed_count

def normalize_name(name):
    """Normalize participant names for better matching"""
    if not name:
        return ""
    # Convert to lowercase and remove common titles and punctuation
    normalized = str(name).lower()
    # Remove common titles
    titles = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'hon.', 'sir', 'madam']
    for title in titles:
        normalized = normalized.replace(title, '').strip()
    # Remove extra spaces and punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def calculate_name_similarity(name1, name2):
    """Calculate similarity between two names using multiple methods"""
    if not name1 or not name2:
        return 0.0

    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Exact match
    if norm1 == norm2:
        return 1.0

    # Check if one is contained in the other (for partial matches)
    if norm1 in norm2 or norm2 in norm1:
        return 0.8

    # Check common words (for names with different order)
    words1 = set(norm1.split())
    words2 = set(norm2.split())

    if len(words1) > 1 and len(words2) > 1:
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        if len(union) > 0:
            jaccard = len(intersection) / len(union)
            if jaccard > 0.5:  # More than half words in common
                return jaccard

    return 0.0

def extract_topics_from_text(text, max_length=100):
    """Extract meaningful topics from text content"""
    if not text:
        return []

    # Simple keyword extraction
    words = re.findall(r'\b[A-Za-z]{4,}\b', str(text))
    # Remove common stop words
    stop_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'their', 'said', 'each', 'which', 'what', 'where', 'when', 'would', 'there', 'could', 'should'}
    keywords = [word.lower() for word in words if word.lower() not in stop_words]

    # Return most frequent keywords
    from collections import Counter
    counter = Counter(keywords)
    return [word for word, count in counter.most_common(5) if count > 1]

def add_cross_platform_connections(graph):
    """Add semantic connections across platforms and datasets"""
    print("\nAdding cross-platform semantic connections...")

    # Enhanced participant matching
    participants_query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>

    SELECT ?participant ?name ?platform
    WHERE {
        ?participant a del:Participant ;
                     del:name ?name .
        OPTIONAL { ?participant del:platform ?platform }
    }
    """

    try:
        results = graph.query(participants_query)
        participants = list(results)
        sameAs_count = 0

        # Optimize: only compare across different platforms
        platform_participants = {}
        for p, name, platform in participants:
            if platform:
                platform_str = str(platform)
                if platform_str not in platform_participants:
                    platform_participants[platform_str] = []
                platform_participants[platform_str].append((p, name))

        # Compare only across different platforms (much faster)
        platform_list = list(platform_participants.keys())

        # Limit comparisons for performance
        max_participants_per_platform = 20
        for platform in platform_participants:
            if len(platform_participants[platform]) > max_participants_per_platform:
                platform_participants[platform] = platform_participants[platform][:max_participants_per_platform]

        for i, platform1 in enumerate(platform_list):
            for platform2 in platform_list[i+1:]:
                for p1, name1 in platform_participants[platform1]:
                    for p2, name2 in platform_participants[platform2]:
                        similarity = calculate_name_similarity(str(name1), str(name2))
                        if similarity >= 0.8:  # High confidence match
                            graph.add((p1, OWL.sameAs, p2))
                            sameAs_count += 1
                            print(f"    Linked: {name1} ({platform1}) ↔ {name2} ({platform2}) (similarity: {similarity:.2f})")
                        elif similarity >= 0.6:  # Medium confidence - add related
                            graph.add((p1, SKOS.related, p2))

        print(f"  Added {sameAs_count} high-confidence participant connections")

    except Exception as e:
        print(f"  Warning: Could not add participant connections: {e}")

    # Add enhanced topic similarity connections
    add_enhanced_topic_connections(graph)

    # Add temporal connections
    add_temporal_connections(graph)

def calculate_topic_similarity(topic1, topic2):
    """Calculate semantic similarity between two topics"""
    if not topic1 or not topic2:
        return 0.0

    # Normalize and tokenize
    topic1_clean = re.sub(r'[^\w\s]', '', str(topic1).lower())
    topic2_clean = re.sub(r'[^\w\s]', '', str(topic2).lower())

    words1 = set(topic1_clean.split())
    words2 = set(topic2_clean.split())

    if not words1 or not words2:
        return 0.0

    # Remove common stop words
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
    words1 = {w for w in words1 if w not in stop_words and len(w) > 2}
    words2 = {w for w in words2 if w not in stop_words and len(w) > 2}

    if not words1 or not words2:
        return 0.0

    # Calculate Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)

    if len(union) == 0:
        return 0.0

    return len(intersection) / len(union)

def add_enhanced_topic_connections(graph):
    """Add enhanced connections between similar topics across platforms"""
    try:
        # Query for all topics
        topics_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT ?topic ?name
        WHERE {
            ?topic a del:Topic ;
                   del:name ?name .
            FILTER(STRLEN(?name) > 5)
        }
        """

        results = graph.query(topics_query)
        topics = list(results)
        related_count = 0
        broader_count = 0

        print(f"  Analyzing {len(topics)} topics for semantic connections...")

        # Compare all topics
        for i, (topic1, name1) in enumerate(topics):
            for j, (topic2, name2) in enumerate(topics[i+1:], i+1):
                similarity = calculate_topic_similarity(str(name1), str(name2))

                if similarity >= 0.7:  # High similarity - broader/narrower relationship
                    # Determine which is broader (longer description usually more specific)
                    if len(str(name1)) > len(str(name2)):
                        graph.add((topic1, SKOS.broader, topic2))
                        graph.add((topic2, SKOS.narrower, topic1))
                    else:
                        graph.add((topic2, SKOS.broader, topic1))
                        graph.add((topic1, SKOS.narrower, topic2))
                    broader_count += 1
                elif similarity >= 0.4:  # Medium similarity - related
                    graph.add((topic1, SKOS.related, topic2))
                    graph.add((topic2, SKOS.related, topic1))
                    related_count += 1

        print(f"  Added {related_count} topic similarity connections")
        print(f"  Added {broader_count} hierarchical topic connections")

    except Exception as e:
        print(f"  Warning: Could not add topic connections: {e}")

def add_topic_connections(graph):
    """Legacy function - redirects to enhanced version"""
    add_enhanced_topic_connections(graph)

def add_temporal_connections(graph):
    """Add temporal sequence relationships between contributions"""
    try:
        # Query for contributions with timestamps in the same process
        temporal_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT ?process ?contrib1 ?timestamp1 ?contrib2 ?timestamp2
        WHERE {
            ?process del:hasContribution ?contrib1 .
            ?process del:hasContribution ?contrib2 .
            ?contrib1 del:timestamp ?timestamp1 .
            ?contrib2 del:timestamp ?timestamp2 .
            FILTER(?contrib1 != ?contrib2)
            FILTER(?timestamp1 < ?timestamp2)
        }
        ORDER BY ?process ?timestamp1
        """

        results = graph.query(temporal_query)
        temporal_count = 0

        # Group by process and add sequence relationships
        process_contributions = defaultdict(list)
        for row in results:
            process, contrib1, timestamp1, contrib2, timestamp2 = row
            process_contributions[process].append((contrib1, timestamp1))

        for process, contributions in process_contributions.items():
            # Sort by timestamp
            contributions.sort(key=lambda x: x[1])

            # Add follows relationships
            for i in range(len(contributions) - 1):
                current_contrib = contributions[i][0]
                next_contrib = contributions[i + 1][0]
                graph.add((next_contrib, DEL.follows, current_contrib))
                temporal_count += 1

        print(f"  Added {temporal_count} temporal sequence connections")

    except Exception as e:
        print(f"  Warning: Could not add temporal connections: {e}")

def save_knowledge_graph(graph, output_dir):
    """Salva il knowledge graph in diversi formati"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Salva in diversi formati
    formats = [
        ("turtle", "ttl"),
        ("xml", "rdf"),
        ("json-ld", "jsonld"),
        ("n3", "n3")
    ]
    
    for format_name, extension in formats:
        output_file = os.path.join(output_dir, f"deliberation_kg_complete.{extension}")
        try:
            graph.serialize(destination=output_file, format=format_name)
            print(f"Knowledge graph salvato in formato {format_name}: {output_file}")
        except Exception as e:
            print(f"Errore nel salvare formato {format_name}: {str(e)}")

def generate_sparql_queries():
    """Genera query SPARQL di esempio"""
    queries = {
        "all_processes": """
# Query 1: Lista tutti i processi deliberativi
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?process ?name ?startDate ?endDate
WHERE {
    ?process a del:DeliberationProcess ;
             del:name ?name .
    OPTIONAL { ?process del:startDate ?startDate }
    OPTIONAL { ?process del:endDate ?endDate }
}
ORDER BY ?startDate
""",
        
        "contributions_by_participant": """
# Query 2: Trova tutti i contributi di un partecipante specifico
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?contribution ?text ?timestamp
WHERE {
    ?contribution a del:Contribution ;
                 del:text ?text ;
                 del:madeBy ?participant .
    ?participant del:name "Iratxe García Pérez" .
    OPTIONAL { ?contribution del:timestamp ?timestamp }
}
ORDER BY ?timestamp
""",
        
        "topics_by_process": """
# Query 3: Trova tutti i topic discussi per processo
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?process ?processName ?topic ?topicName
WHERE {
    ?process a del:DeliberationProcess ;
             del:name ?processName ;
             del:hasTopic ?topic .
    ?topic del:name ?topicName .
}
ORDER BY ?processName ?topicName
""",
        
        "participants_by_organization": """
# Query 4: Partecipanti raggruppati per organizzazione
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?org ?orgName ?participant ?participantName
WHERE {
    ?participant a del:Participant ;
                del:name ?participantName ;
                del:isAffiliatedWith ?org .
    ?org del:name ?orgName .
}
ORDER BY ?orgName ?participantName
""",
        
        "argument_analysis": """
# Query 5: Analisi degli argomenti
PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?argument ?premise ?conclusion ?fallacy
WHERE {
    ?argument a del:Argument .
    OPTIONAL { ?argument del:hasPremise ?premise }
    OPTIONAL { ?argument del:hasConclusion ?conclusion }
    OPTIONAL { ?argument del:containsFallacy ?fallacy }
}
"""
    }
    
    return queries

def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(description='Integra tutti i dati nel formato OWL nell\'ontologia DEL')
    parser.add_argument('--data-dir', default='data', help='Directory contenente i dataset')
    parser.add_argument('--ontology', default='OnToology/ontologies/deliberation.owl', help='Path all\'ontologia DEL')
    parser.add_argument('--output-dir', default='knowledge_graph', help='Directory di output per il knowledge graph')
    parser.add_argument('--include-ontology', action='store_true', help='Includi l\'ontologia nel knowledge graph')
    parser.add_argument('--max-datasets', type=int, help='Limite numero di dataset da processare (per test)')
    parser.add_argument('--quick-test', action='store_true', help='Esegui test rapido con dataset limitati')

    args = parser.parse_args()

    print("=== INTEGRAZIONE DATI NEL FORMATO OWL ===")
    print(f"Directory dati: {args.data_dir}")
    print(f"Ontologia: {args.ontology}")
    print(f"Directory output: {args.output_dir}")

    if args.quick_test:
        args.max_datasets = 2
        print("Modalità test rapido attivata")

    # Crea grafo unificato
    graph = create_unified_graph()

    # Carica ontologia se richiesto
    if args.include_ontology:
        load_ontology(graph, args.ontology)

    # Processa tutti i dataset
    try:
        processed_count = process_all_datasets(graph, args.data_dir, args.max_datasets)

        if processed_count == 0:
            print("Nessun dataset processato con successo. Controllare i path dei dati.")
            return

        # Salva knowledge graph
        save_knowledge_graph(graph, args.output_dir)

        # Genera query SPARQL di esempio
        queries = generate_sparql_queries()
        queries_file = os.path.join(args.output_dir, "example_queries.sparql")
        with open(queries_file, 'w', encoding='utf-8') as f:
            for name, query in queries.items():
                f.write(f"# {name.upper()}\n")
                f.write(query)
                f.write("\n" + "="*50 + "\n\n")

        # Generate summary statistics
        generate_statistics(graph, args.output_dir)

        print(f"\n=== RISULTATI ===")
        print(f"Dataset processati: {processed_count}")
        print(f"Triple totali nel knowledge graph: {len(graph)}")
        print(f"Knowledge graph salvato in: {args.output_dir}")
        print(f"Query SPARQL di esempio salvate in: {queries_file}")

        print(f"\n=== ISTRUZIONI PER SPARQL ENDPOINT ===")
        print("1. Scarica Apache Jena Fuseki da https://jena.apache.org/download/")
        print("2. Estrai l'archivio scaricato")
        print("3. Avvia il server Fuseki: ./fuseki-server --mem /deliberation")
        print("4. Carica il file knowledge graph attraverso l'interfaccia web su http://localhost:3030/")
        print("5. Interroga l'endpoint SPARQL su http://localhost:3030/deliberation/sparql")

    except KeyboardInterrupt:
        print("\nProcessamento interrotto dall'utente")
    except Exception as e:
        print(f"\nErrore durante il processamento: {e}")
        import traceback
        traceback.print_exc()

def generate_statistics(graph, output_dir):
    """Generate and save statistics about the knowledge graph"""
    try:
        stats = {}

        # Count different entity types
        entity_queries = {
            "processes": "SELECT (COUNT(?p) as ?count) WHERE { ?p a <https://w3id.org/deliberation/ontology#DeliberationProcess> }",
            "participants": "SELECT (COUNT(?p) as ?count) WHERE { ?p a <https://w3id.org/deliberation/ontology#Participant> }",
            "contributions": "SELECT (COUNT(?c) as ?count) WHERE { ?c a <https://w3id.org/deliberation/ontology#Contribution> }",
            "topics": "SELECT (COUNT(?t) as ?count) WHERE { ?t a <https://w3id.org/deliberation/ontology#Topic> }",
            "organizations": "SELECT (COUNT(?o) as ?count) WHERE { ?o a <https://w3id.org/deliberation/ontology#Organization> }"
        }

        for entity_type, query in entity_queries.items():
            try:
                result = list(graph.query(query))
                if result:
                    stats[entity_type] = int(result[0][0])
                else:
                    stats[entity_type] = 0
            except:
                stats[entity_type] = 0

        # Count cross-platform connections
        cross_platform_query = "SELECT (COUNT(?s) as ?count) WHERE { ?s <http://www.w3.org/2002/07/owl#sameAs> ?o }"
        try:
            result = list(graph.query(cross_platform_query))
            stats["cross_platform_links"] = int(result[0][0]) if result else 0
        except:
            stats["cross_platform_links"] = 0

        # Save statistics
        stats_file = os.path.join(output_dir, "statistics.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)

        print(f"\n=== STATISTICHE KNOWLEDGE GRAPH ===")
        for entity_type, count in stats.items():
            print(f"{entity_type.replace('_', ' ').title()}: {count}")

    except Exception as e:
        print(f"Errore nella generazione delle statistiche: {e}")

if __name__ == "__main__":
    main()