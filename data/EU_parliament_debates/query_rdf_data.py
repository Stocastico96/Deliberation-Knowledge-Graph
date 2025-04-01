#!/usr/bin/env python3
"""
Script to demonstrate SPARQL queries on the RDF data of European Parliament debates.
"""

import sys
import argparse
from rdflib import Graph, Namespace

def load_rdf_graph(rdf_file):
    """Load RDF data into a graph"""
    g = Graph()
    g.parse(rdf_file, format="xml")
    return g

def print_query_results(results, format_str=None):
    """Print query results in a formatted way"""
    if not results:
        print("No results found.")
        return
    
    # Print header
    if format_str:
        print(format_str.format(*results.vars))
        print("-" * 80)
    else:
        print("\t".join(results.vars))
        print("-" * 80)
    
    # Print results
    for row in results:
        if format_str:
            values = [str(row[var]) if var in row else "" for var in results.vars]
            print(format_str.format(*values))
        else:
            print("\t".join([str(row[var]) if var in row else "" for var in results.vars]))

def query_all_topics(graph):
    """Query all topics in the debate"""
    print("\n=== All Topics in the Debate ===\n")
    
    query = """
    PREFIX dkg: <https://w3id.org/deliberation/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?topic_id ?topic_name
    WHERE {
        ?topic rdf:type dkg:Topic ;
               dkg:identifier ?topic_id ;
               dkg:name ?topic_name .
    }
    ORDER BY ?topic_id
    """
    
    results = graph.query(query)
    print_query_results(results, "{:<15} {}")
    
    return len(results)

def query_all_participants(graph):
    """Query all participants in the debate"""
    print("\n=== All Participants in the Debate ===\n")
    
    query = """
    PREFIX dkg: <https://w3id.org/deliberation/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?name ?role ?organization
    WHERE {
        ?participant rdf:type dkg:Participant ;
                    dkg:name ?name .
        OPTIONAL {
            ?participant dkg:hasRole ?role_uri .
            ?role_uri dkg:name ?role .
        }
        OPTIONAL {
            ?participant dkg:isAffiliatedWith ?org_uri .
            ?org_uri dkg:name ?organization .
        }
    }
    ORDER BY ?name
    """
    
    results = graph.query(query)
    print_query_results(results, "{:<25} {:<15} {}")
    
    return len(results)

def query_contributions_by_participant(graph, participant_name):
    """Query all contributions by a specific participant"""
    print(f"\n=== Contributions by {participant_name} ===\n")
    
    query = """
    PREFIX dkg: <https://w3id.org/deliberation/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?timestamp ?text
    WHERE {
        ?participant rdf:type dkg:Participant ;
                    dkg:name ?name ;
                    ^dkg:madeBy ?contribution .
        ?contribution dkg:timestamp ?timestamp ;
                     dkg:text ?text .
        FILTER(REGEX(?name, ?participant_name, "i"))
    }
    ORDER BY ?timestamp
    """
    
    results = graph.query(query, initBindings={'participant_name': participant_name})
    
    if results:
        for row in results:
            print(f"[{row['timestamp']}]")
            print(f"{row['text']}")
            print("-" * 80)
    else:
        print(f"No contributions found for participant: {participant_name}")
    
    return len(results)

def query_contributions_by_topic(graph, topic_keyword):
    """Query all contributions related to a specific topic"""
    print(f"\n=== Contributions related to '{topic_keyword}' ===\n")
    
    query = """
    PREFIX dkg: <https://w3id.org/deliberation/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?topic_name ?participant_name ?timestamp ?text
    WHERE {
        ?topic rdf:type dkg:Topic ;
              dkg:name ?topic_name .
        ?process dkg:hasTopic ?topic ;
                dkg:hasContribution ?contribution .
        ?contribution dkg:timestamp ?timestamp ;
                     dkg:text ?text ;
                     dkg:madeBy ?participant .
        ?participant dkg:name ?participant_name .
        FILTER(REGEX(?topic_name, ?keyword, "i") || REGEX(?text, ?keyword, "i"))
    }
    ORDER BY ?timestamp
    """
    
    results = graph.query(query, initBindings={'keyword': topic_keyword})
    
    if results:
        for row in results:
            print(f"Topic: {row['topic_name']}")
            print(f"Speaker: {row['participant_name']}")
            print(f"Time: {row['timestamp']}")
            print(f"Text: {row['text']}")
            print("-" * 80)
    else:
        print(f"No contributions found related to: {topic_keyword}")
    
    return len(results)

def main():
    parser = argparse.ArgumentParser(description='Query RDF data of European Parliament debates')
    parser.add_argument('rdf_file', help='Path to the RDF file')
    parser.add_argument('--participant', help='Query contributions by participant name')
    parser.add_argument('--topic', help='Query contributions by topic keyword')
    
    args = parser.parse_args()
    
    try:
        graph = load_rdf_graph(args.rdf_file)
        print(f"Loaded RDF graph with {len(graph)} triples")
        
        if args.participant:
            query_contributions_by_participant(graph, args.participant)
        elif args.topic:
            query_contributions_by_topic(graph, args.topic)
        else:
            # Default queries
            topic_count = query_all_topics(graph)
            print(f"\nFound {topic_count} topics in the debate")
            
            participant_count = query_all_participants(graph)
            print(f"\nFound {participant_count} participants in the debate")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
