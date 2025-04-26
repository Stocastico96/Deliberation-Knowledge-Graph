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
    """Convert JSON debate data to RDF/OWL format"""
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
    
    # Add deliberation process
    process_uri = URIRef(base_uri + data["del:identifier"])
    g.add((process_uri, RDF.type, DEL.DeliberationProcess))
    g.add((process_uri, DEL.identifier, Literal(data["del:identifier"])))
    g.add((process_uri, DEL.name, Literal(data["del:name"])))
    
    if data["del:startDate"]:
        g.add((process_uri, DEL.startDate, Literal(data["del:startDate"], datatype=XSD.dateTime)))
    
    if data["del:endDate"]:
        g.add((process_uri, DEL.endDate, Literal(data["del:endDate"], datatype=XSD.dateTime)))
    
    # Add topics
    for topic in data["del:hasTopic"]:
        topic_uri = URIRef(base_uri + topic["del:identifier"])
        g.add((topic_uri, RDF.type, DEL.Topic))
        g.add((topic_uri, DEL.identifier, Literal(topic["del:identifier"])))
        g.add((topic_uri, DEL.name, Literal(topic["del:name"])))
        
        # Link topic to process
        g.add((process_uri, DEL.hasTopic, topic_uri))
    
    # Add participants
    for participant in data["del:hasParticipant"]:
        participant_uri = URIRef(base_uri + participant["del:identifier"])
        g.add((participant_uri, RDF.type, DEL.Participant))
        g.add((participant_uri, DEL.identifier, Literal(participant["del:identifier"])))
        g.add((participant_uri, DEL.name, Literal(participant["del:name"])))
        
        # Add role if available
        if "del:hasRole" in participant:
            role_uri = URIRef(base_uri + "role_" + participant["del:identifier"])
            g.add((role_uri, RDF.type, DEL.Role))
            g.add((role_uri, DEL.name, Literal(participant["del:hasRole"]["del:name"])))
            g.add((participant_uri, DEL.hasRole, role_uri))
        
        # Add affiliation if available
        if "del:isAffiliatedWith" in participant:
            org_uri = URIRef(base_uri + "org_" + participant["del:isAffiliatedWith"]["del:name"].replace("/", "_"))
            g.add((org_uri, RDF.type, DEL.Organization))
            g.add((org_uri, DEL.name, Literal(participant["del:isAffiliatedWith"]["del:name"])))
            g.add((participant_uri, DEL.isAffiliatedWith, org_uri))
        
        # Link participant to process
        g.add((process_uri, DEL.hasParticipant, participant_uri))
    
    # Add contributions
    for contribution in data["del:hasContribution"]:
        contribution_uri = URIRef(base_uri + contribution["del:identifier"])
        g.add((contribution_uri, RDF.type, DEL.Contribution))
        g.add((contribution_uri, DEL.identifier, Literal(contribution["del:identifier"])))
        g.add((contribution_uri, DEL.text, Literal(contribution["del:text"])))
        
        # Add timestamp if available
        if "del:timestamp" in contribution:
            g.add((contribution_uri, DEL.timestamp, Literal(contribution["del:timestamp"], datatype=XSD.dateTime)))
        
        # Link to participant
        if "del:madeBy" in contribution and "@id" in contribution["del:madeBy"]:
            participant_id = contribution["del:madeBy"]["@id"]
            participant_uri = URIRef(base_uri + participant_id)
            g.add((contribution_uri, DEL.madeBy, participant_uri))
        
        # Link to topic if available
        if "del:hasTopic" in contribution and "@id" in contribution["del:hasTopic"]:
            topic_id = contribution["del:hasTopic"]["@id"]
            topic_uri = URIRef(base_uri + topic_id)
            g.add((contribution_uri, DEL.hasTopic, topic_uri))
        
        # Link contribution to process
        g.add((process_uri, DEL.hasContribution, contribution_uri))
    
    # Serialize to RDF/XML
    g.serialize(destination=output_file, format="xml")
    print(f"Successfully converted {json_file} to RDF format at {output_file}")

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
