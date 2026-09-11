#!/usr/bin/env python3
"""
Infer thematic links between the newly integrated processes (DelibAI topics,
CrowdLaw consultations) and the rest of the Deliberation Knowledge Graph.

  python3 scripts/integration/infer_cross_links.py \
      --sources knowledge_graph/sources/delibai_pilot_kg.ttl knowledge_graph/sources/crowdlaw_kg.ttl \
      --index knowledge_graph/embeddings.pkl \
      --output knowledge_graph/sources/crosslinks_delibai_crowdlaw_kg.ttl

Two kinds of INFERRED links are produced, both reified as del:ProcessLink with
linkType "inferred", the method, its version, the model and the score:

  * thematic_similarity  - top-K processes of the graph whose contributions are
    closest to the topic/process text (cosine between the query embedding and
    the mean embedding of each process's contributions in the index). This is
    the same embedding model and index used by the semantic search; it states a
    thematic association only, never influence, derivation or agreement.
  * eurovoc_concept      - top-K EuroVoc concepts already present in the graph
    (the label vocabulary produced by the HYS-EP alignment pipeline,
    scripts/analysis/05d_eurovoc_mapping.py), matched by label embedding
    similarity. They are scored candidates only (no skos:closeMatch is asserted).

Explicit links documented in the source data (e.g. CrowdLaw comment -> AKN
bill) are produced by the importers, not here. No explicit DelibAI-CrowdLaw
links exist in the historical data, so none are asserted as explicit.
"""

from __future__ import annotations

import argparse
import pickle
import re
import sys
from pathlib import Path

import numpy as np
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, SKOS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEL, EUROVOC_LABEL, KG_DIR, add, bind_namespaces, now_iso, res, slug  # noqa: E402

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
METHOD = "centered_mean_contribution_embedding_cosine"
METHOD_VERSION = "crosslinks-1.0.0"
MAIN_KG = KG_DIR / "deliberation_kg.ttl"


def first(g, s, *preds):
    for p in preds:
        for o in g.objects(s, p):
            return o
    return None


def label(g, s):
    v = first(g, s, DEL.name, RDFS.label, DCTERMS.title)
    return str(v) if v is not None else str(s)


def eurovoc_concepts_from_main(main_path: Path) -> dict[str, str]:
    """Fast text scan of the main TTL for eurovocLabel concepts (avoids a full parse)."""
    concepts: dict[str, str] = {}
    pat = re.compile(r'^eurovocLabel:(\S+) a skos:Concept ;\s*\n\s*skos:prefLabel "([^"]+)"', re.M)
    text = main_path.read_text(encoding="utf-8", errors="ignore") if main_path.stat().st_size < 400_000_000 else None
    if text is None:
        return concepts
    for m in pat.finditer(text):
        concepts[str(EUROVOC_LABEL[m.group(1)])] = m.group(2)
    return concepts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--index", default=str(KG_DIR / "embeddings.pkl"))
    ap.add_argument("--main", default=str(MAIN_KG))
    ap.add_argument("--output", default=str(KG_DIR / "sources" / "crosslinks_delibai_crowdlaw_kg.ttl"))
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--min-similarity", type=float, default=0.5, help="threshold for thematic links (centered cosine)")
    ap.add_argument("--eurovoc-min-similarity", type=float, default=0.5)
    ap.add_argument("--eurovoc-top-k", type=int, default=3)
    args = ap.parse_args()

    src = Graph()
    bind_namespaces(src)
    for f in args.sources:
        src.parse(f, format="turtle")

    # query items: DelibAI topics with descriptions, and every new process
    queries: list[tuple[URIRef, str, str]] = []  # (uri, text, kind)
    own_processes: set[str] = set()
    for p in src.subjects(RDF.type, DEL.DeliberationProcess):
        own_processes.add(str(p))
        desc = first(src, p, DCTERMS.description)
        # for CrowdLaw the bill title + article headings describe the theme better than the process description
        headings = []
        for expr in src.objects(p, DEL.references):
            for prov in src.subjects(DEL.partOfExpression, expr):
                if first(src, prov, DEL.segmentIndex) is None:
                    h = first(src, prov, DEL.heading)
                    if h:
                        headings.append(str(h))
        if headings:
            # legal consultation: use the bill title and its article headings, not the
            # generic process wording ("consultation on the bill ..."), which biases matches
            bill = next((label(src, e) for e in src.objects(p, DEL.references)), label(src, p))
            text = bill + ". " + " ".join(headings)
        else:
            text = label(src, p) + ". " + str(desc or "")
        queries.append((p, text, "process"))
        for t in src.objects(p, DEL.hasTopic):
            tdesc = first(src, t, DCTERMS.description)
            if tdesc is not None:
                queries.append((t, f"{label(src, t)}. {tdesc}", "topic"))

    with open(args.index, "rb") as fh:
        data = pickle.load(fh)
    emb = np.asarray(data["embeddings"], dtype=np.float32)
    meta = data["metadata"]
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1e-9
    emb = emb / norms

    # process-level mean vectors over contribution documents
    proc_rows: dict[str, list[int]] = {}
    proc_names: dict[str, str] = {}
    proc_platform: dict[str, str] = {}
    for i, m in enumerate(meta):
        if m.get("is_ai_generated"):
            continue
        if m.get("type") not in (None, "contribution", "seed_contribution", "legal_provision"):
            continue
        p = m.get("process")
        if not p:
            continue
        proc_rows.setdefault(p, []).append(i)
        proc_names.setdefault(p, m.get("process_name", ""))
        proc_platform.setdefault(p, m.get("platform", ""))
    proc_uris = list(proc_rows)
    proc_vecs = np.vstack([emb[proc_rows[p]].mean(axis=0) for p in proc_uris])
    proc_size = np.array([len(proc_rows[p]) for p in proc_uris])
    # Centering: subtracting the global centroid before the cosine reduces the
    # "hubness" of large generic processes (their mean vector sits near the
    # centroid and would otherwise match everything).
    centroid = proc_vecs.mean(axis=0)
    proc_vecs = proc_vecs - centroid
    proc_vecs /= np.maximum(np.linalg.norm(proc_vecs, axis=1, keepdims=True), 1e-9)

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    qvecs_raw = model.encode([q[1] for q in queries], normalize_embeddings=True)
    qvecs = qvecs_raw - centroid
    qvecs /= np.maximum(np.linalg.norm(qvecs, axis=1, keepdims=True), 1e-9)

    eurovoc = eurovoc_concepts_from_main(Path(args.main))
    ev_uris = list(eurovoc)
    ev_vecs = model.encode([eurovoc[u] for u in ev_uris], normalize_embeddings=True) if ev_uris else None

    out = Graph()
    bind_namespaces(out)
    activity = res(f"crosslinks_inference_{slug(METHOD_VERSION)}")
    out.add((activity, RDF.type, DEL.ImportActivity))
    out.add((activity, RDF.type, PROV.Activity))
    add(out, activity, RDFS.label, "Inference of thematic links for DelibAI and CrowdLaw", lang="en")
    add(out, activity, DEL.annotationMethod, METHOD)
    add(out, activity, DEL.annotationMethodVersion, METHOD_VERSION)
    add(out, activity, DEL.model, MODEL_NAME)

    n_links = 0
    n_ev = 0
    for (uri, _text, kind), qv, qv_raw in zip(queries, qvecs, qvecs_raw):
        sims = proc_vecs @ qv
        # exclude the item's own process and processes with very few documents (noisy means)
        order = np.argsort(-sims)
        rank = 0
        for idx in order:
            target = proc_uris[idx]
            if target == str(uri) or (kind == "topic" and target in own_processes and target == str(first(src, uri, DEL.isPartOf) or "")):
                continue
            if proc_size[idx] < 3:
                continue
            if sims[idx] < args.min_similarity:
                break
            rank += 1
            lu = res(f"link_{slug(str(uri).rsplit('/', 1)[-1])}_to_{slug(target.rsplit('/', 1)[-1])}")
            out.add((lu, RDF.type, DEL.ProcessLink))
            out.add((lu, DEL.linkSource, uri))
            out.add((lu, DEL.linkTarget, URIRef(target)))
            add(out, lu, DEL.linkType, "inferred")
            add(out, lu, DEL.linkRelation, "thematic_similarity")
            add(out, lu, DEL.annotationMethod, METHOD)
            add(out, lu, DEL.annotationMethodVersion, METHOD_VERSION)
            add(out, lu, DEL.model, MODEL_NAME)
            add(out, lu, DEL.similarity, round(float(sims[idx]), 4), datatype=XSD.decimal)
            add(out, lu, DEL.rank, rank, datatype=XSD.integer)
            add(out, lu, RDFS.label, f"Thematic similarity: {label(src, uri)} ~ {proc_names.get(target, target)} ({proc_platform.get(target, '')})", lang="en")
            add(
                out,
                lu,
                RDFS.comment,
                "Automatically inferred thematic association (embedding similarity). It does not assert influence, derivation or agreement between the linked processes.",
                lang="en",
            )
            out.add((lu, PROV.wasGeneratedBy, activity))
            out.add((uri, DEL.hasAnnotation, lu))
            n_links += 1
            if rank >= args.top_k:
                break
        if ev_vecs is not None:
            esims = ev_vecs @ qv_raw  # concept labels are compared on the uncentered embedding
            for r, idx in enumerate(np.argsort(-esims)[: args.eurovoc_top_k], start=1):
                if esims[idx] < args.eurovoc_min_similarity:
                    break
                concept = URIRef(ev_uris[idx])
                lu = res(f"link_{slug(str(uri).rsplit('/', 1)[-1])}_eurovoc_{r}")
                out.add((lu, RDF.type, DEL.ProcessLink))
                out.add((lu, DEL.linkSource, uri))
                out.add((lu, DEL.linkTarget, concept))
                add(out, lu, DEL.linkType, "inferred")
                add(out, lu, DEL.linkRelation, "eurovoc_concept_candidate")
                add(out, lu, DEL.annotationMethod, "eurovoc_label_embedding_cosine")
                add(out, lu, DEL.annotationMethodVersion, METHOD_VERSION)
                add(out, lu, DEL.model, MODEL_NAME)
                add(out, lu, DEL.similarity, round(float(esims[idx]), 4), datatype=XSD.decimal)
                add(out, lu, DEL.rank, r, datatype=XSD.integer)
                add(out, lu, RDFS.label, f"EuroVoc candidate: {label(src, uri)} ~ {eurovoc[ev_uris[idx]]}", lang="en")
                out.add((lu, PROV.wasGeneratedBy, activity))
                out.add((uri, DEL.hasAnnotation, lu))
                # deliberately no skos:closeMatch assertion: the link stays a scored candidate
                n_ev += 1

    out.serialize(destination=args.output, format="turtle")
    print(f"queries={len(queries)} thematic_links={n_links} eurovoc_links={n_ev} triples={len(out)} -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
