#!/usr/bin/env python3
"""
Script to test the knowledge graph connections and verify that real deliberation data
is properly linked across platforms with ontological relationships.
"""

import os
import sys
from rdflib import Graph, Namespace

def test_knowledge_graph_connections(kg_file):
    """Test the knowledge graph for proper ontological connections"""
    print(f"Testing knowledge graph: {kg_file}")

    # Load the knowledge graph
    g = Graph()
    try:
        if kg_file.endswith('.ttl'):
            g.parse(kg_file, format='turtle')
        elif kg_file.endswith('.rdf'):
            g.parse(kg_file, format='xml')
        elif kg_file.endswith('.jsonld'):
            g.parse(kg_file, format='json-ld')
        else:
            g.parse(kg_file)
        print(f"Loaded {len(g)} triples")
    except Exception as e:
        print(f"Error loading knowledge graph: {e}")
        return False

    # Define namespaces
    DEL = Namespace("https://w3id.org/deliberation/ontology#")
    OWL = Namespace("http://www.w3.org/2002/07/owl#")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

    # Test queries
    tests = [
        {
            "name": "Count deliberation processes",
            "query": """
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                SELECT (COUNT(?process) as ?count)
                WHERE { ?process a del:DeliberationProcess }
            """,
            "expected_min": 1
        },
        {
            "name": "Count participants",
            "query": """
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                SELECT (COUNT(?participant) as ?count)
                WHERE { ?participant a del:Participant }
            """,
            "expected_min": 10
        },
        {
            "name": "Count contributions",
            "query": """
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                SELECT (COUNT(?contribution) as ?count)
                WHERE { ?contribution a del:Contribution }
            """,
            "expected_min": 10
        },
        {
            "name": "Count cross-platform participant links (owl:sameAs)",
            "query": """
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                SELECT (COUNT(?link) as ?count)
                WHERE {
                    ?p1 a del:Participant .
                    ?p2 a del:Participant .
                    ?p1 owl:sameAs ?p2 .
                    BIND(?p1 as ?link)
                }
            """,
            "expected_min": 1
        },
        {
            "name": "Count topic relationships (skos:related)",
            "query": """
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                SELECT (COUNT(?link) as ?count)
                WHERE {
                    ?t1 a del:Topic .
                    ?t2 a del:Topic .
                    ?t1 skos:related ?t2 .
                    BIND(?t1 as ?link)
                }
            """,
            "expected_min": 0  # May be 0 if no topics are similar enough
        },
        {
            "name": "Find participants across multiple platforms",
            "query": """
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT ?name1 ?platform1 ?name2 ?platform2
                WHERE {
                    ?p1 a del:Participant ;
                        del:name ?name1 ;
                        del:platform ?platform1 .
                    ?p2 a del:Participant ;
                        del:name ?name2 ;
                        del:platform ?platform2 .
                    ?p1 owl:sameAs ?p2 .
                    FILTER(?platform1 != ?platform2)
                }
                LIMIT 5
            """,
            "expected_min": 0,
            "show_results": True
        },
        {
            "name": "Find contributions by linked participants",
            "query": """
                PREFIX del: <https://w3id.org/deliberation/ontology#>
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                SELECT ?participant_name ?contribution_text
                WHERE {
                    ?p1 a del:Participant ;
                        del:name ?participant_name .
                    ?p2 a del:Participant .
                    ?p1 owl:sameAs ?p2 .
                    ?contribution a del:Contribution ;
                                 del:madeBy ?p2 ;
                                 del:text ?contribution_text .
                }
                LIMIT 3
            """,
            "expected_min": 0,
            "show_results": True
        }
    ]

    # Run tests
    results = {}
    for test in tests:
        print(f"\n--- {test['name']} ---")
        try:
            query_results = list(g.query(test['query']))

            if test.get('show_results', False):
                print(f"Results:")
                for row in query_results:
                    print(f"  {row}")
                count = len(query_results)
            else:
                count = int(query_results[0][0]) if query_results else 0

            print(f"Count: {count}")

            if count >= test['expected_min']:
                print("✓ PASS")
                results[test['name']] = True
            else:
                print(f"✗ FAIL (expected >= {test['expected_min']})")
                results[test['name']] = False

        except Exception as e:
            print(f"✗ ERROR: {e}")
            results[test['name']] = False

    # Summary
    passed = sum(results.values())
    total = len(results)
    print(f"\n=== SUMMARY ===")
    print(f"Passed: {passed}/{total} tests")

    if passed == total:
        print("🎉 All tests passed! The knowledge graph has proper ontological connections.")
        return True
    else:
        print("⚠️  Some tests failed. The knowledge graph may need improvements.")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        kg_file = "test_comprehensive_kg/deliberation_kg_complete.ttl"
        if not os.path.exists(kg_file):
            print("Usage: python test_kg_connections.py <path_to_knowledge_graph_file>")
            print("Available formats: .ttl, .rdf, .jsonld")
            sys.exit(1)
    else:
        kg_file = sys.argv[1]

    if not os.path.exists(kg_file):
        print(f"Error: Knowledge graph file '{kg_file}' not found")
        sys.exit(1)

    success = test_knowledge_graph_connections(kg_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()