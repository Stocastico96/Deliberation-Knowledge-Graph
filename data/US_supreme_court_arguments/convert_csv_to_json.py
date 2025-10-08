#!/usr/bin/env python3
"""
Script to convert US Supreme Court Arguments from CSV format to JSON format
aligned with the deliberation ontology.
"""

import os
import csv
import json
import sys
import argparse
import re
from datetime import datetime
import uuid

def extract_case_number(text):
    """Extract case number from text"""
    match = re.search(r'Case (\d+-\d+)', text)
    if match:
        return match.group(1)
    return None

def extract_case_name(text):
    """Extract case name from text"""
    match = re.search(r'Case \d+-\d+, ([^.]+)', text)
    if match:
        return match.group(1).strip()
    return None

def convert_csv_to_json(csv_file, output_file):
    """Convert CSV data to JSON format aligned with the deliberation ontology"""
    # Read CSV data
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Group by case
    cases = {}
    for row in rows:
        case_id = row['case']
        if case_id not in cases:
            cases[case_id] = []
        cases[case_id].append(row)
    
    # Process each case
    all_cases = []
    for case_id, case_rows in cases.items():
        # Extract case metadata
        case_name = None
        argument_date = None
        
        # Look for case introduction in the first few rows
        for row in case_rows[:5]:
            if "We'll hear argument" in row['text'] and "Case" in row['text']:
                case_name = extract_case_name(row['text'])
                # Use case_id as fallback if extraction fails
                if not case_name:
                    case_name = f"Case {case_id}"
                break
        
        # Create unique participants dictionary to avoid duplicates
        participants = {}
        
        # Process all rows to identify participants
        for row in case_rows:
            speaker = row['speaker'].strip()
            
            # Skip empty speakers
            if not speaker:
                continue
            
            # Normalize speaker name and determine role
            if "CHIEF JUSTICE" in speaker:
                # Extract the name from the text if possible
                chief_justice_name = speaker.replace("CHIEF JUSTICE", "").strip()
                if not chief_justice_name:
                    # If no name is provided, use a generic identifier
                    normalized_name = "Chief Justice"
                else:
                    normalized_name = f"Chief Justice {chief_justice_name}"
                role = "Chief Justice"
            elif "JUSTICE" in speaker:
                # Extract justice name
                justice_name = speaker.replace("JUSTICE", "").strip()
                normalized_name = f"Justice {justice_name}"
                role = "Justice"
            elif "MR." in speaker:
                # Male advocate
                normalized_name = speaker
                role = "Advocate"
            elif "MS." in speaker:
                # Female advocate
                normalized_name = speaker
                role = "Advocate"
            else:
                # Other participant
                normalized_name = speaker
                role = "Other"
            
            # Add to participants dictionary if not already present
            if normalized_name not in participants:
                participants[normalized_name] = {
                    "id": f"participant_{len(participants) + 1}",
                    "name": normalized_name,
                    "role": role
                }
        
        # Create contributions
        contributions = []
        for i, row in enumerate(case_rows):
            speaker = row['speaker'].strip()
            if not speaker:
                continue
                
            # Normalize speaker name to match participants dictionary
            if "CHIEF JUSTICE" in speaker:
                chief_justice_name = speaker.replace("CHIEF JUSTICE", "").strip()
                if not chief_justice_name:
                    normalized_name = "Chief Justice"
                else:
                    normalized_name = f"Chief Justice {chief_justice_name}"
            elif "JUSTICE" in speaker:
                justice_name = speaker.replace("JUSTICE", "").strip()
                normalized_name = f"Justice {justice_name}"
            else:
                normalized_name = speaker
            
            # Create contribution
            contribution_id = f"contribution_{i + 1}"
            contribution = {
                "del:identifier": contribution_id,
                "del:text": row['text'].strip(),
                "del:madeBy": {"@id": participants[normalized_name]["id"]}
            }
            
            contributions.append(contribution)
        
        # Create topic
        topic_id = f"topic_{case_id}"
        topic = {
            "del:identifier": topic_id,
            "del:name": case_name or f"Case {case_id}"
        }
        
        # Create deliberation process
        process_id = f"scotus_case_{case_id}"
        process = {
            "@context": {
                "del": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@type": "del:DeliberationProcess",
            "del:identifier": process_id,
            "del:name": f"US Supreme Court Argument - {case_name or case_id}",
            "del:startDate": None,  # No date information in CSV
            "del:endDate": None,    # No date information in CSV
            "del:hasTopic": [topic],
            "del:hasParticipant": [],
            "del:hasContribution": contributions
        }
        
        # Add participants to process
        for participant_data in participants.values():
            participant = {
                "@type": "del:Participant",
                "del:identifier": participant_data["id"],
                "del:name": participant_data["name"],
                "del:hasRole": {
                    "@type": "del:Role",
                    "del:name": participant_data["role"]
                }
            }
            process["del:hasParticipant"].append(participant)
        
        all_cases.append(process)
    
    # Write output
    if len(all_cases) == 1:
        # Single case, write directly
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_cases[0], f, indent=2, ensure_ascii=False)
    else:
        # Multiple cases, write to separate files
        output_dir = os.path.dirname(output_file)
        base_name = os.path.splitext(os.path.basename(output_file))[0]
        
        for i, case in enumerate(all_cases):
            case_id = case["del:identifier"].replace("scotus_case_", "")
            case_file = os.path.join(output_dir, f"{base_name}_{case_id}.json")
            with open(case_file, 'w', encoding='utf-8') as f:
                json.dump(case, f, indent=2, ensure_ascii=False)
            
            print(f"Saved case {case_id} to {case_file}")
    
    print(f"Successfully converted {csv_file} to JSON format")
    return all_cases

def main():
    parser = argparse.ArgumentParser(description='Convert US Supreme Court Arguments from CSV to JSON format')
    parser.add_argument('input_file', help='Path to the CSV file')
    parser.add_argument('output_file', help='Path to the output JSON file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        convert_csv_to_json(args.input_file, args.output_file)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
