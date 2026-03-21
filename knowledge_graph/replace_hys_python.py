#!/usr/bin/env python3
"""
Replace HYS data using Python - load in chunks to avoid memory issues
"""

from rdflib import Graph, Namespace
from rdflib.namespace import RDF
import sys

DEL = Namespace("https://w3id.org/deliberation/ontology#")

print("="*70)
print("REPLACE HYS DATA - PYTHON VERSION")
print("="*70)

# Files
kg_current = "deliberation_kg.ttl.backup_surgical_20251217_191412"  # Use clean backup
hys_correct = "../data/EU_have_your_say/eu_have_your_say_10k_ONTOLOGY_CORRECT.ttl"
output = "deliberation_kg.ttl"

print(f"\n1. Loading current KG from {kg_current}...")
g = Graph()

try:
    g.parse(kg_current, format='turtle')
    print(f"   ✓ Loaded {len(g):,} triples")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    print("\n   Trying to use the backup WITH publications instead...")
    kg_current = "deliberation_kg.ttl.with_publications_old"
    g = Graph()
    g.parse(kg_current, format='turtle')
    print(f"   ✓ Loaded {len(g):,} triples from backup")

# Remove HYS
print("\n2. Removing HYS data...")
to_remove = set()

# Find all HYS subjects
for s, p, o in g:
    s_str = str(s)
    if 'hys_' in s_str:
        to_remove.add(s)

print(f"   Found {len(to_remove)} HYS subjects to remove")

# Remove all triples with HYS subjects
removed = 0
for subj in to_remove:
    triples = list(g.triples((subj, None, None)))
    for triple in triples:
        g.remove(triple)
        removed += 1

# Also remove triples where HYS is object
for s, p, o in list(g):
    if 'hys_' in str(o):
        g.remove((s, p, o))
        removed += 1

print(f"   ✓ Removed {removed:,} triples")
print(f"   After removal: {len(g):,} triples")

# Load correct HYS
print(f"\n3. Loading correct HYS from {hys_correct}...")
try:
    g.parse(hys_correct, format='turtle')
    print(f"   ✓ Total after merge: {len(g):,} triples")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Verify
print("\n4. Verification...")
pubs = list(g.triples((None, RDF.type, DEL.Publication)))
has_pub = list(g.triples((None, DEL.hasPublication, None)))
has_contrib = list(g.triples((None, DEL.hasContribution, None)))

print(f"   Publications: {len(pubs)} (should be 0)")
print(f"   hasPublication links: {len(has_pub)} (should be 0)")
print(f"   hasContribution links: {len(has_contrib):,}")

if len(pubs) > 0 or len(has_pub) > 0:
    print(f"\n   ⚠ WARNING: Still has Publication references!")
    print("   First 3 Publications:")
    for i, (s, p, o) in enumerate(pubs[:3]):
        print(f"     {i+1}. {s}")

# Save
print(f"\n5. Saving to {output}...")
try:
    g.serialize(destination=output, format='turtle')
    print(f"   ✓ Saved {len(g):,} triples!")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

print("\n" + "="*70)
if len(pubs) == 0 and len(has_pub) == 0:
    print("✅ SUCCESS! KG is now ontology-compliant")
else:
    print("⚠ PARTIAL SUCCESS - some Publication references remain")
print("="*70)
