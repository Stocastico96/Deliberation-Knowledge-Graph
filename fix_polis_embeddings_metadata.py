#!/usr/bin/env python3
"""
Fix metadata for existing Pol.is embeddings
Updates process_name from 'url' to actual process title
"""

import pickle
from rdflib import Graph, Namespace
from pathlib import Path

# Paths
embeddings_file = "knowledge_graph/embeddings.pkl"
polis_kg_file = "knowledge_graph/polis_public_kg.ttl"
backup_file = "knowledge_graph/embeddings_backup_before_metadata_fix.pkl"

print("="*60)
print("FIXING POL.IS EMBEDDINGS METADATA")
print("="*60)

# Backup
print("\n1. Creating backup...")
import shutil
shutil.copy(embeddings_file, backup_file)
print(f"   ✓ Backup saved to {backup_file}")

# Load embeddings
print("\n2. Loading embeddings...")
with open(embeddings_file, 'rb') as f:
    data = pickle.load(f)

embeddings = data['embeddings']
metadata = data['metadata']
print(f"   ✓ Loaded {len(metadata):,} embeddings")

# Load Pol.is KG to get correct process names
print("\n3. Loading Pol.is knowledge graph...")
g = Graph()
g.parse(polis_kg_file, format='turtle')

DEL = Namespace('https://w3id.org/deliberation/ontology#')
RDFS = Namespace('http://www.w3.org/2000/01/rdf-schema#')

# Build process URI -> name mapping
query = """
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?process ?label
WHERE {
    ?process a del:DeliberationProcess .
    ?process rdfs:label ?label
}
"""

process_names = {}
for row in g.query(query):
    process_names[str(row.process)] = str(row.label)

print(f"   ✓ Loaded {len(process_names)} process names")

# Update metadata
print("\n4. Updating Pol.is embedding metadata...")
updated = 0
for m in metadata:
    if 'polis_' in m.get('uri', ''):
        process_uri = m.get('process')
        if process_uri and process_uri in process_names:
            old_name = m.get('process_name')
            new_name = process_names[process_uri]
            if old_name != new_name:
                m['process_name'] = new_name
                updated += 1

print(f"   ✓ Updated {updated:,} Pol.is embeddings")

# Save
print("\n5. Saving updated embeddings...")
updated_data = {
    'embeddings': embeddings,
    'metadata': metadata
}

with open(embeddings_file, 'wb') as f:
    pickle.dump(updated_data, f)

print(f"   ✓ Saved to {embeddings_file}")

print("\n" + "="*60)
print("METADATA FIX COMPLETE!")
print("="*60)
print(f"Updated {updated:,} Pol.is embeddings")
print(f"Backup: {backup_file}")
print("="*60 + "\n")
