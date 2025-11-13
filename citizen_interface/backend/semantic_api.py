#!/usr/bin/env python3
"""
Semantic Search API Integration
Provides semantic search endpoints for the citizen interface
"""

import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

class SemanticSearchAPI:
    def __init__(self, embeddings_path: str):
        """Initialize semantic search API"""
        self.embeddings_path = Path(embeddings_path)
        self.model = None
        self.embeddings = None
        self.metadata = None

    def load(self):
        """Load model and embeddings"""
        if not self.embeddings_path.exists():
            logger.warning(f"Embeddings not found at {self.embeddings_path}")
            return False

        logger.info("Loading semantic search model and embeddings...")

        # Load model
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # Load embeddings
        with open(self.embeddings_path, 'rb') as f:
            data = pickle.load(f)

        self.embeddings = data['embeddings']
        self.metadata = data['metadata']

        logger.info(f"Loaded {len(self.metadata)} embeddings for semantic search")
        return True

    def search(self, query: str, top_k: int = 10, platform_filter: str = None):
        """Perform semantic search"""
        if self.model is None or self.embeddings is None:
            return []

        # Encode query
        query_embedding = self.model.encode([query])[0]

        # Calculate cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top results (fetch more than needed for filtering)
        top_indices = np.argsort(similarities)[::-1][:top_k * 5]

        results = []
        for idx in top_indices:
            result = {
                'uri': self.metadata[idx]['uri'],
                'text': self.metadata[idx]['text'],
                'process': self.metadata[idx]['process'],
                'process_name': self.metadata[idx]['process_name'],
                'similarity_score': float(similarities[idx]),
                'relevance_score': float(similarities[idx])  # For compatibility
            }

            # Apply platform filter if specified
            if platform_filter:
                # Check if process_name or process uri contains platform name
                if platform_filter.lower() not in result['process_name'].lower():
                    continue

            results.append(result)

            if len(results) >= top_k:
                break

        return results

# Global instance
semantic_search = None

def init_semantic_search(embeddings_path: str):
    """Initialize semantic search globally"""
    global semantic_search
    semantic_search = SemanticSearchAPI(embeddings_path)
    return semantic_search.load()

def search_semantic(query: str, top_k: int = 10, platform_filter: str = None):
    """Search using semantic similarity"""
    if semantic_search is None:
        return []
    return semantic_search.search(query, top_k, platform_filter)
