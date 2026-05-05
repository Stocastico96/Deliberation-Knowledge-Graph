#!/usr/bin/env python3
"""
Step 2: Topic alignment between phases.
Computes cosine similarity between BERTopic topic centroids across phases.
Classifies each B-topic as: aligned (θ≥0.65), partial (0.40≤θ<0.65), or gap (<0.40).
Also computes the Topic Jaccard Index (J_BC) as a graph-structural metric.
"""

import json
import numpy as np
from pathlib import Path
from itertools import product

# ── Config ─────────────────────────────────────────────────────────────────────

TOPIC_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/topic_models_v2")
OUT_DIR   = Path("/home/svagnoni/deliberation-knowledge-graph/data/alignment_v2")

CASES = ["case_1_covid", "case_2_climate_target", "case_3_pesticides"]

ALIGNED_THRESHOLD = 0.65
PARTIAL_THRESHOLD = 0.40

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_phase_data(case_dir: Path, phase: str):
    """Load topic info and embeddings for a phase."""
    topic_path = case_dir / f"phase_{phase}_topics.json"
    assign_path = case_dir / f"phase_{phase}_assignments.json"
    emb_path    = case_dir / f"phase_{phase}_embeddings.npy"

    if not topic_path.exists() or not emb_path.exists():
        return None, None, None

    with open(topic_path) as f:
        topics = json.load(f)
    with open(assign_path) as f:
        assignments = json.load(f)

    embeddings = np.load(emb_path)
    return topics, assignments, embeddings


def compute_topic_centroids(topics: dict, assignments: list, embeddings: np.ndarray) -> dict:
    """Compute mean embedding (centroid) for each topic."""
    topic_indices = {}
    for i, item in enumerate(assignments):
        tid = str(item["topic"])
        if tid == "-1":
            continue
        topic_indices.setdefault(tid, []).append(i)

    centroids = {}
    for tid, indices in topic_indices.items():
        if tid in topics:
            centroids[tid] = embeddings[indices].mean(axis=0)
    return centroids


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_n = a / (np.linalg.norm(a) + 1e-9)
    b_n = b / (np.linalg.norm(b) + 1e-9)
    return float(np.dot(a_n, b_n))


def build_similarity_matrix(centroids_b: dict, centroids_other: dict) -> dict:
    """
    Compute pairwise cosine similarity between B topics and another phase's topics.
    Returns: {b_topic_id: {other_topic_id: sim, ...}, ...}
    """
    matrix = {}
    for bid, bvec in centroids_b.items():
        matrix[bid] = {}
        for oid, ovec in centroids_other.items():
            matrix[bid][oid] = cosine_similarity(bvec, ovec)
    return matrix


def classify_alignment(sim_matrix: dict) -> dict:
    """
    For each B topic, find its best-matching other-phase topic and classify.
    Returns: {b_topic_id: {best_match, best_sim, label}}
    """
    result = {}
    for bid, sims in sim_matrix.items():
        if not sims:
            result[bid] = {"best_match": None, "best_sim": 0.0, "label": "gap"}
            continue
        best_match = max(sims, key=sims.get)
        best_sim   = sims[best_match]
        if best_sim >= ALIGNED_THRESHOLD:
            label = "aligned"
        elif best_sim >= PARTIAL_THRESHOLD:
            label = "partial"
        else:
            label = "gap"
        result[bid] = {"best_match": best_match, "best_sim": round(best_sim, 4), "label": label}
    return result


def avg_max_cosine(centroids_p: dict, centroids_q: dict) -> float:
    """Mean over p in P of: max cosine similarity to any q in Q."""
    if not centroids_p or not centroids_q:
        return 0.0
    q_vecs = list(centroids_q.values())
    sims = [max(cosine_similarity(pvec, qvec) for qvec in q_vecs)
            for pvec in centroids_p.values()]
    return float(np.mean(sims))


def avg_max_cosine_sym(centroids_b: dict, centroids_x: dict) -> float:
    """Symmetric avg-max cosine: scale-invariant d_topic input.
    Not biased by topic count asymmetry unlike Jaccard."""
    s_bx = avg_max_cosine(centroids_b, centroids_x)
    s_xb = avg_max_cosine(centroids_x, centroids_b)
    return (s_bx + s_xb) / 2


# ── Main ───────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    case_dir = TOPIC_DIR / case_id
    out_dir  = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load all phases
    phase_data = {}
    for phase in ["A", "B", "C"]:
        topics, assignments, embeddings = load_phase_data(case_dir, phase)
        if topics is not None:
            centroids = compute_topic_centroids(topics, assignments, embeddings)
            phase_data[phase] = {"topics": topics, "assignments": assignments,
                                 "embeddings": embeddings, "centroids": centroids}
            print(f"  Phase {phase}: {len(centroids)} topic centroids")
        else:
            print(f"  Phase {phase}: no data")

    results = {}

    # B ↔ A alignment (if A exists)
    if "B" in phase_data and "A" in phase_data:
        cb = phase_data["B"]["centroids"]
        ca = phase_data["A"]["centroids"]
        sim_ba = build_similarity_matrix(cb, ca)
        align_ba = classify_alignment(sim_ba)
        sim_ab = build_similarity_matrix(ca, cb)
        align_ab = classify_alignment(sim_ab)
        nb, na = len(cb), len(ca)
        n_aligned_b = sum(1 for v in align_ba.values() if v["label"] == "aligned")
        n_aligned_a = sum(1 for v in align_ab.values() if v["label"] == "aligned")
        n_intersection = min(n_aligned_b, n_aligned_a)
        n_union = nb + na - n_intersection
        jaccard_ba = round(n_intersection / n_union, 4) if n_union > 0 else 0.0
        amc_ba = round(avg_max_cosine_sym(cb, ca), 4)
        results["B_vs_A"] = {
            "alignment": align_ba,
            "summary": {
                "aligned": n_aligned_b,
                "partial":  sum(1 for v in align_ba.values() if v["label"] == "partial"),
                "gap":      sum(1 for v in align_ba.values() if v["label"] == "gap"),
            },
            "jaccard_index":    jaccard_ba,
            "avg_max_cosine":   amc_ba,
        }
        print(f"  B vs A: {results['B_vs_A']['summary']}, Jaccard={jaccard_ba}, AvgMaxCos={amc_ba}")

    # B ↔ C alignment
    if "B" in phase_data and "C" in phase_data:
        cb = phase_data["B"]["centroids"]
        cc = phase_data["C"]["centroids"]
        sim_bc = build_similarity_matrix(cb, cc)
        align_bc = classify_alignment(sim_bc)
        sim_cb = build_similarity_matrix(cc, cb)
        align_cb = classify_alignment(sim_cb)
        nb, nc = len(cb), len(cc)
        n_aligned_b = sum(1 for v in align_bc.values() if v["label"] == "aligned")
        n_aligned_c = sum(1 for v in align_cb.values() if v["label"] == "aligned")
        n_intersection = min(n_aligned_b, n_aligned_c)
        n_union = nb + nc - n_intersection
        jaccard = round(n_intersection / n_union, 4) if n_union > 0 else 0.0
        amc_bc = round(avg_max_cosine_sym(cb, cc), 4)

        results["B_vs_C"] = {
            "alignment": align_bc,
            "summary": {
                "aligned": n_aligned_b,
                "partial":  sum(1 for v in align_bc.values() if v["label"] == "partial"),
                "gap":      sum(1 for v in align_bc.values() if v["label"] == "gap"),
            },
            "jaccard_index":   jaccard,
            "avg_max_cosine":  amc_bc,
        }
        print(f"  B vs C: {results['B_vs_C']['summary']}, Jaccard={jaccard}, AvgMaxCos={amc_bc}")

    # A ↔ C alignment (change over time, EP side)
    if "A" in phase_data and "C" in phase_data:
        sim_ac = build_similarity_matrix(phase_data["A"]["centroids"], phase_data["C"]["centroids"])
        align_ac = classify_alignment(sim_ac)
        results["A_vs_C"] = {
            "alignment": align_ac,
            "summary": {
                "aligned": sum(1 for v in align_ac.values() if v["label"] == "aligned"),
                "partial":  sum(1 for v in align_ac.values() if v["label"] == "partial"),
                "gap":      sum(1 for v in align_ac.values() if v["label"] == "gap"),
            },
        }
        print(f"  A vs C: {results['A_vs_C']['summary']}")

    with open(out_dir / "alignment_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"  Saved to {out_dir}")
    return results


if __name__ == "__main__":
    import sys
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_cases = sys.argv[1:] if len(sys.argv) > 1 else CASES
    for case_id in target_cases:
        process_case(case_id)
