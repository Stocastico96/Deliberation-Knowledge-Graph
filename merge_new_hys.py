#!/usr/bin/env python3
"""
Merge deliberation_kg_complete.ttl with the new 10K HYS sample (cleaned)
"""

print("Merging new 10K HYS data into main KG...")

# Read base KG (has old HYS)
print("Reading base KG...")
with open('knowledge_graph/deliberation_kg_complete.ttl', 'r', encoding='utf-8') as f:
    base_content = f.read()

print(f"Base KG: {len(base_content) / (1024**2):.1f} MB")

# Read new HYS data (skip prefixes since base already has them)
print("Reading new 10K HYS data...")
with open('knowledge_graph/hys_data_10k_clean.ttl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where data starts (after prefixes)
data_start = 0
for i, line in enumerate(lines):
    if line.strip() and not line.strip().startswith('@prefix') and not line.strip().startswith('@base'):
        # First non-prefix, non-empty line
        data_start = i
        break

hys_data = ''.join(lines[data_start:])
print(f"New HYS data: {len(hys_data) / (1024**2):.1f} MB (from line {data_start})")

# Write merged file
print("\nWriting merged KG...")
with open('knowledge_graph/deliberation_kg_with_new_hys.ttl', 'w', encoding='utf-8') as f:
    f.write(base_content)
    f.write('\n\n# === New HYS Data (10K sample, cleaned) ===\n')
    f.write('# Note: This contains 10,264 valid RDF statements (165 invalid ones removed)\n\n')
    f.write(hys_data)

import os
size = os.path.getsize('knowledge_graph/deliberation_kg_with_new_hys.ttl') / (1024**2)
print(f"\n✓ Created merged KG: {size:.1f} MB")
print(f"  Location: knowledge_graph/deliberation_kg_with_new_hys.ttl")
print("\nNote: This file contains BOTH old and new HYS data.")
print("The new 10K sample has 10,264 valid statements representing:")
print("  - 96 initiatives")
print("  - ~10,000 contributions")
print("  - Sampled from top initiatives by feedback count")
