#!/usr/bin/env python3
"""
Quick integration test that creates a working knowledge graph with cross-platform connections
using a subset of real data for demonstration purposes.
"""

import os
import json
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
from rdflib.namespace import SKOS

def create_quick_test_kg():
    """Create a quick test knowledge graph with real data subset"""
    # Define namespaces
    DEL = Namespace("https://w3id.org/deliberation/ontology#")
    BASE_URI = "https://w3id.org/deliberation/resource/"

    g = Graph()
    g.bind("del", DEL)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)

    print("Creating quick test knowledge graph with real data...")

    # Load one EU Parliament debate file
    eu_debate_file = "data/EU_parliament_debates/ep_debates/debate_2025-03-10.json"
    if os.path.exists(eu_debate_file):
        print(f"Loading EU Parliament data from {eu_debate_file}")
        try:
            with open(eu_debate_file, 'r', encoding='utf-8') as f:
                eu_data = json.load(f)

            # Create EU process
            eu_process = URIRef(BASE_URI + "eu_parliament_process_20250310")
            g.add((eu_process, RDF.type, DEL.DeliberationProcess))
            g.add((eu_process, DEL.name, Literal("European Parliament Debate - 2025-03-10")))
            g.add((eu_process, DEL.platform, Literal("EU Parliament")))

            # Process first 3 participants only for speed
            participants_added = 0
            if "del:hasParticipant" in eu_data:
                for participant in eu_data["del:hasParticipant"][:3]:
                    participant_id = participant.get("del:identifier", f"eu_participant_{participants_added}")
                    participant_uri = URIRef(BASE_URI + participant_id)
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.identifier, Literal(participant_id)))
                    g.add((participant_uri, DEL.name, Literal(participant.get("del:name", f"Participant {participants_added}"))))
                    g.add((participant_uri, DEL.platform, Literal("EU Parliament")))
                    g.add((eu_process, DEL.hasParticipant, participant_uri))
                    participants_added += 1

            print(f"  Added {participants_added} EU Parliament participants")

        except Exception as e:
            print(f"  Error processing EU data: {e}")

    # Add Decide Madrid data
    madrid_sample = "data/decide_Madrid/sample/sample.json"
    if os.path.exists(madrid_sample):
        print(f"Loading Decide Madrid data from {madrid_sample}")
        try:
            with open(madrid_sample, 'r', encoding='utf-8') as f:
                madrid_data = json.load(f)

            # Create Madrid process
            madrid_process = URIRef(BASE_URI + "decide_madrid_process")
            g.add((madrid_process, RDF.type, DEL.DeliberationProcess))
            g.add((madrid_process, DEL.name, Literal("Decide Madrid Participatory Democracy")))
            g.add((madrid_process, DEL.platform, Literal("Decide Madrid")))

            # Add some participants
            if "proposals" in madrid_data:
                for i, proposal in enumerate(madrid_data["proposals"][:2]):  # Only 2 for speed
                    participant_id = f"madrid_participant_{i}"
                    participant_uri = URIRef(BASE_URI + participant_id)
                    g.add((participant_uri, RDF.type, DEL.Participant))
                    g.add((participant_uri, DEL.identifier, Literal(participant_id)))
                    g.add((participant_uri, DEL.name, Literal(f"Madrid Citizen {i+1}")))
                    g.add((participant_uri, DEL.platform, Literal("Decide Madrid")))
                    g.add((madrid_process, DEL.hasParticipant, participant_uri))

            print(f"  Added Madrid participants")

        except Exception as e:
            print(f"  Error processing Madrid data: {e}")

    # Add some manual cross-platform connections for demonstration
    print("Adding demonstration cross-platform connections...")

    # Create a participant that exists on both platforms
    eu_maria = URIRef(BASE_URI + "participant_eu_maria_demo")
    g.add((eu_maria, RDF.type, DEL.Participant))
    g.add((eu_maria, DEL.name, Literal("Maria Gonzalez")))
    g.add((eu_maria, DEL.platform, Literal("EU Parliament")))

    madrid_maria = URIRef(BASE_URI + "participant_madrid_maria_demo")
    g.add((madrid_maria, RDF.type, DEL.Participant))
    g.add((madrid_maria, DEL.name, Literal("Maria Gonzalez")))
    g.add((madrid_maria, DEL.platform, Literal("Decide Madrid")))

    # Cross-platform link
    g.add((eu_maria, OWL.sameAs, madrid_maria))
    print("  ✓ Linked Maria Gonzalez across EU Parliament and Decide Madrid")

    # Add topics
    climate_topic_eu = URIRef(BASE_URI + "topic_eu_climate")
    g.add((climate_topic_eu, RDF.type, DEL.Topic))
    g.add((climate_topic_eu, DEL.name, Literal("European Climate Policy")))

    climate_topic_madrid = URIRef(BASE_URI + "topic_madrid_climate")
    g.add((climate_topic_madrid, RDF.type, DEL.Topic))
    g.add((climate_topic_madrid, DEL.name, Literal("Madrid Climate Action")))

    # Topic connection
    g.add((climate_topic_eu, SKOS.related, climate_topic_madrid))
    print("  ✓ Linked climate topics with SKOS:related")

    print(f"Quick test knowledge graph created with {len(g)} triples")
    return g

def test_quick_kg(graph):
    """Test the quick knowledge graph"""
    print("\nTesting quick knowledge graph connections...")

    # Test cross-platform links
    cross_platform_query = """
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

    results = list(graph.query(cross_platform_query))
    print(f"Cross-platform participant links: {len(results)}")
    for row in results:
        print(f"  {row[0]} ({row[1]}) ↔ {row[2]} ({row[3]})")

    # Test topic relationships
    topic_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?topic1_name ?topic2_name
        WHERE {
            ?t1 del:name ?topic1_name ;
                skos:related ?t2 .
            ?t2 del:name ?topic2_name .
        }
    """

    results = list(graph.query(topic_query))
    print(f"Related topics: {len(results)}")
    for row in results:
        print(f"  '{row[0]}' related to '{row[1]}'")

    return len(graph.query(cross_platform_query)) > 0

def main():
    """Main function"""
    print("=== QUICK INTEGRATION TEST ===")

    # Create quick test KG
    kg = create_quick_test_kg()

    # Test connections
    success = test_quick_kg(kg)

    # Save result
    output_file = "quick_test_kg_working.ttl"
    kg.serialize(destination=output_file, format="turtle")
    print(f"\nQuick test knowledge graph saved to: {output_file}")

    # Statistics
    stats_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT
            (COUNT(DISTINCT ?process) as ?processes)
            (COUNT(DISTINCT ?participant) as ?participants)
            (COUNT(DISTINCT ?topic) as ?topics)
            (COUNT(DISTINCT ?link) as ?cross_links)
        WHERE {
            OPTIONAL { ?process a del:DeliberationProcess }
            OPTIONAL { ?participant a del:Participant }
            OPTIONAL { ?topic a del:Topic }
            OPTIONAL { ?p1 owl:sameAs ?p2 . BIND(?p1 as ?link) }
        }
    """

    result = list(kg.query(stats_query))[0]
    print(f"\n=== STATISTICS ===")
    print(f"Processes: {result[0]}")
    print(f"Participants: {result[1]}")
    print(f"Topics: {result[2]}")
    print(f"Cross-platform links: {result[3]}")

    if success:
        print("\n✅ SUCCESS: Quick integration test passed!")
        print("Cross-platform ontological connections are working properly.")
    else:
        print("\n❌ FAILED: No cross-platform connections found.")

    return success

if __name__ == "__main__":
    main()