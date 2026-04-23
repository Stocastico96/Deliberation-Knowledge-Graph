#!/usr/bin/env python3
"""
Step 4: Compute Deliberative Distance Index (DDI), ΔDDI, and graph metrics.

DDI(B, X) = 0.35·d_topic + 0.30·d_salience + 0.25·d_stance + 0.10·d_diversity

Where:
  d_topic    = 1 - J_BC  (Topic Jaccard Index from alignment step)
  d_salience = JSD of topic-weight distributions between phases
  d_stance   = JSD of (support, neutral, oppose) distributions between B and X
  d_diversity= 1 - H(actor_types) / log(K)  (Shannon entropy of user_types in B)

ΔDDI = DDI(B, A) − DDI(B, C)  positive → convergence after consultation
       Only computed when Phase A is available.

Graph metrics (KG-structural):
  J_BC:  Topic Jaccard Index (computed in step 2, re-used here)
  BC_max: max betweenness centrality of shared topic nodes
  DCC:   Deliberative Coupling Coefficient
"""

import json
import math
import numpy as np
from pathlib import Path
from collections import Counter

# ── Config ─────────────────────────────────────────────────────────────────────

ALIGNMENT_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/alignment_v2")
STANCE_DIR    = Path("/home/svagnoni/deliberation-knowledge-graph/data/stance_v2")
TOPIC_DIR     = Path("/home/svagnoni/deliberation-knowledge-graph/data/topic_models_v2")
DATASET_DIR   = Path("/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset_v2")
OUT_DIR       = Path("/home/svagnoni/deliberation-knowledge-graph/data/ddi_v2")

CASES = ["case_1_covid", "case_2_dsa", "case_3_pesticides"]

# Weight configurations for sensitivity analysis
WEIGHT_CONFIGS = {
    "uniform":      {"d_topic": 0.25, "d_salience": 0.25, "d_stance": 0.25, "d_diversity": 0.25},
    "base":         {"d_topic": 0.35, "d_salience": 0.30, "d_stance": 0.25, "d_diversity": 0.10},
    "topic_heavy":  {"d_topic": 0.50, "d_salience": 0.25, "d_stance": 0.20, "d_diversity": 0.05},
    "stance_heavy": {"d_topic": 0.25, "d_salience": 0.25, "d_stance": 0.40, "d_diversity": 0.10},
}

# ── Metrics ────────────────────────────────────────────────────────────────────

def jsd(p: dict, q: dict) -> float:
    """Jensen-Shannon Divergence between two probability distributions."""
    keys = sorted(set(p) | set(q))
    pp = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    qq = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    pp /= (pp.sum() + 1e-12)
    qq /= (qq.sum() + 1e-12)
    m = 0.5 * (pp + qq)
    def kl(a, b):
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log(a[mask] / b[mask])))
    return 0.5 * kl(pp, m) + 0.5 * kl(qq, m)


def shannon_entropy(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((v / total) * math.log(v / total) for v in counts.values() if v > 0)


def d_topic_from_jaccard(jaccard: float) -> float:
    return 1.0 - jaccard


def d_salience(topics_b: dict, topics_x: dict) -> float:
    """JSD of topic-weight (count-normalized) distributions."""
    def weight_dist(topics):
        counts = {k: v["count"] for k, v in topics.items()
                  if k != "_outlier_count" and isinstance(v, dict)}
        total = sum(counts.values()) + 1e-12
        return {k: v / total for k, v in counts.items()}
    wb = weight_dist(topics_b)
    wx = weight_dist(topics_x)
    return jsd(wb, wx)


def d_stance_metric(dist_b: dict, dist_x: dict) -> float:
    """JSD between B and X stance distributions."""
    keys = ["support", "neutral", "oppose"]
    pb = {k: dist_b.get(k, 0.0) for k in keys}
    px = {k: dist_x.get(k, 0.0) for k in keys}
    return jsd(pb, px)


def d_diversity_metric(hys_feedback: list) -> float:
    """1 - H(user_types) / log(K)  where K = number of distinct actor types."""
    user_types = Counter(f.get("user_type", "ANONYMOUS") for f in hys_feedback)
    K = len(user_types)
    if K <= 1:
        return 0.0
    H = shannon_entropy(user_types)
    H_max = math.log(K)
    return 1.0 - H / H_max


def ddi(d_t, d_s, d_sal, d_div, weights: dict) -> float:
    return (weights["d_topic"]     * d_t
          + weights["d_salience"]  * d_sal
          + weights["d_stance"]    * d_s
          + weights["d_diversity"] * d_div)


# ── Graph metrics ──────────────────────────────────────────────────────────────

def compute_graph_metrics(alignment: dict, topics_b: dict, topics_c: dict,
                           assign_b: list, assign_c: list) -> dict:
    """
    Compute KG-structural metrics:
      J_BC: Topic Jaccard Index (already in alignment results)
      BC_max: max betweenness of shared topic nodes (approximated via degree)
      DCC: Deliberative Coupling Coefficient
    """
    j_bc = alignment.get("B_vs_C", {}).get("jaccard_index", 0.0)

    # Shared topic IDs (B topics that align with C above threshold)
    aligned_b_ids = set()
    for bid, info in alignment.get("B_vs_C", {}).get("alignment", {}).items():
        if info["label"] == "aligned":
            aligned_b_ids.add(bid)

    nb = len(assign_b)
    nc = len(assign_c)

    if nb == 0 or nc == 0 or not aligned_b_ids:
        return {"J_BC": j_bc, "BC_max": 0.0, "DCC": 0.0}

    # DCC: fraction of (b, c) pairs sharing at least one aligned topic
    # b_docs with aligned topics
    b_aligned_docs = sum(1 for item in assign_b
                         if str(item.get("topic", -1)) in aligned_b_ids)
    # approximate DCC (exact would need the full bipartite graph)
    dcc = (b_aligned_docs / nb) * (len(aligned_b_ids) / max(1, len(topics_b) - 1))

    # BC_max: proxy — aligned topics with most documents (high degree = high betweenness proxy)
    topic_degrees = Counter(str(item.get("topic", -1)) for item in assign_b)
    bc_max = max(
        (topic_degrees.get(tid, 0) / nb for tid in aligned_b_ids),
        default=0.0
    )

    return {
        "J_BC":   round(j_bc, 4),
        "BC_max": round(bc_max, 4),
        "DCC":    round(dcc, 4),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    out_dir = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load alignment results
    align_path = ALIGNMENT_DIR / case_id / "alignment_results.json"
    if not align_path.exists():
        print(f"  [SKIP] No alignment results found — run step 2 first")
        return None
    with open(align_path) as f:
        alignment = json.load(f)

    # Load stance summaries
    def load_stance_dist(phase):
        p = STANCE_DIR / case_id / "stance_summary.json"
        if not p.exists():
            return None
        with open(p) as f:
            s = json.load(f)
        return s.get(phase, {}).get("distribution")

    # Load topic summaries
    def load_topics(phase):
        p = TOPIC_DIR / case_id / f"phase_{phase}_topics.json"
        if not p.exists():
            return {}
        with open(p) as f:
            return json.load(f)

    def load_assignments(phase):
        p = TOPIC_DIR / case_id / f"phase_{phase}_assignments.json"
        if not p.exists():
            return []
        with open(p) as f:
            return json.load(f)

    # Load HYS feedback for diversity
    with open(DATASET_DIR / case_id / "hys_feedback.json") as f:
        hys_data = json.load(f)
    hys_feedback = hys_data.get("feedback", [])

    topics_b = load_topics("B")
    topics_a = load_topics("A")
    topics_c = load_topics("C")
    assign_b = load_assignments("B")
    assign_a = load_assignments("A")
    assign_c = load_assignments("C")

    # Component metrics
    d_div = d_diversity_metric(hys_feedback)

    has_a = bool(topics_a) and bool(align_path.exists()) and "B_vs_A" in alignment
    has_c = bool(topics_c) and "B_vs_C" in alignment

    results = {"components": {}, "ddi": {}, "delta_ddi": None, "graph_metrics": {}}

    if has_c:
        j_bc   = alignment["B_vs_C"].get("jaccard_index", 0.0)
        d_t_c  = d_topic_from_jaccard(j_bc)
        d_sal_c = d_salience(topics_b, topics_c) if topics_b and topics_c else 0.5

        stance_b = load_stance_dist("B")
        stance_c = load_stance_dist("C")
        d_s_c = d_stance_metric(stance_b, stance_c) if stance_b and stance_c else 0.5

        results["components"]["B_vs_C"] = {
            "d_topic":     round(d_t_c, 4),
            "d_salience":  round(d_sal_c, 4),
            "d_stance":    round(d_s_c, 4),
            "d_diversity": round(d_div, 4),
        }

        ddi_bc = {}
        for wname, weights in WEIGHT_CONFIGS.items():
            ddi_bc[wname] = round(ddi(d_t_c, d_s_c, d_sal_c, d_div, weights), 4)
        results["ddi"]["B_vs_C"] = ddi_bc
        print(f"  DDI(B,C) = {ddi_bc}")

        # Graph metrics
        gm = compute_graph_metrics(alignment, topics_b, topics_c, assign_b, assign_c)
        results["graph_metrics"] = gm
        print(f"  Graph metrics: {gm}")

    if has_a:
        j_ba   = alignment["B_vs_A"].get("jaccard_index",
                   1.0 - d_topic_from_jaccard(
                       alignment["B_vs_A"]["summary"].get("aligned", 0) /
                       max(1, len(alignment["B_vs_A"]["alignment"]))
                   ))
        d_t_a  = d_topic_from_jaccard(j_ba)
        d_sal_a = d_salience(topics_b, topics_a) if topics_b and topics_a else 0.5

        stance_a = load_stance_dist("A")
        stance_b = load_stance_dist("B")
        d_s_a = d_stance_metric(stance_b, stance_a) if stance_b and stance_a else 0.5

        results["components"]["B_vs_A"] = {
            "d_topic":     round(d_t_a, 4),
            "d_salience":  round(d_sal_a, 4),
            "d_stance":    round(d_s_a, 4),
            "d_diversity": round(d_div, 4),
        }

        ddi_ba = {}
        for wname, weights in WEIGHT_CONFIGS.items():
            ddi_ba[wname] = round(ddi(d_t_a, d_s_a, d_sal_a, d_div, weights), 4)
        results["ddi"]["B_vs_A"] = ddi_ba
        print(f"  DDI(B,A) = {ddi_ba}")

    if has_a and has_c:
        delta = {}
        for wname in WEIGHT_CONFIGS:
            d_ba = results["ddi"]["B_vs_A"][wname]
            d_bc = results["ddi"]["B_vs_C"][wname]
            delta[wname] = round(d_ba - d_bc, 4)
        results["delta_ddi"] = delta
        print(f"  ΔDDI     = {delta}")

    with open(out_dir / "ddi_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved to {out_dir}")
    return results


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {}
    for case_id in CASES:
        r = process_case(case_id)
        if r:
            all_results[case_id] = r

    print("\n" + "="*60)
    print("DDI SUMMARY (base weights)")
    print("="*60)
    for cid, r in all_results.items():
        ddi_bc = r.get("ddi", {}).get("B_vs_C", {}).get("base", "N/A")
        ddi_ba = r.get("ddi", {}).get("B_vs_A", {}).get("base", "N/A")
        delta  = r.get("delta_ddi", {})
        delta_base = delta.get("base", "N/A") if delta else "N/A"
        gm = r.get("graph_metrics", {})
        print(f"  {cid}:")
        print(f"    DDI(B,C)={ddi_bc}  DDI(B,A)={ddi_ba}  ΔDDI={delta_base}")
        print(f"    J_BC={gm.get('J_BC','N/A')}  BC_max={gm.get('BC_max','N/A')}  DCC={gm.get('DCC','N/A')}")

    with open(OUT_DIR / "ddi_summary.json", "w") as f:
        json.dump(all_results, f, indent=2)
