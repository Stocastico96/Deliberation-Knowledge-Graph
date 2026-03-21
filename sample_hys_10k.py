#!/usr/bin/env python3
"""
Sample 10K representative HYS contributions from the existing embeddings
Select from diverse initiatives to maintain topic diversity
"""

import pickle
import random
import json
from collections import defaultdict

print("Loading embeddings...")
with open('knowledge_graph/embeddings.pkl', 'rb') as f:
    data = pickle.load(f)

embeddings = data['embeddings']
metadata = data['metadata']

print(f"Total embeddings: {len(metadata):,}")

# Separate HYS and other contributions
hys_indices = []
other_indices = []

for i, m in enumerate(metadata):
    if 'hys_' in m.get('uri', ''):
        hys_indices.append(i)
    else:
        other_indices.append(i)

print(f"HYS contributions: {len(hys_indices):,}")
print(f"Other platforms: {len(other_indices):,}")

# Group HYS contributions by initiative to maintain diversity
hys_by_initiative = defaultdict(list)
for idx in hys_indices:
    process_uri = metadata[idx].get('process', '')
    # Extract initiative ID from URI like http://data.cogenta.org/deliberation/hys_initiative_12345
    if 'hys_initiative_' in process_uri:
        init_id = process_uri.split('hys_initiative_')[-1]
        hys_by_initiative[init_id].append(idx)

print(f"\nHYS contributions across {len(hys_by_initiative)} initiatives")

# Sample proportionally from each initiative
target_sample = 10000
sample_per_init = max(1, target_sample // len(hys_by_initiative))

print(f"Sampling ~{sample_per_init} contributions per initiative...")

sampled_hys_indices = []
for init_id, indices in sorted(hys_by_initiative.items()):
    # Sample proportionally, but ensure at least some from each initiative
    n_sample = min(sample_per_init, len(indices))
    sampled = random.sample(indices, n_sample)
    sampled_hys_indices.extend(sampled)

# If we're under 10K, add more randomly from larger initiatives
if len(sampled_hys_indices) < target_sample:
    remaining = target_sample - len(sampled_hys_indices)
    # Get initiatives sorted by size
    large_inits = sorted(hys_by_initiative.items(), key=lambda x: len(x[1]), reverse=True)

    for init_id, indices in large_inits:
        if remaining <= 0:
            break
        # Get indices not yet sampled
        available = [i for i in indices if i not in sampled_hys_indices]
        if available:
            n_add = min(remaining, len(available))
            sampled_hys_indices.extend(random.sample(available, n_add))
            remaining -= n_add

# Trim to exactly 10K if we overshot
sampled_hys_indices = sampled_hys_indices[:target_sample]

print(f"\nSampled {len(sampled_hys_indices):,} HYS contributions")

# Save the list of sampled URIs for later use
sampled_hys_uris = [metadata[i]['uri'] for i in sampled_hys_indices]
with open('/tmp/sampled_hys_uris.txt', 'w') as f:
    for uri in sampled_hys_uris:
        f.write(uri + '\n')

print(f"Saved URIs to /tmp/sampled_hys_uris.txt")

# Create new embeddings file with sampled HYS + all other platforms
print("\nCreating new embeddings file...")
combined_indices = other_indices + sampled_hys_indices

new_embeddings = embeddings[combined_indices]
new_metadata = [metadata[i] for i in combined_indices]

print(f"New total: {len(new_metadata):,} embeddings")
print(f"  - HYS: {len(sampled_hys_indices):,}")
print(f"  - Other: {len(other_indices):,}")

# Save new embeddings
with open('knowledge_graph/embeddings.pkl', 'wb') as f:
    pickle.dump({
        'embeddings': new_embeddings,
        'metadata': new_metadata
    }, f)

print("\n✓ Saved reduced embeddings to knowledge_graph/embeddings.pkl")

# Get list of initiative IDs that are represented in the sample
sampled_init_ids = set()
for idx in sampled_hys_indices:
    process_uri = metadata[idx].get('process', '')
    if 'hys_initiative_' in process_uri:
        init_id = int(process_uri.split('hys_initiative_')[-1])
        sampled_init_ids.add(init_id)

print(f"\nRepresented initiatives: {len(sampled_init_ids)}")

# Save initiative IDs for RDF filtering
with open('/tmp/sampled_hys_init_ids.txt', 'w') as f:
    for init_id in sorted(sampled_init_ids):
        f.write(str(init_id) + '\n')

print(f"Saved {len(sampled_init_ids)} initiative IDs to /tmp/sampled_hys_init_ids.txt")
