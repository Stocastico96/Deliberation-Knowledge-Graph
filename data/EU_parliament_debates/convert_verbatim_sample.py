#!/usr/bin/env python3
"""
Script to convert a sample of the European Parliament verbatim HTML file to JSON format
aligned with the deliberation ontology.
"""

import os
import re
import json
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import argparse

def extract_date_from_title(title_text):
    """Extract date from the title text"""
    date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', title_text)
    if date_match:
        date_str = date_match.group(1)
        try:
            # Parse the date string to a datetime object
            date_obj = datetime.strptime(date_str, '%d %B %Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None

def extract_speaker_info(speaker_text):
    """Extract speaker name, role, and political group from speaker text"""
    speaker_info = {
        "name": "",
        "role": "",
        "politicalGroup": ""
    }
    
    # Extract name and political group if present
    if '(' in speaker_text and ')' in speaker_text:
        name_part = speaker_text.split('(')[0].strip()
        group_part = speaker_text.split('(')[1].split(')')[0].strip()
        speaker_info["name"] = name_part
        speaker_info["politicalGroup"] = group_part
    else:
        speaker_info["name"] = speaker_text.strip()
    
    # Check if the speaker is the President
    if "President" in speaker_text:
        speaker_info["role"] = "President"
    
    return speaker_info

def parse_verbatim_sample(html_file, max_lines=150):
    """Parse a sample of the verbatim HTML file and convert to JSON structure"""
    # Read only the first max_lines lines
    with open(html_file, 'r', encoding='utf-8') as f:
        lines = []
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line)
        
        html_content = ''.join(lines)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract debate date from title
    title_elem = soup.find('title')
    debate_date = None
    if title_elem:
        debate_date = extract_date_from_title(title_elem.text)
    
    # Extract debate topics from the table of contents
    toc_items = soup.select('table.list_summary tr')
    topics = []
    for item in toc_items:
        link = item.find('a')
        if link:
            topic_text = link.text.strip()
            topic_id = link.get('href', '').replace('#', '')
            topics.append({
                "id": topic_id,
                "title": topic_text
            })
    
    # Extract speeches (limited to what's in the sample)
    speeches = []
    speech_sections = soup.select('table.doc_box_header')
    
    for section in speech_sections:
        # Get the topic title
        topic_title_elem = section.select_one('td.doc_title')
        topic_title = topic_title_elem.text.strip() if topic_title_elem else ""
        
        # Get all speeches in this section
        speech_tables = section.select('table[width="100%"][border="0"][cellpadding="5"][cellspacing="0"]')
        
        for speech_table in speech_tables:
            speaker_elem = speech_table.select_one('span.doc_subtitle_level1_bis span.bold')
            if not speaker_elem:
                continue
                
            speaker_text = speaker_elem.text.strip()
            speaker_info = extract_speaker_info(speaker_text)
            
            # Extract speech content
            content_paras = speech_table.select('p.contents')
            speech_text = ""
            for para in content_paras:
                # Skip the paragraph that contains the speaker info
                if para.find('span', class_='doc_subtitle_level1_bis'):
                    continue
                speech_text += para.text.strip() + "\n"
            
            # Extract timestamp if available
            timestamp = None
            video_link = speech_table.select_one('a[title="Video of the speeches"]')
            if video_link:
                timestamp_match = re.search(r'playerStartTime=(\d{8}-\d{2}:\d{2}:\d{2})', video_link.get('href', ''))
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    try:
                        # Format: YYYYMMDD-HH:MM:SS
                        date_part = timestamp_str.split('-')[0]
                        time_part = timestamp_str.split('-')[1]
                        timestamp = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}T{time_part}"
                    except (IndexError, ValueError):
                        pass
            
            speech = {
                "speaker": speaker_info,
                "text": speech_text.strip(),
                "topic": topic_title,
                "timestamp": timestamp
            }
            
            speeches.append(speech)
    
    # Create the JSON structure aligned with the deliberation ontology
    debate_id = f"ep_debate_{debate_date.replace('-', '')}" if debate_date else "ep_debate_unknown"
    
    debate_json = {
        "@context": {
            "del": "https://w3id.org/deliberation/ontology#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@type": "del:DeliberationProcess",
        "del:identifier": debate_id,
        "del:name": f"European Parliament Debate - {debate_date} (Sample)",
        "del:startDate": f"{debate_date}T00:00:00Z" if debate_date else None,
        "del:endDate": f"{debate_date}T23:59:59Z" if debate_date else None,
        "del:hasTopic": [
            {
                "@type": "del:Topic",
                "del:identifier": topic["id"],
                "del:name": topic["title"]
            } for topic in topics
        ],
        "del:hasParticipant": [],
        "del:hasContribution": []
    }
    
    # Add unique participants
    participants = {}
    for speech in speeches:
        speaker_name = speech["speaker"]["name"]
        if speaker_name not in participants:
            participant_id = f"participant_{len(participants) + 1}"
            participant = {
                "@type": "del:Participant",
                "del:identifier": participant_id,
                "del:name": speaker_name
            }
            
            # Add role if available
            if speech["speaker"]["role"]:
                participant["del:hasRole"] = {
                    "@type": "del:Role",
                    "del:name": speech["speaker"]["role"]
                }
            
            # Add political group if available
            if speech["speaker"]["politicalGroup"]:
                participant["del:isAffiliatedWith"] = {
                    "@type": "del:Organization",
                    "del:name": speech["speaker"]["politicalGroup"]
                }
            
            participants[speaker_name] = participant_id
            debate_json["del:hasParticipant"].append(participant)
    
    # Add contributions (speeches)
    for i, speech in enumerate(speeches):
        contribution_id = f"contribution_{i + 1}"
        contribution = {
            "@type": "del:Contribution",
            "del:identifier": contribution_id,
            "del:text": speech["text"],
            "del:madeBy": {"@id": participants[speech["speaker"]["name"]]}
        }
        
        # Add timestamp if available
        if speech["timestamp"]:
            contribution["del:timestamp"] = speech["timestamp"]
        
        # Add topic reference
        if speech["topic"]:
            # Find matching topic
            for topic in debate_json["del:hasTopic"]:
                if topic["del:name"] == speech["topic"]:
                    contribution["del:hasTopic"] = {"@id": topic["del:identifier"]}
                    break
        
        debate_json["del:hasContribution"].append(contribution)
    
    return debate_json

def main():
    parser = argparse.ArgumentParser(description='Convert EP verbatim HTML sample to JSON')
    parser.add_argument('input_file', help='Path to the verbatim HTML file')
    parser.add_argument('output_file', help='Path to the output JSON file')
    parser.add_argument('--max-lines', type=int, default=150, help='Maximum number of lines to process')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    try:
        debate_json = parse_verbatim_sample(args.input_file, args.max_lines)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(debate_json, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted sample of {args.input_file} to {args.output_file}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
