#!/usr/bin/env python3
"""
Generate embeddings - memory efficient version
Extracts texts first, then generates embeddings in batches
"""

import sys
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from rdflib import Graph, Namespace
from tqdm import tqdm
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
DELDATA = Namespace("http://data.cogenta.org/ontology/")

def extract_contributions_texts():
    """Extract contribution texts from RDF"""

    kg_path = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg.ttl'

    logger.info(f"Loading knowledge graph from {kg_path}...")
    g = Graph()
    g.parse(kg_path, format='turtle')
    logger.info(f"Loaded {len(g):,} triples")

    logger.info("Extracting contribution texts...")

    query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX deldata: <http://data.cogenta.org/ontology/>

    SELECT DISTINCT ?contribution ?text ?process ?processName
    WHERE {
        ?contribution a del:Contribution .
        {
            ?contribution del:text ?text .
        } UNION {
            ?contribution deldata:content ?text .
        }
        ?process del:hasContribution ?contribution .
        OPTIONAL { ?process del:name ?processName }
        OPTIONAL { ?process del:title ?processName }
        OPTIONAL { ?process <http://purl.org/dc/terms/title> ?processName }
        FILTER(STRLEN(?text) > 20)
    }
    """

    results = g.query(query)

    contributions_data = []
    for row in tqdm(results, desc="Processing contributions"):
        text = str(row.text).strip()
        if text and len(text) > 20:
            contributions_data.append({
                'uri': str(row.contribution),
                'text': text,
                'process': str(row.process),
                'process_name': str(row.processName) if row.processName else "Unknown Process"
            })

    logger.info(f"Extracted {len(contributions_data):,} contributions")

    # Free memory
    del g

    return contributions_data


def generate_embeddings():
    """Generate embeddings"""

    output_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings.pkl'

    logger.info("=== Generating Embeddings (Efficient Mode) ===")

    # Extract texts
    contributions_data = extract_contributions_texts()

    if len(contributions_data) == 0:
        logger.error("No contributions found!")
        return

    # Load model
    logger.info("Loading sentence transformer model...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    # Generate embeddings in batches
    logger.info("Generating embeddings...")
    batch_size = 32
    texts = [c['text'] for c in contributions_data]

    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Encoding"):
        batch = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.append(batch_embeddings)

    embeddings = np.vstack(all_embeddings)
    logger.info(f"Generated embeddings shape: {embeddings.shape}")

    # Save
    logger.info(f"Saving to {output_file}...")
    data = {
        'embeddings': embeddings,
        'metadata': contributions_data,
        'model_name': 'paraphrase-multilingual-MiniLM-L12-v2'
    }

    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    logger.info("✓ Embeddings saved successfully!")
    logger.info(f"  Total contributions: {len(contributions_data):,}")
    logger.info(f"  Embeddings shape: {embeddings.shape}")


if __name__ == '__main__':
    generate_embeddings()
