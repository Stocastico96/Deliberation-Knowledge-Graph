#!/usr/bin/env python3
"""
Script to convert EU Have Your Say data to RDF format
compatible with the deliberation ontology.
"""

import os
import csv
import json
import sys
import argparse
import re
import subprocess
from datetime import datetime
import uuid

def clean_text(text):
    """Clean text by removing special characters and normalizing whitespace"""
    if not text:
        return ""
    # Replace multiple spaces with a single space
    clean_text = re.sub(r'\s+', ' ', text)
    return clean_text.strip()

def convert_csv_to_json(csv_file, output_file):
    """Convert EU Have Your Say CSV data to JSON format aligned with the deliberation ontology"""
    # Read CSV data
    feedbacks = []
    try:
        with open(csv_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            feedbacks = list(reader)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return False
    
    # Group feedbacks by publication
    publications = {}
    for feedback in feedbacks:
        pub_id = feedback.get('publication_id', '')
        pub_name = feedback.get('publication', '')
        
        if not pub_id or not pub_name:
            continue
        
        if pub_id not in publications:
            publications[pub_id] = {
                "id": pub_id,
                "name": pub_name,
                "reference": feedback.get('reference_initiative', ''),
                "feedbacks": []
            }
        
        publications[pub_id]["feedbacks"].append(feedback)
    
    # Convert to deliberation ontology format
    all_processes = []
    
    for pub_id, publication in publications.items():
        # Create a deliberation process for each publication
        process = {
            "@context": {
                "del": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@type": "del:DeliberationProcess",
            "del:identifier": f"euhys_process_{pub_id}",
            "del:name": f"EU Have Your Say: {publication['name']}",
            "del:startDate": None,
            "del:endDate": None,
            "del:hasTopic": [],
            "del:hasParticipant": [],
            "del:hasContribution": []
        }
        
        # Add topic for the publication
        topic_id = f"euhys_topic_{pub_id}"
        topic = {
            "del:identifier": topic_id,
            "del:name": publication['name']
        }
        process["del:hasTopic"].append(topic)
        
        # Track unique participants
        participants = {}
        
        # Process each feedback
        for feedback in publication["feedbacks"]:
            # Create participant identifier
            participant_name = ""
            if feedback.get('first_name') and feedback.get('surname'):
                participant_name = f"{feedback['first_name']} {feedback['surname']}"
            elif feedback.get('organization'):
                participant_name = feedback['organization']
            else:
                participant_name = f"Anonymous_{feedback.get('id', uuid.uuid4())}"
            
            # Add participant if not already added
            if participant_name not in participants:
                participant_id = f"participant_{len(participants) + 1}"
                participants[participant_name] = participant_id
                
                participant = {
                    "@type": "del:Participant",
                    "del:identifier": participant_id,
                    "del:name": participant_name
                }
                
                # Add role if available
                if feedback.get('user_type'):
                    role = {
                        "@type": "del:Role",
                        "del:name": feedback['user_type']
                    }
                    participant["del:hasRole"] = role
                
                # Add organization if available
                if feedback.get('organization'):
                    org_id = f"organization_{len(participants) + 1}"
                    org = {
                        "@type": "del:Organization",
                        "del:identifier": org_id,
                        "del:name": feedback['organization']
                    }
                    # Organizations are linked via participants, not directly to process
                    # Store organization for later reference
                    participant["del:isAffiliatedWith"] = {"@id": org_id}
                
                process["del:hasParticipant"].append(participant)
            
            # Add feedback as contribution
            contribution_id = f"euhys_feedback_{feedback.get('id', uuid.uuid4())}"
            
            # Get feedback text
            feedback_text = feedback.get('feedback', '')
            feedback_text = clean_text(feedback_text)
            
            if not feedback_text:
                continue
            
            # Create contribution
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": feedback_text,
                "del:madeBy": {"@id": participants[participant_name]},
                "del:hasTopic": {"@id": topic_id}
            }
            
            # Add timestamp if available
            if feedback.get('timestamp'):
                contribution["del:timestamp"] = feedback['timestamp']
            elif feedback.get('date_feedback'):
                contribution["del:timestamp"] = feedback['date_feedback']
            
            # Add contribution to process
            process["del:hasContribution"].append(contribution)
        
        all_processes.append(process)
    
    # Write output
    if len(all_processes) == 1:
        # Single process, write directly
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_processes[0], f, indent=2, ensure_ascii=False)
    else:
        # Multiple processes, write to separate files
        output_dir = os.path.dirname(output_file)
        base_name = os.path.splitext(os.path.basename(output_file))[0]
        
        for i, process in enumerate(all_processes):
            process_id = process["del:identifier"].replace("euhys_process_", "")
            process_file = os.path.join(output_dir, f"{base_name}_{process_id}.json")
            with open(process_file, 'w', encoding='utf-8') as f:
                json.dump(process, f, indent=2, ensure_ascii=False)
            
            print(f"Saved process {process_id} to {process_file}")
    
    print(f"Successfully converted EU Have Your Say data to JSON format")
    return True

def convert_to_rdf(csv_file, output_dir):
    """Convert EU Have Your Say data to RDF format"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Step 1: Convert CSV to JSON
    json_dir = os.path.join(output_dir, "json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    
    json_output = os.path.join(json_dir, "eu_have_your_say.json")
    
    # Convert CSV to JSON
    success = convert_csv_to_json(csv_file, json_output)
    if not success:
        return False
    
    # Step 2: Convert JSON to RDF
    # Get the path to the convert_json_to_rdf.py script from EU Parliament debates
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    json_to_rdf_script = os.path.join(parent_dir, "EU_parliament_debates", "convert_json_to_rdf.py")
    
    # Check if the script exists
    if not os.path.exists(json_to_rdf_script):
        print(f"Error: JSON to RDF conversion script not found at {json_to_rdf_script}")
        return False
    
    # Find all JSON files in the json_dir
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    if not json_files:
        print("Error: No JSON files found to convert to RDF")
        return False
    
    # Convert each JSON file to RDF
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        rdf_file = os.path.splitext(json_file)[0] + ".rdf"
        rdf_path = os.path.join(output_dir, rdf_file)
        
        print(f"Converting {json_file} to RDF format...")
        try:
            subprocess.run([sys.executable, json_to_rdf_script, json_path, rdf_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error converting JSON to RDF: {e}")
            continue
    
    print(f"Conversion complete. RDF files saved to {output_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Convert EU Have Your Say data to RDF format')
    parser.add_argument('input_file', help='Path to the CSV file')
    parser.add_argument('output_dir', help='Directory to save the output RDF files')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    success = convert_to_rdf(args.input_file, args.output_dir)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
