#!/usr/bin/env python3
"""
Step 1b: Unified BERTopic model across phases.
Pools B + C texts (and A if available) into a single corpus,
fits ONE model so topics become genuinely shared nodes in the KG.
Each document retains its phase label (A/B/C).

This is the prerequisite for true topological graph metrics in step 04b.
The phase-stratified models from step 01 are kept for DDI components.
"""

import json
import pickle
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import CountVectorizer


def _build_eu_stopwords() -> list:
    import nltk
    nltk.download("stopwords", quiet=True)
    from nltk.corpus import stopwords
    langs = ["english", "german", "french", "italian", "spanish", "dutch",
             "portuguese", "swedish", "danish", "finnish", "norwegian",
             "romanian", "hungarian", "greek", "slovene"]
    words = set()
    for lang in langs:
        try:
            words.update(stopwords.words(lang))
        except OSError:
            pass
    return list(words)


_EU_STOPWORDS = _build_eu_stopwords()

DATA_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset_v2")
OUT_DIR  = Path("/home/svagnoni/deliberation-knowledge-graph/data/unified_topic_models_v2")

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

CASES = ["case_1_covid", "case_2_climate_target", "case_3_pesticides"]

MIN_TOPIC_SIZE = {
    "case_1_covid":      15,
    "case_2_climate_target":        8,   # small corpus
    "case_3_pesticides": 20,
}


def load_texts(case_dir: Path) -> list[dict]:
    """Load all texts from all available phases, returning list of {id, text, phase}."""
    items = []

    hys_path = case_dir / "hys_feedback.json"
    with open(hys_path) as f:
        hys = json.load(f)
    for i, item in enumerate(hys.get("feedback", [])):
        if item.get("text") and len(item["text"].strip()) > 30:
            items.append({"id": str(item.get("id", f"B_{i}")), "text": item["text"], "phase": "B"})

    for phase, fname in [("A", "ep_phase_a.json"), ("C", "ep_phase_c.json")]:
        with open(case_dir / fname) as f:
            speeches = json.load(f)
        for i, item in enumerate(speeches):
            if item.get("text") and len(item["text"].strip()) > 50:
                items.append({"id": f"{phase}_{i}", "text": item["text"], "phase": phase})

    return items


def run_unified_bertopic(items: list, min_topic_size: int, embedding_model):
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN

    texts = [it["text"] for it in items]
    n = len(texts)
    print(f"    Total texts: {n}")

    vectorizer = CountVectorizer(
        stop_words=list(set(_EU_STOPWORDS)),
        min_df=2,
        ngram_range=(1, 2),
    )
    umap_model = UMAP(
        n_neighbors=min(15, n - 1),
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_topic_size,
        min_samples=max(1, min_topic_size // 2),
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer,
        top_n_words=10,
        verbose=True,
    )

    print("    Encoding...")
    embeddings = embedding_model.encode(texts, show_progress_bar=True, batch_size=64)
    print("    Fitting BERTopic...")
    topic_ids, probs = model.fit_transform(texts, embeddings=embeddings)

    return model, topic_ids, probs, embeddings


def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    case_dir = DATA_DIR / case_id
    out_dir  = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    from sentence_transformers import SentenceTransformer
    emb_model = SentenceTransformer(EMBEDDING_MODEL)

    items = load_texts(case_dir)
    phase_counts = {}
    for phase in ["A", "B", "C"]:
        phase_counts[phase] = sum(1 for it in items if it["phase"] == phase)
    print(f"  Phase counts: {phase_counts}")

    n_total = len(items)
    base_ts = MIN_TOPIC_SIZE[case_id]
    if n_total < 300:   min_ts = 5
    elif n_total < 600: min_ts = max(8, base_ts // 2)
    else:               min_ts = base_ts
    print(f"  min_topic_size: {min_ts} (base={base_ts}, n={n_total})")
    model, topic_ids, probs, embeddings = run_unified_bertopic(items, min_ts, emb_model)

    n_topics = len(set(t for t in topic_ids if t != -1))
    n_outlier = sum(1 for t in topic_ids if t == -1)
    print(f"  → {n_topics} unified topics, {n_outlier} outliers")

    # Save assignments with phase labels
    assignments = []
    for item, tid, prob in zip(items, topic_ids, (probs if probs is not None else [None]*len(topic_ids))):
        assignments.append({
            "id":    item["id"],
            "phase": item["phase"],
            "topic": int(tid),
            "prob":  float(prob) if prob is not None else None,
        })

    with open(out_dir / "unified_assignments.json", "w") as f:
        json.dump(assignments, f, indent=2)

    # Topic info
    topic_info = {}
    from collections import Counter, defaultdict
    phase_by_topic = defaultdict(list)
    for a in assignments:
        if a["topic"] != -1:
            phase_by_topic[str(a["topic"])].append(a["phase"])

    for tid in set(t for t in topic_ids if t != -1):
        words = [w for w, _ in model.get_topic(tid)]
        counts = Counter(phase_by_topic[str(tid)])
        topic_info[str(tid)] = {
            "label":      "_".join(words[:4]),
            "words":      words,
            "count_A":    counts.get("A", 0),
            "count_B":    counts.get("B", 0),
            "count_C":    counts.get("C", 0),
            "total":      sum(counts.values()),
            "is_bridging_BC": counts.get("B", 0) > 0 and counts.get("C", 0) > 0,
        }

    with open(out_dir / "unified_topics.json", "w") as f:
        json.dump(topic_info, f, ensure_ascii=False, indent=2)

    np.save(out_dir / "unified_embeddings.npy", embeddings)
    with open(out_dir / "unified_model.pkl", "wb") as f:
        pickle.dump(model, f)

    summary = {
        "n_topics":   n_topics,
        "n_outliers": n_outlier,
        "phase_counts": phase_counts,
        "bridging_BC": sum(1 for v in topic_info.values() if v["is_bridging_BC"]),
    }
    with open(out_dir / "unified_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  Bridging B-C topics: {summary['bridging_BC']} / {n_topics}")
    print(f"  Saved to {out_dir}")
    return summary


if __name__ == "__main__":
    import sys
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_cases = sys.argv[1:] if len(sys.argv) > 1 else CASES
    for case_id in target_cases:
        process_case(case_id)
