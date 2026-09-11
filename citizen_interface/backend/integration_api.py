#!/usr/bin/env python3
"""
Citizen interface - inspection API for annotated sources (DelibAI, CrowdLaw)
and generic, paginated access to contributions of any process.

Registered as a Flask blueprint by simple_server.py; works on the same
in-memory rdflib graph. All lookups are direct triple scans (no SPARQL) so they
stay fast on the 240 MB graph.

Endpoints
  GET /api/platforms                       forums/platforms with counts and logos
  GET /api/process/summary?uri=            computed statistics, topics, legal documents, links, provenance
  GET /api/process/contributions?uri=&offset=&limit=&kind=&topic=&condition=
  GET /api/resource/inspect?uri=           human-readable, type-aware view of any resource (+ raw triples)
  GET /api/links?uri=                      explicit / human / inferred links touching a resource
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

from flask import Blueprint, jsonify, request
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, PROV, RDF, RDFS, SKOS

logger = logging.getLogger(__name__)

DEL = "https://w3id.org/deliberation/ontology#"
RES = "https://svagnoni.linkeddata.es/resource/"


def D(name: str) -> URIRef:
    return URIRef(DEL + name)


bp = Blueprint("integration_api", __name__)
_state: dict = {"kg": None, "platforms": None, "labels": {}}

# Logos shipped with the citizen interface (served from /images/) or the DKG site.
PLATFORM_LOGOS = {
    "forum_delibai": {"logo": "/images/delibai-logo.png", "alt": "DelibAI logo (official mascot)", "official": True},
    "forum_crowdlaw": {"logo": "/images/crowdlaw-logo.svg", "alt": "CrowdLaw / Portale del Cittadino brand mark (rendered from the platform's CSS mark; no official raster logo exists)", "official": False},
    "forum_decidim_barcelona": {"logo": "https://dkg.svagnoni.linkeddata.es/img/decidim.png", "alt": "Decidim logo", "official": True},
    "forum_decide_madrid": {"logo": "https://dkg.svagnoni.linkeddata.es/img/decide-madrid.png", "alt": "Decide Madrid logo", "official": True},
    "forum_eu_have_your_say": {"logo": "https://dkg.svagnoni.linkeddata.es/img/hys.jpg", "alt": "EU Have Your Say logo", "official": True},
    "forum_european_parliament": {"logo": "https://dkg.svagnoni.linkeddata.es/img/european-parliament.png", "alt": "European Parliament logo", "official": True},
    "forum_polis": {"logo": "https://dkg.svagnoni.linkeddata.es/img/polis-logo.png", "alt": "Pol.is logo", "official": True},
    "forum_cip": {"logo": "https://dkg.svagnoni.linkeddata.es/img/logo-global-dialogues-cip.png", "alt": "CIP Global Dialogues logo", "official": True},
    "forum_scotus": {"logo": "https://dkg.svagnoni.linkeddata.es/img/us-sup-court.png", "alt": "US Supreme Court logo", "official": True},
    "forum_habermas": {"logo": "https://dkg.svagnoni.linkeddata.es/img/deepmind-color.png", "alt": "Google DeepMind logo", "official": True},
    "forum_your_priorities": {"logo": None, "alt": "Your Priorities", "official": False},
}

TYPE_LABELS = {
    "Contribution": "Contribution",
    "DeliberationProcess": "Deliberation process",
    "Participant": "Participant",
    "ArtificialAgent": "Artificial agent (model)",
    "AIFeedback": "AI feedback",
    "FallacyAnnotation": "Fallacy label",
    "StanceAnnotation": "Stance label",
    "AspectAnnotation": "Key aspects",
    "PeerEvaluation": "Peer evaluation",
    "AnnotationResponse": "Recorded response to an annotation",
    "AutomatedAnnotation": "Automated annotation",
    "HumanAnnotation": "Human annotation",
    "ModelRun": "Model run",
    "LegalResourceAnchor": "Anchor to legal text",
    "LegalProvision": "Legal provision",
    "LegalExpression": "Legal document (version)",
    "LegalWork": "Legal document (work)",
    "LegalSource": "Legal source",
    "ProcessLink": "Link between resources",
    "Topic": "Topic",
    "Forum": "Platform / forum",
    "FallacyType": "Fallacy type",
    "InformationResource": "Information resource",
    "ImportActivity": "Import activity",
    "Position": "Position",
    "Stage": "Stage",
    "Role": "Role",
    "Facilitator": "Facilitator role",
}

# Predicates whose objects should not be exposed as raw values (none of the
# importers write them; kept as a defensive allow-list of excluded terms).
HIDDEN_PREDICATES = set()

MAX_INCOMING = 200


def init(kg: Graph) -> None:
    _state["kg"] = kg
    _state["platforms"] = None
    _state["labels"] = {}


def kg() -> Graph:
    return _state["kg"]


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------
def first(s, *preds):
    g = kg()
    for p in preds:
        for o in g.objects(s, p):
            return o
    return None


def values(s, p):
    return [o for o in kg().objects(s, p)]


def label_of(uri) -> str:
    if uri is None:
        return ""
    cache = _state["labels"]
    key = str(uri)
    if key in cache:
        return cache[key]
    v = first(uri, D("name"), RDFS.label, DCTERMS.title, FOAF.name, SKOS.prefLabel)
    lab = str(v) if v is not None else key.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
    if len(cache) < 200000:
        cache[key] = lab
    return lab


def types_of(uri) -> list[str]:
    out = []
    for t in kg().objects(uri, RDF.type):
        out.append(str(t).replace(DEL, "").replace(str(PROV), "prov:").replace(str(DCAT), "dcat:").replace(str(SKOS), "skos:"))
    return sorted(out)


def local(uri) -> str:
    return str(uri).rsplit("/", 1)[-1]


def lit(v):
    if isinstance(v, Literal):
        val = v.toPython() if v.datatype else str(v)
        if hasattr(val, "isoformat"):
            return val.isoformat()
        if isinstance(val, Literal):
            return str(val)
        return val
    return str(v)


def ref(uri):
    return {"uri": str(uri), "label": label_of(uri), "types": types_of(uri)}


def text_of(c) -> str:
    v = first(c, D("text"), RDFS.comment, D("content"))
    return str(v) if v is not None else ""


def author_of(c):
    a = first(c, D("madeBy"), D("author"))
    if a is None:
        return None
    return {"uri": str(a), "name": label_of(a), "type": str(first(a, D("participantType")) or "")}


# ---------------------------------------------------------------------------
# platforms
# ---------------------------------------------------------------------------
def _compute_platforms():
    g = kg()
    forums = {}
    for f in g.subjects(RDF.type, D("Forum")):
        key = local(f)
        procs = list(g.subjects(D("takesPlaceIn"), f))
        n_contrib = 0
        dates = []
        langs = Counter()
        status = Counter()
        for p in procs:
            n_contrib += sum(1 for _ in g.objects(p, D("hasContribution")))
            for d in (first(p, D("startDate")), first(p, D("endDate")), first(p, DCTERMS.date)):
                if d is not None:
                    dates.append(str(d)[:10])
            lang = first(p, DCTERMS.language)
            if lang is not None:
                langs[str(lang)] += 1
            st = first(p, D("datasetStatus"))
            if st is not None:
                status[str(st)] += 1
        info = PLATFORM_LOGOS.get(key, {"logo": None, "alt": label_of(f), "official": False})
        forums[key] = {
            "uri": str(f),
            "key": key,
            "name": label_of(f),
            "description": str(first(f, DCTERMS.description) or ""),
            "url": str(first(f, D("url")) or ""),
            "processes_count": len(procs),
            "contributions_count": n_contrib,
            "date_from": min(dates) if dates else None,
            "date_to": max(dates) if dates else None,
            "languages": sorted(langs),
            "dataset_status": sorted(status),
            "logo": info["logo"],
            "logo_alt": info["alt"],
            "logo_official": info["official"],
            "processes": [{"uri": str(p), "title": label_of(p)} for p in procs] if len(procs) <= 12 else [],
        }
    return sorted(forums.values(), key=lambda x: -x["contributions_count"])


@bp.route("/api/platforms")
def platforms():
    if kg() is None:
        return jsonify({"error": "Knowledge graph not loaded"}), 503
    if _state["platforms"] is None:
        _state["platforms"] = _compute_platforms()
    return jsonify({"platforms": _state["platforms"]})


# ---------------------------------------------------------------------------
# process summary
# ---------------------------------------------------------------------------
def _dataset_of(p):
    ds = first(p, DCTERMS.isPartOf)
    if ds is None or (ds, RDF.type, DCAT.Dataset) not in kg():
        return None
    act = first(ds, PROV.wasGeneratedBy)
    return {
        "uri": str(ds),
        "title": str(first(ds, DCTERMS.title) or ""),
        "description": str(first(ds, DCTERMS.description) or ""),
        "dataset_status": str(first(ds, D("datasetStatus")) or ""),
        "import_version": str(first(ds, D("importVersion")) or ""),
        "mapping_version": str(first(ds, D("mappingVersion")) or ""),
        "snapshot_date": lit(first(ds, D("sourceSnapshotDate"))) if first(ds, D("sourceSnapshotDate")) is not None else None,
        "landing_page": str(first(ds, DCAT.landingPage) or ""),
        "license": str(first(ds, DCTERMS.license) or ""),
        "import_activity": {"uri": str(act), "label": label_of(act), "started_at": lit(first(act, PROV.startedAtTime)) if act is not None and first(act, PROV.startedAtTime) is not None else None} if act is not None else None,
    }


def _links_of(uri, limit=50):
    g = kg()
    out = []
    seen = set()
    for pred in (D("linkSource"), D("linkTarget")):
        for l in g.subjects(pred, uri):
            if l in seen:
                continue
            seen.add(l)
            src = first(l, D("linkSource"))
            tgt = first(l, D("linkTarget"))
            other = tgt if str(src) == str(uri) else src
            out.append(
                {
                    "uri": str(l),
                    "link_type": str(first(l, D("linkType")) or ""),
                    "relation": str(first(l, D("linkRelation")) or ""),
                    "direction": "outgoing" if str(src) == str(uri) else "incoming",
                    "other": ref(other) if other is not None else None,
                    "other_platform": _platform_of(other) if other is not None else None,
                    "similarity": lit(first(l, D("similarity"))) if first(l, D("similarity")) is not None else None,
                    "rank": lit(first(l, D("rank"))) if first(l, D("rank")) is not None else None,
                    "method": str(first(l, D("annotationMethod")) or ""),
                    "method_version": str(first(l, D("annotationMethodVersion")) or ""),
                    "model": str(first(l, D("model")) or ""),
                    "label": str(first(l, RDFS.label) or ""),
                    "note": str(first(l, RDFS.comment) or ""),
                }
            )
            if len(out) >= limit:
                return out
    # explicit links carried by plain properties
    for pred, rel in ((D("references"), "references"), (SKOS.closeMatch, "closeMatch")):
        for o in g.objects(uri, pred):
            if (o, RDF.type, D("LegalExpression")) in g or (o, RDF.type, SKOS.Concept) in g:
                out.append({"uri": None, "link_type": "explicit" if rel == "references" else "inferred", "relation": rel, "direction": "outgoing", "other": ref(o), "similarity": None, "method": "", "label": f"{rel}: {label_of(o)}"})
    return out


def _platform_of(uri):
    g = kg()
    if uri is None:
        return None
    if (uri, RDF.type, D("DeliberationProcess")) in g:
        f = first(uri, D("takesPlaceIn"))
        if f is not None:
            return label_of(f)
        pl = first(uri, D("platform"))
        return str(pl) if pl is not None else None
    p = first(uri, D("isPartOf"))
    if p is not None:
        return _platform_of(p)
    if (uri, RDF.type, SKOS.Concept) in g:
        return "EuroVoc"
    return None


@bp.route("/api/process/summary")
def process_summary():
    uri = request.args.get("uri", "")
    g = kg()
    if not uri:
        return jsonify({"error": "URI parameter required"}), 400
    p = URIRef(uri)
    if (p, RDF.type, D("DeliberationProcess")) not in g:
        return jsonify({"error": "Process not found"}), 404
    contribs = list(g.objects(p, D("hasContribution")))
    kinds, conditions, sources, langs = Counter(), Counter(), Counter(), Counter()
    ai_feedback = 0
    ai_flags = 0
    peer_evals = 0
    responses = 0
    stances = Counter()
    anchors_user = anchors_system = 0
    authors = set()
    dates = []
    by_topic = Counter()
    for c in contribs:
        k = first(c, D("contributionKind"))
        kinds[str(k) if k is not None else "contribution"] += 1
        cond = first(c, D("experimentalCondition"))
        if cond is not None:
            conditions[str(cond)] += 1
        src = first(c, D("contributionSource"))
        sources[str(src) if src is not None else "participant"] += 1
        lang = first(c, DCTERMS.language)
        if lang is not None:
            langs[str(lang)] += 1
        a = first(c, D("madeBy"), D("author"))
        if a is not None:
            authors.add(str(a))
        d = first(c, D("timestamp"), DCTERMS.created)
        if d is not None:
            dates.append(str(d)[:10])
        for t in g.objects(c, D("hasTopic")):
            by_topic[str(t)] += 1
        for an in g.objects(c, D("hasAnnotation")):
            ts = set(g.objects(an, RDF.type))
            if D("AIFeedback") in ts:
                ai_feedback += 1
            elif D("FallacyAnnotation") in ts and D("AutomatedAnnotation") in ts:
                ai_flags += 1
            elif D("PeerEvaluation") in ts:
                peer_evals += 1
            elif D("AnnotationResponse") in ts:
                responses += 1
            elif D("StanceAnnotation") in ts:
                sl = first(an, D("stanceLabel"))
                if sl is not None and D("HumanAnnotation") not in ts:
                    stances[str(sl)] += 1
        for an in g.objects(c, D("hasAnchor")):
            m = str(first(an, D("anchorMethod")) or "")
            if m.startswith("user"):
                anchors_user += 1
            else:
                anchors_system += 1
    topics = []
    for t in g.objects(p, D("hasTopic")):
        topics.append(
            {
                "uri": str(t),
                "label": label_of(t),
                "description": str(first(t, DCTERMS.description) or ""),
                "top_terms": str(first(t, D("topicWords")) or ""),
                "contributions_count": by_topic.get(str(t), 0),
                "method": str(first(t, D("annotationMethod")) or ""),
            }
        )
    topics.sort(key=lambda x: -x["contributions_count"])
    legal_docs = []
    for e in g.objects(p, D("references")):
        if (e, RDF.type, D("LegalExpression")) in g:
            work = first(e, D("expressionOf"))
            provisions = [x for x in g.subjects(D("partOfExpression"), e) if first(x, D("segmentIndex")) is None]
            legal_docs.append(
                {
                    "uri": str(e),
                    "label": label_of(e),
                    "frbr_expression": str(first(e, D("frbrExpressionUri")) or ""),
                    "frbr_work": str(first(work, D("frbrWorkUri")) or "") if work is not None else "",
                    "work": ref(work) if work is not None else None,
                    "filename": str(first(e, D("sourceFilename")) or ""),
                    "language": str(first(e, DCTERMS.language) or ""),
                    "provisions_count": len(provisions),
                    "provisions": [{"uri": str(x), "label": label_of(x), "anchored_contributions": sum(1 for _ in g.subjects(D("anchorProvision"), x))} for x in sorted(provisions, key=lambda x: int(lit(first(x, D("sourceRecordId")) or 0)))],
                }
            )
    metrics = []
    for m in g.objects(p, D("hasAnnotation")):
        if first(m, D("metricName")) is not None:
            metrics.append({"name": str(first(m, D("metricName"))), "value": lit(first(m, D("metricValue"))), "type": str(first(m, D("metricType")) or "")})
    forum = first(p, D("takesPlaceIn"))
    out = {
        "uri": uri,
        "title": label_of(p),
        "description": str(first(p, DCTERMS.description) or ""),
        "platform": label_of(forum) if forum is not None else str(first(p, D("platform")) or ""),
        "platform_uri": str(forum) if forum is not None else None,
        "platform_logo": PLATFORM_LOGOS.get(local(forum), {}).get("logo") if forum is not None else None,
        "platform_logo_alt": PLATFORM_LOGOS.get(local(forum), {}).get("alt") if forum is not None else None,
        "platform_logo_official": PLATFORM_LOGOS.get(local(forum), {}).get("official") if forum is not None else None,
        "url": str(first(p, D("url")) or ""),
        "language": str(first(p, DCTERMS.language) or ""),
        "dataset_status": str(first(p, D("datasetStatus")) or ""),
        "protocol_version": str(first(p, D("annotationMethodVersion")) or ""),
        "taxonomy_version": str(first(p, D("taxonomyVersion")) or ""),
        "disclosure": str(first(p, D("rationale")) or ""),
        "start_date": str(first(p, D("startDate")) or "")[:10] or None,
        "end_date": str(first(p, D("endDate")) or "")[:10] or None,
        "stats": {
            "contributions": len(contribs),
            "participants": len(authors),
            "participants_declared": sum(1 for _ in g.objects(p, D("hasParticipant"))),
            "by_kind": dict(kinds),
            "by_condition": dict(conditions),
            "by_source": dict(sources),
            "languages": dict(langs),
            "ai_feedback": ai_feedback,
            "ai_fallacy_flags": ai_flags,
            "peer_evaluations": peer_evals,
            "recorded_responses": responses,
            "stance_labels": dict(stances),
            "anchors_user": anchors_user,
            "anchors_system": anchors_system,
            "date_from": min(dates) if dates else None,
            "date_to": max(dates) if dates else None,
        },
        "topics": topics,
        "legal_documents": legal_docs,
        "evaluation_metrics": sorted(metrics, key=lambda x: x["name"])[:80],
        "links": _links_of(p) + [l for t in g.objects(p, D("hasTopic")) for l in _links_of(t, 20)],
        "dataset": _dataset_of(p),
    }
    return jsonify(out)


# ---------------------------------------------------------------------------
# contributions (paginated, generic)
# ---------------------------------------------------------------------------
def _contribution_card(c):
    g = kg()
    d = first(c, D("timestamp"), DCTERMS.created)
    topic = first(c, D("hasTopic"))
    resp = first(c, D("responseTo"))
    ann = Counter()
    stance = None
    stance_method = None
    ai_labels = []
    for an in g.objects(c, D("hasAnnotation")):
        ts = set(g.objects(an, RDF.type))
        if D("AIFeedback") in ts:
            ann["ai_feedback"] += 1
        elif D("FallacyAnnotation") in ts and (D("AutomatedAnnotation") in ts or D("HumanAnnotation") in ts) and D("PeerEvaluation") not in ts and D("AnnotationResponse") not in ts:
            ann["fallacy_labels"] += 1
            ai_labels.append(label_of(first(an, D("identifiesFallacy"))) if first(an, D("identifiesFallacy")) is not None else str(first(an, D("annotationLabel")) or ""))
        elif D("PeerEvaluation") in ts:
            ann["peer_evaluations"] += 1
        elif D("AnnotationResponse") in ts:
            ann["responses"] += 1
        elif D("StanceAnnotation") in ts:
            if stance is None or D("HumanAnnotation") in ts:
                stance = str(first(an, D("stanceLabel")) or "")
                stance_method = str(first(an, D("annotationMethod")) or "")
        elif D("ProcessLink") in ts:
            ann["links"] += 1
    anchors = []
    for an in g.objects(c, D("hasAnchor")):
        prov = first(an, D("anchorProvision"))
        anchors.append({"method": str(first(an, D("anchorMethod")) or ""), "provision": label_of(prov), "provision_uri": str(prov) if prov is not None else None, "text": str(first(an, D("anchorText")) or "")[:200], "confidence": lit(first(an, D("confidence"))) if first(an, D("confidence")) is not None else None, "agrees": lit(first(an, D("anchorsAgree"))) if first(an, D("anchorsAgree")) is not None else None})
    return {
        "uri": str(c),
        "text": text_of(c),
        "draft_text": str(first(c, D("draftText")) or "") or None,
        "author": author_of(c),
        "timestamp": str(d) if d is not None else None,
        "language": str(first(c, DCTERMS.language) or "") or None,
        "kind": str(first(c, D("contributionKind")) or "") or None,
        "relation": str(first(c, D("replyRelation")) or "") or None,
        "condition": str(first(c, D("experimentalCondition")) or "") or None,
        "source": str(first(c, D("contributionSource")) or "") or None,
        "responseTo": str(resp) if resp is not None else None,
        "responseTo_label": (text_of(resp)[:120] if resp is not None else None),
        "topic": {"uri": str(topic), "label": label_of(topic)} if topic is not None else None,
        "stance": stance,
        "stance_method": stance_method,
        "annotations": dict(ann),
        "fallacy_labels": ai_labels,
        "anchors": anchors,
        "about_provision": [ref(x) for x in g.objects(c, D("aboutProvision"))],
        "proposes_change_to": [ref(x) for x in g.objects(c, D("proposesChangeTo"))],
        "proposed_operation": str(first(c, D("proposedOperation")) or "") or None,
        "word_count": lit(first(c, D("wordCount"))) if first(c, D("wordCount")) is not None else None,
    }


@bp.route("/api/process/contributions")
def process_contributions():
    uri = request.args.get("uri", "")
    g = kg()
    if not uri:
        return jsonify({"error": "URI parameter required"}), 400
    p = URIRef(uri)
    if (p, RDF.type, D("DeliberationProcess")) not in g:
        return jsonify({"error": "Process not found"}), 404
    try:
        offset = max(0, int(request.args.get("offset", 0)))
        limit = min(200, max(1, int(request.args.get("limit", 20))))
    except ValueError:
        return jsonify({"error": "offset/limit must be integers"}), 400
    kind = request.args.get("kind") or None
    topic = request.args.get("topic") or None
    condition = request.args.get("condition") or None
    source = request.args.get("source") or None
    order = request.args.get("order", "asc")
    items = []
    for c in g.objects(p, D("hasContribution")):
        if not text_of(c).strip():
            continue
        if kind and str(first(c, D("contributionKind")) or "") != kind:
            continue
        if condition and str(first(c, D("experimentalCondition")) or "") != condition:
            continue
        if source and str(first(c, D("contributionSource")) or "") != source:
            continue
        if topic and topic not in {str(t) for t in g.objects(c, D("hasTopic"))}:
            continue
        d = first(c, D("timestamp"), DCTERMS.created)
        items.append((str(d) if d is not None else "", str(c), c))
    items.sort(key=lambda x: (x[0], x[1]), reverse=(order == "desc"))
    total = len(items)
    page = [_contribution_card(c) for _d, _u, c in items[offset : offset + limit]]
    return jsonify({"process": uri, "total": total, "offset": offset, "limit": limit, "contributions": page})


# ---------------------------------------------------------------------------
# resource inspection (type-aware)
# ---------------------------------------------------------------------------
def _props(uri):
    g = kg()
    props = defaultdict(list)
    for p, o in g.predicate_objects(uri):
        if p == RDF.type or p in HIDDEN_PREDICATES:
            continue
        name = str(p).replace(DEL, "del:").replace(str(DCTERMS), "dct:").replace(str(RDFS), "rdfs:").replace(str(PROV), "prov:").replace(str(FOAF), "foaf:").replace(str(SKOS), "skos:").replace(str(DCAT), "dcat:")
        if isinstance(o, URIRef):
            props[name].append({"uri": str(o), "label": label_of(o), "types": types_of(o)})
        else:
            v = {"value": lit(o)}
            if isinstance(o, Literal) and o.language:
                v["lang"] = o.language
            props[name].append(v)
    return dict(props)


def _incoming(uri, limit=MAX_INCOMING):
    g = kg()
    inc = defaultdict(list)
    n = 0
    for s, p in g.subject_predicates(uri):
        name = str(p).replace(DEL, "del:").replace(str(DCTERMS), "dct:").replace(str(PROV), "prov:").replace(str(SKOS), "skos:")
        if name in ("del:hasContribution", "del:hasParticipant", "del:hasAnnotation") and n > limit:
            continue
        inc[name].append({"uri": str(s), "label": label_of(s), "types": types_of(s), "text": text_of(s)[:160]})
        n += 1
        if n >= limit * 3:
            break
    return {k: v[:limit] for k, v in inc.items()}


def _annotation_view(an):
    g = kg()
    ts = types_of(an)
    who = first(an, PROV.wasAttributedTo)
    v = {
        "uri": str(an),
        "types": ts,
        "kind": next((t for t in ("AIFeedback", "PeerEvaluation", "AnnotationResponse", "FallacyAnnotation", "StanceAnnotation", "AspectAnnotation", "ProcessLink") if t in ts), "Annotation"),
        "origin": "automated" if "AutomatedAnnotation" in ts else ("human" if "HumanAnnotation" in ts else "unspecified"),
        "attributed_to": ref(who) if who is not None else None,
        "method": str(first(an, D("annotationMethod")) or ""),
        "method_version": str(first(an, D("annotationMethodVersion")) or ""),
        "model": str(first(an, D("model")) or ""),
        "provider": str(first(an, D("provider")) or ""),
        "label": str(first(an, D("annotationLabel")) or ""),
        "fallacy": ref(first(an, D("identifiesFallacy"))) if first(an, D("identifiesFallacy")) is not None else None,
        "stance": str(first(an, D("stanceLabel")) or "") or None,
        "confidence": lit(first(an, D("confidence"))) if first(an, D("confidence")) is not None else None,
        "rationale": str(first(an, D("rationale")) or "") or None,
        "advice": str(first(an, D("advice")) or "") or None,
        "rewrite": str(first(an, D("rewriteSuggestion")) or "") or None,
        "reviewed_text": str(first(an, D("reviewedText")) or "") or None,
        "action": str(first(an, D("actionType")) or "") or None,
        "action_reason": str(first(an, D("actionReason")) or "") or None,
        "corrected_to": str(first(an, D("correctedTo")) or "") or None,
        "has_problem": lit(first(an, D("hasProblem"))) if first(an, D("hasProblem")) is not None else None,
        "timestamp": str(first(an, D("timestamp"), D("presentedAt")) or "") or None,
        "presented_at": [str(x) for x in g.objects(an, D("presentedAt"))],
        "condition": str(first(an, D("experimentalCondition")) or "") or None,
        "note": str(first(an, RDFS.comment) or "") or None,
        "target": ref(first(an, D("annotationTarget"))) if first(an, D("annotationTarget")) is not None else None,
        "responds_to": ref(first(an, D("respondsToAnnotation"))) if first(an, D("respondsToAnnotation")) is not None else None,
        "aspects": [str(x) for x in g.objects(an, D("annotationLabel"))] if "AspectAnnotation" in ts else None,
        "pending_models": [str(x) for x in g.objects(an, D("pendingModel"))],
        "response_strategy": str(first(an, D("responseStrategy")) or "") or None,
        "runs": [
            {
                "model": str(first(r, D("model")) or ""),
                "role": str(first(r, D("modelRole")) or ""),
                "succeeded": lit(first(r, D("runSucceeded"))) if first(r, D("runSucceeded")) is not None else None,
                "latency_ms": lit(first(r, D("latencyMs"))) if first(r, D("latencyMs")) is not None else None,
                "prompt_tokens": lit(first(r, D("promptTokens"))) if first(r, D("promptTokens")) is not None else None,
                "completion_tokens": lit(first(r, D("completionTokens"))) if first(r, D("completionTokens")) is not None else None,
                "labels": [str(x) for x in g.objects(r, D("annotationLabel"))],
            }
            for r in g.objects(an, D("hasModelRun"))
        ],
        # nested: labels produced within an AI feedback, and responses to this annotation
        "children": [],
    }
    for ch in g.objects(an, D("hasAnnotation")):
        cts = types_of(ch)
        v["children"].append(
            {
                "uri": str(ch),
                "kind": next((t for t in ("FallacyAnnotation", "AnnotationResponse", "PeerEvaluation") if t in cts), "Annotation"),
                "origin": "automated" if "AutomatedAnnotation" in cts else ("human" if "HumanAnnotation" in cts else "unspecified"),
                "label": str(first(ch, D("annotationLabel")) or ""),
                "fallacy": label_of(first(ch, D("identifiesFallacy"))) if first(ch, D("identifiesFallacy")) is not None else None,
                "confidence": lit(first(ch, D("confidence"))) if first(ch, D("confidence")) is not None else None,
                "rationale": str(first(ch, D("rationale")) or "") or None,
                "action": str(first(ch, D("actionType")) or "") or None,
                "corrected_to": str(first(ch, D("correctedTo")) or "") or None,
                "attributed_to": label_of(first(ch, PROV.wasAttributedTo)) if first(ch, PROV.wasAttributedTo) is not None else None,
                "timestamp": str(first(ch, D("timestamp")) or "") or None,
            }
        )
    return v


def _anchor_view(an):
    prov = first(an, D("anchorProvision"))
    expr = first(an, D("anchorExpression"))
    return {
        "uri": str(an),
        "method": str(first(an, D("anchorMethod")) or ""),
        "kind": str(first(an, D("anchorKind")) or ""),
        "text": str(first(an, D("anchorText")) or "") or None,
        "provision": ref(prov) if prov is not None else None,
        "provision_text": text_of(prov)[:600] if prov is not None else None,
        "expression": ref(expr) if expr is not None else None,
        "frbr_expression": str(first(expr, D("frbrExpressionUri")) or "") if expr is not None else "",
        "resolution_method": str(first(an, D("annotationMethod")) or "") or None,
        "model": str(first(an, D("model")) or "") or None,
        "confidence": lit(first(an, D("confidence"))) if first(an, D("confidence")) is not None else None,
        "agrees_with_user": lit(first(an, D("anchorsAgree"))) if first(an, D("anchorsAgree")) is not None else None,
        "attributed_to": label_of(first(an, PROV.wasAttributedTo)) if first(an, PROV.wasAttributedTo) is not None else None,
    }


@bp.route("/api/resource/inspect")
def inspect_resource():
    uri = request.args.get("uri", "")
    g = kg()
    if not uri:
        return jsonify({"error": "URI parameter required"}), 400
    u = URIRef(uri)
    ts = types_of(u)
    props = _props(u)
    if not props and not ts:
        return jsonify({"error": "Resource not found"}), 404
    out = {
        "uri": uri,
        "label": label_of(u),
        "types": ts,
        "type_labels": [TYPE_LABELS.get(t, t) for t in ts],
        "properties": props,
        "incoming": _incoming(u),
        "platform": _platform_of(u),
        "sections": {},
    }
    process = first(u, D("isPartOf"))
    if process is not None and (process, RDF.type, D("DeliberationProcess")) in g:
        out["process"] = ref(process)
    if "DeliberationProcess" in ts:
        out["process"] = ref(u)

    if "Contribution" in ts:
        card = _contribution_card(u)
        nested = set()
        for a in g.objects(u, D("hasAnnotation")):
            for ch in g.objects(a, D("hasAnnotation")):
                nested.add(ch)
            for ch in g.subjects(D("respondsToAnnotation"), a):
                nested.add(ch)
        card["annotation_details"] = [_annotation_view(a) for a in g.objects(u, D("hasAnnotation")) if (a, RDF.type, D("ProcessLink")) not in g and a not in nested]
        card["annotation_details"].sort(key=lambda v: ({"AIFeedback": 0, "FallacyAnnotation": 1, "StanceAnnotation": 2, "PeerEvaluation": 3, "AnnotationResponse": 4}.get(v["kind"], 9), v.get("timestamp") or ""))
        card["anchor_details"] = [_anchor_view(a) for a in g.objects(u, D("hasAnchor"))]
        card["replies"] = [{"uri": str(r), "text": text_of(r)[:200], "relation": str(first(r, D("replyRelation")) or ""), "author": author_of(r)} for r in g.subjects(D("responseTo"), u)]
        card["references"] = [ref(x) for x in g.objects(u, D("references"))]
        if card["responseTo"]:
            parent = URIRef(card["responseTo"])
            card["parent"] = {"uri": card["responseTo"], "text": text_of(parent)[:300], "author": author_of(parent), "source": str(first(parent, D("contributionSource")) or "")}
        out["sections"]["contribution"] = card
    if any(t in ts for t in ("AIFeedback", "PeerEvaluation", "AnnotationResponse", "FallacyAnnotation", "StanceAnnotation", "AspectAnnotation")):
        view = _annotation_view(u)
        target = first(u, D("annotates"))
        view["annotates"] = {"uri": str(target), "label": label_of(target), "text": text_of(target)[:400], "types": types_of(target)} if target is not None else None
        out["sections"]["annotation"] = view
    if "LegalResourceAnchor" in ts:
        out["sections"]["anchor"] = _anchor_view(u)
        out["sections"]["anchor"]["contribution"] = [ref(c) for c in g.subjects(D("hasAnchor"), u)]
    if "LegalProvision" in ts:
        expr = first(u, D("partOfExpression"))
        work = first(expr, D("expressionOf")) if expr is not None else None
        anchored = [c for a in g.subjects(D("anchorProvision"), u) for c in g.subjects(D("hasAnchor"), a)]
        seen = set()
        anchored_cards = []
        for c in anchored:
            if str(c) in seen:
                continue
            seen.add(str(c))
            anchored_cards.append({"uri": str(c), "text": text_of(c)[:200], "author": author_of(c), "methods": [str(first(a, D("anchorMethod")) or "") for a in g.objects(c, D("hasAnchor")) if first(a, D("anchorProvision")) == u]})
        out["sections"]["provision"] = {
            "eId": str(first(u, D("eId")) or ""),
            "number": str(first(u, D("articleNumber")) or ""),
            "heading": str(first(u, D("heading")) or ""),
            "text": text_of(u),
            "segment_index": lit(first(u, D("segmentIndex"))) if first(u, D("segmentIndex")) is not None else None,
            "expression": ref(expr) if expr is not None else None,
            "frbr_expression": str(first(expr, D("frbrExpressionUri")) or "") if expr is not None else "",
            "work": ref(work) if work is not None else None,
            "frbr_work": str(first(work, D("frbrWorkUri")) or "") if work is not None else "",
            "segments": [{"uri": str(s), "index": lit(first(s, D("segmentIndex"))), "text": text_of(s)} for s in sorted(g.subjects(DCTERMS.isPartOf, u), key=lambda s: int(lit(first(s, D("segmentIndex")) or 0)))],
            "aspects": [str(x) for a in g.objects(u, D("hasAnnotation")) for x in g.objects(a, D("annotationLabel"))],
            "anchored_contributions": anchored_cards,
            "opinions_about": [{"uri": str(c), "text": text_of(c)[:160]} for c in g.subjects(D("aboutProvision"), u)][:100],
            "change_proposals": [{"uri": str(c), "text": text_of(c)[:160]} for c in g.subjects(D("proposesChangeTo"), u)][:100],
        }
    if "LegalExpression" in ts or "LegalWork" in ts:
        exprs = [u] if "LegalExpression" in ts else list(g.subjects(D("expressionOf"), u))
        docs = []
        for e in exprs:
            provisions = [x for x in g.subjects(D("partOfExpression"), e) if first(x, D("segmentIndex")) is None]
            docs.append({"uri": str(e), "label": label_of(e), "frbr_expression": str(first(e, D("frbrExpressionUri")) or ""), "frbr_manifestation": str(first(e, D("frbrManifestationUri")) or ""), "filename": str(first(e, D("sourceFilename")) or ""), "provisions": [{"uri": str(x), "label": label_of(x), "anchored_contributions": sum(1 for _ in g.subjects(D("anchorProvision"), x))} for x in sorted(provisions, key=lambda x: int(lit(first(x, D("sourceRecordId")) or 0)))], "processes": [ref(p) for p in g.subjects(D("references"), e) if (p, RDF.type, D("DeliberationProcess")) in g]})
        out["sections"]["legal_document"] = {"expressions": docs, "work": ref(first(u, D("expressionOf"))) if first(u, D("expressionOf")) is not None else (ref(u) if "LegalWork" in ts else None)}
    if "Participant" in ts:
        contribs = list(g.subjects(D("madeBy"), u))
        out["sections"]["participant"] = {
            "name": label_of(u),
            "participant_type": str(first(u, D("participantType")) or ""),
            "note": str(first(u, RDFS.comment) or ""),
            "condition_assignments": [str(x) for x in g.objects(u, D("conditionAssignment"))],
            "contributions_count": len(contribs),
            "contributions": [{"uri": str(c), "text": text_of(c)[:200], "timestamp": str(first(c, D("timestamp")) or "") or None, "kind": str(first(c, D("contributionKind")) or "") or None} for c in sorted(contribs, key=lambda c: str(first(c, D("timestamp")) or ""))][:100],
            "evaluations_made": sum(1 for _ in g.subjects(PROV.wasAttributedTo, u)),
        }
    if "Topic" in ts:
        contribs = list(g.subjects(D("hasTopic"), u))
        out["sections"]["topic"] = {
            "label": label_of(u),
            "description": str(first(u, DCTERMS.description) or ""),
            "top_terms": str(first(u, D("topicWords")) or ""),
            "contributions_count": sum(1 for c in contribs if (c, RDF.type, D("Contribution")) in g),
            "processes": [ref(p) for p in g.subjects(D("hasTopic"), u) if (p, RDF.type, D("DeliberationProcess")) in g],
            "expected_fallacies": [label_of(x) for x in g.objects(u, D("containsFallacy"))],
            "links": _links_of(u, 30),
        }
    if "ProcessLink" in ts:
        src = first(u, D("linkSource"))
        tgt = first(u, D("linkTarget"))
        out["sections"]["link"] = {"source": ref(src) if src is not None else None, "target": ref(tgt) if tgt is not None else None, "link_type": str(first(u, D("linkType")) or ""), "relation": str(first(u, D("linkRelation")) or ""), "similarity": lit(first(u, D("similarity"))) if first(u, D("similarity")) is not None else None, "method": str(first(u, D("annotationMethod")) or ""), "model": str(first(u, D("model")) or ""), "note": str(first(u, RDFS.comment) or "")}
    if "FallacyType" in ts:
        out["sections"]["fallacy_type"] = {"label": label_of(u), "macro_category": str(first(u, D("macroCategory")) or ""), "fine_label": str(first(u, D("fineLabel")) or ""), "question": str(first(u, D("userQuestion")) or ""), "example": str(first(u, D("example")) or ""), "taxonomy_version": str(first(u, D("taxonomyVersion")) or ""), "annotations_count": sum(1 for _ in g.subjects(D("identifiesFallacy"), u))}
    if "Forum" in ts:
        if _state["platforms"] is None:
            _state["platforms"] = _compute_platforms()
        out["sections"]["platform"] = next((p for p in _state["platforms"] if p["uri"] == uri), None)
    out["links"] = _links_of(u, 30)
    return jsonify(out)


@bp.route("/api/links")
def links():
    uri = request.args.get("uri", "")
    if not uri:
        return jsonify({"error": "URI parameter required"}), 400
    return jsonify({"uri": uri, "links": _links_of(URIRef(uri), 100)})
