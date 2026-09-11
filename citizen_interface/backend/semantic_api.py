#!/usr/bin/env python3
"""
Semantic Search API Integration
Provides semantic search endpoints for the citizen interface

Index format: {'embeddings': np.ndarray[N, 384], 'metadata': list[dict]}.
Metadata entries always carry uri/text/process/process_name and, for the
sources integrated with typed documents (DelibAI, CrowdLaw), also
type/platform/source/language/date/topic/document/is_ai_generated.
"""

import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

# Document types that are never returned unless the caller asks for them.
AI_GENERATED_TYPES = {"ai_feedback", "ai_rewrite"}
DEFAULT_TYPES = {"contribution", "seed_contribution", "legal_provision", "process", "topic"}


def _entry_type(m):
    t = m.get("type")
    if t:
        return t
    return "contribution"


def _entry_platform(m):
    return m.get("platform") or m.get("forum") or m.get("process_name", "")


class SemanticSearchAPI:
    def __init__(self, embeddings_path: str):
        """Initialize semantic search API"""
        self.embeddings_path = Path(embeddings_path)
        self.model = None
        self.embeddings = None
        self.metadata = None
        self.facets = {}

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
        # Pre-compute norms once (older entries may not be normalised)
        norms = np.linalg.norm(self.embeddings, axis=1)
        self._norms = np.where(norms == 0, 1e-9, norms)
        self._compute_facets()

        logger.info(f"Loaded {len(self.metadata)} embeddings for semantic search")
        return True

    def _compute_facets(self):
        """Distinct filter values present in the index (for the UI)."""
        types, langs, platforms, docs, years = {}, {}, {}, {}, {}
        for m in self.metadata:
            t = _entry_type(m)
            types[t] = types.get(t, 0) + 1
            if m.get("language"):
                langs[m["language"]] = langs.get(m["language"], 0) + 1
            p = _entry_platform(m)
            if p:
                platforms[p] = platforms.get(p, 0) + 1
            if m.get("document"):
                docs[m["document"]] = docs.get(m["document"], 0) + 1
            if m.get("date"):
                y = str(m["date"])[:4]
                years[y] = years.get(y, 0) + 1
        self.facets = {
            "content_types": dict(sorted(types.items())),
            "languages": dict(sorted(langs.items())),
            "platforms": dict(sorted(platforms.items())),
            "documents": dict(sorted(docs.items())),
            "years": dict(sorted(years.items())),
        }

    # ------------------------------------------------------------------
    def _scores(self, query: str):
        query_embedding = self.model.encode([query], normalize_embeddings=True)[0]
        return (self.embeddings @ query_embedding) / self._norms

    @staticmethod
    def _selective(filters):
        """True when a filter restricts results to a subset of the index."""
        keys = ("content_types", "languages", "topic", "document", "process", "date_from", "date_to", "platform")
        return any(filters.get(k) for k in keys)

    @staticmethod
    def _passes(m, filters):
        """Apply metadata filters. An active filter is strict: documents that do
        not record the filtered field (e.g. undated entries of older sources) are
        excluded, so a date or language filter never returns undated or
        unlabelled documents. AI-generated feedback is excluded unless requested."""
        t = _entry_type(m)
        if t in AI_GENERATED_TYPES and not filters.get("include_ai_feedback"):
            return False
        types = filters.get("content_types")
        if types and t not in types:
            return False
        plat = filters.get("platform")
        if plat and plat.lower() not in _entry_platform(m).lower():
            return False
        proc = filters.get("process")
        if proc and m.get("process") != proc:
            return False
        langs = filters.get("languages")
        if langs and m.get("language") not in langs:
            return False
        topic = filters.get("topic")
        if topic and topic.lower() not in (m.get("topic") or "").lower():
            return False
        doc = filters.get("document")
        if doc and doc.lower() not in (m.get("document") or "").lower():
            return False
        date_from, date_to = filters.get("date_from"), filters.get("date_to")
        if date_from or date_to:
            d = str(m.get("date") or "")[:10]
            if not d:
                return False
            if date_from and d < date_from:
                return False
            if date_to and d > date_to:
                return False
        return True

    @staticmethod
    def _result(m, score):
        r = {
            'uri': m['uri'],
            'text': m['text'],
            'process': m.get('process', ''),
            'process_name': m.get('process_name', ''),
            'platform': _entry_platform(m),
            'type': _entry_type(m),
            'source': m.get('source'),
            'language': m.get('language'),
            'date': m.get('date'),
            'topic': m.get('topic'),
            'topic_uri': m.get('topic_uri'),
            'document': m.get('document'),
            'document_uri': m.get('document_uri'),
            'provision': m.get('provision'),
            'provision_uri': m.get('provision_uri'),
            'kind': m.get('kind'),
            'condition': m.get('condition'),
            'stance': m.get('stance'),
            'is_ai_generated': bool(m.get('is_ai_generated')),
            'model': m.get('model'),
            'annotates': m.get('annotates'),
            'similarity_score': score,
            'relevance_score': score,
        }
        return {k: v for k, v in r.items() if v is not None}

    def search(self, query: str, top_k: int = 10, platform_filter: str = None, filters: dict = None):
        """Perform semantic search, returning one best-scoring document per process."""
        if self.model is None or self.embeddings is None:
            return []
        filters = dict(filters or {})
        if platform_filter:
            filters["platform"] = platform_filter

        similarities = self._scores(query)

        # Scan enough candidates to surface top_k *distinct processes* even on
        # imbalanced datasets (Decidim has 31k processes; CIP has 2 with 33k contribs).
        # Heuristic: scan at least 2000 contribution-level candidates.
        n_candidates = min(len(self.metadata), max(2000, top_k * 200))
        if self._selective(filters):
            # a selective filter may match nothing among the top candidates;
            # scan the whole ranked index instead (cheap: similarities are computed for all)
            n_candidates = len(self.metadata)
        top_indices = np.argsort(similarities)[::-1][:n_candidates]

        # Deduplicate: keep only the best-scoring document per process
        seen_processes = {}  # process_uri → result dict
        for idx in top_indices:
            m = self.metadata[idx]
            if not self._passes(m, filters):
                continue
            process_uri = m.get('process') or m['uri']
            score = float(similarities[idx])
            if process_uri not in seen_processes or score > seen_processes[process_uri]['similarity_score']:
                seen_processes[process_uri] = self._result(m, score)

            # Stop early once we have enough distinct processes
            if len(seen_processes) >= top_k * 10:
                break

        # Sort by score and return top_k
        results = sorted(seen_processes.values(), key=lambda r: r['similarity_score'], reverse=True)
        return results[:top_k]

    def search_items(self, query: str, top_k: int = 20, filters: dict = None):
        """Search individual documents (contributions, provisions, AI feedback...)
        without collapsing by process."""
        if self.model is None or self.embeddings is None:
            return []
        filters = dict(filters or {})
        similarities = self._scores(query)
        n_candidates = min(len(self.metadata), max(3000, top_k * 100))
        if self._selective(filters):
            n_candidates = len(self.metadata)
        top_indices = np.argsort(similarities)[::-1][:n_candidates]
        results = []
        for idx in top_indices:
            m = self.metadata[idx]
            if not self._passes(m, filters):
                continue
            results.append(self._result(m, float(similarities[idx])))
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


def search_semantic(query: str, top_k: int = 10, platform_filter: str = None, filters: dict = None):
    """Search using semantic similarity (one result per process)"""
    if semantic_search is None:
        return []
    return semantic_search.search(query, top_k, platform_filter, filters)


def search_semantic_items(query: str, top_k: int = 20, filters: dict = None):
    """Search individual documents"""
    if semantic_search is None:
        return []
    return semantic_search.search_items(query, top_k, filters)


def search_facets():
    if semantic_search is None:
        return {}
    return semantic_search.facets
