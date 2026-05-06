#!/usr/bin/env python3
"""
Step 4b: True topological graph metrics on the unified KG.

Prerequisite: run 01b_unified_topic_model.py first.

The bipartite graph G = (U ∪ V, E):
  U = contribution nodes (tagged with phase A/B/C)
  V = topic nodes (shared vocabulary from unified BERTopic)
  E = hasTopic edges

Three metrics, all computed with NetworkX on the actual graph:

  CPBR  Cross-Phase Bridging Ratio
        |{t ∈ V : deg_B(t)>0 AND deg_C(t)>0}| / |V|
        "What fraction of topic nodes connect both phases?"

  MPET  Mean Phase Entropy of bridging Topics
        For each bridging topic, H_2(p_B, p_C) normalised by log2.
        "Are shared topics evenly used by both phases?"
        MPET=1: perfectly balanced. MPET=0: dominated by one side.

  CPBC  Cross-Phase Betweenness Concentration
        NetworkX betweenness_centrality_subset with sources=B_nodes,
        targets=C_nodes.  Reports max and the identity of the top topic.
        "Which topic node mediates the most B→C connections?"

  r_BC  Cross-Phase Degree Correlation
        Pearson r between deg_B(t) and deg_C(t) vectors across all topics.
        r≈1: phases emphasise the same topics proportionally (agenda alignment).
        r≈0: phases emphasise different sub-topics (agenda divergence).

These metrics depend only on graph structure (who is connected to whom),
not on embedding similarity.  They are independent of and complementary
to the DDI computed in step 04.
"""

import json
import math
import numpy as np
import networkx as nx
from pathlib import Path
from collections import defaultdict

UNIFIED_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/unified_topic_models_v2")
OUT_DIR     = Path("/home/svagnoni/deliberation-knowledge-graph/data/graph_metrics_v2")

CASES = ["case_1_covid", "case_2_climate_target", "case_3_pesticides"]


# ── Graph construction ──────────────────────────────────────────────────────────

def build_bipartite_graph(assignments: list, phases: tuple = ("B", "C")) -> nx.Graph:
    """
    Build bipartite graph from unified assignments.
    Left nodes = contributions (bipartite=0), right nodes = topics (bipartite=1).
    Only include documents from the requested phases.
    """
    G = nx.Graph()
    for a in assignments:
        if a["topic"] == -1:
            continue
        if a["phase"] not in phases:
            continue
        doc_node   = f"doc_{a['id']}"
        topic_node = f"topic_{a['topic']}"
        G.add_node(doc_node,   bipartite=0, phase=a["phase"])
        G.add_node(topic_node, bipartite=1)
        G.add_edge(doc_node, topic_node)
    return G


# ── Metric 1: CPBR ──────────────────────────────────────────────────────────────

def cross_phase_bridging_ratio(G: nx.Graph) -> dict:
    """
    CPBR = |bridging topics| / |all topic nodes|
    A topic is bridging if it has at least one B-neighbour AND one C-neighbour.
    """
    topic_nodes = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
    b_nodes     = {n for n, d in G.nodes(data=True) if d.get("phase") == "B"}
    c_nodes     = {n for n, d in G.nodes(data=True) if d.get("phase") == "C"}

    bridging = []
    for t in topic_nodes:
        nbrs = set(G.neighbors(t))
        if nbrs & b_nodes and nbrs & c_nodes:
            bridging.append(t)

    cpbr = len(bridging) / len(topic_nodes) if topic_nodes else 0.0
    return {
        "CPBR":           round(cpbr, 4),
        "n_topics":       len(topic_nodes),
        "n_bridging":     len(bridging),
        "bridging_topics": [t.replace("topic_", "") for t in bridging],
    }


# ── Metric 2: MPET ──────────────────────────────────────────────────────────────

def mean_phase_entropy(G: nx.Graph) -> dict:
    """
    For each bridging topic node, compute binary entropy of (p_B, p_C).
    MPET = mean over bridging topics, normalised to [0,1] by log(2).
    """
    topic_nodes = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
    b_nodes     = {n for n, d in G.nodes(data=True) if d.get("phase") == "B"}
    c_nodes     = {n for n, d in G.nodes(data=True) if d.get("phase") == "C"}

    entropies = {}
    for t in topic_nodes:
        nbrs  = list(G.neighbors(t))
        deg_b = sum(1 for n in nbrs if n in b_nodes)
        deg_c = sum(1 for n in nbrs if n in c_nodes)
        if deg_b == 0 or deg_c == 0:
            continue                          # not bridging
        deg   = deg_b + deg_c
        p_b, p_c = deg_b / deg, deg_c / deg
        H = -(p_b * math.log(p_b) + p_c * math.log(p_c))   # nats
        H_norm = H / math.log(2)                             # normalise to [0,1]
        entropies[t.replace("topic_", "")] = round(H_norm, 4)

    mpet = sum(entropies.values()) / len(entropies) if entropies else 0.0
    return {
        "MPET":                  round(mpet, 4),
        "n_bridging_with_entropy": len(entropies),
        "per_topic_entropy":     entropies,
    }


# ── Metric 3: CPBC ──────────────────────────────────────────────────────────────

def cross_phase_betweenness(G: nx.Graph) -> dict:
    """
    Betweenness centrality of topic nodes restricted to B→C paths.
    Uses nx.betweenness_centrality_subset with sources=B_nodes, targets=C_nodes.
    Normalised by (|B|*|C|) so it is comparable across cases.
    """
    topic_nodes = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
    b_nodes     = [n for n, d in G.nodes(data=True) if d.get("phase") == "B"]
    c_nodes     = [n for n, d in G.nodes(data=True) if d.get("phase") == "C"]

    if not b_nodes or not c_nodes or not topic_nodes:
        return {"CPBC_max": 0.0, "CPBC_mean": 0.0, "top_topic": None}

    print(f"      Computing betweenness on graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges...")
    bc = nx.betweenness_centrality_subset(
        G,
        sources=b_nodes,
        targets=c_nodes,
        normalized=True,
    )

    topic_bc = {t.replace("topic_", ""): bc.get(t, 0.0) for t in topic_nodes}
    top_topic  = max(topic_bc, key=topic_bc.get)
    cpbc_max   = topic_bc[top_topic]
    cpbc_mean  = sum(topic_bc.values()) / len(topic_bc) if topic_bc else 0.0

    return {
        "CPBC_max":  round(cpbc_max, 6),
        "CPBC_mean": round(cpbc_mean, 6),
        "top_topic": top_topic,
        "per_topic_betweenness": {k: round(v, 6) for k, v in
                                   sorted(topic_bc.items(), key=lambda x: -x[1])[:20]},
    }


# ── Metric 4: r_BC ──────────────────────────────────────────────────────────────

def cross_phase_degree_correlation(G: nx.Graph) -> dict:
    """
    Pearson r between deg_B(t) and deg_C(t).

    Two variants:
      r_BC_all      — all topic nodes, including those with deg=0 in one phase.
                      Biased toward negative values when one phase is much smaller,
                      because zero-degree nodes inflate the count of (high, 0) pairs.
      r_BC_bridging — restricted to bridging topics (deg_B>0 AND deg_C>0).
                      Conceptually cleaner: "among shared topics, are relative
                      intensities correlated?" Preferred for reporting; note n_bridging
                      for reliability (n<10 → interpret with caution).
    """
    topic_nodes = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
    b_nodes     = {n for n, d in G.nodes(data=True) if d.get("phase") == "B"}
    c_nodes     = {n for n, d in G.nodes(data=True) if d.get("phase") == "C"}

    if len(topic_nodes) < 2:
        return {"r_BC_all": 0.0, "r_BC_bridging": None, "n_topics": len(topic_nodes), "n_bridging": 0}

    degs = [(sum(1 for nb in G.neighbors(t) if nb in b_nodes),
             sum(1 for nb in G.neighbors(t) if nb in c_nodes))
            for t in topic_nodes]
    deg_b_all = np.array([d[0] for d in degs], dtype=float)
    deg_c_all = np.array([d[1] for d in degs], dtype=float)

    r_all = float(np.corrcoef(deg_b_all, deg_c_all)[0, 1]) \
            if deg_b_all.std() > 0 and deg_c_all.std() > 0 else 0.0

    bridge_mask = (deg_b_all > 0) & (deg_c_all > 0)
    n_bridging  = int(bridge_mask.sum())
    if n_bridging >= 3:
        db_br = deg_b_all[bridge_mask]
        dc_br = deg_c_all[bridge_mask]
        r_bridging = float(np.corrcoef(db_br, dc_br)[0, 1]) \
                     if db_br.std() > 0 and dc_br.std() > 0 else 0.0
    else:
        r_bridging = None

    return {
        "r_BC_all":      round(r_all, 4),
        "r_BC_bridging": round(r_bridging, 4) if r_bridging is not None else None,
        "n_topics":      len(topic_nodes),
        "n_bridging":    n_bridging,
        "reliable":      n_bridging >= 10,
    }


# ── Main ────────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    unified_dir = UNIFIED_DIR / case_id
    out_dir     = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    assign_path = unified_dir / "unified_assignments.json"
    if not assign_path.exists():
        print(f"  [SKIP] No unified assignments — run 01b first")
        return None

    with open(assign_path) as f:
        assignments = json.load(f)

    with open(unified_dir / "unified_topics.json") as f:
        topic_info = json.load(f)

    phase_counts = {
        ph: sum(1 for a in assignments if a["phase"] == ph and a["topic"] != -1)
        for ph in ["A", "B", "C"]
    }
    print(f"  Documents in graph: {phase_counts}")

    # Build B-C bipartite graph (primary comparison)
    G_bc = build_bipartite_graph(assignments, phases=("B", "C"))
    print(f"  B-C graph: {G_bc.number_of_nodes()} nodes, {G_bc.number_of_edges()} edges")

    # ── Compute the four metrics ──
    print("  Computing CPBR...")
    cpbr = cross_phase_bridging_ratio(G_bc)

    print("  Computing MPET...")
    mpet = mean_phase_entropy(G_bc)

    print("  Computing CPBC (betweenness)...")
    cpbc = cross_phase_betweenness(G_bc)

    print("  Computing r_BC (degree correlation)...")
    r_bc = cross_phase_degree_correlation(G_bc)

    # ── Enrich with topic labels ──
    for tid in cpbr["bridging_topics"][:10]:
        if tid in topic_info:
            print(f"    Bridging topic {tid}: {topic_info[tid]['label']} "
                  f"(B={topic_info[tid]['count_B']}, C={topic_info[tid]['count_C']})")

    if cpbc["top_topic"] and cpbc["top_topic"] in topic_info:
        top = topic_info[cpbc["top_topic"]]
        print(f"  Top betweenness topic: {top['label']} "
              f"(CPBC_max={cpbc['CPBC_max']}, B={top['count_B']}, C={top['count_C']})")

    # ── Also compute A-C graph if Phase A available ──
    a_c_results = None
    if phase_counts.get("A", 0) > 0:
        G_ac = build_bipartite_graph(assignments, phases=("A", "C"))
        print(f"\n  A-C graph: {G_ac.number_of_nodes()} nodes, {G_ac.number_of_edges()} edges")
        a_c_results = {
            "CPBR": cross_phase_bridging_ratio(G_ac),
            "MPET": mean_phase_entropy(G_ac),
            "CPBC": cross_phase_betweenness(G_ac),
            "r_BC": cross_phase_degree_correlation(G_ac),
        }

    results = {
        "B_vs_C": {"CPBR": cpbr, "MPET": mpet, "CPBC": cpbc, "r_BC": r_bc},
        "A_vs_C": a_c_results,
    }
    with open(out_dir / "graph_metrics.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Summary B-C:")
    print(f"    CPBR     = {cpbr['CPBR']} ({cpbr['n_bridging']}/{cpbr['n_topics']} topics bridge)")
    print(f"    MPET     = {mpet['MPET']} (phase balance of shared topics)")
    print(f"    CPBC_max = {cpbc['CPBC_max']} (top bridge: {cpbc['top_topic']})")
    print(f"    r_BC_all      = {r_bc['r_BC_all']} (all topics, n={r_bc['n_topics']})")
    print(f"    r_BC_bridging = {r_bc['r_BC_bridging']} (bridging only, n={r_bc['n_bridging']}, reliable={r_bc['reliable']})")
    print(f"  Saved to {out_dir}")
    return results


if __name__ == "__main__":
    import sys
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_cases = sys.argv[1:] if len(sys.argv) > 1 else CASES
    summary = {}
    for case_id in target_cases:
        r = process_case(case_id)
        if r:
            bc = r["B_vs_C"]
            summary[case_id] = {
                "CPBR":          bc["CPBR"]["CPBR"],
                "MPET":          bc["MPET"]["MPET"],
                "CPBC_max":      bc["CPBC"]["CPBC_max"],
                "top_topic":     bc["CPBC"]["top_topic"],
                "r_BC_all":      bc["r_BC"]["r_BC_all"],
                "r_BC_bridging": bc["r_BC"]["r_BC_bridging"],
                "r_BC_n":        bc["r_BC"]["n_bridging"],
                "r_BC_reliable": bc["r_BC"]["reliable"],
            }

    print("\n" + "="*60)
    print("GRAPH METRICS SUMMARY")
    print("="*60)
    for cid, s in summary.items():
        print(f"  {cid}:")
        print(f"    CPBR={s['CPBR']}  MPET={s['MPET']}  CPBC_max={s['CPBC_max']}")
        print(f"    r_BC_all={s['r_BC_all']}  r_BC_bridging={s['r_BC_bridging']} (n={s['r_BC_n']}, reliable={s['r_BC_reliable']})  top={s['top_topic']}")

    import json as _json
    with open(OUT_DIR / "graph_metrics_summary.json", "w") as f:
        _json.dump(summary, f, indent=2)
