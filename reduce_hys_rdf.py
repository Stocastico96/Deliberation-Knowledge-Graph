#!/usr/bin/env python3
"""
Reduce hys_data.ttl to only include the sampled contributions
"""

import re

print("Loading sampled URIs...")
with open('/tmp/sampled_hys_uris.txt', 'r') as f:
    sampled_uris = set(line.strip() for line in f)

print(f"Sampled URIs: {len(sampled_uris):,}")

# Extract feedback IDs from URIs
sampled_feedback_ids = set()
for uri in sampled_uris:
    # URI format: http://data.cogenta.org/deliberation/hys_feedback_123456
    if 'hys_feedback_' in uri:
        fb_id = uri.split('hys_feedback_')[-1]
        sampled_feedback_ids.add(fb_id)

print(f"Sampled feedback IDs: {len(sampled_feedback_ids):,}")

# Load initiative IDs
with open('/tmp/sampled_hys_init_ids.txt', 'r') as f:
    sampled_init_ids = set(line.strip() for line in f)

print(f"Sampled initiatives: {len(sampled_init_ids)}")

print("\nFiltering hys_data.ttl...")

# We'll write a new filtered file
input_file = 'knowledge_graph/hys_data.ttl'
output_file = 'knowledge_graph/hys_data_10k.ttl'

with open(input_file, 'r', encoding='utf-8') as fin:
    with open(output_file, 'w', encoding='utf-8') as fout:
        # Copy prefixes and base
        in_header = True
        current_subject = None
        buffer = []
        include_current = False

        for line in fin:
            stripped = line.strip()

            # Copy prefixes
            if stripped.startswith('@prefix') or stripped.startswith('@base'):
                fout.write(line)
                continue

            # End of header
            if stripped == '' and in_header:
                fout.write(line)
                in_header = False
                continue

            if in_header:
                continue

            # Check if this is a new subject (starts with <http...)
            if stripped.startswith('<http'):
                # Flush previous subject if included
                if include_current and buffer:
                    fout.writelines(buffer)

                # Start new subject
                buffer = [line]
                current_subject = stripped.split()[0].strip('<>')

                # Decide if we include this subject
                if 'hys_feedback_' in current_subject:
                    fb_id = current_subject.split('hys_feedback_')[-1]
                    include_current = fb_id in sampled_feedback_ids
                elif 'hys_initiative_' in current_subject:
                    init_id = current_subject.split('hys_initiative_')[-1]
                    include_current = init_id in sampled_init_ids
                elif 'hys_publication_' in current_subject:
                    # Include publications for sampled initiatives
                    # We'll be conservative and include all (they're lightweight)
                    include_current = True
                else:
                    include_current = False
            else:
                # Continuation of current subject
                buffer.append(line)

        # Flush last subject
        if include_current and buffer:
            fout.writelines(buffer)

print(f"\n✓ Created reduced RDF file: {output_file}")

# Get file sizes
import os
original_size = os.path.getsize(input_file) / (1024**2)
reduced_size = os.path.getsize(output_file) / (1024**2)

print(f"\nFile sizes:")
print(f"  Original: {original_size:.1f} MB")
print(f"  Reduced:  {reduced_size:.1f} MB")
print(f"  Reduction: {100 * (1 - reduced_size/original_size):.1f}%")
