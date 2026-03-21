#!/usr/bin/env python3
"""
Regenerate embeddings for the unified knowledge graph (with HYS data)
Memory-efficient version
"""

import sys
sys.path.insert(0, '/home/svagnoni/deliberation-knowledge-graph')

from semantic_search import SemanticSearchEngine
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    kg_path = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg.ttl'
    embeddings_path = '/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/embeddings.pkl'

    logger.info("=== Regenerating Embeddings for Unified Knowledge Graph ===")
    logger.info(f"KG file: {kg_path}")
    logger.info(f"Output: {embeddings_path}")

    # Initialize search engine
    search_engine = SemanticSearchEngine(
        kg_path=kg_path,
        embeddings_path=embeddings_path
    )

    # Load knowledge graph
    search_engine.load_knowledge_graph()

    # Extract contributions
    search_engine.extract_contributions()

    # Generate embeddings
    search_engine.generate_embeddings()

    # Save embeddings
    search_engine.save_embeddings()

    logger.info("✓ Embeddings regeneration complete!")

if __name__ == '__main__':
    main()
