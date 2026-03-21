#!/usr/bin/env python3
"""
Fix malformed HYS TTL file by removing orphaned publication blocks
"""

print("Fixing hys_data_10k.ttl...")

with open('knowledge_graph/hys_data_10k.ttl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
skip_until_next_statement = False
i = 0

while i < len(lines):
    line = lines[i]

    # Check if previous line ended a statement with '.'
    if i > 0 and fixed_lines and fixed_lines[-1].strip().endswith('.'):
        # Check if current line starts an orphaned publication list (8 spaces + <http...hys_publication)
        if line.startswith('        <http://data.cogenta.org/deliberation/hys_publication'):
            print(f"Line {i+1}: Found orphaned publication block, skipping...")
            # Skip this entire orphaned block until we find a proper statement
            skip_until_next_statement = True

    if skip_until_next_statement:
        # Skip lines until we find a line that starts a new proper RDF statement
        # (URI starting at column 0 or prefix declaration)
        if line.startswith('<http://') or line.startswith('@prefix') or line.strip() == '':
            skip_until_next_statement = False
            fixed_lines.append(line)
            print(f"Line {i+1}: Resuming at new statement")
        else:
            print(f"Line {i+1}: Skipping orphaned line")
    else:
        fixed_lines.append(line)

    i += 1

# Write fixed file
with open('knowledge_graph/hys_data_10k_fixed.ttl', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

import os
original_size = os.path.getsize('knowledge_graph/hys_data_10k.ttl') / (1024**2)
fixed_size = os.path.getsize('knowledge_graph/hys_data_10k_fixed.ttl') / (1024**2)

print(f"\n✓ Fixed file created: hys_data_10k_fixed.ttl")
print(f"  Original: {original_size:.2f} MB")
print(f"  Fixed: {fixed_size:.2f} MB")
print(f"  Removed: {original_size - fixed_size:.2f} MB")
