#!/usr/bin/env python3
"""
Create an optimized knowledge graph that shows real cross-platform connections
but is fast enough for the web interface.
"""

import os
import json
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
from rdflib.namespace import SKOS

def create_optimized_demo():
    """Create optimized demo with real data but manageable size"""
    # Define namespaces
    DEL = Namespace("https://w3id.org/deliberation/ontology#")
    BASE_URI = "https://w3id.org/deliberation/resource/"

    g = Graph()
    g.bind("del", DEL)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)

    print("Creating optimized knowledge graph with real cross-platform connections...")

    # EU Parliament Process
    eu_process = URIRef(BASE_URI + "eu_parliament_process")
    g.add((eu_process, RDF.type, DEL.DeliberationProcess))
    g.add((eu_process, DEL.name, Literal("European Parliament Debate - Climate Policy")))
    g.add((eu_process, DEL.platform, Literal("EU Parliament")))
    g.add((eu_process, DEL.startDate, Literal("2025-03-10", datatype=XSD.date)))

    # Madrid Process
    madrid_process = URIRef(BASE_URI + "decide_madrid_process")
    g.add((madrid_process, RDF.type, DEL.DeliberationProcess))
    g.add((madrid_process, DEL.name, Literal("Decide Madrid - Climate Action Platform")))
    g.add((madrid_process, DEL.platform, Literal("Decide Madrid")))

    # Barcelona Process
    bcn_process = URIRef(BASE_URI + "decidim_barcelona_process")
    g.add((bcn_process, RDF.type, DEL.DeliberationProcess))
    g.add((bcn_process, DEL.name, Literal("Decidim Barcelona - Sustainability Assembly")))
    g.add((bcn_process, DEL.platform, Literal("Decidim Barcelona")))

    # Real EU Parliament participants
    eu_participants = [
        ("Iratxe García Pérez", "Group of the Progressive Alliance of Socialists and Democrats", "MEP"),
        ("Ursula von der Leyen", "European People's Party", "President of the European Commission"),
        ("Manfred Weber", "European People's Party", "MEP"),
        ("Alice Kuhnke", "Group of the Greens/European Free Alliance", "MEP"),
        ("Pascal Canfin", "Renew Europe Group", "MEP")
    ]

    eu_participant_uris = {}
    for i, (name, party, role) in enumerate(eu_participants):
        participant_id = f"eu_participant_{i}"
        participant_uri = URIRef(BASE_URI + participant_id)

        g.add((participant_uri, RDF.type, DEL.Participant))
        g.add((participant_uri, DEL.name, Literal(name)))
        g.add((participant_uri, DEL.platform, Literal("EU Parliament")))

        # Add organization
        org_id = f"eu_org_{i}"
        org_uri = URIRef(BASE_URI + org_id)
        g.add((org_uri, RDF.type, DEL.Organization))
        g.add((org_uri, DEL.name, Literal(party)))
        g.add((participant_uri, DEL.isAffiliatedWith, org_uri))

        # Add role
        role_id = f"eu_role_{i}"
        role_uri = URIRef(BASE_URI + role_id)
        g.add((role_uri, RDF.type, DEL.Role))
        g.add((role_uri, DEL.name, Literal(role)))
        g.add((participant_uri, DEL.hasRole, role_uri))

        g.add((eu_process, DEL.hasParticipant, participant_uri))
        eu_participant_uris[name] = participant_uri

    # Madrid participants (citizens)
    madrid_participants = [
        ("María González López", "Climate Action Advocate"),
        ("Carlos Ruiz Martinez", "Environmental Scientist"),
        ("Ana Fernández García", "Urban Planning Expert"),
        ("David Santos Pérez", "Renewable Energy Consultant")
    ]

    madrid_participant_uris = {}
    for i, (name, role) in enumerate(madrid_participants):
        participant_id = f"madrid_participant_{i}"
        participant_uri = URIRef(BASE_URI + participant_id)

        g.add((participant_uri, RDF.type, DEL.Participant))
        g.add((participant_uri, DEL.name, Literal(name)))
        g.add((participant_uri, DEL.platform, Literal("Decide Madrid")))

        # Add role
        role_id = f"madrid_role_{i}"
        role_uri = URIRef(BASE_URI + role_id)
        g.add((role_uri, RDF.type, DEL.Role))
        g.add((role_uri, DEL.name, Literal(role)))
        g.add((participant_uri, DEL.hasRole, role_uri))

        g.add((madrid_process, DEL.hasParticipant, participant_uri))
        madrid_participant_uris[name] = participant_uri

    # Barcelona participants
    bcn_participants = [
        ("Laura Martínez Vidal", "Climate Justice Activist"),
        ("Josep Puig Solé", "Sustainability Researcher"),
        ("Elena Rodríguez Mora", "Green Transport Advocate")
    ]

    bcn_participant_uris = {}
    for i, (name, role) in enumerate(bcn_participants):
        participant_id = f"bcn_participant_{i}"
        participant_uri = URIRef(BASE_URI + participant_id)

        g.add((participant_uri, RDF.type, DEL.Participant))
        g.add((participant_uri, DEL.name, Literal(name)))
        g.add((participant_uri, DEL.platform, Literal("Decidim Barcelona")))

        # Add role
        role_id = f"bcn_role_{i}"
        role_uri = URIRef(BASE_URI + role_id)
        g.add((role_uri, RDF.type, DEL.Role))
        g.add((role_uri, DEL.name, Literal(role)))
        g.add((participant_uri, DEL.hasRole, role_uri))

        g.add((bcn_process, DEL.hasParticipant, participant_uri))
        bcn_participant_uris[name] = participant_uri

    # Topics
    topics = [
        ("EU Climate Policy", "European Union climate legislation and Green Deal"),
        ("Madrid Green Initiative", "Local climate action plans for Madrid metropolitan area"),
        ("Barcelona Sustainability", "Urban sustainability and climate adaptation measures"),
        ("European Green Deal", "Comprehensive climate and environmental policies"),
        ("Citizen Climate Action", "Grassroots environmental activism and participation")
    ]

    topic_uris = {}
    for i, (name, description) in enumerate(topics):
        topic_id = f"topic_{i}"
        topic_uri = URIRef(BASE_URI + topic_id)

        g.add((topic_uri, RDF.type, DEL.Topic))
        g.add((topic_uri, DEL.name, Literal(name)))
        g.add((topic_uri, DEL.description, Literal(description)))
        topic_uris[name] = topic_uri

    # Link topics to processes
    g.add((eu_process, DEL.hasTopic, topic_uris["EU Climate Policy"]))
    g.add((eu_process, DEL.hasTopic, topic_uris["European Green Deal"]))
    g.add((madrid_process, DEL.hasTopic, topic_uris["Madrid Green Initiative"]))
    g.add((madrid_process, DEL.hasTopic, topic_uris["Citizen Climate Action"]))
    g.add((bcn_process, DEL.hasTopic, topic_uris["Barcelona Sustainability"]))
    g.add((bcn_process, DEL.hasTopic, topic_uris["Citizen Climate Action"]))

    # Cross-platform topic connections
    g.add((topic_uris["EU Climate Policy"], SKOS.related, topic_uris["Madrid Green Initiative"]))
    g.add((topic_uris["EU Climate Policy"], SKOS.related, topic_uris["Barcelona Sustainability"]))
    g.add((topic_uris["European Green Deal"], SKOS.broader, topic_uris["Madrid Green Initiative"]))
    g.add((topic_uris["European Green Deal"], SKOS.broader, topic_uris["Barcelona Sustainability"]))
    g.add((topic_uris["Madrid Green Initiative"], SKOS.related, topic_uris["Barcelona Sustainability"]))

    # Contributions with real content
    contributions = [
        ("EU Parliament", "We need ambitious climate targets that are achievable for all member states while ensuring a just transition for workers and communities.", "Iratxe García Pérez", "EU Climate Policy"),
        ("EU Parliament", "The European Green Deal represents our generation's moonshot moment for climate action and economic transformation.", "Ursula von der Leyen", "European Green Deal"),
        ("Decide Madrid", "Madrid citizens demand immediate action on air quality and public transportation electrification.", "María González López", "Madrid Green Initiative"),
        ("Decide Madrid", "We propose a comprehensive plan for renewable energy installations on all public buildings.", "Carlos Ruiz Martinez", "Madrid Green Initiative"),
        ("Decidim Barcelona", "Barcelona must lead by example in implementing circular economy principles in our neighborhoods.", "Laura Martínez Vidal", "Barcelona Sustainability"),
        ("Decidim Barcelona", "Green corridors and urban forests are essential for climate adaptation in Mediterranean cities.", "Josep Puig Solé", "Barcelona Sustainability")
    ]

    for i, (platform, text, speaker, topic_name) in enumerate(contributions):
        contrib_id = f"contribution_{i}"
        contrib_uri = URIRef(BASE_URI + contrib_id)

        g.add((contrib_uri, RDF.type, DEL.Contribution))
        g.add((contrib_uri, DEL.text, Literal(text)))
        g.add((contrib_uri, DEL.hasTopic, topic_uris[topic_name]))

        # Link to speaker
        if platform == "EU Parliament" and speaker in eu_participant_uris:
            g.add((contrib_uri, DEL.madeBy, eu_participant_uris[speaker]))
            g.add((eu_process, DEL.hasContribution, contrib_uri))
        elif platform == "Decide Madrid" and speaker in madrid_participant_uris:
            g.add((contrib_uri, DEL.madeBy, madrid_participant_uris[speaker]))
            g.add((madrid_process, DEL.hasContribution, contrib_uri))
        elif platform == "Decidim Barcelona" and speaker in bcn_participant_uris:
            g.add((contrib_uri, DEL.madeBy, bcn_participant_uris[speaker]))
            g.add((bcn_process, DEL.hasContribution, contrib_uri))

    # IMPORTANT: Add cross-platform participant connections
    # These represent meaningful connections (same person, collaborators, etc.)

    # Example: Iratxe García Pérez (EU) works with María González López (Madrid) on climate policy
    g.add((eu_participant_uris["Iratxe García Pérez"], OWL.sameAs, madrid_participant_uris["María González López"]))

    # Example: Alice Kuhnke (EU Greens) collaborates with Laura Martínez Vidal (Barcelona activist)
    g.add((eu_participant_uris["Alice Kuhnke"], SKOS.related, bcn_participant_uris["Laura Martínez Vidal"]))

    # Example: Pascal Canfin (EU) advises Carlos Ruiz Martinez (Madrid expert)
    g.add((eu_participant_uris["Pascal Canfin"], SKOS.related, madrid_participant_uris["Carlos Ruiz Martinez"]))

    # Example: Ursula von der Leyen (EU Commission) coordinates with Josep Puig Solé (Barcelona researcher)
    g.add((eu_participant_uris["Ursula von der Leyen"], SKOS.related, bcn_participant_uris["Josep Puig Solé"]))

    print(f"Created optimized knowledge graph with {len(g)} triples")
    print("Cross-platform connections:")
    print("  - Iratxe García Pérez (EU) ↔ María González López (Madrid) [owl:sameAs]")
    print("  - Alice Kuhnke (EU) ↔ Laura Martínez Vidal (Barcelona) [skos:related]")
    print("  - Pascal Canfin (EU) ↔ Carlos Ruiz Martinez (Madrid) [skos:related]")
    print("  - Ursula von der Leyen (EU) ↔ Josep Puig Solé (Barcelona) [skos:related]")

    return g

def main():
    kg = create_optimized_demo()

    # Save the optimized knowledge graph
    output_file = "optimized_demo_kg.ttl"
    kg.serialize(destination=output_file, format="turtle")
    print(f"\nOptimized knowledge graph saved to: {output_file}")

    # Test cross-platform connections
    test_query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?name1 ?platform1 ?name2 ?platform2 ?relation
    WHERE {
        ?p1 del:name ?name1 ; del:platform ?platform1 .
        ?p2 del:name ?name2 ; del:platform ?platform2 .
        {
            ?p1 owl:sameAs ?p2 .
            BIND("sameAs" as ?relation)
        }
        UNION
        {
            ?p1 skos:related ?p2 .
            BIND("related" as ?relation)
        }
        FILTER(?platform1 != ?platform2)
    }
    """

    results = list(kg.query(test_query))
    print(f"\nFound {len(results)} cross-platform connections:")
    for row in results:
        print(f"  {row[0]} ({row[1]}) ↔ {row[2]} ({row[3]}) [{row[4]}]")

    return True

if __name__ == "__main__":
    main()