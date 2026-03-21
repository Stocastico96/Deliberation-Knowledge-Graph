#!/usr/bin/env python3
"""
Generate embeddings ONLY for HYS contributions directly from SQLite
Much faster than SPARQL query on huge RDF graph
Then merge with existing embeddings
"""

import sqlite3
import json
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    db_path = '/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db'
    embeddings_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings.pkl'

    logger.info("=== Generating HYS Embeddings Directly from SQLite ===")

    # Load top 100 initiative IDs
    with open('/tmp/top100_init_ids.txt', 'r') as f:
        init_ids_list = [int(line.strip()) for line in f]

    logger.info(f"Processing top {len(init_ids_list)} initiatives")

    # Connect to database
    conn = sqlite3.connect(db_path)

    # Get feedbacks with text
    logger.info("Extracting feedbacks...")
    contributions_data = []

    for init_id in tqdm(init_ids_list, desc="Initiatives"):
        # Get initiative data
        init_row = conn.execute('SELECT data FROM initiatives WHERE id = ?', (init_id,)).fetchone()
        if not init_row:
            continue

        init_data = json.loads(init_row[0])
        init_title = init_data.get('shortTitle', f'Initiative {init_id}')[:100]

        # Get publication IDs for this initiative
        pub_ids = [p['id'] for p in init_data.get('publications', []) if p.get('id')]

        if not pub_ids:
            continue

        # Get feedbacks for these publications
        placeholders = ','.join('?' * len(pub_ids))
        feedbacks = conn.execute(
            f'SELECT id, publication_id, data FROM feedback WHERE publication_id IN ({placeholders})',
            pub_ids
        ).fetchall()

        for fb_id, pub_id, fb_data_str in feedbacks:
            fb_data = json.loads(fb_data_str)
            text = fb_data.get('feedback', '').strip()

            if text and len(text) > 20:
                contributions_data.append({
                    'uri': f'http://data.cogenta.org/deliberation/hys_feedback_{fb_id}',
                    'text': text,
                    'process': f'http://data.cogenta.org/deliberation/hys_initiative_{init_id}',
                    'process_name': init_title
                })

    conn.close()

    logger.info(f"Extracted {len(contributions_data):,} HYS contributions")

    if len(contributions_data) == 0:
        logger.error("No contributions found!")
        return

    # Load existing embeddings
    logger.info(f"Loading existing embeddings from {embeddings_file}...")
    with open(embeddings_file, 'rb') as f:
        existing_data = pickle.load(f)

    logger.info(f"Existing embeddings: {len(existing_data['metadata']):,}")

    # Load model
    logger.info("Loading sentence transformer model...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    # Generate embeddings for HYS contributions
    logger.info("Generating embeddings for HYS contributions...")
    batch_size = 32
    texts = [c['text'] for c in contributions_data]

    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Encoding HYS"):
        batch = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        all_embeddings.append(batch_embeddings)

    hys_embeddings = np.vstack(all_embeddings)
    logger.info(f"Generated HYS embeddings shape: {hys_embeddings.shape}")

    # Merge with existing embeddings
    logger.info("Merging with existing embeddings...")
    combined_embeddings = np.vstack([existing_data['embeddings'], hys_embeddings])
    combined_metadata = existing_data['metadata'] + contributions_data

    logger.info(f"Combined embeddings shape: {combined_embeddings.shape}")
    logger.info(f"Combined metadata count: {len(combined_metadata):,}")

    # Save combined embeddings
    logger.info(f"Saving to {embeddings_file}...")
    data = {
        'embeddings': combined_embeddings,
        'metadata': combined_metadata,
        'model_name': 'paraphrase-multilingual-MiniLM-L12-v2'
    }

    with open(embeddings_file, 'wb') as f:
        pickle.dump(data, f)

    logger.info("✓ Embeddings generation complete!")
    logger.info(f"  Existing contributions: {len(existing_data['metadata']):,}")
    logger.info(f"  New HYS contributions: {len(contributions_data):,}")
    logger.info(f"  Total contributions: {len(combined_metadata):,}")
    logger.info(f"  Embeddings shape: {combined_embeddings.shape}")

if __name__ == '__main__':
    main()
