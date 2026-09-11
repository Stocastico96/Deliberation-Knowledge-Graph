#!/usr/bin/env python3
"""
Build the semantic-search documents of one source graph and update the
embeddings index used by the citizen interface (knowledge_graph/embeddings.pkl).

  python3 scripts/integration/update_embeddings_for_source.py --source delibai \
      --file knowledge_graph/sources/delibai_pilot_kg.ttl

Index format (unchanged): {'embeddings': np.ndarray[N,384], 'metadata': list[dict]}
with the model paraphrase-multilingual-MiniLM-L12-v2 (same as semantic_api.py).

Every document of this source carries metadata['source'] = <source>; a re-run
first drops all documents of that source and then appends the fresh ones, so
the index never keeps stale entries or links to resources that no longer exist.
A backup of the index is written before overwriting.

Document types produced (metadata['type']):
  process, topic, contribution, seed_contribution, legal_provision,
  ai_feedback (advice), ai_rewrite (rewrite suggestion) - the last two carry
  is_ai_generated=True and are excluded from ordinary results by the API
  unless explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import pickle
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEL, KG_DIR, bind_namespaces, now_iso  # noqa: E402

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDINGS = KG_DIR / "embeddings.pkl"


def first(g: Graph, s, *preds):
    for p in preds:
        for o in g.objects(s, p):
            return o
    return None


def label(g: Graph, s) -> str:
    v = first(g, s, DEL.name, RDFS.label, DCTERMS.title)
    return str(v) if v is not None else str(s).rsplit("/", 1)[-1]


def date_str(g: Graph, s) -> str | None:
    v = first(g, s, DEL.timestamp, DCTERMS.created, DEL.startDate, DCTERMS.date)
    return str(v)[:10] if v is not None else None


def build_documents(g: Graph, source: str) -> list[dict]:
    docs: list[dict] = []
    forum_name: dict[URIRef, str] = {}
    for p in g.subjects(RDF.type, DEL.DeliberationProcess):
        forum = first(g, p, DEL.takesPlaceIn)
        forum_name[p] = label(g, forum) if forum is not None else (str(first(g, p, DEL.platform) or source))

    def base(uri, process, typ, text, **extra):
        d = {
            "uri": str(uri),
            "text": text,
            "process": str(process) if process is not None else "",
            "process_name": label(g, process) if process is not None else "",
            "platform": forum_name.get(process, source),
            "type": typ,
            "source": source,
            "language": str(first(g, uri, DCTERMS.language) or first(g, process, DCTERMS.language) or "") if process is not None else str(first(g, uri, DCTERMS.language) or ""),
            "date": date_str(g, uri) or (date_str(g, process) if process is not None else None),
            "is_ai_generated": False,
        }
        d.update(extra)
        return d

    # processes
    for p in g.subjects(RDF.type, DEL.DeliberationProcess):
        desc = first(g, p, DCTERMS.description)
        text = label(g, p) + (". " + str(desc) if desc else "")
        docs.append(base(p, p, "process", text))
        # topics attached to the process (DelibAI topics / CrowdLaw clusters)
        for t in g.objects(p, DEL.hasTopic):
            tdesc = first(g, t, DCTERMS.description)
            if tdesc is None:
                continue  # clusters have only key words - not useful as search documents
            docs.append(base(t, p, "topic", f"{label(g, t)}. {tdesc}", topic=label(g, t), topic_uri=str(t)))

    # contributions
    for c in g.subjects(RDF.type, DEL.Contribution):
        text = first(g, c, DEL.text)
        if text is None or not str(text).strip():
            continue
        process = first(g, c, DEL.isPartOf)
        kind = str(first(g, c, DEL.contributionSource) or "participant")
        typ = "seed_contribution" if kind == "seed" else "contribution"
        topic = first(g, c, DEL.hasTopic)
        extra = {}
        if topic is not None:
            extra["topic"] = label(g, topic)
            extra["topic_uri"] = str(topic)
        if first(g, c, DEL.replyRelation) is not None:
            extra["kind"] = str(first(g, c, DEL.contributionKind))
        cond = first(g, c, DEL.experimentalCondition)
        if cond is not None:
            extra["condition"] = str(cond)
        # legal document (CrowdLaw): expression referenced by the contribution
        for ref in g.objects(c, DEL.references):
            if (ref, RDF.type, DEL.LegalExpression) in g:
                extra["document"] = label(g, ref)
                extra["document_uri"] = str(ref)
        for prov in g.objects(c, DEL.aboutProvision):
            extra["provision"] = label(g, prov)
            extra["provision_uri"] = str(prov)
        stance = None
        for a in g.objects(c, DEL.hasAnnotation):
            if (a, RDF.type, DEL.StanceAnnotation) in g and stance is None:
                stance = str(first(g, a, DEL.stanceLabel) or "")
        if stance:
            extra["stance"] = stance
        docs.append(base(c, process, typ, str(text), **extra))
        # AI feedback on this contribution
        for a in g.objects(c, DEL.hasAnnotation):
            if (a, RDF.type, DEL.AIFeedback) not in g:
                continue
            model = str(first(g, a, DEL.model) or "")
            advice = first(g, a, DEL.advice)
            rewrite = first(g, a, DEL.rewriteSuggestion)
            if advice:
                docs.append(base(a, process, "ai_feedback", str(advice), is_ai_generated=True, model=model, annotates=str(c), **{k: v for k, v in extra.items() if k in ("topic", "topic_uri")}))
            if rewrite:
                docs.append(base(a, process, "ai_rewrite", str(rewrite), is_ai_generated=True, model=model, annotates=str(c), **{k: v for k, v in extra.items() if k in ("topic", "topic_uri")}))

    # legal provisions (articles only; segments are parts of articles)
    for prov in g.subjects(RDF.type, DEL.LegalProvision):
        if first(g, prov, DEL.segmentIndex) is not None:
            continue
        text = first(g, prov, DEL.text)
        if text is None or not str(text).strip():
            continue
        expr = first(g, prov, DEL.partOfExpression)
        process = None
        for p in g.subjects(DEL.references, expr):
            if (p, RDF.type, DEL.DeliberationProcess) in g:
                process = p
                break
        docs.append(
            base(
                prov,
                process,
                "legal_provision",
                f"{label(g, prov)}. {text}",
                document=label(g, expr) if expr is not None else "",
                document_uri=str(expr) if expr is not None else "",
                provision=label(g, prov),
                provision_uri=str(prov),
                language="it",
            )
        )
    return docs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--index", default=str(EMBEDDINGS))
    ap.add_argument("--documents-out", default=None, help="also write the search documents as JSON")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    g = Graph()
    bind_namespaces(g)
    g.parse(args.file, format="turtle")
    docs = build_documents(g, args.source)
    print(f"{len(docs)} search documents for source '{args.source}'", flush=True)
    by_type: dict[str, int] = {}
    for d in docs:
        by_type[d["type"]] = by_type.get(d["type"], 0) + 1
    print(json.dumps(by_type, indent=2), flush=True)
    if args.documents_out:
        Path(args.documents_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.documents_out).write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    t = time.time()
    vectors = model.encode([d["text"] for d in docs], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    vectors = np.asarray(vectors, dtype=np.float32)
    print(f"encoded in {time.time() - t:.0f}s", flush=True)

    index_path = Path(args.index)
    if index_path.exists():
        with open(index_path, "rb") as fh:
            data = pickle.load(fh)
        emb = np.asarray(data["embeddings"])
        meta = list(data["metadata"])
        keep = [i for i, m in enumerate(meta) if m.get("source") != args.source]
        dropped = len(meta) - len(keep)
        emb = emb[keep] if dropped else emb
        meta = [meta[i] for i in keep] if dropped else meta
        if not args.no_backup:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = index_path.with_name(f"embeddings_backup_before_{args.source}_{stamp}.pkl")
            shutil.copy2(index_path, backup)
            print(f"backup: {backup}", flush=True)
    else:
        emb = np.zeros((0, vectors.shape[1]), dtype=np.float32)
        meta = []
        dropped = 0
    if emb.dtype != vectors.dtype:
        vectors = vectors.astype(emb.dtype)
    merged = np.vstack([emb, vectors]) if len(emb) else vectors
    meta.extend(docs)
    with open(index_path, "wb") as fh:
        pickle.dump({"embeddings": merged, "metadata": meta, "model_name": MODEL_NAME, "updated_at": now_iso()}, fh)
    print(json.dumps({"index": str(index_path), "dropped_previous": dropped, "added": len(docs), "total": len(meta)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
