#!/usr/bin/env python3
"""
Update embeddings with new Pol.is public data
Creates embeddings for new Pol.is contributions and merges with existing embeddings
"""

import pickle
import numpy as np
from rdflib import Graph, Namespace
from sentence_transformers import SentenceTransformer
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RESOURCE = Namespace("https://svagnoni.linkeddata.es/resource/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

def main():
    print("="*60)
    print("UPDATING EMBEDDINGS WITH POL.IS DATA")
    print("="*60)

    # Paths
    kg_file = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/polis_public_kg.ttl"
    embeddings_file = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings.pkl"
    output_file = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings.pkl"
    backup_file = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings_backup_before_polis.pkl"

    # Load existing embeddings
    print(f"\n1. Loading existing embeddings...")
    with open(embeddings_file, 'rb') as f:
        existing_data = pickle.load(f)

    existing_embeddings = existing_data['embeddings']
    existing_metadata = existing_data['metadata']
    print(f"   ✓ Loaded {len(existing_metadata)} existing embeddings")

    # Backup
    print(f"\n2. Creating backup...")
    import shutil
    shutil.copy(embeddings_file, backup_file)
    print(f"   ✓ Backup saved to {backup_file}")

    # Load Pol.is KG
    print(f"\n3. Loading Pol.is knowledge graph...")
    g = Graph()
    g.parse(kg_file, format='turtle')
    print(f"   ✓ Loaded {len(g):,} triples")

    # Extract Pol.is contributions
    print(f"\n4. Extracting Pol.is contributions...")
    query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT ?contribution ?text ?process ?processLabel
    WHERE {
        ?contribution a del:Contribution ;
                     del:text ?text ;
                     del:isPartOf ?process .
        OPTIONAL { ?process rdfs:label ?processLabel }
    }
    """

    results = g.query(query)

    new_contributions = []
    for row in results:
        new_contributions.append({
            'uri': str(row.contribution),
            'text': str(row.text),
            'process': str(row.process),
            'process_name': str(row.processLabel) if row.processLabel else "Untitled",
            'platform': 'Pol.is'
        })

    print(f"   ✓ Found {len(new_contributions)} Pol.is contributions")

    # Load sentence transformer model
    print(f"\n5. Loading sentence transformer model...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print(f"   ✓ Model loaded")

    # Create embeddings for new contributions
    print(f"\n6. Creating embeddings for Pol.is contributions...")
    new_texts = [c['text'] for c in new_contributions]

    batch_size = 32
    new_embeddings = []

    for i in range(0, len(new_texts), batch_size):
        batch = new_texts[i:i+batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=False)
        new_embeddings.extend(batch_embeddings)

        if (i // batch_size + 1) % 10 == 0:
            print(f"   • Processed {i+len(batch)}/{len(new_texts)} contributions...")

    new_embeddings = np.array(new_embeddings)
    print(f"   ✓ Created {len(new_embeddings)} new embeddings")

    # Merge embeddings
    print(f"\n7. Merging embeddings...")
    merged_embeddings = np.vstack([existing_embeddings, new_embeddings])
    merged_metadata = existing_metadata + new_contributions

    print(f"   ✓ Total embeddings: {len(merged_metadata):,}")
    print(f"     • Existing: {len(existing_metadata):,}")
    print(f"     • New (Pol.is): {len(new_contributions):,}")

    # Save merged embeddings
    print(f"\n8. Saving merged embeddings...")
    merged_data = {
        'embeddings': merged_embeddings,
        'metadata': merged_metadata
    }

    with open(output_file, 'wb') as f:
        pickle.dump(merged_data, f)

    print(f"   ✓ Saved to {output_file}")

    print("\n" + "="*60)
    print("EMBEDDINGS UPDATE COMPLETE!")
    print("="*60)
    print(f"Total embeddings: {len(merged_metadata):,}")
    print(f"Backup: {backup_file}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
