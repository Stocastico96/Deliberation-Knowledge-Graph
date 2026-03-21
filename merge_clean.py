#!/usr/bin/env python3
"""
Merge base KG with sampled HYS data, removing duplicate prefixes
"""

print("Merging KG files...")

# Read base KG
with open('knowledge_graph/deliberation_kg_all_platforms.ttl.backup', 'r', encoding='utf-8') as f:
    base_content = f.read()

# Read HYS data (skip prefixes)
with open('knowledge_graph/hys_data_10k.ttl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where data starts (after prefixes)
data_start = 0
for i, line in enumerate(lines):
    if line.strip() and not line.strip().startswith('@prefix') and not line.strip().startswith('@base'):
        # First non-prefix, non-empty line
        data_start = i
        break

hys_data = ''.join(lines[data_start:])

# Write merged file
with open('knowledge_graph/deliberation_kg.ttl', 'w', encoding='utf-8') as f:
    f.write(base_content)
    f.write('\n\n# === HYS Data (10K sample) ===\n\n')
    f.write(hys_data)

import os
size = os.path.getsize('knowledge_graph/deliberation_kg.ttl') / (1024**2)
print(f"✓ Created merged KG: {size:.1f} MB")
