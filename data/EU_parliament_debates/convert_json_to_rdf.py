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
    DKG = Namespace("https://w3id.org/deliberation/ontology#")
    g.bind("dkg", DKG)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    
    # Base URI for resources
    base_uri = "https://w3id.org/deliberation/resource/"
    
    # Add deliberation process
    process_uri = URIRef(base_uri + data["dkg:identifier"])
    g.add((process_uri, RDF.type, DKG.DeliberationProcess))
    g.add((process_uri, DKG.identifier, Literal(data["dkg:identifier"])))
    g.add((process_uri, DKG.name, Literal(data["dkg:name"])))
    
    if data["dkg:startDate"]:
        g.add((process_uri, DKG.startDate, Literal(data["dkg:startDate"], datatype=XSD.dateTime)))
    
    if data["dkg:endDate"]:
        g.add((process_uri, DKG.endDate, Literal(data["dkg:endDate"], datatype=XSD.dateTime)))
    
    # Add topics
    for topic in data["dkg:hasTopic"]:
        topic_uri = URIRef(base_uri + topic["dkg:identifier"])
        g.add((topic_uri, RDF.type, DKG.Topic))
        g.add((topic_uri, DKG.identifier, Literal(topic["dkg:identifier"])))
        g.add((topic_uri, DKG.name, Literal(topic["dkg:name"])))
        
        # Link topic to process
        g.add((process_uri, DKG.hasTopic, topic_uri))
    
    # Add participants
    for participant in data["dkg:hasParticipant"]:
        participant_uri = URIRef(base_uri + participant["dkg:identifier"])
        g.add((participant_uri, RDF.type, DKG.Participant))
        g.add((participant_uri, DKG.identifier, Literal(participant["dkg:identifier"])))
        g.add((participant_uri, DKG.name, Literal(participant["dkg:name"])))
        
        # Add role if available
        if "dkg:hasRole" in participant:
            role_uri = URIRef(base_uri + "role_" + participant["dkg:identifier"])
            g.add((role_uri, RDF.type, DKG.Role))
            g.add((role_uri, DKG.name, Literal(participant["dkg:hasRole"]["dkg:name"])))
            g.add((participant_uri, DKG.hasRole, role_uri))
        
        # Add affiliation if available
        if "dkg:isAffiliatedWith" in participant:
            org_uri = URIRef(base_uri + "org_" + participant["dkg:isAffiliatedWith"]["dkg:name"].replace("/", "_"))
            g.add((org_uri, RDF.type, DKG.Organization))
            g.add((org_uri, DKG.name, Literal(participant["dkg:isAffiliatedWith"]["dkg:name"])))
            g.add((participant_uri, DKG.isAffiliatedWith, org_uri))
        
        # Link participant to process
        g.add((process_uri, DKG.hasParticipant, participant_uri))
    
    # Add contributions
    for contribution in data["dkg:hasContribution"]:
        contribution_uri = URIRef(base_uri + contribution["dkg:identifier"])
        g.add((contribution_uri, RDF.type, DKG.Contribution))
        g.add((contribution_uri, DKG.identifier, Literal(contribution["dkg:identifier"])))
        g.add((contribution_uri, DKG.text, Literal(contribution["dkg:text"])))
        
        # Add timestamp if available
        if "dkg:timestamp" in contribution:
            g.add((contribution_uri, DKG.timestamp, Literal(contribution["dkg:timestamp"], datatype=XSD.dateTime)))
        
        # Link to participant
        if "dkg:madeBy" in contribution and "@id" in contribution["dkg:madeBy"]:
            participant_id = contribution["dkg:madeBy"]["@id"]
            participant_uri = URIRef(base_uri + participant_id)
            g.add((contribution_uri, DKG.madeBy, participant_uri))
        
        # Link to topic if available
        if "dkg:hasTopic" in contribution and "@id" in contribution["dkg:hasTopic"]:
            topic_id = contribution["dkg:hasTopic"]["@id"]
            topic_uri = URIRef(base_uri + topic_id)
            g.add((contribution_uri, DKG.hasTopic, topic_uri))
        
        # Link contribution to process
        g.add((process_uri, DKG.hasContribution, contribution_uri))
    
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
