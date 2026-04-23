#!/usr/bin/env python3
"""
Step 3: Zero-shot stance detection using multilingual NLI.
Model: mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
For each topic (from BERTopic), generates a proposition and classifies
each document's stance as: support / oppose / neutral.
Works across all 24 HYS languages without translation.
"""

import json
import torch
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict

# ── Config ─────────────────────────────────────────────────────────────────────

TOPIC_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/topic_models_v2")
OUT_DIR   = Path("/home/svagnoni/deliberation-knowledge-graph/data/stance_v2")

CASES = ["case_1_covid", "case_2_dsa", "case_3_pesticides"]

NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
BATCH_SIZE = 32
MAX_TEXT_LEN = 512   # tokens (NLI model limit)

# Proposition templates per case (populated from top BERTopic keywords)
# These are filled at runtime from topic keywords
CASE_PROPOSITIONS = {
    "case_1_covid":      "The EU digital COVID certificate should be extended.",
    "case_2_dsa":        "Online platforms should be regulated more strictly.",
    "case_3_pesticides": "The use of pesticides in EU agriculture should be reduced.",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_phase_texts(case_dir: Path, phase: str) -> list:
    """Load (id, text, topic_id) for a phase."""
    data_root = Path("/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset_v2")

    if phase == "B":
        with open(data_root / case_dir.name / "hys_feedback.json") as f:
            items = json.load(f)["feedback"]
        texts = [(str(item.get("id", i)), item["text"], None)
                 for i, item in enumerate(items)
                 if item.get("text") and len(item["text"].strip()) > 30]
    else:
        fname = "ep_phase_a.json" if phase == "A" else "ep_phase_c.json"
        with open(data_root / case_dir.name / fname) as f:
            items = json.load(f)
        texts = [(f"{phase}_{i}", item["text"], None)
                 for i, item in enumerate(items)
                 if item.get("text") and len(item["text"].strip()) > 50]

    # Attach topic assignments if available
    assign_path = TOPIC_DIR / case_dir.name / f"phase_{phase}_assignments.json"
    if assign_path.exists():
        with open(assign_path) as f:
            assignments = {item["id"]: item["topic"] for item in json.load(f)}
        texts = [(tid, text, assignments.get(tid)) for tid, text, _ in texts]

    return texts


def classify_stance_batch(model, tokenizer, texts: list, hypothesis: str, device) -> list:
    """
    Run NLI on a batch. Returns list of (entailment_prob, neutral_prob, contradiction_prob).
    """
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i+BATCH_SIZE]
        # Truncate texts to avoid exceeding model limits
        batch_texts_trunc = [t[:1500] for t in batch_texts]

        encoding = tokenizer(
            batch_texts_trunc,
            [hypothesis] * len(batch_texts_trunc),
            truncation=True,
            max_length=MAX_TEXT_LEN,
            padding=True,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            output = model(**encoding)
            probs = torch.softmax(output.logits, dim=-1).cpu().numpy()

        for row in probs:
            # mDeBERTa NLI label order: contradiction=0, neutral=1, entailment=2
            results.append({
                "entailment":    float(row[2]),
                "neutral":       float(row[1]),
                "contradiction": float(row[0]),
            })

        if (i // BATCH_SIZE) % 10 == 0:
            print(f"    batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1}")

    return results


def stance_label(probs: dict, threshold: float = 0.4) -> str:
    ent = probs["entailment"]
    con = probs["contradiction"]
    if ent > threshold and ent > con:
        return "support"
    elif con > threshold and con > ent:
        return "oppose"
    else:
        return "neutral"


def aggregate_stance_distribution(stance_results: list) -> dict:
    counts = Counter(r["label"] for r in stance_results)
    total = len(stance_results)
    if total == 0:
        return {"support": 0.0, "neutral": 0.0, "oppose": 0.0, "total": 0}
    return {
        "support": round(counts.get("support", 0) / total, 4),
        "neutral": round(counts.get("neutral", 0) / total, 4),
        "oppose":  round(counts.get("oppose", 0) / total, 4),
        "total":   total,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def process_case(case_id: str):
    print(f"\n{'='*60}")
    print(f"Case: {case_id}")
    case_dir = TOPIC_DIR / case_id
    out_dir  = OUT_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)

    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")
    print(f"  Loading NLI model: {NLI_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL).to(device)
    model.eval()

    hypothesis = CASE_PROPOSITIONS[case_id]
    print(f"  Hypothesis: {hypothesis}")

    case_summary = {}

    for phase in ["A", "B", "C"]:
        items = load_phase_texts(case_dir, phase)
        print(f"\n  Phase {phase}: {len(items)} texts")

        if not items:
            case_summary[phase] = {"n_texts": 0, "distribution": {}}
            continue

        ids, texts, topic_ids = zip(*items)

        print(f"    Running NLI stance detection...")
        probs_list = classify_stance_batch(model, tokenizer, list(texts), hypothesis, device)

        results = []
        for doc_id, text, tid, probs in zip(ids, texts, topic_ids, probs_list):
            label = stance_label(probs)
            results.append({
                "id":       doc_id,
                "topic":    tid,
                "label":    label,
                "probs":    {k: round(v, 4) for k, v in probs.items()},
            })

        distribution = aggregate_stance_distribution(results)
        print(f"    Distribution: {distribution}")

        with open(out_dir / f"phase_{phase}_stance.json", "w") as f:
            json.dump(results, f, indent=2)

        # Stance by topic
        by_topic = defaultdict(list)
        for r in results:
            if r["topic"] is not None and r["topic"] != -1:
                by_topic[str(r["topic"])].append(r["label"])
        topic_stance = {
            tid: {
                "support": round(labels.count("support") / len(labels), 4),
                "neutral": round(labels.count("neutral") / len(labels), 4),
                "oppose":  round(labels.count("oppose") / len(labels), 4),
                "n": len(labels),
            }
            for tid, labels in by_topic.items()
        }
        with open(out_dir / f"phase_{phase}_topic_stance.json", "w") as f:
            json.dump(topic_stance, f, indent=2)

        case_summary[phase] = {"n_texts": len(results), "distribution": distribution}

    with open(out_dir / "stance_summary.json", "w") as f:
        json.dump(case_summary, f, indent=2)

    print(f"\n  Saved to {out_dir}")
    return case_summary


if __name__ == "__main__":
    import sys
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_cases = sys.argv[1:] if len(sys.argv) > 1 else CASES
    for case_id in target_cases:
        process_case(case_id)
