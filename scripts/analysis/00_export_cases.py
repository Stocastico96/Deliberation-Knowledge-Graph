#!/usr/bin/env python3
"""
Step 0: Export pilot study cases from HYS DB + EP verbatim JSON.
Replaces old cases (AI Act, Deforestation) with DSA and Forest Strategy.
Implements temporal stratification (Phase A / B / C).
"""

import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Config ────────────────────────────────────────────────────────────────────

HYS_DB = Path("/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db")
EP_DIR  = Path("/home/svagnoni/deliberation-knowledge-graph/data/EU_parliament_debates/json_2021_2024")
OUT_DIR = Path("/home/svagnoni/deliberation-knowledge-graph/data/pilot_study_dataset_v2")

CASES = {
    "case_1_covid": {
        "name": "EU Digital COVID Certificate",
        # COM(2022)50 — extension of Reg. 2021/953; large civic response
        "hys_publication_ids": [15596],
        "hys_refs": ["COM(2022)50"],
        "eurlex_procedure": "2022/0031(COD)",
        "consultation_open":  "2022-03-15",
        "consultation_close": "2022-05-12",
        "ep_keywords": ["covid certificate", "digital covid", "covid-19 certificate",
                        "digital green certificate"],
        "hys_sample_size": 5000,   # down-sample for BERTopic (296k total)
    },
    "case_2_dsa": {
        "name": "Digital Services Act",
        # Ares(2020)3387364 — pub_ids 13125+13971 have text; 13127 is form-only
        "hys_publication_ids": [13125, 13971],
        "hys_refs": ["Ares(2020)3387364"],
        "eurlex_procedure": "2020/0361(COD)",
        "consultation_open":  "2020-06-02",
        "consultation_close": "2020-09-08",
        # Note: consultation pre-dates EP data (Jul 2021+) → Phase A = N/A
        "ep_phase_a_available": False,
        "ep_keywords": ["digital services act", "digital services regulation",
                        "dsa", "online platform", "very large online platform",
                        "content moderation"],
        "hys_sample_size": None,
    },
    "case_3_pesticides": {
        "name": "Sustainable Use of Pesticides (SUR)",
        # Ares(2020)2804518 — pub_id 16030 is the 2022 open consultation with rich text
        "hys_publication_ids": [16030],
        "hys_refs": ["Ares(2020)2804518"],
        "eurlex_procedure": "2022/0196(COD)",
        "consultation_open":  "2022-06-24",
        "consultation_close": "2022-09-21",
        "ep_keywords": ["sustainable use of pesticides", "pesticide regulation",
                        "plant protection", "sur regulation", "pesticide reduction",
                        "farm to fork", "pesticides"],
        "hys_sample_size": None,
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_hys_feedback(pub_ids: list, sample_size: int = None) -> list:
    import random
    conn = sqlite3.connect(HYS_DB)
    cur = conn.cursor()
    placeholders = ",".join("?" * len(pub_ids))
    cur.execute(f"SELECT data FROM feedback WHERE publication_id IN ({placeholders})", pub_ids)
    rows = cur.fetchall()
    conn.close()
    items = []
    for (data,) in rows:
        d = json.loads(data)
        text = d.get("feedback") or d.get("feedbackText") or d.get("feedbackTextUserLanguage") or d.get("text", "")
        items.append({
            "id":           d.get("id"),
            "date":         d.get("dateFeedback") or d.get("date") or d.get("feedbackDate"),
            "language":     d.get("language") or d.get("userLanguage"),
            "country":      d.get("country"),
            "user_type":    d.get("userType") or d.get("publication", "ANONYMOUS"),
            "organization": d.get("organization") or d.get("organisationName", ""),
            "text":         text,
        })
    if sample_size and len(items) > sample_size:
        random.seed(42)
        items = random.sample(items, sample_size)
        print(f"  (sampled {sample_size:,} from {len(rows):,} total)")
    return items


def load_ep_speeches(keywords: list, phase_a_before: str, phase_c_after: str) -> tuple:
    """
    Returns (phase_a_speeches, phase_c_speeches).
    phase_a_before: ISO date string — speeches BEFORE this date → Phase A
    phase_c_after:  same date — speeches AFTER → Phase C
    """
    t_close = datetime.fromisoformat(phase_c_after)
    phase_a, phase_c = [], []

    for fname in sorted(EP_DIR.glob("*.json")):
        # Extract date from filename: debate_YYYY-MM-DD.json
        parts = fname.stem.split("_")
        if len(parts) < 2:
            continue
        try:
            debate_date = datetime.fromisoformat(parts[-1])
        except ValueError:
            continue

        with open(fname) as f:
            try:
                d = json.load(f)
            except Exception:
                continue

        contributions = d.get("del:hasContribution", [])
        debate_title = " ".join(
            t.get("del:name", "") for t in d.get("del:hasTopic", [])
        ).lower()

        for speech in contributions:
            text = speech.get("del:text", "")
            if not text or len(text) < 50:
                continue
            text_lower = text.lower()
            title_lower = debate_title

            if not any(kw in text_lower or kw in title_lower for kw in keywords):
                continue

            record = {
                "date":    debate_date.isoformat()[:10],
                "speaker": speech.get("del:madeBy", {}).get("del:name", "")
                           if isinstance(speech.get("del:madeBy"), dict)
                           else speech.get("del:madeBy", ""),
                "text":    text,
                "debate_file": fname.name,
            }

            if debate_date < t_close:
                phase_a.append(record)
            else:
                phase_c.append(record)

    return phase_a, phase_c


def actor_diversity(feedback: list) -> dict:
    counts = Counter(f.get("user_type", "ANONYMOUS") for f in feedback)
    total = sum(counts.values())
    return {k: round(v / total, 4) for k, v in counts.most_common()}


# ── Main ──────────────────────────────────────────────────────────────────────

def export_case(case_id: str, cfg: dict):
    print(f"\n{'='*60}")
    print(f"Exporting {case_id}: {cfg['name']}")

    out = OUT_DIR / case_id
    out.mkdir(parents=True, exist_ok=True)

    # ── HYS feedback (Phase B) ──
    print("  Loading HYS feedback...")
    hys = load_hys_feedback(cfg["hys_publication_ids"], sample_size=cfg.get("hys_sample_size"))
    hys = [f for f in hys if f.get("text") and len(f["text"].strip()) > 20]
    print(f"  → {len(hys)} feedback items with text")

    lang_dist = Counter(f.get("language", "?") for f in hys)
    actor_dist = actor_diversity(hys)

    with open(out / "hys_feedback.json", "w") as f:
        json.dump({"consultations": cfg["hys_refs"],
                   "feedback": hys}, f, ensure_ascii=False, indent=2)

    # ── EP speeches (Phase A + C) ──
    print("  Loading EP speeches with temporal split...")
    phase_a_available = cfg.get("ep_phase_a_available", True)
    if phase_a_available:
        phase_a, phase_c = load_ep_speeches(
            cfg["ep_keywords"],
            phase_a_before=cfg["consultation_close"],
            phase_c_after=cfg["consultation_close"],
        )
    else:
        _, phase_c = load_ep_speeches(
            cfg["ep_keywords"],
            phase_a_before="2000-01-01",   # far past → no Phase A
            phase_c_after=cfg["consultation_close"],
        )
        phase_a = []
        print("  → Phase A: N/A (consultation pre-dates EP data window)")
    print(f"  → Phase A (pre-consult):  {len(phase_a)} speeches")
    print(f"  → Phase C (post-consult): {len(phase_c)} speeches")

    with open(out / "ep_phase_a.json", "w") as f:
        json.dump(phase_a, f, ensure_ascii=False, indent=2)
    with open(out / "ep_phase_c.json", "w") as f:
        json.dump(phase_c, f, ensure_ascii=False, indent=2)

    # ── Metadata ──
    metadata = {
        "case_id": case_id,
        "case_name": cfg["name"],
        "eurlex_procedure": cfg["eurlex_procedure"],
        "consultation_open":  cfg["consultation_open"],
        "consultation_close": cfg["consultation_close"],
        "hys": {
            "publication_ids": cfg["hys_publication_ids"],
            "total_feedback": len(hys),
            "languages": dict(lang_dist.most_common(10)),
            "actor_distribution": actor_dist,
        },
        "ep": {
            "phase_a_speeches": len(phase_a),
            "phase_c_speeches": len(phase_c),
            "keywords_used": cfg["ep_keywords"],
        },
        "exported_at": datetime.now().isoformat(),
    }
    with open(out / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✓ Saved to {out}")
    return metadata


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}

    for case_id, cfg in CASES.items():
        meta = export_case(case_id, cfg)
        summary[case_id] = {
            "name": meta["case_name"],
            "hys_feedback": meta["hys"]["total_feedback"],
            "ep_phase_a": meta["ep"]["phase_a_speeches"],
            "ep_phase_c": meta["ep"]["phase_c_speeches"],
        }

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for cid, s in summary.items():
        print(f"  {cid}: HYS={s['hys_feedback']:,}  "
              f"EP-A={s['ep_phase_a']}  EP-C={s['ep_phase_c']}")

    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nDone. Output: {OUT_DIR}")
