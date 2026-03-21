#!/usr/bin/env python3
"""
Semantic Search Implementation for Deliberation Knowledge Graph
Uses sentence-transformers for multilingual semantic embeddings
"""

import numpy as np
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
from rdflib import Graph, Namespace
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

class SemanticSearchEngine:
    def __init__(self, kg_path: str, embeddings_path: str = "knowledge_graph/embeddings.pkl"):
        """Initialize semantic search engine"""
        self.kg_path = Path(kg_path)
        self.embeddings_path = Path(embeddings_path)

        # Load multilingual model (supports IT, ES, CA, EN)
        logger.info("Loading multilingual sentence transformer model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        self.kg = None
        self.contributions = []
        self.embeddings = None
        self.contribution_metadata = []

    def load_knowledge_graph(self):
        """Load knowledge graph"""
        logger.info(f"Loading knowledge graph from {self.kg_path}...")
        self.kg = Graph()
        self.kg.bind("del", DEL)
        self.kg.bind("rdfs", RDFS)
        self.kg.parse(self.kg_path, format="turtle")
        logger.info(f"Loaded {len(self.kg)} triples")

    def extract_contributions(self):
        """Extract all contributions with text"""
        logger.info("Extracting contributions...")

        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX deldata: <http://data.cogenta.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

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
            FILTER(STRLEN(?text) > 20)
        }
        """

        results = self.kg.query(query)

        for row in results:
            text = str(row.text).strip()
            if text and len(text) > 20:
                self.contributions.append(text)
                self.contribution_metadata.append({
                    'uri': str(row.contribution),
                    'text': text,
                    'process': str(row.process),
                    'process_name': str(row.processName) if row.processName else "Unknown Process"
                })

        logger.info(f"Extracted {len(self.contributions)} contributions")

    def generate_embeddings(self):
        """Generate embeddings for all contributions"""
        logger.info("Generating semantic embeddings...")

        # Generate embeddings in batches
        batch_size = 32
        all_embeddings = []

        for i in tqdm(range(0, len(self.contributions), batch_size)):
            batch = self.contributions[i:i+batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=False)
            all_embeddings.append(batch_embeddings)

        self.embeddings = np.vstack(all_embeddings)
        logger.info(f"Generated embeddings shape: {self.embeddings.shape}")

    def save_embeddings(self):
        """Save embeddings and metadata to disk"""
        logger.info(f"Saving embeddings to {self.embeddings_path}...")

        data = {
            'embeddings': self.embeddings,
            'metadata': self.contribution_metadata,
            'model_name': 'paraphrase-multilingual-MiniLM-L12-v2'
        }

        with open(self.embeddings_path, 'wb') as f:
            pickle.dump(data, f)

        logger.info("Embeddings saved successfully")

    def load_embeddings(self):
        """Load pre-computed embeddings"""
        logger.info(f"Loading embeddings from {self.embeddings_path}...")

        with open(self.embeddings_path, 'rb') as f:
            data = pickle.load(f)

        self.embeddings = data['embeddings']
        self.contribution_metadata = data['metadata']

        logger.info(f"Loaded {len(self.contribution_metadata)} embeddings")

    def search(self, query: str, top_k: int = 10):
        """Perform semantic search"""
        # Encode query
        query_embedding = self.model.encode([query])[0]

        # Calculate cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            result = self.contribution_metadata[idx].copy()
            result['similarity_score'] = float(similarities[idx])
            results.append(result)

        return results

    def build_index(self):
        """Build complete semantic search index"""
        self.load_knowledge_graph()
        self.extract_contributions()
        self.generate_embeddings()
        self.save_embeddings()
        logger.info("Semantic search index built successfully!")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Semantic Search for Deliberation KG")
    parser.add_argument('--kg-path', required=True, help='Path to knowledge graph TTL file')
    parser.add_argument('--embeddings-path', default='knowledge_graph/embeddings.pkl',
                       help='Path to save/load embeddings')
    parser.add_argument('--build', action='store_true', help='Build new index')
    parser.add_argument('--query', type=str, help='Search query')
    parser.add_argument('--top-k', type=int, default=10, help='Number of results')

    args = parser.parse_args()

    engine = SemanticSearchEngine(args.kg_path, args.embeddings_path)

    if args.build:
        engine.build_index()

    if args.query:
        if not Path(args.embeddings_path).exists():
            logger.error("Embeddings not found. Please run with --build first.")
            return

        engine.load_embeddings()
        results = engine.search(args.query, args.top_k)

        print(f"\n🔍 Semantic Search Results for: '{args.query}'\n")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['similarity_score']:.4f}")
            print(f"   Process: {result['process_name']}")
            print(f"   Text: {result['text'][:200]}...")
            print(f"   URI: {result['uri']}")


if __name__ == '__main__':
    main()
