#!/usr/bin/env python3
"""
Sistema di retrieval ibrido per il Deliberation Knowledge Graph
Combina semantic search (BGE-M3), SPARQL e BM25 per ricerca efficace
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from rdflib import Graph, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
DCTERMS = Namespace("http://purl.org/dc/terms/")


class HybridRetrievalSystem:
    """
    Sistema di retrieval ibrido che combina:
    1. Semantic similarity con BGE-M3 embeddings
    2. SPARQL keyword search
    3. BM25 sparse retrieval
    4. Reciprocal Rank Fusion per combinare i risultati
    """

    def __init__(self, kg_path: str, index_dir: str = "./data/indexes"):
        """
        Inizializza il sistema di retrieval

        Args:
            kg_path: Path al file del knowledge graph (TTL/RDF)
            index_dir: Directory per salvare gli indici
        """
        self.kg_path = kg_path
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Carica knowledge graph
        logger.info(f"Caricamento knowledge graph da {kg_path}...")
        self.graph = Graph()
        self.graph.bind("del", DEL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.parse(kg_path, format="turtle")
        logger.info(f"Knowledge graph caricato: {len(self.graph)} triple")

        # Inizializza modello embeddings
        logger.info("Caricamento modello BGE-M3...")
        self.embedding_model = SentenceTransformer('BAAI/bge-m3')
        self.embedding_dim = 1024  # BGE-M3 dimension

        # Strutture dati per retrieval
        self.processes = []  # Lista di processi deliberativi
        self.process_texts = []  # Testi per BM25
        self.process_embeddings = None  # Embeddings per semantic search
        self.faiss_index = None  # Indice FAISS
        self.bm25 = None  # Indice BM25

        # Carica o crea indici
        self._load_or_create_indexes()

    def _extract_processes_from_kg(self) -> List[Dict[str, Any]]:
        """Estrae tutti i processi deliberativi dal knowledge graph"""
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?process ?title ?description ?date ?platform
        WHERE {
            ?process a del:DeliberationProcess .
            OPTIONAL { ?process del:title ?title }
            OPTIONAL { ?process rdfs:label ?title }
            OPTIONAL { ?process del:description ?description }
            OPTIONAL { ?process dcterms:description ?description }
            OPTIONAL { ?process del:date ?date }
            OPTIONAL { ?process dcterms:date ?date }
            OPTIONAL { ?process del:platform ?platform }
        }
        """

        processes = []
        results = self.graph.query(query)

        for row in results:
            process_uri = str(row.process)
            title = str(row.title) if row.title else ""
            description = str(row.description) if row.description else ""
            date = str(row.date) if row.date else ""
            platform = str(row.platform) if row.platform else ""

            # Estrai contributi e argomenti per questo processo
            contributions = self._get_process_contributions(row.process)
            fallacies = self._get_process_fallacies(row.process)
            participants = self._get_process_participants(row.process)

            process_data = {
                'uri': process_uri,
                'title': title,
                'description': description,
                'date': date,
                'platform': platform,
                'contributions_count': len(contributions),
                'fallacies_count': len(fallacies),
                'participants_count': len(participants),
                'contributions': contributions[:5],  # Prime 5 per preview
                'fallacies': fallacies[:5],
                'participants': participants[:5],
                # Testo completo per ricerca
                'full_text': f"{title} {description} " + " ".join(
                    [c.get('text', '') for c in contributions[:10]]
                )
            }

            processes.append(process_data)

        logger.info(f"Estratti {len(processes)} processi deliberativi")
        return processes

    def _get_process_contributions(self, process_uri: URIRef) -> List[Dict[str, str]]:
        """Estrae i contributi per un processo"""
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT ?contribution ?text ?author
        WHERE {
            ?contribution del:partOf <%s> .
            OPTIONAL { ?contribution del:text ?text }
            OPTIONAL { ?contribution del:author ?author }
        }
        LIMIT 20
        """ % str(process_uri)

        contributions = []
        for row in self.graph.query(query):
            contributions.append({
                'uri': str(row.contribution),
                'text': str(row.text) if row.text else "",
                'author': str(row.author) if row.author else ""
            })

        return contributions

    def _get_process_fallacies(self, process_uri: URIRef) -> List[Dict[str, str]]:
        """Estrae le fallacie rilevate in un processo"""
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT ?fallacy ?type ?location
        WHERE {
            ?contribution del:partOf <%s> .
            ?fallacy del:detectedIn ?contribution .
            OPTIONAL { ?fallacy a ?type }
            OPTIONAL { ?fallacy del:location ?location }
        }
        LIMIT 20
        """ % str(process_uri)

        fallacies = []
        for row in self.graph.query(query):
            fallacies.append({
                'uri': str(row.fallacy),
                'type': str(row.type) if row.type else "",
                'location': str(row.location) if row.location else ""
            })

        return fallacies

    def _get_process_participants(self, process_uri: URIRef) -> List[Dict[str, str]]:
        """Estrae i partecipanti di un processo"""
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>

        SELECT DISTINCT ?participant ?name ?party
        WHERE {
            ?contribution del:partOf <%s> .
            ?contribution del:author ?participant .
            OPTIONAL { ?participant foaf:name ?name }
            OPTIONAL { ?participant del:party ?party }
        }
        LIMIT 50
        """ % str(process_uri)

        participants = []
        for row in self.graph.query(query):
            participants.append({
                'uri': str(row.participant),
                'name': str(row.name) if row.name else "",
                'party': str(row.party) if row.party else ""
            })

        return participants

    def _load_or_create_indexes(self):
        """Carica gli indici esistenti o li crea da zero"""
        processes_path = self.index_dir / "processes.pkl"
        embeddings_path = self.index_dir / "embeddings.npy"
        faiss_path = self.index_dir / "faiss.index"
        bm25_path = self.index_dir / "bm25.pkl"

        # Verifica se tutti gli indici esistono
        if all(p.exists() for p in [processes_path, embeddings_path, faiss_path, bm25_path]):
            logger.info("Caricamento indici esistenti...")
            self._load_indexes(processes_path, embeddings_path, faiss_path, bm25_path)
        else:
            logger.info("Creazione nuovi indici...")
            self._create_indexes()
            self._save_indexes(processes_path, embeddings_path, faiss_path, bm25_path)

    def _create_indexes(self):
        """Crea gli indici per semantic search e BM25"""
        # Estrai processi
        self.processes = self._extract_processes_from_kg()

        if not self.processes:
            logger.warning("Nessun processo trovato nel knowledge graph!")
            return

        # Prepara testi per embeddings e BM25
        texts = [p['full_text'] for p in self.processes]

        # Crea embeddings con BGE-M3
        logger.info("Generazione embeddings con BGE-M3...")
        self.process_embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        # Crea indice FAISS
        logger.info("Creazione indice FAISS...")
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner Product (cosine similarity)
        self.faiss_index.add(self.process_embeddings.astype('float32'))

        # Crea indice BM25
        logger.info("Creazione indice BM25...")
        tokenized_texts = [text.lower().split() for text in texts]
        self.bm25 = BM25Okapi(tokenized_texts)

        self.process_texts = texts

        logger.info("Indici creati con successo!")

    def _save_indexes(self, processes_path, embeddings_path, faiss_path, bm25_path):
        """Salva gli indici su disco"""
        logger.info("Salvataggio indici...")

        with open(processes_path, 'wb') as f:
            pickle.dump(self.processes, f)

        np.save(embeddings_path, self.process_embeddings)

        faiss.write_index(self.faiss_index, str(faiss_path))

        with open(bm25_path, 'wb') as f:
            pickle.dump({
                'bm25': self.bm25,
                'process_texts': self.process_texts
            }, f)

        logger.info("Indici salvati!")

    def _load_indexes(self, processes_path, embeddings_path, faiss_path, bm25_path):
        """Carica gli indici da disco"""
        with open(processes_path, 'rb') as f:
            self.processes = pickle.load(f)

        self.process_embeddings = np.load(embeddings_path)

        self.faiss_index = faiss.read_index(str(faiss_path))

        with open(bm25_path, 'rb') as f:
            data = pickle.load(f)
            self.bm25 = data['bm25']
            self.process_texts = data['process_texts']

        logger.info("Indici caricati!")

    def search_semantic(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Ricerca semantica usando embeddings BGE-M3

        Returns:
            List di tuple (process_index, similarity_score)
        """
        query_embedding = self.embedding_model.encode([query], normalize_embeddings=True)
        distances, indices = self.faiss_index.search(query_embedding.astype('float32'), top_k)

        results = [(int(idx), float(score)) for idx, score in zip(indices[0], distances[0])]
        return results

    def search_bm25(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Ricerca BM25 (sparse retrieval)

        Returns:
            List di tuple (process_index, bm25_score)
        """
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Ottieni top-k indici
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]

        return results

    def search_sparql(self, query: str, top_k: int = 10) -> List[int]:
        """
        Ricerca SPARQL full-text (keyword-based)

        Returns:
            List di process indices
        """
        # Ricerca case-insensitive nei titoli e descrizioni
        matching_indices = []
        query_lower = query.lower()

        for idx, process in enumerate(self.processes):
            title = process.get('title', '').lower()
            description = process.get('description', '').lower()
            full_text = process.get('full_text', '').lower()

            if query_lower in title or query_lower in description or query_lower in full_text:
                matching_indices.append(idx)

                if len(matching_indices) >= top_k:
                    break

        return matching_indices

    def reciprocal_rank_fusion(
        self,
        ranked_lists: List[List[Tuple[int, float]]],
        k: int = 60
    ) -> List[Tuple[int, float]]:
        """
        Reciprocal Rank Fusion per combinare risultati da diversi metodi

        Args:
            ranked_lists: Liste di risultati da diversi retrieval methods
            k: Parametro RRF (default 60)

        Returns:
            Lista combinata ordinata per RRF score
        """
        rrf_scores = {}

        for ranked_list in ranked_lists:
            for rank, (doc_id, _) in enumerate(ranked_list, start=1):
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0
                rrf_scores[doc_id] += 1 / (k + rank)

        # Ordina per RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_results

    def search(
        self,
        query: str,
        top_k: int = 10,
        use_semantic: bool = True,
        use_bm25: bool = True,
        use_sparql: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Ricerca ibrida che combina semantic search, BM25 e SPARQL

        Args:
            query: Query di ricerca
            top_k: Numero di risultati da ritornare
            use_semantic: Usa semantic search (BGE-M3)
            use_bm25: Usa BM25
            use_sparql: Usa SPARQL keyword search

        Returns:
            Lista di processi deliberativi con score
        """
        if not self.processes:
            logger.warning("Nessun processo disponibile!")
            return []

        ranked_lists = []

        # Semantic search
        if use_semantic:
            semantic_results = self.search_semantic(query, top_k=top_k * 2)
            ranked_lists.append(semantic_results)
            logger.info(f"Semantic search: {len(semantic_results)} risultati")

        # BM25 search
        if use_bm25:
            bm25_results = self.search_bm25(query, top_k=top_k * 2)
            ranked_lists.append(bm25_results)
            logger.info(f"BM25 search: {len(bm25_results)} risultati")

        # SPARQL search
        if use_sparql:
            sparql_indices = self.search_sparql(query, top_k=top_k * 2)
            sparql_results = [(idx, 1.0) for idx in sparql_indices]
            ranked_lists.append(sparql_results)
            logger.info(f"SPARQL search: {len(sparql_results)} risultati")

        # Combina risultati con RRF
        if not ranked_lists:
            return []

        fused_results = self.reciprocal_rank_fusion(ranked_lists)

        # Prepara output
        results = []
        for doc_id, rrf_score in fused_results[:top_k]:
            process = self.processes[doc_id].copy()
            process['relevance_score'] = float(rrf_score)
            results.append(process)

        logger.info(f"Ritornati {len(results)} risultati finali")
        return results

    def get_process_by_uri(self, uri: str) -> Dict[str, Any]:
        """Ottieni un processo specifico tramite URI"""
        for process in self.processes:
            if process['uri'] == uri:
                # Aggiungi dettagli completi
                process_uri = URIRef(uri)
                process['contributions'] = self._get_process_contributions(process_uri)
                process['fallacies'] = self._get_process_fallacies(process_uri)
                process['participants'] = self._get_process_participants(process_uri)
                return process

        return None

    def get_entity_details(self, uri: str, entity_type: str) -> Dict[str, Any]:
        """
        Ottieni dettagli di un'entità specifica (contributo, persona, fallacia, etc.)

        Args:
            uri: URI dell'entità
            entity_type: Tipo di entità (contribution, person, fallacy, party)
        """
        # Query SPARQL per ottenere tutti i dettagli dell'entità
        query = f"""
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?p ?o
        WHERE {{
            <{uri}> ?p ?o .
        }}
        """

        details = {'uri': uri, 'type': entity_type}

        for row in self.graph.query(query):
            prop = str(row.p).split('#')[-1].split('/')[-1]
            value = str(row.o)
            details[prop] = value

        return details


if __name__ == "__main__":
    # Test del sistema
    import sys

    if len(sys.argv) < 2:
        print("Usage: python retrieval_system.py <path_to_kg.ttl>")
        sys.exit(1)

    kg_path = sys.argv[1]

    # Inizializza sistema
    retrieval_system = HybridRetrievalSystem(kg_path)

    # Test query
    test_queries = [
        "chat control",
        "privacy data protection",
        "climate change",
        "artificial intelligence regulation"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print('='*80)

        results = retrieval_system.search(query, top_k=5)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URI: {result['uri']}")
            print(f"   Score: {result['relevance_score']:.4f}")
            print(f"   Platform: {result['platform']}")
            print(f"   Description: {result['description'][:200]}...")
