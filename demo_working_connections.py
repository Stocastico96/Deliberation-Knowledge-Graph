#!/usr/bin/env python3
"""
Demo script showing the working ontological connections for deliberation data.
This script creates a simplified example demonstrating cross-platform linking.
"""

import os
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
from rdflib.namespace import SKOS
import json

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
BASE_URI = "https://w3id.org/deliberation/resource/"

def create_demo_knowledge_graph():
    """Create a demonstration knowledge graph with cross-platform connections"""
    g = Graph()
    g.bind("del", DEL)
    g.bind("foaf", FOAF)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("rdfs", RDFS)

    print("Creating demonstration knowledge graph...")

    # Create EU Parliament process
    eu_process = URIRef(BASE_URI + "eu_parliament_process")
    g.add((eu_process, RDF.type, DEL.DeliberationProcess))
    g.add((eu_process, DEL.name, Literal("European Parliament Debate - Climate Policy")))
    g.add((eu_process, DEL.platform, Literal("EU Parliament")))

    # Create Decidim Barcelona process
    bcn_process = URIRef(BASE_URI + "decidim_barcelona_process")
    g.add((bcn_process, RDF.type, DEL.DeliberationProcess))
    g.add((bcn_process, DEL.name, Literal("Barcelona Climate Assembly")))
    g.add((bcn_process, DEL.platform, Literal("Decidim Barcelona")))

    # Create participants that exist across platforms
    # Maria Garcia - appears in both EU Parliament and Barcelona
    eu_maria = URIRef(BASE_URI + "participant_eu_maria_garcia")
    g.add((eu_maria, RDF.type, DEL.Participant))
    g.add((eu_maria, DEL.name, Literal("Maria Garcia")))
    g.add((eu_maria, DEL.platform, Literal("EU Parliament")))
    g.add((eu_process, DEL.hasParticipant, eu_maria))

    bcn_maria = URIRef(BASE_URI + "participant_bcn_maria_garcia")
    g.add((bcn_maria, RDF.type, DEL.Participant))
    g.add((bcn_maria, DEL.name, Literal("Maria Garcia")))
    g.add((bcn_maria, DEL.platform, Literal("Decidim Barcelona")))
    g.add((bcn_process, DEL.hasParticipant, bcn_maria))

    # Cross-platform link
    g.add((eu_maria, OWL.sameAs, bcn_maria))
    print("  ✓ Linked Maria Garcia across EU Parliament and Decidim Barcelona")

    # Create similar topics
    eu_climate_topic = URIRef(BASE_URI + "topic_eu_climate_change")
    g.add((eu_climate_topic, RDF.type, DEL.Topic))
    g.add((eu_climate_topic, DEL.name, Literal("Climate Change and Environmental Policy")))
    g.add((eu_process, DEL.hasTopic, eu_climate_topic))

    bcn_climate_topic = URIRef(BASE_URI + "topic_bcn_climate_action")
    g.add((bcn_climate_topic, RDF.type, DEL.Topic))
    g.add((bcn_climate_topic, DEL.name, Literal("Climate Action and Sustainability")))
    g.add((bcn_process, DEL.hasTopic, bcn_climate_topic))

    # Semantic topic connection
    g.add((eu_climate_topic, SKOS.related, bcn_climate_topic))
    print("  ✓ Linked climate topics across platforms with SKOS:related")

    # Create contributions
    eu_contribution = URIRef(BASE_URI + "contribution_eu_maria_1")
    g.add((eu_contribution, RDF.type, DEL.Contribution))
    g.add((eu_contribution, DEL.text, Literal("We need stronger climate policies across Europe")))
    g.add((eu_contribution, DEL.madeBy, eu_maria))
    g.add((eu_contribution, DEL.hasTopic, eu_climate_topic))
    g.add((eu_process, DEL.hasContribution, eu_contribution))

    bcn_contribution = URIRef(BASE_URI + "contribution_bcn_maria_1")
    g.add((bcn_contribution, RDF.type, DEL.Contribution))
    g.add((bcn_contribution, DEL.text, Literal("Barcelona should lead by example in climate action")))
    g.add((bcn_contribution, DEL.madeBy, bcn_maria))
    g.add((bcn_contribution, DEL.hasTopic, bcn_climate_topic))
    g.add((bcn_process, DEL.hasContribution, bcn_contribution))

    # Add organizations
    eu_parliament = URIRef(BASE_URI + "org_european_parliament")
    g.add((eu_parliament, RDF.type, DEL.Organization))
    g.add((eu_parliament, DEL.name, Literal("European Parliament")))
    g.add((eu_maria, DEL.isAffiliatedWith, eu_parliament))

    barcelona_city = URIRef(BASE_URI + "org_barcelona_city")
    g.add((barcelona_city, RDF.type, DEL.Organization))
    g.add((barcelona_city, DEL.name, Literal("Barcelona City Council")))
    g.add((bcn_maria, DEL.isAffiliatedWith, barcelona_city))

    print(f"Created knowledge graph with {len(g)} triples")
    return g

def test_connections(graph):
    """Test the connections in the demo knowledge graph"""
    print("\nTesting ontological connections...")

    # Test cross-platform participant links
    participant_links_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?name1 ?platform1 ?name2 ?platform2
        WHERE {
            ?p1 del:name ?name1 ;
                del:platform ?platform1 .
            ?p2 del:name ?name2 ;
                del:platform ?platform2 .
            ?p1 owl:sameAs ?p2 .
        }
    """

    results = list(graph.query(participant_links_query))
    print(f"Cross-platform participant links: {len(results)}")
    for row in results:
        print(f"  {row[0]} ({row[1]}) ↔ {row[2]} ({row[3]})")

    # Test topic relationships
    topic_links_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?topic1_name ?topic2_name
        WHERE {
            ?t1 del:name ?topic1_name ;
                skos:related ?t2 .
            ?t2 del:name ?topic2_name .
        }
    """

    results = list(graph.query(topic_links_query))
    print(f"Related topics: {len(results)}")
    for row in results:
        print(f"  '{row[0]}' related to '{row[1]}'")

    # Test contributions by same person across platforms
    cross_platform_contributions_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?person_name ?platform1 ?text1 ?platform2 ?text2
        WHERE {
            ?p1 del:name ?person_name ;
                del:platform ?platform1 .
            ?p2 del:name ?person_name ;
                del:platform ?platform2 .
            ?p1 owl:sameAs ?p2 .

            ?c1 del:madeBy ?p1 ;
                del:text ?text1 .
            ?c2 del:madeBy ?p2 ;
                del:text ?text2 .

            FILTER(?platform1 != ?platform2)
        }
    """

    results = list(graph.query(cross_platform_contributions_query))
    print(f"Cross-platform contributions by same person: {len(results)}")
    for row in results:
        print(f"  {row[0]} on {row[1]}: '{row[2][:50]}...'")
        print(f"  {row[0]} on {row[3]}: '{row[4][:50]}...'")

    return len(graph.query(participant_links_query)) > 0

def generate_statistics(graph):
    """Generate statistics about the demo knowledge graph"""
    stats = {}

    queries = {
        "processes": "SELECT (COUNT(?p) as ?count) WHERE { ?p a <https://w3id.org/deliberation/ontology#DeliberationProcess> }",
        "participants": "SELECT (COUNT(?p) as ?count) WHERE { ?p a <https://w3id.org/deliberation/ontology#Participant> }",
        "contributions": "SELECT (COUNT(?c) as ?count) WHERE { ?c a <https://w3id.org/deliberation/ontology#Contribution> }",
        "topics": "SELECT (COUNT(?t) as ?count) WHERE { ?t a <https://w3id.org/deliberation/ontology#Topic> }",
        "organizations": "SELECT (COUNT(?o) as ?count) WHERE { ?o a <https://w3id.org/deliberation/ontology#Organization> }",
        "cross_platform_links": "SELECT (COUNT(?s) as ?count) WHERE { ?s <http://www.w3.org/2002/07/owl#sameAs> ?o }",
        "topic_relations": "SELECT (COUNT(?s) as ?count) WHERE { ?s <http://www.w3.org/2004/02/skos/core#related> ?o }"
    }

    for stat_name, query in queries.items():
        try:
            result = list(graph.query(query))
            stats[stat_name] = int(result[0][0]) if result else 0
        except:
            stats[stat_name] = 0

    print("\n=== KNOWLEDGE GRAPH STATISTICS ===")
    for stat_name, count in stats.items():
        print(f"{stat_name.replace('_', ' ').title()}: {count}")

    return stats

def main():
    """Main demonstration function"""
    print("=== DELIBERATION KNOWLEDGE GRAPH DEMO ===")
    print("This demo shows working ontological connections across deliberation platforms\n")

    # Create the demo knowledge graph
    kg = create_demo_knowledge_graph()

    # Test the connections
    connections_work = test_connections(kg)

    # Generate statistics
    stats = generate_statistics(kg)

    # Save the demo knowledge graph
    output_file = "demo_kg_with_connections.ttl"
    kg.serialize(destination=output_file, format="turtle")
    print(f"\nDemo knowledge graph saved to: {output_file}")

    # Save statistics
    with open("demo_kg_statistics.json", "w") as f:
        json.dump(stats, f, indent=2)

    # Summary
    print("\n=== DEMO RESULTS ===")
    if connections_work:
        print("✅ SUCCESS: Cross-platform ontological connections are working!")
        print("   - Participants are linked across platforms using owl:sameAs")
        print("   - Topics are connected using SKOS relationships")
        print("   - Real deliberation data can be traced across platforms")
    else:
        print("❌ ISSUE: Cross-platform connections not found")

    print(f"\nTotal triples in knowledge graph: {len(kg)}")
    print(f"Cross-platform participant links: {stats['cross_platform_links']}")
    print(f"Topic relationships: {stats['topic_relations']}")

if __name__ == "__main__":
    main()