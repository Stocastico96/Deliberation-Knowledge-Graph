#!/usr/bin/env python3
"""
Script to convert the JSON representation of European Parliament debates
to RDF/OWL format compatible with the deliberation ontology.
"""

import os
import json
import sys
import argparse
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD

def convert_json_to_rdf(json_file, output_file):
    """Convert EU Parliament JSON debate data to RDF/OWL format"""
    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create RDF graph
    g = Graph()
    
    # Define namespaces
    DEL = Namespace("https://w3id.org/deliberation/ontology#")
    g.bind("del", DEL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Base URI for resources
    base_uri = "https://w3id.org/deliberation/resource/"
    
    # Extract date from filename or use date from data
    debate_date = data.get("date", "unknown")
    process_id = f"eu_parliament_debate_{debate_date}"
    
    # Add deliberation process
    process_uri = URIRef(base_uri + process_id)
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.identifier, Literal(process_id)))
    g.add((process_uri, DEL.name, Literal(f"EU Parliament Debate {debate_date}")))
    g.add((process_uri, DEL.platform, Literal("EU Parliament")))
    
    if debate_date != "unknown":
        g.add((process_uri, DEL.startDate, Literal(debate_date, datatype=XSD.date)))
    
    # Track unique participants and topics
    participants = {}
    topics = {}
    
    # Process speeches
    speeches = data.get("speeches", [])
    for i, speech in enumerate(speeches):
        # Create contribution
        contribution_id = f"speech_{speech.get('id', i)}"
        contribution_uri = URIRef(base_uri + contribution_id)
        g.add((contribution_uri, RDF.type, DEL.Contribution))
        g.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
        
        # Add activity label as text content
        activity_label = speech.get("activity_label", {})
        if isinstance(activity_label, dict) and "en" in activity_label:
            text_content = activity_label["en"]
        else:
            text_content = str(activity_label) if activity_label else f"Speech {i+1}"
        
        g.add((contribution_uri, DEL.text, Literal(text_content)))
        
        # Add timestamps
        if "activity_start_date" in speech:
            g.add((contribution_uri, DEL.timestamp, Literal(speech["activity_start_date"], datatype=XSD.dateTime)))
        
        # Process participation info
        participation = speech.get("had_participation", {})
        if participation:
            # Get participant person ID
            participant_persons = participation.get("had_participant_person", [])
            if participant_persons:
                person_id = participant_persons[0] if isinstance(participant_persons, list) else participant_persons
                participant_id = f"participant_{person_id}"
                
                # Create participant if not exists
                if participant_id not in participants:
                    participant_uri = URIRef(base_uri + participant_id)
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.identifier, Literal(participant_id)))
                    g.add((participant_uri, DEL.name, Literal(f"Person {person_id}")))
                    
                    # Add role
                    role = participation.get("participation_role", "")
                    if role:
                        role_id = f"role_{role.split('/')[-1]}"
                        role_uri = URIRef(base_uri + role_id)
                        g.add((role_uri, RDF.type, DEL.Role))
                        g.add((role_uri, DEL.name, Literal(role.split('/')[-1].replace('_', ' ').title())))
                        g.add((participant_uri, DEL.hasRole, role_uri))
                    
                    # Add organization if available
                    org_name = participation.get("participation_in_name_of", "")
                    if org_name:
                        org_id = f"org_{org_name.replace('/', '_').replace(' ', '_')}"
                        org_uri = URIRef(base_uri + org_id)
                        g.add((org_uri, RDF.type, DEL.Organization))
                        g.add((org_uri, DEL.name, Literal(org_name)))
                        g.add((participant_uri, DEL.isAffiliatedWith, org_uri))
                    
                    participants[participant_id] = participant_uri
                    g.add((participants[participant_id], DEL.partOf, process_uri))
                
                # Link contribution to participant
                g.add((contribution_uri, DEL.madeBy, participants[participant_id]))
        
        # Create topic from activity label
        if text_content and text_content not in topics:
            topic_id = f"topic_{len(topics) + 1}"
            topic_uri = URIRef(base_uri + topic_id)
            g.add((topic_uri, RDF.type, DEL.Topic))
            g.add((topic_uri, DEL.identifier, Literal(topic_id)))
            g.add((topic_uri, DEL.name, Literal(text_content[:100] + "..." if len(text_content) > 100 else text_content)))
            topics[text_content] = topic_uri
            g.add((process_uri, DEL.hasTopic, topic_uri))
        
        if text_content in topics:
            g.add((contribution_uri, DEL.hasTopic, topics[text_content]))
        
        # Link contribution to process
        g.add((contribution_uri, DEL.partOf, process_uri))
    
    # Serialize to RDF/XML
    g.serialize(destination=output_file, format="xml")
    print(f"Successfully converted {json_file} to RDF format at {output_file}")
    print(f"  - Processed {len(speeches)} speeches")
    print(f"  - Created {len(participants)} participants")
    print(f"  - Created {len(topics)} topics")

def main():
    parser = argparse.ArgumentParser(description='Convert JSON debate data to RDF/OWL format')
    parser.add_argument('input_file', help='Path to the JSON file')
    parser.add_argument('output_file', help='Path to the output RDF file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        convert_json_to_rdf(args.input_file, args.output_file)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
