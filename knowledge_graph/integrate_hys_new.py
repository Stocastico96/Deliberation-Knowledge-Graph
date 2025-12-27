#!/usr/bin/env python3
"""
Integra i nuovi dati HYS (con ontologia corretta) nel KG principale
1. Rimuove vecchi dati HYS
2. Aggiunge nuovi dati HYS con Forum
"""

from rdflib import Graph, Namespace
import sys

print("=== Integrating new HYS data into main KG ===\n")

# Paths
kg_current = "deliberation_kg.ttl"
hys_new = "../data/EU_have_your_say/eu_have_your_say_FULL_DEL_ONTOLOGY.ttl"
kg_output = "deliberation_kg_with_hys_new.ttl"

# Load current KG
print("1. Loading current KG...")
g = Graph()
g.parse(kg_current, format='turtle')
print(f"   Loaded {len(g):,} triples")

# Find and remove old HYS data
print("\n2. Removing old HYS data...")
to_remove = set()

# Find all subjects with 'hys_' in URI
for s, p, o in g:
    s_str = str(s)
    if 'hys_' in s_str:
        to_remove.add(s)

print(f"   Found {len(to_remove):,} old HYS entities")

# Remove all triples involving HYS entities
removed_count = 0
for entity in to_remove:
    # Remove as subject
    for p, o in g.predicate_objects(entity):
        g.remove((entity, p, o))
        removed_count += 1
    # Remove as object
    for s, p in g.subject_predicates(entity):
        g.remove((s, p, entity))
        removed_count += 1

print(f"   Removed {removed_count:,} triples")
print(f"   KG now has {len(g):,} triples")

# Load new HYS data
print("\n3. Loading new HYS data with Forum ontology...")
g_hys = Graph()
g_hys.parse(hys_new, format='turtle')
print(f"   Loaded {len(g_hys):,} triples from new HYS")

# Merge
print("\n4. Merging into main KG...")
for s, p, o in g_hys:
    g.add((s, p, o))

print(f"   Final KG has {len(g):,} triples")

# Verify
print("\n5. Verification...")
DEL = Namespace("https://w3id.org/deliberation/ontology#")
BASE = Namespace("https://svagnoni.linkeddata.es/resource/")

processes = len([s for s in g.subjects(None, DEL.DeliberationProcess)])
contributions = len([s for s in g.subjects(None, DEL.Contribution)])
participants = len([s for s in g.subjects(None, DEL.Participant)])
forums = len([s for s in g.subjects(None, DEL.Forum)])

print(f"   Processes: {processes:,}")
print(f"   Contributions: {contributions:,}")
print(f"   Participants: {participants:,}")
print(f"   Forums: {forums:,}")

# Check HYS specifically
hys_processes = len([s for s in g.subjects(None, DEL.DeliberationProcess) if 'hys_initiative' in str(s)])
hys_contributions = len([s for s in g.subjects(None, DEL.Contribution) if 'hys_feedback' in str(s)])
hys_forum_links = len(list(g.triples((None, DEL.takesPlaceIn, BASE["forum_eu_have_your_say"]))))

print(f"\n   HYS specifically:")
print(f"   - Processes: {hys_processes:,}")
print(f"   - Contributions: {hys_contributions:,}")
print(f"   - Forum links: {hys_forum_links:,}")

# Save
print(f"\n6. Saving to {kg_output}...")
g.serialize(destination=kg_output, format='turtle')
print(f"   ✅ Done!")

print(f"\n✅ Integration complete!")
print(f"   Final KG: {len(g):,} triples")
print(f"\nNext steps:")
print(f"   1. mv {kg_output} {kg_current}")
print(f"   2. Create embeddings for new HYS data")
print(f"   3. Update server")
