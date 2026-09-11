#!/usr/bin/env python3
"""
CrowdLaw / Citizen Portal (portale-cittadino-mvp) -> DEL source graph.

Reads the portal's SQLite database (documents with Akoma Ntoso XML, articles,
comments with user-chosen and system-resolved anchors, stance labels,
clusters, PCA coordinates, aspects) and the evaluation ground-truth files, and
writes:

  knowledge_graph/sources/crowdlaw_kg.ttl        (source graph, Turtle)
  data/crowdlaw/reconciliation_report.json       (counts + exclusions)

Only the documents listed in the local config (the evaluation corpora of the
paper, seeded with synthetic comments and ground truth) are imported; the
developer test documents of the prototype database are excluded and counted.

Field-level mapping: documentation/delibai_crowdlaw_integration.md
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, FOAF, PROV, RDF, RDFS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    DEL,
    REPO_ROOT,
    SOURCES_DIR,
    Report,
    add,
    add_datetime,
    add_import_provenance,
    bind_namespaces,
    load_json,
    parse_datetime,
    res,
    screen_text,
    slug,
    write_graph,
)

IMPORT_VERSION = "crowdlaw-import-1.0.0"
MAPPING_VERSION = "crowdlaw-del-mapping-1.0.0"
SOURCE_KEY = "crowdlaw"

FORUM_URI = res("forum_crowdlaw")
DATASET_URI = res("dataset_crowdlaw_evaluation_2026")
RESEARCH_TEAM_URI = res("crowdlaw_research_team")
FACILITATOR_ROLE_URI = res("crowdlaw_role_facilitator")
PLATFORM_NAME = "CrowdLaw (Portale del Cittadino)"

SBERT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

STANCE_LABELS_IT = {"pro": "favorevole", "contro": "contrario", "neutro": "neutro", "altro": "altro"}


# ---------------------------------------------------------------------------
# AKN helpers
# ---------------------------------------------------------------------------
def frbr(root: ET.Element) -> dict:
    def get(node, tag):
        if node is None:
            return ""
        el = node.find("{*}" + tag)
        if el is None:
            return ""
        return el.attrib.get("value") or el.attrib.get("date") or ""

    work = root.find(".//{*}FRBRWork")
    expr = root.find(".//{*}FRBRExpression")
    man = root.find(".//{*}FRBRManifestation")
    return {
        "work_this": get(work, "FRBRthis"),
        "work_uri": get(work, "FRBRuri"),
        "work_date": get(work, "FRBRdate"),
        "expr_this": get(expr, "FRBRthis"),
        "expr_uri": get(expr, "FRBRuri"),
        "expr_date": get(expr, "FRBRdate"),
        "expr_lang": (expr.find("{*}FRBRlanguage").attrib.get("language") if expr is not None and expr.find("{*}FRBRlanguage") is not None else ""),
        "man_this": get(man, "FRBRthis"),
        "man_uri": get(man, "FRBRuri"),
    }


def parse_segments(root: ET.Element) -> dict[str, list[str]]:
    """eId -> list of paragraph texts (same rule as the portal: one <p> = one segment)."""
    out: dict[str, list[str]] = {}
    for article in root.findall(".//{*}article"):
        e_id = article.get("eId") or article.get("id") or ""
        segs = []
        for p in article.findall(".//{*}p"):
            txt = " ".join(t.strip() for t in p.itertext() if t and t.strip()).strip()
            if txt:
                segs.append(txt)
        out[e_id] = segs
    return out


# ---------------------------------------------------------------------------
# URI helpers
# ---------------------------------------------------------------------------
def process_uri(doc_id: int) -> URIRef:
    return res(f"crowdlaw_consultation_doc{int(doc_id)}")


def work_uri_for(work_uri: str) -> URIRef:
    return res(f"crowdlaw_work_{slug(work_uri)}")


def expression_uri_for(expr_uri: str) -> URIRef:
    return res(f"crowdlaw_expression_{slug(expr_uri)}")


def provision_uri_for(expr_uri: str, e_id: str) -> URIRef:
    return res(f"crowdlaw_provision_{slug(expr_uri)}_{slug(e_id)}")


def segment_uri_for(expr_uri: str, e_id: str, index: int) -> URIRef:
    return res(f"crowdlaw_provision_{slug(expr_uri)}_{slug(e_id)}_segment_{index}")


def comment_uri(cid: int) -> URIRef:
    return res(f"crowdlaw_comment_{int(cid)}")


def participant_uri(author: str) -> URIRef:
    return res(f"crowdlaw_participant_{slug(author)}")


def cluster_uri(doc_id: int, key: int) -> URIRef:
    return res(f"crowdlaw_cluster_doc{int(doc_id)}_{int(key)}")


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------
def build_graph(cfg: dict, report: Report) -> Graph:
    g = Graph()
    bind_namespaces(g)
    db_path = Path(cfg["db_path"])
    portal_repo = Path(cfg["portal_repo"])
    included_docs = {int(d["doc_id"]): d for d in cfg["documents"]}
    landing = cfg.get("landing_page")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    activity = add_import_provenance(
        g,
        source_key=SOURCE_KEY,
        dataset_uri=DATASET_URI,
        title="CrowdLaw / Citizen Portal - evaluation corpora (Italian parliamentary bills, 2026)",
        description=(
            "Comments anchored to Akoma Ntoso passages of three Italian parliamentary bills, produced to "
            "evaluate the Citizen Portal research prototype (ICEDEG 2026 paper). Comments are synthetic, "
            "seeded by the research team with pseudonymous authors and a ground-truth stance and target "
            "article; the system-resolved anchors, NLI stance labels, clusters and PCA coordinates are the "
            "prototype's own outputs. Not a real public consultation."
        ),
        import_version=IMPORT_VERSION,
        mapping_version=MAPPING_VERSION,
        snapshot_date=cfg.get("snapshot_date"),
        script_name="scripts/integration/import_crowdlaw.py",
        dataset_status="synthetic-evaluation",
        landing_page=landing,
        license_uri=None,
    )

    g.add((FORUM_URI, RDF.type, DEL.Forum))
    add(g, FORUM_URI, DEL.name, PLATFORM_NAME)
    add(g, FORUM_URI, RDFS.label, PLATFORM_NAME, lang="it")
    add(
        g,
        FORUM_URI,
        DCTERMS.description,
        "Prototipo di ricerca per la consultazione pubblica su disegni di legge codificati in Akoma Ntoso: "
        "i cittadini ancorano i commenti a passaggi specifici, propongono modifiche con motivazione separata "
        "e il sistema traccia anchoring, stance, cluster e distanza semantica.",
        lang="it",
    )
    if landing:
        g.add((FORUM_URI, DEL.url, Literal(landing, datatype=XSD.anyURI)))

    g.add((RESEARCH_TEAM_URI, RDF.type, DEL.Participant))
    add(g, RESEARCH_TEAM_URI, DEL.name, "Citizen Portal research team", lang="en")
    add(g, RESEARCH_TEAM_URI, FOAF.name, "Citizen Portal research team")
    add(g, RESEARCH_TEAM_URI, DEL.participantType, "RESEARCH_TEAM")
    g.add((RESEARCH_TEAM_URI, DEL.hasRole, FACILITATOR_ROLE_URI))
    g.add((FACILITATOR_ROLE_URI, RDF.type, DEL.Facilitator))
    add(g, FACILITATOR_ROLE_URI, RDFS.label, "Facilitator (evaluation design)", lang="en")

    # ---- Documents -----------------------------------------------------------
    documents = {int(r["id"]): dict(r) for r in conn.execute("SELECT id, filename, title, uploaded_at, raw_xml FROM documents")}
    report.read("documents", len(documents))
    expression_of_doc: dict[int, str] = {}
    article_info: dict[int, dict] = {}  # article row id -> info
    for doc_id, doc in documents.items():
        if doc_id not in included_docs:
            report.excluded("documents", "developer test document or duplicate upload (not an evaluation corpus)")
            continue
        try:
            root = ET.fromstring(doc["raw_xml"])
        except ET.ParseError as exc:
            report.failed("documents", f"doc {doc_id}: AKN parse error {exc}")
            continue
        ids = frbr(root)
        if not ids["expr_uri"]:
            report.failed("documents", f"doc {doc_id}: missing FRBRExpression")
            continue
        wu = work_uri_for(ids["work_uri"])
        eu = expression_uri_for(ids["expr_uri"])
        expression_of_doc[doc_id] = ids["expr_uri"]
        title = doc.get("title") or included_docs[doc_id].get("title") or doc["filename"]

        g.add((wu, RDF.type, DEL.LegalWork))
        g.add((wu, RDF.type, DEL.LegalSource))
        add(g, wu, RDFS.label, title, lang="it")
        add(g, wu, DEL.name, title, lang="it")
        add(g, wu, DEL.frbrWorkUri, ids["work_uri"])
        add(g, wu, DEL.identifier, ids["work_uri"])
        add(g, wu, DCTERMS.date, ids["work_date"])
        add(g, wu, DEL.annotationLabel, included_docs[doc_id].get("short_label"))

        g.add((eu, RDF.type, DEL.LegalExpression))
        g.add((eu, RDF.type, DEL.LegalSource))
        g.add((eu, DEL.expressionOf, wu))
        add(g, eu, RDFS.label, f"{title} (versione {ids['expr_lang'] or 'ita'})", lang="it")
        add(g, eu, DEL.name, title, lang="it")
        add(g, eu, DEL.frbrExpressionUri, ids["expr_uri"])
        add(g, eu, DEL.frbrManifestationUri, ids["man_this"] or ids["man_uri"])
        add(g, eu, DEL.identifier, ids["expr_this"] or ids["expr_uri"])
        add(g, eu, DEL.sourceFilename, doc["filename"])
        add(g, eu, DCTERMS.language, "it")
        add(g, eu, DCTERMS.source, "CIRSFID GenAI4Lex Camera-Bill collection (Legislature XVIII-XIX AKN archive)")
        add(g, eu, DEL.url, included_docs[doc_id].get("source_url"), datatype=XSD.anyURI)

        pu = process_uri(doc_id)
        g.add((pu, RDF.type, DEL.DeliberationProcess))
        add(g, pu, DEL.identifier, f"crowdlaw_consultation_doc{doc_id}")
        add(g, pu, DEL.name, f"Consultazione sul disegno di legge: {included_docs[doc_id].get('short_label') or title}", lang="it")
        add(g, pu, RDFS.label, f"Consultazione sul disegno di legge: {included_docs[doc_id].get('short_label') or title}", lang="it")
        add(
            g,
            pu,
            DCTERMS.description,
            f"Corpus di valutazione del Portale del Cittadino sul disegno di legge «{title}» "
            f"({doc['filename']}). I commenti sono stati generati dal gruppo di ricerca con autori pseudonimi, "
            "stance e articolo di destinazione noti (ground truth), per valutare anchoring semantico, "
            "inferenza della stance e clustering. Non si tratta di una consultazione pubblica reale.",
            lang="it",
        )
        g.add((pu, DEL.takesPlaceIn, FORUM_URI))
        add(g, pu, DEL.platform, PLATFORM_NAME)
        add(g, pu, DCTERMS.language, "it")
        add(g, pu, DEL.datasetStatus, "synthetic-evaluation")
        g.add((pu, DEL.references, eu))
        g.add((pu, DCTERMS.isPartOf, DATASET_URI))
        g.add((pu, PROV.wasGeneratedBy, activity))
        g.add((pu, DEL.hasParticipant, RESEARCH_TEAM_URI))
        add_datetime(g, pu, DCTERMS.created, doc.get("uploaded_at"))
        add(g, pu, DEL.sourceRecordId, str(doc_id))
        add(g, pu, DEL.sourceTable, "documents")

        # articles + segments
        segments = parse_segments(root)
        arts = list(conn.execute("SELECT id, e_id, num, heading, text FROM articles WHERE doc_id = ? ORDER BY id", (doc_id,)))
        report.read("articles", len(arts))
        for a in arts:
            prov_uri = provision_uri_for(ids["expr_uri"], a["e_id"] or f"art_{a['id']}")
            article_info[int(a["id"])] = {"uri": prov_uri, "doc_id": doc_id, "e_id": a["e_id"], "num": a["num"], "heading": a["heading"]}
            g.add((prov_uri, RDF.type, DEL.LegalProvision))
            g.add((prov_uri, RDF.type, DEL.LegalSource))
            g.add((prov_uri, DEL.partOfExpression, eu))
            add(g, prov_uri, DEL.eId, a["e_id"])
            add(g, prov_uri, DEL.articleNumber, a["num"])
            add(g, prov_uri, DEL.heading, a["heading"], lang="it")
            label = " ".join(x for x in [a["num"], a["heading"]] if x).strip() or (a["e_id"] or f"article {a['id']}")
            add(g, prov_uri, RDFS.label, label, lang="it")
            add(g, prov_uri, DEL.name, label, lang="it")
            add(g, prov_uri, DEL.text, a["text"], lang="it")
            add(g, prov_uri, DCTERMS.language, "it")
            add(g, prov_uri, DEL.sourceRecordId, str(a["id"]))
            add(g, prov_uri, DEL.sourceTable, "articles")
            for i, seg_text in enumerate(segments.get(a["e_id"] or "", [])):
                su = segment_uri_for(ids["expr_uri"], a["e_id"], i)
                g.add((su, RDF.type, DEL.LegalProvision))
                g.add((su, DEL.partOfExpression, eu))
                g.add((su, DCTERMS.isPartOf, prov_uri))
                add(g, su, DEL.segmentIndex, i, datatype=XSD.integer)
                add(g, su, DEL.text, seg_text, lang="it")
                add(g, su, RDFS.label, f"{label} - segmento {i + 1}", lang="it")
            report.imported("articles")
        report.imported("documents")

        # aspects (article + segment level)
        meta = conn.execute("SELECT method, updated_at FROM aspects_meta WHERE doc_id = ?", (doc_id,)).fetchone()
        method = (meta["method"] if meta else None) or "deterministic"
        method_label = {"deterministic": "tfidf_keyphrases_cosine_merge", "llm": "tfidf_keyphrases_llm_merge"}.get(method, method)
        for row in conn.execute("SELECT id, article_id, aspects_json, created_at FROM article_aspects WHERE doc_id = ?", (doc_id,)):
            report.read("article_aspects")
            info = article_info.get(int(row["article_id"]))
            aspects = json.loads(row["aspects_json"] or "[]")
            if not info or not aspects:
                report.excluded("article_aspects", "empty aspect list or unknown article")
                continue
            au = res(f"crowdlaw_provision_{slug(ids['expr_uri'])}_{slug(info['e_id'])}_aspects")
            g.add((au, RDF.type, DEL.AspectAnnotation))
            g.add((au, RDF.type, DEL.AutomatedAnnotation))
            g.add((au, DEL.annotates, info["uri"]))
            g.add((info["uri"], DEL.hasAnnotation, au))
            for asp in aspects:
                add(g, au, DEL.annotationLabel, asp, lang="it")
            add(g, au, DEL.annotationMethod, method_label)
            add_datetime(g, au, DEL.timestamp, row["created_at"])
            g.add((au, PROV.wasGeneratedBy, activity))
            report.imported("article_aspects")
        for row in conn.execute("SELECT id, article_id, segment_index, aspects_json, created_at FROM segment_aspects WHERE doc_id = ?", (doc_id,)):
            report.read("segment_aspects")
            info = article_info.get(int(row["article_id"]))
            aspects = json.loads(row["aspects_json"] or "[]")
            if not info or not aspects:
                report.excluded("segment_aspects", "empty aspect list or unknown article")
                continue
            su = segment_uri_for(ids["expr_uri"], info["e_id"], int(row["segment_index"]))
            if (su, RDF.type, DEL.LegalProvision) not in g:
                report.excluded("segment_aspects", "segment index not found in AKN text")
                continue
            au = res(f"crowdlaw_provision_{slug(ids['expr_uri'])}_{slug(info['e_id'])}_segment_{int(row['segment_index'])}_aspects")
            g.add((au, RDF.type, DEL.AspectAnnotation))
            g.add((au, RDF.type, DEL.AutomatedAnnotation))
            g.add((au, DEL.annotates, su))
            g.add((su, DEL.hasAnnotation, au))
            for asp in aspects:
                add(g, au, DEL.annotationLabel, asp, lang="it")
            add(g, au, DEL.annotationMethod, method_label)
            add_datetime(g, au, DEL.timestamp, row["created_at"])
            g.add((au, PROV.wasGeneratedBy, activity))
            report.imported("segment_aspects")

        # clusters
        clusters = list(conn.execute("SELECT id, label, size, top_terms, cluster_key FROM clusters WHERE doc_id = ? ORDER BY id", (doc_id,)))
        report.read("clusters", len(clusters))
        for c in clusters:
            if c["cluster_key"] is None:
                report.excluded("clusters", "cluster without cluster_key (older processing run) - cannot be joined to comments")
                continue
            cu = cluster_uri(doc_id, int(c["cluster_key"]))
            g.add((cu, RDF.type, DEL.Topic))
            add(g, cu, DEL.identifier, f"doc{doc_id}-cluster-{c['cluster_key']}")
            add(g, cu, RDFS.label, f"Cluster {c['cluster_key']}: {c['label']}", lang="it")
            add(g, cu, DEL.name, c["label"], lang="it")
            add(g, cu, DEL.topicWords, c["top_terms"] or c["label"], lang="it")
            add(g, cu, DEL.clusterKey, int(c["cluster_key"]), datatype=XSD.integer)
            add(g, cu, DEL.clusterSize, int(c["size"]), datatype=XSD.integer)
            add(g, cu, DEL.annotationMethod, "kmeans_on_comment_minus_anchor_sbert_embeddings_tfidf_labels")
            add(g, cu, DEL.model, SBERT_MODEL)
            add(g, cu, DEL.datasetStatus, "derived-annotation")
            g.add((pu, DEL.hasTopic, cu))
            g.add((cu, PROV.wasGeneratedBy, activity))
            report.imported("clusters")

    # ---- Ground truth (research annotation) -------------------------------------
    ground_truth: dict[int, dict] = {}
    gt_by_author: dict[tuple, dict] = {}
    for doc_id, dcfg in included_docs.items():
        gt_file = dcfg.get("ground_truth")
        if not gt_file:
            continue
        path = portal_repo / gt_file
        if not path.exists():
            report.warn(f"ground truth file missing: {path}")
            continue
        for item in load_json(path):
            report.read("ground_truth")
            if item.get("comment_id") is not None:
                ground_truth[int(item["comment_id"])] = item
            else:
                gt_by_author[(doc_id, item.get("author"))] = item

    # ---- Comments -----------------------------------------------------------------
    comments = list(conn.execute("SELECT * FROM comments ORDER BY id"))
    cols = comments[0].keys() if comments else []
    has_proposal_cols = "proposed_change_text" in cols
    report.notes["proposal_columns_present_in_db"] = has_proposal_cols
    dates_per_doc: dict[int, list] = defaultdict(list)
    participants_seen: set[str] = set()
    for c in comments:
        report.read("comments")
        doc_id = int(c["doc_id"])
        if doc_id not in expression_of_doc:
            report.excluded("comments", "belongs to an excluded document (developer test data)")
            continue
        content = (c["content"] or "").strip()
        if not content:
            report.excluded("comments", "empty content")
            continue
        hits = screen_text(content)
        if hits:
            report.warn(f"comment {c['id']} matched personal-data patterns {hits}")
        expr = expression_of_doc[doc_id]
        eu = expression_uri_for(expr)
        pu = process_uri(doc_id)
        cu = comment_uri(c["id"])
        author = c["author"] or "anon"
        au = participant_uri(author)
        if author not in participants_seen:
            participants_seen.add(author)
            g.add((au, RDF.type, DEL.Participant))
            add(g, au, DEL.identifier, author)
            add(g, au, DEL.name, author)
            add(g, au, FOAF.name, author)
            add(g, au, DEL.participantType, "SYNTHETIC_EVALUATION_AUTHOR")
            add(g, au, RDFS.comment, "Pseudonymous author generated by the evaluation seeding scripts; not a real person.", lang="en")
        g.add((pu, DEL.hasParticipant, au))

        g.add((cu, RDF.type, DEL.Contribution))
        add(g, cu, DEL.identifier, f"comment-{c['id']}")
        add(g, cu, DEL.sourceTable, "comments")
        add(g, cu, DEL.sourceRecordId, str(c["id"]))
        add(g, cu, DEL.text, content, lang="it")
        add(g, cu, DCTERMS.language, "it")
        add_datetime(g, cu, DEL.timestamp, c["created_at"])
        dt = parse_datetime(c["created_at"])
        if dt:
            dates_per_doc[doc_id].append(dt)
        g.add((cu, DEL.madeBy, au))
        g.add((cu, DEL.isPartOf, pu))
        g.add((pu, DEL.hasContribution, cu))
        add(g, cu, DEL.platform, PLATFORM_NAME)
        add(g, cu, DEL.contributionSource, "synthetic_seed")
        add(g, cu, DEL.contributionKind, "comment")
        add(g, cu, DEL.datasetStatus, "synthetic-evaluation")
        g.add((cu, PROV.wasGeneratedBy, activity))
        g.add((cu, DEL.references, eu))

        # proposal fields: from the dedicated columns when the schema has them,
        # otherwise from the platform's own composed content format
        # ("Richiesta di rimozione..." / "Proposta di modifica:\n..." / "Motivazione:\n...",
        # see backend/app/main.py:_compose_comment_content in the portal).
        proposed_text = motivation = None
        removal = False
        if has_proposal_cols:
            proposed_text = c["proposed_change_text"]
            motivation = c["motivation_text"]
            removal = bool(c["removal_requested"])
        if not (proposed_text or motivation or removal):
            parsed = parse_composed_content(content)
            proposed_text = proposed_text or parsed.get("proposed_text")
            motivation = motivation or parsed.get("motivation")
            removal = removal or parsed.get("removal", False)
            if parsed:
                report.imported("proposal_fields_parsed_from_content")
        add(g, cu, DEL.proposedText, proposed_text, lang="it")
        add(g, cu, DEL.motivation, motivation, lang="it")
        if removal:
            add(g, cu, DEL.proposedOperation, "remove")
        elif proposed_text:
            add(g, cu, DEL.proposedOperation, "modify")
        has_proposal = bool(proposed_text or removal)

        # anchors
        declared = article_info.get(int(c["article_id"])) if c["article_id"] is not None else None
        selected = article_info.get(int(c["selection_article_id"])) if c["selection_article_id"] is not None else None
        predicted = article_info.get(int(c["predicted_article_id"])) if c["predicted_article_id"] is not None else None
        user_provision = (selected or declared)
        if user_provision:
            g.add((cu, DEL.aboutProvision, user_provision["uri"]))
            if has_proposal:
                g.add((cu, DEL.proposesChangeTo, user_provision["uri"]))
            ua = res(f"crowdlaw_comment_{int(c['id'])}_anchor_user")
            g.add((ua, RDF.type, DEL.LegalResourceAnchor))
            g.add((cu, DEL.hasAnchor, ua))
            g.add((ua, DEL.anchorProvision, user_provision["uri"]))
            g.add((ua, DEL.anchorExpression, eu))
            add(g, ua, DEL.anchorMethod, "user_selection" if selected else "user_declared")
            kind = (c["selection_kind"] or "").lower()
            add(g, ua, DEL.anchorKind, {"partial": "range", "range": "range", "full": "article", "article": "article"}.get(kind, "article" if not c["selection_text"] else "range"))
            add(g, ua, DEL.anchorText, c["selection_text"], lang="it")
            g.add((ua, PROV.wasAttributedTo, au))
            report.imported("anchors_user")
        else:
            report.excluded("anchors_user", "comment without declared or selected article")
        if predicted:
            sa = res(f"crowdlaw_comment_{int(c['id'])}_anchor_system")
            g.add((sa, RDF.type, DEL.LegalResourceAnchor))
            g.add((cu, DEL.hasAnchor, sa))
            g.add((sa, DEL.anchorProvision, predicted["uri"]))
            g.add((sa, DEL.anchorExpression, eu))
            add(g, sa, DEL.anchorMethod, "system_prediction")
            add(g, sa, DEL.anchorKind, "article")
            add(g, sa, DEL.annotationMethod, "sbert_cosine_argmax")
            add(g, sa, DEL.model, SBERT_MODEL)
            add(g, sa, DEL.confidence, c["similarity"], datatype=XSD.decimal)
            if user_provision:
                add(g, sa, DEL.anchorsAgree, predicted["uri"] == user_provision["uri"])
            report.imported("anchors_system")
        else:
            report.excluded("anchors_system", "no system-resolved anchor stored")

        # stance (system or seed label)
        if c["sentiment"]:
            method = c["sentiment_method"]
            st = res(f"crowdlaw_comment_{int(c['id'])}_stance")
            g.add((st, RDF.type, DEL.StanceAnnotation))
            g.add((st, DEL.annotates, cu))
            g.add((cu, DEL.hasAnnotation, st))
            add(g, st, DEL.stanceLabel, c["sentiment"])
            add(g, st, DEL.annotationLabel, STANCE_LABELS_IT.get(c["sentiment"], c["sentiment"]), lang="it")
            add(g, st, DEL.confidence, c["sentiment_conf"], datatype=XSD.decimal)
            if method == "manual":
                g.add((st, RDF.type, DEL.HumanAnnotation))
                add(g, st, DEL.annotationMethod, "seed_ground_truth")
                g.add((st, PROV.wasAttributedTo, RESEARCH_TEAM_URI))
            elif method == "nli":
                g.add((st, RDF.type, DEL.AutomatedAnnotation))
                add(g, st, DEL.annotationMethod, "nli_cross_encoder_targeted_stance")
                add(g, st, DEL.model, NLI_MODEL)
            elif method == "targeted":
                g.add((st, RDF.type, DEL.AutomatedAnnotation))
                add(g, st, DEL.annotationMethod, "llm_targeted_stance_openrouter")
                add(g, st, RDFS.comment, "LLM fallback; the model identifier was not recorded by the source.", lang="en")
            else:
                g.add((st, RDF.type, DEL.AutomatedAnnotation))
                add(g, st, DEL.annotationMethod, "unrecorded")
                report.warn(f"comment {c['id']}: stance without recorded method")
            target = selected or declared or predicted
            if target:
                g.add((st, DEL.annotationTarget, target["uri"]))
            g.add((st, PROV.wasGeneratedBy, activity))
            report.imported("stance_annotations")

        # ground truth as separate research annotation (only when it adds information)
        gt = ground_truth.get(int(c["id"])) or gt_by_author.get((doc_id, author))
        if gt and gt.get("stance") and not (c["sentiment_method"] == "manual" and gt["stance"] == c["sentiment"]):
            gu = res(f"crowdlaw_comment_{int(c['id'])}_ground_truth")
            g.add((gu, RDF.type, DEL.StanceAnnotation))
            g.add((gu, RDF.type, DEL.HumanAnnotation))
            g.add((gu, DEL.annotates, cu))
            g.add((cu, DEL.hasAnnotation, gu))
            add(g, gu, DEL.stanceLabel, gt["stance"])
            add(g, gu, DEL.annotationLabel, STANCE_LABELS_IT.get(gt["stance"], gt["stance"]), lang="it")
            add(g, gu, DEL.annotationMethod, "seed_ground_truth")
            g.add((gu, PROV.wasAttributedTo, RESEARCH_TEAM_URI))
            gt_art = article_info.get(int(gt["article_id"])) if gt.get("article_id") is not None else None
            if gt_art:
                g.add((gu, DEL.annotationTarget, gt_art["uri"]))
            report.imported("ground_truth")
        elif gt:
            report.imported("ground_truth")  # already represented by the manual stance annotation

        # cluster + PCA
        if c["cluster_id"] is not None:
            cu_cluster = cluster_uri(doc_id, int(c["cluster_id"]))
            if (cu_cluster, RDF.type, DEL.Topic) in g:
                g.add((cu, DEL.hasTopic, cu_cluster))
            else:
                report.warn(f"comment {c['id']}: cluster {c['cluster_id']} not found for doc {doc_id}")
        if c["pca_x"] is not None and c["pca_y"] is not None:
            add(g, cu, DEL.pcaX, round(float(c["pca_x"]), 6), datatype=XSD.decimal)
            add(g, cu, DEL.pcaY, round(float(c["pca_y"]), 6), datatype=XSD.decimal)
        report.imported("comments")

    # process dates from data
    for doc_id, dts in dates_per_doc.items():
        pu = process_uri(doc_id)
        add(g, pu, DEL.startDate, min(dts).isoformat(), datatype=XSD.dateTime)
        add(g, pu, DEL.endDate, max(dts).isoformat(), datatype=XSD.dateTime)
        add(g, pu, DCTERMS.date, min(dts).date().isoformat(), datatype=XSD.date)

    # evaluation metrics of the paper (anchoring accuracy), per document
    for doc_id, dcfg in included_docs.items():
        ev = dcfg.get("eval_results")
        if not ev:
            continue
        path = portal_repo / ev
        if not path.exists():
            report.warn(f"eval results missing: {path}")
            continue
        data = load_json(path)
        pu = process_uri(doc_id)
        flat = _flatten("", data)
        n = 0
        for key, value in flat.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            mu = res(f"crowdlaw_consultation_doc{doc_id}_metric_{slug(key)}")
            g.add((mu, RDF.type, DEL.InformationResource))
            add(g, mu, DEL.metricType, "evaluation")
            add(g, mu, DEL.metricName, key)
            add(g, mu, DEL.metricValue, value, datatype=XSD.decimal if isinstance(value, float) else XSD.integer)
            g.add((mu, PROV.wasDerivedFrom, pu))
            g.add((pu, DEL.hasAnnotation, mu))
            n += 1
        report.notes[f"eval_metrics_doc{doc_id}"] = n

    report.notes["included_documents"] = sorted(included_docs)
    return g


_SECTION_RE = re.compile(r"^(Richiesta di rimozione del segmento selezionato\.|Proposta di modifica:|Motivazione:)\s*", re.M)


def parse_composed_content(content: str) -> dict:
    """Split a comment composed by the portal into its structured parts.
    Returns {} when the content does not follow the composed format."""
    if not content or not _SECTION_RE.search(content):
        return {}
    out: dict = {}
    parts = _SECTION_RE.split(content)
    # parts: [pre, marker, body, marker, body, ...]
    for i in range(1, len(parts) - 1, 2):
        marker, body = parts[i], parts[i + 1].strip()
        if marker.startswith("Richiesta di rimozione"):
            out["removal"] = True
        elif marker.startswith("Proposta di modifica"):
            out["proposed_text"] = body or None
        elif marker.startswith("Motivazione"):
            out["motivation"] = body or None
    return out


def _flatten(prefix: str, obj) -> dict:
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(f"{prefix}_{k}" if prefix else str(k), v))
    elif isinstance(obj, list):
        return out  # lists of examples are not metrics
    else:
        out[prefix] = obj
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(REPO_ROOT / "config/integration/crowdlaw.json"))
    ap.add_argument("--output", default=str(SOURCES_DIR / "crowdlaw_kg.ttl"))
    ap.add_argument("--report", default=str(REPO_ROOT / "data/crowdlaw/reconciliation_report.json"))
    args = ap.parse_args()
    cfg = load_json(Path(args.config))
    report = Report(SOURCE_KEY, IMPORT_VERSION, MAPPING_VERSION)
    g = build_graph(cfg, report)
    write_graph(g, Path(args.output))
    report.notes["output"] = args.output
    report.write(Path(args.report), g)
    print(json.dumps(report.to_dict(g), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
