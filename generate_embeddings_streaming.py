#!/usr/bin/env python3
"""
Generate embeddings using streaming parser - memory efficient
Parses TTL file line by line without loading entire graph in memory
"""

import re
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StreamingTTLParser:
    def __init__(self, ttl_file):
        self.ttl_file = ttl_file
        self.contributions = {}  # uri -> text
        self.contribution_to_process = {}  # contribution_uri -> process_uri
        self.process_names = {}  # process_uri -> name

    def parse(self):
        """Parse TTL file line by line"""
        logger.info(f"Parsing {self.ttl_file}...")

        current_subject = None

        with open(self.ttl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(tqdm(f, desc="Reading TTL")):
                line = line.strip()

                # Skip comments and prefixes
                if not line or line.startswith('#') or line.startswith('@'):
                    continue

                # Extract subject if line starts with <
                if line.startswith('<'):
                    subject_match = re.match(r'<([^>]+)>', line)
                    if subject_match:
                        current_subject = subject_match.group(1)

                # Check for contribution type
                if 'Contribution>' in line and current_subject:
                    if current_subject not in self.contributions:
                        self.contributions[current_subject] = None

                # Extract text content (del:text or deldata:content)
                if current_subject and current_subject in self.contributions:
                    # Match: <predicate> "text"@lang .
                    content_match = re.search(r'<[^>]*(text|content)>\s+"([^"]+)"', line)
                    if content_match:
                        text = content_match.group(2)
                        # Unescape common escapes
                        text = text.replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"').replace('\\\\', '\\')
                        if len(text) > 20:
                            self.contributions[current_subject] = text

                # Extract hasContribution relationships
                if 'hasContribution' in line:
                    match = re.search(r'<([^>]+)>\s+<[^>]*hasContribution>\s+<([^>]+)>', line)
                    if match:
                        process_uri = match.group(1)
                        contrib_uri = match.group(2)
                        self.contribution_to_process[contrib_uri] = process_uri

                # Extract process names/titles
                if current_subject and ('del:name' in line or 'del:title' in line or 'dcterms:title' in line):
                    name_match = re.search(r'"([^"]+)"', line)
                    if name_match:
                        self.process_names[current_subject] = name_match.group(1)

        logger.info(f"Found {len([c for c in self.contributions.values() if c])} contributions with text")

    def get_contributions_with_metadata(self):
        """Return list of (text, metadata) tuples"""
        results = []

        for contrib_uri, text in self.contributions.items():
            if not text:
                continue

            process_uri = self.contribution_to_process.get(contrib_uri, "unknown")
            process_name = self.process_names.get(process_uri, "Unknown Process")

            results.append({
                'uri': contrib_uri,
                'text': text,
                'process': process_uri,
                'process_name': process_name
            })

        return results


def generate_embeddings(kg_file, output_file):
    """Generate embeddings using streaming approach"""

    # Parse TTL file
    parser = StreamingTTLParser(kg_file)
    parser.parse()

    # Get contributions
    contributions_data = parser.get_contributions_with_metadata()
    logger.info(f"Extracted {len(contributions_data)} contributions")

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
    kg_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg.ttl'
    output_file = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings.pkl'

    logger.info("=== Generating Embeddings (Streaming Mode) ===")
    generate_embeddings(kg_file, output_file)
