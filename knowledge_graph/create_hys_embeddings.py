#!/usr/bin/env python3
"""
Crea embeddings per i nuovi dati HYS e li integra con gli embeddings esistenti
"""

import pickle
import sys
import numpy as np
from sentence_transformers import SentenceTransformer
from rdflib import Graph, Namespace, URIRef
from tqdm import tqdm

print("=== Creating embeddings for new HYS data ===\n")

# Load model
print("Loading embedding model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("✅ Model loaded\n")

# Load KG
print("Loading KG...")
g = Graph()
g.parse('deliberation_kg.ttl', format='turtle')
print(f"✅ Loaded {len(g):,} triples\n")

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
BASE = Namespace("https://svagnoni.linkeddata.es/resource/")

# Load existing embeddings
print("Loading existing embeddings...")
with open('embeddings.pkl', 'rb') as f:
    existing_embeddings = pickle.load(f)

existing_metadata = existing_embeddings['metadata']
existing_vectors = existing_embeddings['embeddings']
print(f"✅ Loaded {len(existing_metadata):,} existing embeddings\n")

# Find existing HYS URIs to skip
existing_hys_uris = set()
for meta in existing_metadata:
    uri = meta.get('uri', '')
    if 'hys_' in uri:
        existing_hys_uris.add(uri)

print(f"Found {len(existing_hys_uris):,} existing HYS embeddings to skip\n")

# Extract new HYS contributions
print("Extracting new HYS contributions...")
new_texts = []
new_metadata = []

for contrib_uri in tqdm(g.subjects(None, DEL.Contribution), desc="Scanning contributions"):
    contrib_str = str(contrib_uri)

    # Only process HYS that don't exist yet
    if 'hys_feedback' in contrib_str and contrib_str not in existing_hys_uris:
        # Get text
        text = None
        for s, p, o in g.triples((contrib_uri, DEL.text, None)):
            text = str(o)
            break

        if not text or not text.strip():
            continue

        # Get process info
        process_uri = None
        process_name = None
        for s, p, o in g.triples((None, DEL.hasContribution, contrib_uri)):
            process_uri = str(s)
            # Get process title
            for ps, pp, po in g.triples((s, DCTERMS.title, None)):
                process_name = str(po)
                break
            break

        if not process_uri or not process_name:
            continue

        # Get forum
        forum_name = None
        if process_uri:
            for ps, pp, po in g.triples((URIRef(process_uri), DEL.takesPlaceIn, None)):
                # Get forum name
                for fs, fp, fo in g.triples((po, DEL.name, None)):
                    forum_name = str(fo)
                    break
                break

        # Get timestamp
        timestamp = None
        for s, p, o in g.triples((contrib_uri, DEL.timestamp, None)):
            timestamp = str(o)
            break

        # Get participant info
        participant_country = None
        participant_type = None
        for s, p, o in g.triples((contrib_uri, DEL.madeBy, None)):
            # Get country
            for ps, pp, po in g.triples((o, DEL.country, None)):
                participant_country = str(po)
                break
            # Get type
            for ps, pp, po in g.triples((o, DEL.participantType, None)):
                participant_type = str(po)
                break
            break

        meta = {
            'uri': contrib_str,
            'text': text[:500],  # First 500 chars
            'process_uri': process_uri,
            'process_name': process_name,
            'type': 'contribution'
        }

        if forum_name:
            meta['forum'] = forum_name
        if timestamp:
            meta['timestamp'] = timestamp
        if participant_country:
            meta['country'] = participant_country
        if participant_type:
            meta['participant_type'] = participant_type

        new_texts.append(text)
        new_metadata.append(meta)

print(f"\n✅ Found {len(new_texts):,} new HYS contributions to embed\n")

if len(new_texts) == 0:
    print("No new HYS data to embed. Exiting.")
    sys.exit(0)

# Create embeddings
print("Creating embeddings...")
new_embeddings = model.encode(new_texts, show_progress_bar=True, convert_to_numpy=True)
print(f"✅ Created {len(new_embeddings):,} embeddings\n")

# Merge with existing
print("Merging with existing embeddings...")
import numpy as np

all_metadata = existing_metadata + new_metadata
all_embeddings = np.vstack([existing_vectors, new_embeddings])

print(f"✅ Total embeddings: {len(all_metadata):,}\n")

# Save
print("Saving updated embeddings...")
with open('embeddings.pkl', 'wb') as f:
    pickle.dump({
        'embeddings': all_embeddings,
        'metadata': all_metadata,
        'model': 'paraphrase-multilingual-MiniLM-L12-v2'
    }, f)

print(f"✅ Done!\n")
print(f"Summary:")
print(f"  Previous embeddings: {len(existing_metadata):,}")
print(f"  New HYS embeddings: {len(new_metadata):,}")
print(f"  Total embeddings: {len(all_metadata):,}")
