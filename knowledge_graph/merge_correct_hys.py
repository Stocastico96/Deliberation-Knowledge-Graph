#!/usr/bin/env python3
"""
Merge non-HYS base KG with ontology-correct HYS data
"""

from rdflib import Graph
import sys

print("="*70)
print("MERGE ONTOLOGY-CORRECT HYS WITH BASE KG")
print("="*70)

base_kg = "deliberation_kg_base.ttl"
hys_data = "hys_data.ttl"
output = "deliberation_kg.ttl"

# Create new graph
print("\nCreating merged graph...")
g = Graph()

# Load base (non-HYS)
print(f"\n1. Loading base KG from {base_kg}...")
try:
    g.parse(base_kg, format='turtle')
    print(f"   ✓ Loaded {len(g):,} triples")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Load HYS
print(f"\n2. Loading HYS data from {hys_data}...")
try:
    g.parse(hys_data, format='turtle')
    print(f"   ✓ Total after merge: {len(g):,} triples")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Save
print(f"\n3. Saving to {output}...")
try:
    g.serialize(destination=output, format='turtle')
    print(f"   ✓ Saved!")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✅ MERGE COMPLETE!")
print(f"   Output: {output}")
print(f"   Total triples: {len(g):,}")
print("="*70)
