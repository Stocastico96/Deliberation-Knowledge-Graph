#!/usr/bin/env python3
"""
Script to convert Habermas Machine data to RDF format
compatible with the deliberation ontology.
"""

import os
import json
import sys
import argparse
import subprocess
import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime
import uuid

def convert_habermas_to_json(parquet_dir, output_file, max_sessions=None):
    """Convert Habermas Machine parquet files to JSON format aligned with the deliberation ontology"""
    # Check if the directory exists
    if not os.path.exists(parquet_dir):
        print(f"Error: Directory {parquet_dir} does not exist")
        return False
    
    # Check for required parquet files
    required_files = [
        "hm_all_candidate_comparisons.parquet",
        "hm_all_final_preference_rankings.parquet",
        "hm_all_position_statement_ratings.parquet",
        "hm_all_round_survey_responses.parquet"
    ]
    
    for file in required_files:
        if not os.path.exists(os.path.join(parquet_dir, file)):
            print(f"Warning: File {file} not found in {parquet_dir}")
    
    # Load data from parquet files
    data = {}
    try:
        for file in required_files:
            file_path = os.path.join(parquet_dir, file)
            if os.path.exists(file_path):
                # Extract the key name from the file name
                key = file.replace("hm_all_", "").replace(".parquet", "")
                data[key] = pq.read_table(file_path).to_pandas()
                print(f"Loaded {len(data[key])} rows from {file}")
    except Exception as e:
        print(f"Error loading parquet files: {e}")
        return False
    
    # Group data by session
    sessions = {}
    
    # Extract unique session IDs
    if 'candidate_comparisons' in data:
        session_ids = data['candidate_comparisons']['session_id'].unique()
        if max_sessions:
            session_ids = session_ids[:max_sessions]
        
        for session_id in session_ids:
            sessions[session_id] = {
                "session_id": session_id,
                "participants": set(),
                "topics": set(),
                "candidates": set(),
                "comparisons": [],
                "rankings": [],
                "statements": [],
                "surveys": []
            }
    
    # Process candidate comparisons
    if 'candidate_comparisons' in data:
        for _, row in data['candidate_comparisons'].iterrows():
            session_id = row['session_id']
            if session_id in sessions:
                sessions[session_id]['participants'].add(row['participant_id'])
                sessions[session_id]['candidates'].add(row['candidate_a'])
                sessions[session_id]['candidates'].add(row['candidate_b'])
                sessions[session_id]['comparisons'].append({
                    "comparison_id": row['comparison_id'],
                    "participant_id": row['participant_id'],
                    "round": row['round'],
                    "candidate_a": row['candidate_a'],
                    "candidate_b": row['candidate_b'],
                    "preference": row['preference'],
                    "strength": row['strength'],
                    "timestamp": row['timestamp'],
                    "reasoning": row['reasoning']
                })
    
    # Process final preference rankings
    if 'final_preference_rankings' in data:
        for _, row in data['final_preference_rankings'].iterrows():
            session_id = row['session_id']
            if session_id in sessions:
                sessions[session_id]['participants'].add(row['participant_id'])
                rankings = row['rankings']
                if isinstance(rankings, str):
                    try:
                        rankings = json.loads(rankings)
                    except:
                        rankings = []
                
                for ranking in rankings:
                    sessions[session_id]['candidates'].add(ranking['candidate'])
                
                sessions[session_id]['rankings'].append({
                    "participant_id": row['participant_id'],
                    "round": row['round'],
                    "rankings": rankings,
                    "timestamp": row['timestamp']
                })
    
    # Process position statement ratings
    if 'position_statement_ratings' in data:
        for _, row in data['position_statement_ratings'].iterrows():
            session_id = row['session_id']
            if session_id in sessions:
                sessions[session_id]['participants'].add(row['participant_id'])
                sessions[session_id]['candidates'].add(row['candidate'])
                sessions[session_id]['topics'].add(row['topic'])
                sessions[session_id]['statements'].append({
                    "statement_id": row['statement_id'],
                    "participant_id": row['participant_id'],
                    "round": row['round'],
                    "candidate": row['candidate'],
                    "topic": row['topic'],
                    "statement": row['statement'],
                    "agreement_rating": row['agreement_rating'],
                    "importance_rating": row['importance_rating'],
                    "timestamp": row['timestamp'],
                    "comment": row['comment']
                })
    
    # Process round survey responses
    if 'round_survey_responses' in data:
        for _, row in data['round_survey_responses'].iterrows():
            session_id = row['session_id']
            if session_id in sessions:
                sessions[session_id]['participants'].add(row['participant_id'])
                questions = row['questions']
                if isinstance(questions, str):
                    try:
                        questions = json.loads(questions)
                    except:
                        questions = []
                
                sessions[session_id]['surveys'].append({
                    "participant_id": row['participant_id'],
                    "round": row['round'],
                    "survey_id": row['survey_id'],
                    "questions": questions,
                    "timestamp": row['timestamp']
                })
    
    # Convert to deliberation ontology format
    all_processes = []
    
    for session_id, session in sessions.items():
        # Create a deliberation process for each session
        process = {
            "@context": {
                "del": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@type": "del:DeliberationProcess",
            "del:identifier": f"habermas_process_{session_id}",
            "del:name": f"Habermas Machine Deliberation {session_id}",
            "del:startDate": None,
            "del:endDate": None,
            "del:hasTopic": [],
            "del:hasParticipant": [],
            "del:hasContribution": []
        }
        
        # Add topics
        for topic in session['topics']:
            topic_id = f"habermas_topic_{topic.replace(' ', '_')}"
            topic_obj = {
                "del:identifier": topic_id,
                "del:name": topic
            }
            process["del:hasTopic"].append(topic_obj)
        
        # Add participants
        participants = {}
        for participant_id in session['participants']:
            participant_obj_id = f"participant_{participant_id}"
            participants[participant_id] = participant_obj_id
            
            participant_obj = {
                "@type": "del:Participant",
                "del:identifier": participant_obj_id,
                "del:name": f"Participant {participant_id}"
            }
            process["del:hasParticipant"].append(participant_obj)
        
        # Add candidate comparisons as contributions
        for i, comparison in enumerate(session['comparisons']):
            contribution_id = f"habermas_comparison_{comparison['comparison_id']}"
            
            # Create text from comparison
            text = f"Comparison between {comparison['candidate_a']} and {comparison['candidate_b']}. "
            text += f"Preference: {comparison['preference']}. Strength: {comparison['strength']}. "
            if comparison['reasoning']:
                text += f"Reasoning: {comparison['reasoning']}"
            
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": text,
                "del:madeBy": {"@id": participants[comparison['participant_id']]}
            }
            
            # Add timestamp if available
            if comparison['timestamp']:
                contribution["del:timestamp"] = comparison['timestamp']
            
            # Add contribution to process
            process["del:hasContribution"].append(contribution)
        
        # Add position statements as contributions with arguments
        for i, statement in enumerate(session['statements']):
            contribution_id = f"habermas_statement_{statement['statement_id']}"
            
            # Find topic object
            topic_id = None
            for topic_obj in process["del:hasTopic"]:
                if topic_obj["del:name"] == statement['topic']:
                    topic_id = topic_obj["del:identifier"]
                    break
            
            # Create text from statement
            text = f"{statement['candidate']}'s position on {statement['topic']}: {statement['statement']}. "
            text += f"Agreement: {statement['agreement_rating']}/5. Importance: {statement['importance_rating']}/5. "
            if statement['comment']:
                text += f"Comment: {statement['comment']}"
            
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": text,
                "del:madeBy": {"@id": participants[statement['participant_id']]}
            }
            
            # Add topic if found
            if topic_id:
                contribution["del:hasTopic"] = {"@id": topic_id}
            
            # Add timestamp if available
            if statement['timestamp']:
                contribution["del:timestamp"] = statement['timestamp']
            
            # Create argument
            argument_id = f"habermas_argument_{statement['statement_id']}"
            argument = {
                "@type": "del:Argument",
                "del:identifier": argument_id,
                "del:text": statement['statement']
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
            process_id = process["del:identifier"].replace("habermas_process_", "")
            process_file = os.path.join(output_dir, f"{base_name}_{i+1}.json")
            with open(process_file, 'w', encoding='utf-8') as f:
                json.dump(process, f, indent=2, ensure_ascii=False)
            
            print(f"Saved process {i+1} to {process_file}")
    
    print(f"Successfully converted Habermas Machine data to JSON format")
    return True

def convert_to_rdf(parquet_dir, output_dir, max_sessions=None):
    """Convert Habermas Machine data to RDF format"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Step 1: Convert to JSON
    json_dir = os.path.join(output_dir, "json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    
    json_output = os.path.join(json_dir, "habermas_machine.json")
    
    # Convert to JSON
    success = convert_habermas_to_json(parquet_dir, json_output, max_sessions)
    if not success:
        return False
    
    # Step 2: Convert JSON to RDF
    # Use the specific Habermas Machine JSON to RDF converter
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_to_rdf_script = os.path.join(script_dir, "convert_json_to_rdf_habermas.py")
    
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
    parser = argparse.ArgumentParser(description='Convert Habermas Machine data to RDF format')
    parser.add_argument('input_dir', help='Directory containing Habermas Machine parquet files')
    parser.add_argument('output_dir', help='Directory to save the output RDF files')
    parser.add_argument('--max-sessions', type=int, help='Maximum number of sessions to process')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist")
        sys.exit(1)
    
    success = convert_to_rdf(args.input_dir, args.output_dir, args.max_sessions)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
