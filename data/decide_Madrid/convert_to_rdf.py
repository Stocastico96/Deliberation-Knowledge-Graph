#!/usr/bin/env python3
"""
Script to convert Decide Madrid data to RDF format
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

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    # Simple regex to remove HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', text)
    # Replace multiple spaces with a single space
    clean_text = re.sub(r'\s+', ' ', clean_text)
    return clean_text.strip()

def convert_debates_to_json(debates_csv, comments_csv, output_file):
    """Convert Decide Madrid debates and comments to JSON format"""
    # Read debates CSV
    debates = {}
    try:
        with open(debates_csv, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                debate_id = row['id']
                debates[debate_id] = {
                    'id': debate_id,
                    'title': row['title'],
                    'description': clean_html(row['description']),
                    'created_at': row['created_at'],
                    'votes_total': row['cached_votes_total'],
                    'votes_up': row['cached_votes_up'],
                    'votes_down': row['cached_votes_down'],
                    'comments_count': row['comments_count'],
                    'author_name': row['author_name'],
                    'comments': []
                }
    except Exception as e:
        print(f"Error reading debates CSV: {e}")
        return False
    
    # Read comments CSV if provided
    if comments_csv and os.path.exists(comments_csv):
        try:
            with open(comments_csv, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    debate_id = row.get('debate_id')
                    if debate_id and debate_id in debates:
                        debates[debate_id]['comments'].append({
                            'id': row.get('id', ''),
                            'body': clean_html(row.get('body', '')),
                            'created_at': row.get('created_at', ''),
                            'author_name': row.get('author_name', '')
                        })
        except Exception as e:
            print(f"Error reading comments CSV: {e}")
            # Continue without comments if there's an error
    
    # Convert to deliberation ontology format
    process = {
        "@context": {
            "del": "https://w3id.org/deliberation/ontology#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@type": "del:DeliberationProcess",
        "del:identifier": "decide_madrid_process",
        "del:name": "Decide Madrid Participatory Democracy Platform",
        "del:startDate": None,
        "del:endDate": None,
        "del:hasTopic": [],
        "del:hasParticipant": [],
        "del:hasContribution": []
    }
    
    # Track unique participants
    participants = {}
    
    # Process each debate
    for debate_id, debate in debates.items():
        # Create topic for each debate
        topic_id = f"madrid_topic_{debate_id}"
        topic = {
            "del:identifier": topic_id,
            "del:name": debate['title']
        }
        process["del:hasTopic"].append(topic)
        
        # Add author as participant if not already added
        author_name = debate['author_name']
        if author_name not in participants:
            participant_id = f"participant_{len(participants) + 1}"
            participants[author_name] = participant_id
            
            participant = {
                "@type": "del:Participant",
                "del:identifier": participant_id,
                "del:name": author_name
            }
            process["del:hasParticipant"].append(participant)
        
        # Add debate as contribution
        contribution_id = f"madrid_debate_{debate_id}"
        contribution = {
            "@type": "del:Contribution",
            "del:identifier": contribution_id,
            "del:text": debate['description'],
            "del:madeBy": {"@id": participants[author_name]},
            "del:hasTopic": {"@id": topic_id}
        }
        
        # Add timestamp if available
        if debate['created_at']:
            try:
                # Try to parse the date
                date_obj = datetime.strptime(debate['created_at'], '%d/%m/%Y %H')
                contribution["del:timestamp"] = date_obj.strftime('%Y-%m-%dT%H:00:00Z')
            except ValueError:
                # If parsing fails, use the original string
                pass
        
        process["del:hasContribution"].append(contribution)
        
        # Process comments
        for i, comment in enumerate(debate['comments']):
            # Add comment author as participant if not already added
            comment_author = comment['author_name']
            if comment_author not in participants:
                participant_id = f"participant_{len(participants) + 1}"
                participants[comment_author] = participant_id
                
                participant = {
                    "@type": "del:Participant",
                    "del:identifier": participant_id,
                    "del:name": comment_author
                }
                process["del:hasParticipant"].append(participant)
            
            # Add comment as contribution
            comment_id = f"madrid_comment_{comment['id']}"
            comment_contribution = {
                "@type": "del:Contribution",
                "del:identifier": comment_id,
                "del:text": comment['body'],
                "del:madeBy": {"@id": participants[comment_author]},
                "del:hasTopic": {"@id": topic_id},
                "del:responseTo": {"@id": contribution_id}
            }
            
            # Add timestamp if available
            if comment['created_at']:
                try:
                    # Try to parse the date
                    date_obj = datetime.strptime(comment['created_at'], '%d/%m/%Y %H')
                    comment_contribution["del:timestamp"] = date_obj.strftime('%Y-%m-%dT%H:00:00Z')
                except ValueError:
                    # If parsing fails, use the original string
                    pass
            
            process["del:hasContribution"].append(comment_contribution)
    
    # Write JSON output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(process, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully converted Decide Madrid data to JSON format at {output_file}")
    return True

def convert_to_rdf(debates_csv, comments_csv, output_dir):
    """Convert Decide Madrid data to RDF format"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Step 1: Convert CSV to JSON
    json_dir = os.path.join(output_dir, "json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    
    json_output = os.path.join(json_dir, "decide_madrid.json")
    
    # Convert debates and comments to JSON
    success = convert_debates_to_json(debates_csv, comments_csv, json_output)
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
    
    # Convert JSON to RDF
    rdf_output = os.path.join(output_dir, "decide_madrid.rdf")
    print(f"Converting JSON to RDF format...")
    try:
        subprocess.run([sys.executable, json_to_rdf_script, json_output, rdf_output], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting JSON to RDF: {e}")
        return False
    
    print(f"Conversion complete. RDF file saved to {rdf_output}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Convert Decide Madrid data to RDF format')
    parser.add_argument('--debates', required=True, help='Path to the debates CSV file')
    parser.add_argument('--comments', help='Path to the comments CSV file')
    parser.add_argument('--output', required=True, help='Directory to save the output RDF files')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.debates):
        print(f"Error: Debates file '{args.debates}' does not exist")
        sys.exit(1)
    
    if args.comments and not os.path.exists(args.comments):
        print(f"Error: Comments file '{args.comments}' does not exist")
        sys.exit(1)
    
    success = convert_to_rdf(args.debates, args.comments, args.output)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
