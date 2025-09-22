#!/usr/bin/env python3
"""
Script to convert DeliData dataset to RDF format
compatible with the deliberation ontology.
"""

import os
import csv
import json
import sys
import argparse
import re
import subprocess
import glob
from datetime import datetime
import uuid

def clean_text(text):
    """Clean text by removing special characters and normalizing whitespace"""
    if not text:
        return ""
    # Replace multiple spaces with a single space
    clean_text = re.sub(r'\s+', ' ', text)
    return clean_text.strip()

def convert_delidata_to_json(input_dir, output_file, max_files=None):
    """Convert DeliData files to JSON format aligned with the deliberation ontology"""
    # Find all files in the input directory
    files = glob.glob(os.path.join(input_dir, '*'))
    
    if max_files:
        files = files[:max_files]
    
    if not files:
        print(f"No files found in {input_dir}")
        return False
    
    # Create a deliberation process for each conversation (file)
    all_processes = []
    
    for file_path in files:
        file_name = os.path.basename(file_path)
        group_id = file_name  # Use file name as group ID
        
        # Create a new deliberation process
        process = {
            "@context": {
                "del": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@type": "del:DeliberationProcess",
            "del:identifier": f"delidata_process_{group_id}",
            "del:name": f"DeliData Conversation {group_id}",
            "del:startDate": None,
            "del:endDate": None,
            "del:hasTopic": [],
            "del:hasParticipant": [],
            "del:hasContribution": []
        }
        
        # Read the file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            continue
        
        # Create a topic for the conversation
        topic_id = f"delidata_topic_{group_id}"
        topic = {
            "del:identifier": topic_id,
            "del:name": f"Conversation {group_id}"
        }
        process["del:hasTopic"].append(topic)
        
        # Track unique participants
        participants = {}
        
        # Process each message
        for row in rows:
            # Skip system messages
            if row.get('origin') == 'SYSTEM':
                continue
            
            # Get participant
            participant_name = row.get('origin', '')
            if not participant_name or participant_name == 'SYSTEM':
                continue
                
            # Add participant if not already added
            if participant_name not in participants:
                participant_id = f"participant_{len(participants) + 1}"
                participants[participant_name] = participant_id
                
                participant = {
                    "@type": "del:Participant",
                    "del:identifier": participant_id,
                    "del:name": participant_name
                }
                process["del:hasParticipant"].append(participant)
            
            # Add message as contribution
            message_id = row.get('message_id', '')
            if not message_id:
                continue
                
            contribution_id = f"delidata_message_{message_id}"
            
            # Get message text
            message_text = row.get('clean_text', '') or row.get('original_text', '')
            message_text = clean_text(message_text)
            
            if not message_text:
                continue
            
            # Create contribution
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": message_text,
                "del:madeBy": {"@id": participants[participant_name]},
                "del:hasTopic": {"@id": topic_id}
            }
            
            # Add annotation if available
            annotation_type = row.get('annotation_type', '')
            if annotation_type and annotation_type != 'None':
                # Create an argument structure
                argument_id = f"delidata_argument_{message_id}"
                argument = {
                    "@type": "del:Argument",
                    "del:identifier": argument_id,
                    "del:text": message_text
                }
                
                # Link argument to contribution
                contribution["del:hasArgument"] = {"@id": argument_id}
                
                # Add argument to process
                process["del:hasArgument"] = process.get("del:hasArgument", []) + [argument]
            
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
            process_id = process["del:identifier"].replace("delidata_process_", "")
            process_file = os.path.join(output_dir, f"{base_name}_{i+1}.json")
            with open(process_file, 'w', encoding='utf-8') as f:
                json.dump(process, f, indent=2, ensure_ascii=False)
            
            print(f"Saved process {i+1} to {process_file}")
    
    print(f"Successfully converted DeliData to JSON format")
    return True

def convert_to_rdf(input_dir, output_dir, max_files=None):
    """Convert DeliData to RDF format"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Step 1: Convert to JSON
    json_dir = os.path.join(output_dir, "json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    
    json_output = os.path.join(json_dir, "delidata.json")
    
    # Convert to JSON
    success = convert_delidata_to_json(input_dir, json_output, max_files)
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
    parser = argparse.ArgumentParser(description='Convert DeliData to RDF format')
    parser.add_argument('input_dir', help='Directory containing DeliData files')
    parser.add_argument('output_dir', help='Directory to save the output RDF files')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist")
        sys.exit(1)
    
    success = convert_to_rdf(args.input_dir, args.output_dir, args.max_files)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
