#!/usr/bin/env python3
"""
Script to convert Decidim Barcelona data to RDF format
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

def load_csv(file_path, delimiter=';'):
    """Load CSV file into a list of dictionaries"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            data = list(reader)
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
    return data

def convert_decidim_to_json(data_dir, output_file):
    """Convert Decidim Barcelona data to JSON format aligned with the deliberation ontology"""
    # Define file paths
    proposals_file = os.path.join(data_dir, "www.decidim.barcelona-open-data-proposals.csv")
    proposal_comments_file = os.path.join(data_dir, "www.decidim.barcelona-open-data-proposal_comments.csv")
    meetings_file = os.path.join(data_dir, "www.decidim.barcelona-open-data-meetings.csv")
    meeting_comments_file = os.path.join(data_dir, "www.decidim.barcelona-open-data-meeting_comments.csv")
    
    # Check if files exist
    if not os.path.exists(proposals_file):
        print(f"Error: Proposals file not found at {proposals_file}")
        return False
    
    # Load data
    proposals = load_csv(proposals_file)
    proposal_comments = load_csv(proposal_comments_file) if os.path.exists(proposal_comments_file) else []
    meetings = load_csv(meetings_file) if os.path.exists(meetings_file) else []
    meeting_comments = load_csv(meeting_comments_file) if os.path.exists(meeting_comments_file) else []
    
    print(f"Loaded {len(proposals)} proposals, {len(proposal_comments)} proposal comments, {len(meetings)} meetings, and {len(meeting_comments)} meeting comments")
    
    # Group by participatory space
    spaces = {}
    
    # Process proposals
    for proposal in proposals:
        space_id = proposal.get('participatory_space/id', '')
        space_name = proposal.get('participatory_space/url', '').split('?')[0].split('/')[-1]
        
        if not space_id:
            continue
        
        if space_id not in spaces:
            spaces[space_id] = {
                "id": space_id,
                "name": space_name,
                "url": proposal.get('participatory_space/url', ''),
                "proposals": [],
                "meetings": [],
                "comments": []
            }
        
        spaces[space_id]["proposals"].append(proposal)
    
    # Process meetings
    for meeting in meetings:
        space_id = meeting.get('participatory_space/id', '')
        
        if not space_id or space_id not in spaces:
            continue
        
        spaces[space_id]["meetings"].append(meeting)
    
    # Process proposal comments
    for comment in proposal_comments:
        # Find the proposal
        proposal_id = comment.get('commentable_id', '')
        
        if not proposal_id:
            continue
        
        # Find which space this proposal belongs to
        for space_id, space in spaces.items():
            for proposal in space["proposals"]:
                if proposal.get('id') == proposal_id:
                    spaces[space_id]["comments"].append({
                        "id": comment.get('id', ''),
                        "body": comment.get('body', ''),
                        "created_at": comment.get('created_at', ''),
                        "author_name": comment.get('author/name', ''),
                        "author_id": comment.get('author/id', ''),
                        "commentable_id": proposal_id,
                        "commentable_type": "proposal",
                        "alignment": comment.get('alignment', '0'),
                        "depth": comment.get('depth', '0')
                    })
                    break
    
    # Process meeting comments
    for comment in meeting_comments:
        # Find the meeting
        meeting_id = comment.get('commentable_id', '')
        
        if not meeting_id:
            continue
        
        # Find which space this meeting belongs to
        for space_id, space in spaces.items():
            for meeting in space["meetings"]:
                if meeting.get('id') == meeting_id:
                    spaces[space_id]["comments"].append({
                        "id": comment.get('id', ''),
                        "body": comment.get('body', ''),
                        "created_at": comment.get('created_at', ''),
                        "author_name": comment.get('author/name', ''),
                        "author_id": comment.get('author/id', ''),
                        "commentable_id": meeting_id,
                        "commentable_type": "meeting",
                        "alignment": comment.get('alignment', '0'),
                        "depth": comment.get('depth', '0')
                    })
                    break
    
    # Convert to deliberation ontology format
    all_processes = []
    
    for space_id, space in spaces.items():
        # Create a deliberation process for each participatory space
        process = {
            "@context": {
                "del": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@type": "del:DeliberationProcess",
            "del:identifier": f"decidim_process_{space_id}",
            "del:name": f"Decidim Barcelona: {space['name']}",
            "del:startDate": None,
            "del:endDate": None,
            "del:hasTopic": [],
            "del:hasParticipant": [],
            "del:hasContribution": []
        }
        
        # Add topics (categories)
        topics = {}
        for proposal in space["proposals"]:
            category_id = proposal.get('category/id', '')
            category_name = proposal.get('category/name/ca', '') or proposal.get('category/name/es', '') or proposal.get('category/name/en', '')
            
            if category_id and category_name and category_id not in topics:
                topic_id = f"decidim_topic_{category_id}"
                topics[category_id] = topic_id
                
                topic = {
                    "del:identifier": topic_id,
                    "del:name": category_name
                }
                process["del:hasTopic"].append(topic)
        
        # Add participants
        participants = {}
        
        # Add proposal authors
        for proposal in space["proposals"]:
            author_id = proposal.get('author/id', '')
            author_name = proposal.get('author/name', '')
            
            if author_id and author_name and author_id not in participants:
                participant_id = f"participant_{author_id}"
                participants[author_id] = participant_id
                
                participant = {
                    "@type": "del:Participant",
                    "del:identifier": participant_id,
                    "del:name": author_name
                }
                process["del:hasParticipant"].append(participant)
        
        # Add comment authors
        for comment in space["comments"]:
            author_id = comment.get('author_id', '')
            author_name = comment.get('author_name', '')
            
            if author_id and author_name and author_id not in participants:
                participant_id = f"participant_{author_id}"
                participants[author_id] = participant_id
                
                participant = {
                    "@type": "del:Participant",
                    "del:identifier": participant_id,
                    "del:name": author_name
                }
                process["del:hasParticipant"].append(participant)
        
        # Add proposals as contributions
        for proposal in space["proposals"]:
            proposal_id = proposal.get('id', '')
            if not proposal_id:
                continue
                
            contribution_id = f"decidim_proposal_{proposal_id}"
            
            # Get proposal text
            title = proposal.get('title/ca', '') or proposal.get('title/es', '') or proposal.get('title/en', '')
            body = proposal.get('body/ca', '') or proposal.get('body/es', '') or proposal.get('body/en', '')
            
            if not title and not body:
                continue
            
            # Create contribution
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": f"{title}\n\n{body}".strip(),
                "del:madeBy": {"@id": participants.get(proposal.get('author/id', ''), '')}
            }
            
            # Add topic if available
            category_id = proposal.get('category/id', '')
            if category_id in topics:
                contribution["del:hasTopic"] = {"@id": topics[category_id]}
            
            # Add timestamp if available
            if proposal.get('published_at'):
                contribution["del:timestamp"] = proposal.get('published_at')
            
            # Add contribution to process
            process["del:hasContribution"].append(contribution)
        
        # Add meetings as contributions
        for meeting in space["meetings"]:
            meeting_id = meeting.get('id', '')
            if not meeting_id:
                continue
                
            contribution_id = f"decidim_meeting_{meeting_id}"
            
            # Get meeting text
            title = meeting.get('title/ca', '') or meeting.get('title/es', '') or meeting.get('title/en', '')
            description = meeting.get('description/ca', '') or meeting.get('description/es', '') or meeting.get('description/en', '')
            
            if not title and not description:
                continue
            
            # Create contribution
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": f"{title}\n\n{description}".strip()
            }
            
            # Add topic if available
            category_id = meeting.get('category/id', '')
            if category_id in topics:
                contribution["del:hasTopic"] = {"@id": topics[category_id]}
            
            # Add timestamp if available
            if meeting.get('start_time'):
                contribution["del:timestamp"] = meeting.get('start_time')
            
            # Add contribution to process
            process["del:hasContribution"].append(contribution)
        
        # Add comments as contributions
        for comment in space["comments"]:
            comment_id = comment.get('id', '')
            if not comment_id:
                continue
                
            contribution_id = f"decidim_comment_{comment_id}"
            
            # Get comment text
            body = comment.get('body', '')
            
            if not body:
                continue
            
            # Create contribution
            contribution = {
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": body,
                "del:madeBy": {"@id": participants.get(comment.get('author_id', ''), '')}
            }
            
            # Add timestamp if available
            if comment.get('created_at'):
                contribution["del:timestamp"] = comment.get('created_at')
            
            # Add response to if it's a comment
            if comment.get('commentable_type') == 'proposal':
                contribution["del:responseTo"] = {"@id": f"decidim_proposal_{comment.get('commentable_id', '')}"}
            elif comment.get('commentable_type') == 'meeting':
                contribution["del:responseTo"] = {"@id": f"decidim_meeting_{comment.get('commentable_id', '')}"}
            
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
            process_id = process["del:identifier"].replace("decidim_process_", "")
            process_file = os.path.join(output_dir, f"{base_name}_{process_id}.json")
            with open(process_file, 'w', encoding='utf-8') as f:
                json.dump(process, f, indent=2, ensure_ascii=False)
            
            print(f"Saved process {process_id} to {process_file}")
    
    print(f"Successfully converted Decidim Barcelona data to JSON format")
    return True

def convert_to_rdf(data_dir, output_dir):
    """Convert Decidim Barcelona data to RDF format"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Step 1: Convert to JSON
    json_dir = os.path.join(output_dir, "json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    
    json_output = os.path.join(json_dir, "decidim_barcelona.json")
    
    # Convert to JSON
    success = convert_decidim_to_json(data_dir, json_output)
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
    parser = argparse.ArgumentParser(description='Convert Decidim Barcelona data to RDF format')
    parser.add_argument('data_dir', help='Directory containing Decidim Barcelona CSV files')
    parser.add_argument('output_dir', help='Directory to save the output RDF files')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory '{args.data_dir}' does not exist")
        sys.exit(1)
    
    success = convert_to_rdf(args.data_dir, args.output_dir)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
