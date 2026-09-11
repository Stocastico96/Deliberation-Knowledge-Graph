#!/usr/bin/env python3
"""
Merge (or re-merge) one source graph into the main Deliberation Knowledge Graph.

  python3 scripts/integration/merge_source_into_kg.py --source delibai \
      --file knowledge_graph/sources/delibai_pilot_kg.ttl

Behaviour
  1. A timestamped backup of the main graph is written to knowledge_graph/backups/
     (same convention as merge_polis_to_main_kg.py) unless --no-backup is given.
  2. If this source was merged before, the triples of the PREVIOUSLY merged
     version (kept in knowledge_graph/sources/merged/<source>.ttl) are removed
     from the main graph first. Nothing else is ever deleted, so corrections
     and authorised removals are explicit and reviewable.
  3. The new source triples are added (rdflib set semantics: no duplicates).
  4. The main graph is serialised back; the merged source version is archived
     in knowledge_graph/sources/history/<source>_<timestamp>.ttl and a JSON log
     with before/removed/added/after counts is written to
     knowledge_graph/sources/merged/<source>.merge_log.json.

Re-running with the same source file is a no-op on the triple set (idempotent).
Loading the 240 MB main graph with rdflib takes several minutes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KG_DIR, SOURCES_DIR, bind_namespaces, now_iso  # noqa: E402

MAIN_KG = KG_DIR / "deliberation_kg.ttl"
BACKUP_DIR = KG_DIR / "backups"
MERGED_DIR = SOURCES_DIR / "merged"
HISTORY_DIR = SOURCES_DIR / "history"


def load(path: Path, label: str) -> Graph:
    t = time.time()
    g = Graph()
    bind_namespaces(g)
    g.parse(str(path), format="turtle")
    print(f"  loaded {label}: {len(g):,} triples in {time.time() - t:.0f}s", flush=True)
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, action="append", help="source key, e.g. delibai, crowdlaw, crosslinks (repeatable)")
    ap.add_argument("--file", required=True, action="append", help="Turtle file produced by the importer (one per --source, same order)")
    ap.add_argument("--main", default=str(MAIN_KG))
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="compute counts, do not write")
    args = ap.parse_args()

    if len(args.source) != len(args.file):
        ap.error("--source and --file must be given the same number of times")
    main_path = Path(args.main)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    label = "+".join(args.source)
    print(f"Merging sources {args.source} into {main_path}", flush=True)

    pairs = []
    for source, f in zip(args.source, args.file):
        previous = MERGED_DIR / f"{source}.ttl"
        new_g = load(Path(f), f"new source graph '{source}'")
        prev_g = load(previous, f"previously merged '{source}'") if previous.exists() else None
        pairs.append((source, Path(f), previous, new_g, prev_g))

    backup = None
    if not args.no_backup and not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUP_DIR / f"deliberation_kg_before_{label}_{stamp}.ttl"
        shutil.copy2(main_path, backup)
        print(f"  backup written: {backup}", flush=True)

    main_g = load(main_path, "main knowledge graph")
    logs = []
    for source, src_path, previous, new_g, prev_g in pairs:
        before = len(main_g)
        removed = 0
        if prev_g is not None:
            for triple in prev_g:
                if triple in main_g:
                    main_g.remove(triple)
                    removed += 1
        after_removal = len(main_g)
        for triple in new_g:
            main_g.add(triple)
        after = len(main_g)
        log = {
            "source": source, "file": str(src_path), "main": str(main_path), "started_at": now_iso(),
            "dry_run": args.dry_run, "backup": str(backup) if backup else None,
            "triples_before": before, "triples_removed_previous_version": removed,
            "triples_after_removal": after_removal, "triples_in_source": len(new_g),
            "triples_added": after - after_removal, "triples_after": after,
        }
        logs.append(log)
        print(json.dumps({k: v for k, v in log.items() if k.startswith("triples") or k == "source"}, indent=2), flush=True)

    if args.dry_run:
        return 0

    t = time.time()
    tmp = main_path.with_suffix(".ttl.tmp")
    main_g.serialize(destination=str(tmp), format="turtle")
    tmp.replace(main_path)
    print(f"  main graph written in {time.time() - t:.0f}s", flush=True)

    for (source, src_path, previous, _n, _p), log in zip(pairs, logs):
        if previous.exists():
            shutil.copy2(previous, HISTORY_DIR / f"{source}_{stamp}_replaced.ttl")
        shutil.copy2(src_path, previous)
        shutil.copy2(src_path, HISTORY_DIR / f"{source}_{stamp}.ttl")
        log["finished_at"] = now_iso()
        (MERGED_DIR / f"{source}.merge_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
        with open(MERGED_DIR / "merge_history.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(log) + "\n")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
