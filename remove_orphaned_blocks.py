#!/usr/bin/env python3
"""
Remove orphaned property list blocks from TTL file
These are blocks that start with spaces (no subject URI) after a blank line
"""

print("Removing orphaned blocks from hys_data_10k_clean.ttl...")

with open('knowledge_graph/hys_data_10k_clean.ttl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

output_lines = []
i = 0
removed_blocks = 0

while i < len(lines):
    # Check if this is an orphaned property list
    if i < len(lines) - 1:
        current = lines[i]
        next_line = lines[i + 1]

        # Check if next line is indented (4+ spaces) but not a proper subject URI at column 0
        is_indented = len(next_line) > 0 and next_line[0] == ' '
        is_not_subject = not next_line.strip().startswith('<http://data.cogenta.org/deliberation/hys_')

        # Case 1: Blank line followed by indented content (not a subject URI)
        if current.strip() == '' and is_indented and is_not_subject:
            # Found orphaned block - skip it
            output_lines.append(current)  # Keep the blank line
            i += 1

            # Skip all indented lines
            block_start = i
            while i < len(lines) and len(lines[i]) > 0 and lines[i][0] == ' ':
                i += 1

            removed_blocks += 1
            print(f"Removed orphaned block at line {block_start + 1}: {lines[block_start][:80].strip()}...")
            continue

        # Case 2: Statement ends with '.' and next line is indented (not a subject URI, not blank)
        if current.rstrip().endswith('.') and is_indented and is_not_subject and next_line.strip() != '':
            # Keep current line
            output_lines.append(current)
            i += 1

            # Skip orphaned block
            block_start = i
            while i < len(lines) and len(lines[i]) > 0 and lines[i][0] == ' ' and lines[i].strip() != '':
                i += 1

            removed_blocks += 1
            print(f"Removed orphaned block at line {block_start + 1}: {lines[block_start][:80].strip()}...")
            continue

    # Keep this line
    output_lines.append(lines[i])
    i += 1

print(f"\nRemoved {removed_blocks} orphaned blocks")

# Write output
with open('knowledge_graph/hys_data_10k_final.ttl', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

import os
original_size = os.path.getsize('knowledge_graph/hys_data_10k_clean.ttl') / (1024**2)
final_size = os.path.getsize('knowledge_graph/hys_data_10k_final.ttl') / (1024**2)

print(f"\n✓ Final file created: hys_data_10k_final.ttl")
print(f"  Original (clean): {original_size:.2f} MB")
print(f"  Final: {final_size:.2f} MB")
print(f"  Removed: {original_size - final_size:.2f} MB ({removed_blocks} blocks)")
