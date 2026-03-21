#!/usr/bin/env python3
"""
Merge HYS data with main knowledge graph using streaming
Creates: deliberation_kg.ttl (unified knowledge graph)
"""

import shutil
import os

# Configuration
hys_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/hys_data.ttl'
main_kg_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg_complete.ttl'
output_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg.ttl'

def merge_files():
    """Merge files using simple concatenation"""

    print("Merging knowledge graphs...")
    print(f"  Base KG: {main_kg_file} ({os.path.getsize(main_kg_file)/(1024**2):.1f} MB)")
    print(f"  HYS data: {hys_file} ({os.path.getsize(hys_file)/(1024**2):.1f} MB)")

    # Copy main KG first
    print("\nCopying base knowledge graph...")
    shutil.copy2(main_kg_file, output_file)

    # Append HYS data (skip prefixes that are already in main KG)
    print("Appending HYS data (skipping duplicate prefixes)...")

    with open(hys_file, 'r', encoding='utf-8') as hys_in:
        with open(output_file, 'a', encoding='utf-8') as out:
            skip_prefixes = True
            lines_written = 0

            for line in hys_in:
                # Skip prefix declarations at the beginning
                if skip_prefixes:
                    if line.strip().startswith('@prefix') or line.strip().startswith('@base'):
                        continue
                    elif line.strip() == '':
                        continue
                    else:
                        skip_prefixes = False

                # Write data
                out.write(line)
                lines_written += 1

                if lines_written % 100000 == 0:
                    print(f"  {lines_written:,} lines appended...")

    output_size = os.path.getsize(output_file) / (1024**2)
    print(f"\n✓ Merge complete!")
    print(f"  Output: {output_file}")
    print(f"  Size: {output_size:.1f} MB")

    return output_file

if __name__ == '__main__':
    merge_files()
