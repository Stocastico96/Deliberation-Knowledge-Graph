#!/usr/bin/env python3
"""
DelibAI pilot -> DEL source graph.

Reads the JSON export of the Your Priorities pilot tables
(scripts/integration/export_delibai_pilot.sh) plus the pilot configuration
and seed comments from the Your Priorities research fork, and writes:

  knowledge_graph/sources/delibai_pilot_kg.ttl   (source graph, Turtle)
  data/delibai/reconciliation_report.json        (counts + exclusions)
  data/delibai/screening_report.json             (personal-data screening)

Field-level mapping: documentation/delibai_crowdlaw_integration.md

Idempotent: URIs are deterministic functions of source ids, so re-running the
importer on the same snapshot yields the same graph.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
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
    pseudonym,
    res,
    screen_text,
    slug,
    write_graph,
)

IMPORT_VERSION = "delibai-import-1.0.0"
MAPPING_VERSION = "delibai-del-mapping-1.0.0"
SOURCE_KEY = "delibai"

PROCESS_URI = res("delibai_pilot_2026")
FORUM_URI = res("forum_delibai")
DATASET_URI = res("dataset_delibai_pilot_2026")
RESEARCH_TEAM_URI = res("delibai_research_team")
FACILITATOR_ROLE_URI = res("delibai_role_facilitator")

# Events that are imported as recorded actions on AI feedback. Behavioural
# events (thread views, logins, surveys, disclosure) stay out of the graph.
RESPONSE_EVENTS = {
    "DelibAI Suggestion Accepted": "accepted",
    "DelibAI Suggestion Ignored": "ignored",
}
SHOWN_EVENT = "DelibAI Suggestion Shown"
EXCLUDED_EVENTS = {
    "Comment Thread Viewed": "behavioural log (thread views) - not published",
    "Pilot Participant Started": "session log - not published",
    "AI Disclosure Accepted": "consent/disclosure log - kept private (counted)",
    "Pre Survey Completed": "survey - reserved",
    "Post Survey Completed": "survey - reserved",
    "Control Delay Applied": "experimental timing detail - captured as controlDelayMs on the contribution",
    "Topic Task Completed": "redundant with the task record",
    "Peer Flag Submitted": "redundant with the flag record",
    "Peer Flag Cleared": "redundant with the flag record (action=cleared)",
    "DelibAI Suggestion Confirmed": "redundant with the flag record (aiAgreement=ai_confirmed)",
    "DelibAI Suggestion Corrected": "redundant with the flag record (aiAgreement=ai_corrected)",
    "DelibAI Suggestion Rejected": "redundant with the flag record (aiAgreement=ai_rejected)",
    "DelibAI Model Monitor Completed": "redundant with delibai_analysis.modelComparison",
}


# ---------------------------------------------------------------------------
# Source configuration (topics, taxonomy, versions, seeds)
# ---------------------------------------------------------------------------
def load_pilot_config(yp_repo: Path) -> dict:
    cfg_path = yp_repo / "server_api/src/services/pilot/delibaiPilotConfig.cjs"
    out = subprocess.run(
        ["node", "-e", f"console.log(JSON.stringify(require({json.dumps(str(cfg_path))})))"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


_SEED_BLOCK_RE = re.compile(r"const seedComments[^=]*=\s*\{(.*?)\n\};", re.S)
_SEED_ITEM_RE = re.compile(
    r"\{\s*id:\s*\"(?P<id>[^\"]+)\",\s*topicId:\s*\"(?P<topic>[^\"]+)\",\s*authorLabel:\s*\"[^\"]*\",\s*"
    r"sourceType:\s*\"seed\",\s*text:\s*\"(?P<text>(?:[^\"\\]|\\.)*)\",?"
    r"(?:\s*delibAiSuggestion:\s*\"(?P<sugg>[^\"]+)\",\s*delibAiRationale:\s*\"(?P<rat>(?:[^\"\\]|\\.)*)\",?)?\s*\}",
    re.S,
)


def load_seed_comments(yp_repo: Path) -> list[dict]:
    src = (yp_repo / "webApps/client/src/yp-delibai-pilot/yp-delibai-pilot-forum.ts").read_text(encoding="utf-8")
    block = _SEED_BLOCK_RE.search(src)
    if not block:
        raise RuntimeError("seedComments block not found in yp-delibai-pilot-forum.ts")
    seeds = []
    for m in _SEED_ITEM_RE.finditer(block.group(1)):
        seeds.append(
            {
                "id": m.group("id"),
                "topicId": m.group("topic"),
                "text": m.group("text").encode().decode("unicode_escape"),
                "delibAiSuggestion": m.group("sugg"),
                "delibAiRationale": (m.group("rat") or "").encode().decode("unicode_escape") or None,
            }
        )
    return seeds


# ---------------------------------------------------------------------------
# URI helpers
# ---------------------------------------------------------------------------
def topic_uri(topic_id: str) -> URIRef:
    return res(f"delibai_topic_{slug(topic_id)}")


def seed_uri(seed_id: str) -> URIRef:
    return res(f"delibai_seed_{slug(seed_id)}")


def seed_label_uri(seed_id: str) -> URIRef:
    return res(f"delibai_seed_{slug(seed_id)}_label_0")


def task_uri(task_id: int | str) -> URIRef:
    return res(f"delibai_contribution_{int(task_id)}")


def feedback_uri(task_id: int | str) -> URIRef:
    return res(f"delibai_feedback_{int(task_id)}")


def fallacy_uri(task_id: int | str, index: int) -> URIRef:
    return res(f"delibai_feedback_{int(task_id)}_fallacy_{index}")


def fallacy_type_uri(taxonomy_id: str) -> URIRef:
    return res(f"delibai_fallacy_type_{slug(taxonomy_id)}")


def agent_uri(model: str) -> URIRef:
    return res(f"delibai_agent_{slug(model)}")


def evaluation_uri(flag_id: int | str) -> URIRef:
    return res(f"delibai_evaluation_{int(flag_id)}")


def response_uri(event_id: int | str) -> URIRef:
    return res(f"delibai_response_{int(event_id)}")


def resolve_target(target_id: str | None) -> tuple[URIRef | None, URIRef | None, str | None]:
    """Return (base contribution URI, annotated label URI or None, source type)."""
    if not target_id:
        return None, None, None
    m = re.match(r"^(.*)::ai-fallacy-(\d+)$", target_id)
    base = m.group(1) if m else target_id
    idx = int(m.group(2)) if m else None
    if base.startswith("seed-"):
        base_uri = seed_uri(base)
        label = seed_label_uri(base) if idx is not None else None
        return base_uri, label, "seed"
    pm = re.match(r"^peer-(\d+)$", base)
    if pm:
        base_uri = task_uri(pm.group(1))
        label = fallacy_uri(pm.group(1), idx) if idx is not None else None
        return base_uri, label, "peer"
    return None, None, None


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------
def build_graph(cfg: dict, report: Report, screening: dict) -> Graph:
    g = Graph()
    bind_namespaces(g)

    input_dir = Path(cfg["input_dir"])
    yp_repo = Path(cfg["yp_repo"])
    salt = cfg["pseudonym_salt"]
    window_start = parse_datetime(cfg["pilot_window_start"])
    window_end = parse_datetime(cfg["pilot_window_end"])
    snapshot_date = (input_dir / "snapshot_date.txt").read_text().strip() if (input_dir / "snapshot_date.txt").exists() else None

    pilot_cfg = load_pilot_config(yp_repo)
    study = pilot_cfg["study"]
    seeds = load_seed_comments(yp_repo)
    if len(seeds) != 20:
        report.warn(f"expected 20 seed comments, parsed {len(seeds)}")

    participants = load_json(input_dir / "pilot_participants.json")
    tasks = load_json(input_dir / "pilot_task_responses.json")
    flags = load_json(input_dir / "pilot_peer_flags.json")
    events = load_json(input_dir / "pilot_events.json")
    surveys_path = input_dir / "pilot_survey_responses.json"
    if surveys_path.exists():
        n_surveys = len(load_json(surveys_path))
        report.read("pilot_survey_responses", n_surveys)
        report.excluded("pilot_survey_responses", "questionnaires are reserved - never exported to the graph", n_surveys)

    def in_window(value) -> bool:
        dt = parse_datetime(value)
        return dt is not None and window_start <= dt <= window_end

    # ---- Provenance ------------------------------------------------------
    activity = add_import_provenance(
        g,
        source_key=SOURCE_KEY,
        dataset_uri=DATASET_URI,
        title="DelibAI pilot (May 2026) - contestable AI feedback in civic deliberation",
        description=(
            "Pseudonymised historical data of the DelibAI pilot run in May 2026 on a research fork of "
            "Your Priorities: four discussion topics, participants' comments and replies, AI feedback "
            "(advice, rewrite suggestions, fallacy flags) with model provenance, peer evaluations and the "
            "participants' recorded responses to AI suggestions. Questionnaires, behavioural logs and "
            "participant credentials are not included."
        ),
        import_version=IMPORT_VERSION,
        mapping_version=MAPPING_VERSION,
        snapshot_date=snapshot_date,
        script_name="scripts/integration/import_delibai.py",
        dataset_status="pilot-historical",
        landing_page=cfg.get("landing_page"),
        license_uri="http://creativecommons.org/licenses/by/4.0/",
    )

    # ---- Forum / platform, process, topics ---------------------------------
    g.add((FORUM_URI, RDF.type, DEL.Forum))
    add(g, FORUM_URI, DEL.name, "DelibAI")
    add(g, FORUM_URI, RDFS.label, "DelibAI", lang="en")
    add(
        g,
        FORUM_URI,
        DCTERMS.description,
        "DelibAI is a research prototype for contestable AI feedback in civic deliberation, implemented as a "
        "pilot mode of a research fork of the open-source Your Priorities platform. It flags possible "
        "argumentation fallacies and may suggest a clearer formulation; it never edits participants' text.",
        lang="en",
    )
    g.add((FORUM_URI, DEL.url, Literal(cfg.get("landing_page", ""), datatype=XSD.anyURI)))

    g.add((PROCESS_URI, RDF.type, DEL.DeliberationProcess))
    add(g, PROCESS_URI, DEL.identifier, "delibai_pilot_2026")
    add(g, PROCESS_URI, DEL.name, f"{study['name']} (May 2026)", lang="en")
    add(g, PROCESS_URI, RDFS.label, f"{study['name']} (May 2026)", lang="en")
    add(
        g,
        PROCESS_URI,
        DCTERMS.description,
        "Within-participant pilot of DelibAI: each participant discussed four civic topics in a forum, "
        "writing a first-level comment, one agreeing and one disagreeing reply per topic, and evaluating "
        "possible argumentation fallacies in other comments. On two topics per participant the AI "
        "feedback was active (delibai_on), on the other two it was inactive (delibai_off). "
        f"Protocol {study['protocolVersion']}; taxonomy {study['taxonomyVersion']}.",
        lang="en",
    )
    g.add((PROCESS_URI, DEL.takesPlaceIn, FORUM_URI))
    add(g, PROCESS_URI, DEL.platform, "DelibAI")
    add(g, PROCESS_URI, DCTERMS.language, "en")
    add(g, PROCESS_URI, DEL.datasetStatus, "pilot-historical")
    add(g, PROCESS_URI, DEL.annotationMethodVersion, study["protocolVersion"])
    add(g, PROCESS_URI, DEL.taxonomyVersion, study["taxonomyVersion"])
    g.add((PROCESS_URI, DCTERMS.isPartOf, DATASET_URI))
    g.add((PROCESS_URI, PROV.wasGeneratedBy, activity))
    add(g, PROCESS_URI, DEL.url, cfg.get("landing_page"), datatype=XSD.anyURI)
    # disclosure text shown to participants (documented condition of the study)
    add(g, PROCESS_URI, DEL.rationale, pilot_cfg["disclosure"], lang="en")

    topic_labels = {}
    for t in pilot_cfg["recommendedTopics"]:
        tu = topic_uri(t["id"])
        topic_labels[t["id"]] = t["label"]
        g.add((tu, RDF.type, DEL.Topic))
        add(g, tu, DEL.identifier, t["id"])
        add(g, tu, DEL.name, t["label"], lang="en")
        add(g, tu, RDFS.label, t["label"], lang="en")
        add(g, tu, DCTERMS.description, t["proposal"], lang="en")
        for f in t.get("expectedFallacies", []):
            g.add((tu, DEL.containsFallacy, fallacy_type_uri(f)))  # expected by design
        for ax in t.get("politicalAxes", []):
            add(g, tu, DEL.annotationLabel, ax)
        g.add((PROCESS_URI, DEL.hasTopic, tu))

    # ---- Fallacy taxonomy -------------------------------------------------
    for f in pilot_cfg["fallacyTaxonomy"]:
        fu = fallacy_type_uri(f["taxonomyId"])
        g.add((fu, RDF.type, DEL.FallacyType))
        add(g, fu, DEL.identifier, f["taxonomyId"])
        add(g, fu, RDFS.label, f["userLabel"], lang="en")
        add(g, fu, DEL.name, f["userLabel"], lang="en")
        add(g, fu, DEL.macroCategory, f["macroCategory"])
        add(g, fu, DEL.fineLabel, f["fineLabel"])
        add(g, fu, DEL.userQuestion, f["userQuestion"], lang="en")
        add(g, fu, DEL.example, f["example"], lang="en")
        add(g, fu, DEL.taxonomyVersion, study["taxonomyVersion"])

    # ---- Research team (author of seeds and of the displayed labels) --------
    g.add((RESEARCH_TEAM_URI, RDF.type, DEL.Participant))
    add(g, RESEARCH_TEAM_URI, DEL.name, "DelibAI research team", lang="en")
    add(g, RESEARCH_TEAM_URI, FOAF.name, "DelibAI research team")
    add(g, RESEARCH_TEAM_URI, DEL.participantType, "RESEARCH_TEAM")
    g.add((RESEARCH_TEAM_URI, DEL.hasRole, FACILITATOR_ROLE_URI))
    g.add((FACILITATOR_ROLE_URI, RDF.type, DEL.Facilitator))
    add(g, FACILITATOR_ROLE_URI, RDFS.label, "Facilitator (study design)", lang="en")
    g.add((PROCESS_URI, DEL.hasParticipant, RESEARCH_TEAM_URI))

    # ---- Seed comments ------------------------------------------------------
    for s in seeds:
        report.read("seed_comments")
        su = seed_uri(s["id"])
        g.add((su, RDF.type, DEL.Contribution))
        add(g, su, DEL.identifier, s["id"])
        add(g, su, DEL.text, s["text"], lang="en")
        add(g, su, DCTERMS.language, "en")
        add(g, su, DEL.contributionSource, "seed")
        add(g, su, DEL.contributionKind, "seed")
        g.add((su, DEL.madeBy, RESEARCH_TEAM_URI))
        g.add((su, DEL.hasTopic, topic_uri(s["topicId"])))
        g.add((su, DEL.isPartOf, PROCESS_URI))
        g.add((PROCESS_URI, DEL.hasContribution, su))
        add(g, su, DEL.platform, "DelibAI")
        g.add((su, PROV.wasGeneratedBy, activity))
        if s["delibAiSuggestion"]:
            lu = seed_label_uri(s["id"])
            g.add((lu, RDF.type, DEL.FallacyAnnotation))
            g.add((lu, RDF.type, DEL.HumanAnnotation))
            g.add((lu, DEL.annotates, su))
            g.add((su, DEL.hasAnnotation, lu))
            g.add((lu, DEL.identifiesFallacy, fallacy_type_uri(s["delibAiSuggestion"])))
            add(g, lu, DEL.annotationLabel, s["delibAiSuggestion"])
            add(g, lu, DEL.rationale, s["delibAiRationale"], lang="en")
            add(g, lu, DEL.annotationMethod, "study_design_displayed_label")
            add(
                g,
                lu,
                RDFS.comment,
                "Label fixed by the study design and displayed to participants in the delibai_on condition as a "
                "DelibAI suggestion; it was not generated by a model at run time.",
                lang="en",
            )
            g.add((lu, PROV.wasAttributedTo, RESEARCH_TEAM_URI))
        report.imported("seed_comments")

    # ---- Participants -------------------------------------------------------
    code_to_uri: dict[str, URIRef] = {}
    for p in participants:
        report.read("pilot_participants")
        if not in_window(p.get("created_at")):
            report.excluded("pilot_participants", "created outside the pilot window (post-pilot session)")
            continue
        code = p["participant_code"]
        pid = pseudonym(code, salt)
        pu = res(f"delibai_participant_{pid}")
        code_to_uri[code] = pu
        g.add((pu, RDF.type, DEL.Participant))
        add(g, pu, DEL.identifier, pid)
        add(g, pu, DEL.name, f"Pilot participant {pid[:6]}", lang="en")
        add(g, pu, FOAF.name, f"Pilot participant {pid[:6]}")
        add(g, pu, DEL.participantType, "PSEUDONYMOUS_PILOT_PARTICIPANT")
        add(g, pu, RDFS.comment, "Re-pseudonymised participant code (salted hash); no personal data is stored.", lang="en")
        for a in p.get("assigned_topics") or []:
            add(g, pu, DEL.conditionAssignment, f"{a.get('topicId')}:{a.get('condition')}")
        add_datetime(g, pu, DEL.startDate, p.get("started_at"))
        add_datetime(g, pu, DEL.endDate, p.get("completed_at"))
        g.add((PROCESS_URI, DEL.hasParticipant, pu))
        # metadata (password material) and status intentionally not copied
        report.imported("pilot_participants")
    report.notes["participants_metadata_column"] = "excluded: contains password hashes and salts"

    # ---- Tasks -> contributions + AI feedback --------------------------------
    task_by_id: dict[int, dict] = {}
    task_index: dict[tuple, list[int]] = defaultdict(list)  # (code, topic, kind, final) -> ids
    reviewed_index: dict[tuple, list[int]] = defaultdict(list)  # (code, topic, reviewedText) -> ids
    for t in tasks:
        report.read("pilot_task_responses")
        if not in_window(t.get("created_at")):
            report.excluded("pilot_task_responses", "created outside the pilot window")
            continue
        code = t["participant_code"]
        if code not in code_to_uri:
            report.excluded("pilot_task_responses", "participant not imported")
            continue
        text = t.get("final_text") or t.get("comment_text") or t.get("response_text") or ""
        if not text.strip():
            report.excluded("pilot_task_responses", "empty text")
            continue
        metrics = t.get("metrics") or {}
        kind = metrics.get("kind") or ("reply" if t.get("selected_seed_id") else "main")
        for field in ("final_text", "draft_text", "comment_text", "response_text"):
            hits = screen_text(t.get(field) or "")
            if hits:
                screening["flagged"].append({"record": f"task:{t['id']}:{field}", "patterns": hits})
        screening["texts_screened"] += 1

        tu = task_uri(t["id"])
        task_by_id[int(t["id"])] = t
        task_index[(code, t["topic_id"], kind, text)].append(int(t["id"]))
        if metrics.get("reviewedText"):
            reviewed_index[(code, t["topic_id"], metrics["reviewedText"])].append(int(t["id"]))
        g.add((tu, RDF.type, DEL.Contribution))
        add(g, tu, DEL.identifier, f"task-{t['id']}")
        add(g, tu, DEL.sourceTable, "pilot_task_responses")
        add(g, tu, DEL.sourceRecordId, str(t["id"]))
        add(g, tu, DEL.text, text, lang="en")
        add(g, tu, DCTERMS.language, "en")
        draft = t.get("draft_text")
        if draft and draft != text:
            add(g, tu, DEL.draftText, draft, lang="en")
        elif draft:
            add(g, tu, DEL.draftText, draft, lang="en")
        add_datetime(g, tu, DEL.timestamp, t.get("completed_at") or t.get("created_at"))
        add_datetime(g, tu, DCTERMS.created, t.get("created_at"))
        g.add((tu, DEL.madeBy, code_to_uri[code]))
        g.add((tu, DEL.hasTopic, topic_uri(t["topic_id"])))
        g.add((tu, DEL.isPartOf, PROCESS_URI))
        g.add((PROCESS_URI, DEL.hasContribution, tu))
        add(g, tu, DEL.platform, "DelibAI")
        add(g, tu, DEL.contributionSource, "participant")
        add(g, tu, DEL.contributionKind, kind)
        add(g, tu, DEL.replyRelation, metrics.get("relation"))
        add(g, tu, DEL.experimentalCondition, t.get("condition"))
        add(g, tu, DEL.wordCount, t.get("word_count"), datatype=XSD.integer)
        add(g, tu, DEL.reviewDurationMs, metrics.get("reviewDurationMs"), datatype=XSD.integer)
        if t.get("condition") == "delibai_off":
            add(g, tu, DEL.controlDelayMs, metrics.get("controlDelayMs"), datatype=XSD.integer)
        add(g, tu, DEL.annotationMethodVersion, metrics.get("protocolVersion"))
        g.add((tu, PROV.wasGeneratedBy, activity))

        parent_id = t.get("selected_seed_id") or metrics.get("parentId")
        if parent_id:
            parent_uri, _lbl, _src = resolve_target(parent_id)
            if parent_uri is None:
                report.warn(f"task {t['id']}: unresolved reply target {parent_id}")
            else:
                g.add((tu, DEL.responseTo, parent_uri))

        analysis = t.get("delibai_analysis") or {}
        if t.get("condition") == "delibai_on" and analysis:
            report.read("ai_feedback")
            fu = feedback_uri(t["id"])
            g.add((fu, RDF.type, DEL.AIFeedback))
            g.add((fu, RDF.type, DEL.AutomatedAnnotation))
            g.add((fu, DEL.annotates, tu))
            g.add((tu, DEL.hasAnnotation, fu))
            add(g, fu, DEL.identifier, f"feedback-task-{t['id']}")
            add(g, fu, DEL.advice, analysis.get("advice"), lang="en")
            add(g, fu, DEL.rewriteSuggestion, analysis.get("rewrite"), lang="en")
            add(g, fu, DEL.reviewedText, metrics.get("reviewedText") or draft, lang="en")
            add(g, fu, DEL.model, analysis.get("model"))
            add(g, fu, DEL.provider, analysis.get("provider"))
            add(g, fu, DEL.annotationMethod, "llm_fallacy_review")
            add(g, fu, DEL.annotationMethodVersion, metrics.get("instrumentationVersion"))
            add(g, fu, DEL.taxonomyVersion, study["taxonomyVersion"])
            if analysis.get("shouldBlock") is not None:
                add(g, fu, DEL.annotationLabel, f"shouldBlock={str(bool(analysis.get('shouldBlock'))).lower()}")
            comp = analysis.get("modelComparison") or {}
            add(g, fu, DEL.responseStrategy, comp.get("responseStrategy"))
            add(g, fu, DEL.primaryModel, comp.get("primaryModel"))
            for pm in comp.get("pendingModels") or []:
                add(g, fu, DEL.pendingModel, pm)
            if analysis.get("model"):
                au = agent_uri(analysis["model"])
                g.add((au, RDF.type, DEL.ArtificialAgent))
                add(g, au, DEL.name, analysis["model"])
                add(g, au, FOAF.name, analysis["model"])
                add(g, au, DEL.model, analysis["model"])
                add(g, au, DEL.provider, analysis.get("provider"))
                g.add((fu, PROV.wasAttributedTo, au))
            for i, run in enumerate(comp.get("models") or []):
                ru = res(f"delibai_feedback_{int(t['id'])}_run_{i}")
                g.add((ru, RDF.type, DEL.ModelRun))
                g.add((fu, DEL.hasModelRun, ru))
                add(g, ru, DEL.model, run.get("model"))
                add(g, ru, DEL.modelRole, run.get("role"))
                if run.get("ok") is not None:
                    add(g, ru, DEL.runSucceeded, bool(run.get("ok")))
                add(g, ru, DEL.latencyMs, run.get("latencyMs"), datatype=XSD.integer)
                add(g, ru, DEL.actionReason, run.get("error"))
                usage = run.get("usage") or {}
                add(g, ru, DEL.promptTokens, usage.get("prompt_tokens"), datatype=XSD.integer)
                add(g, ru, DEL.completionTokens, usage.get("completion_tokens"), datatype=XSD.integer)
                add(g, ru, DEL.inferenceCost, usage.get("cost"), datatype=XSD.decimal)
                for f in run.get("fallacies") or []:
                    add(g, ru, DEL.annotationLabel, f.get("taxonomyId") or f.get("label"))
            for i, f in enumerate(analysis.get("fallacies") or []):
                report.read("ai_fallacy_flags")
                fau = fallacy_uri(t["id"], i)
                g.add((fau, RDF.type, DEL.FallacyAnnotation))
                g.add((fau, RDF.type, DEL.AutomatedAnnotation))
                g.add((fau, DEL.annotates, tu))
                g.add((tu, DEL.hasAnnotation, fau))
                g.add((fu, DEL.hasAnnotation, fau))
                g.add((fau, DEL.annotates, fu))
                tax = f.get("taxonomyId") or f.get("label")
                if tax:
                    g.add((fau, DEL.identifiesFallacy, fallacy_type_uri(tax)))
                add(g, fau, DEL.annotationLabel, tax)
                add(g, fau, DEL.confidence, f.get("score"), datatype=XSD.decimal)
                add(g, fau, DEL.rationale, f.get("rationale") or f.get("explanation"), lang="en")
                add(g, fau, DEL.model, analysis.get("model"))
                add(g, fau, DEL.annotationMethod, "llm_fallacy_review")
                if analysis.get("model"):
                    g.add((fau, PROV.wasAttributedTo, agent_uri(analysis["model"])))
                for fld in ("advice", "rewrite"):
                    hits = screen_text(analysis.get(fld) or "")
                    if hits:
                        screening["flagged"].append({"record": f"task:{t['id']}:ai.{fld}", "patterns": hits})
                report.imported("ai_fallacy_flags")
            report.imported("ai_feedback")
        elif t.get("condition") == "delibai_on":
            report.warn(f"task {t['id']}: delibai_on without stored analysis")
        report.imported("pilot_task_responses")

    # ---- Peer flags -> evaluations / responses to displayed labels ------------
    for f in flags:
        report.read("pilot_peer_flags")
        if not in_window(f.get("created_at")):
            report.excluded("pilot_peer_flags", "created outside the pilot window")
            continue
        flagger = f.get("flagger_participant_code")
        if flagger not in code_to_uri:
            report.excluded("pilot_peer_flags", "flagger not imported")
            continue
        base_uri, label_uri, src_type = resolve_target(f.get("target_comment_id"))
        if base_uri is None:
            report.failed("pilot_peer_flags", f"flag {f['id']}: unresolved target {f.get('target_comment_id')}")
            continue
        if src_type == "peer":
            pm = re.match(r"^peer-(\d+)", f["target_comment_id"])
            if pm and int(pm.group(1)) not in task_by_id:
                report.excluded("pilot_peer_flags", "target contribution not imported")
                continue
        meta = f.get("metadata") or {}
        action = meta.get("action")
        ai_agreement = meta.get("aiAgreement")
        eu = evaluation_uri(f["id"])
        add(g, eu, DEL.identifier, f"flag-{f['id']}")
        add(g, eu, DEL.sourceTable, "pilot_peer_flags")
        add(g, eu, DEL.sourceRecordId, str(f["id"]))
        g.add((eu, PROV.wasAttributedTo, code_to_uri[flagger]))
        add_datetime(g, eu, DEL.timestamp, f.get("created_at"))
        add(g, eu, DEL.experimentalCondition, f.get("condition"))
        add(g, eu, DEL.annotationMethod, "participant_peer_flag")
        add(g, eu, DEL.annotationMethodVersion, meta.get("protocolVersion"))
        g.add((eu, PROV.wasGeneratedBy, activity))
        if label_uri is not None and ai_agreement in ("ai_confirmed", "ai_corrected", "ai_rejected"):
            # A response to a displayed (AI-presented) fallacy label
            g.add((eu, RDF.type, DEL.AnnotationResponse))
            g.add((eu, RDF.type, DEL.HumanAnnotation))
            g.add((eu, DEL.respondsToAnnotation, label_uri))
            g.add((eu, DEL.annotates, base_uri))
            g.add((base_uri, DEL.hasAnnotation, eu))
            g.add((label_uri, DEL.hasAnnotation, eu))
            add(g, eu, DEL.actionType, ai_agreement.replace("ai_", ""))
            add(g, eu, DEL.hasProblem, bool(f.get("has_problem")))
            add(g, eu, DEL.annotationLabel, f.get("taxonomy_id"))
            if ai_agreement == "ai_corrected":
                add(g, eu, DEL.correctedTo, meta.get("correctedTaxonomyId") or f.get("taxonomy_id"))
            add(g, eu, DEL.rationale, f.get("free_text"))
        else:
            g.add((eu, RDF.type, DEL.PeerEvaluation))
            g.add((eu, RDF.type, DEL.HumanAnnotation))
            g.add((eu, DEL.annotates, base_uri))
            g.add((base_uri, DEL.hasAnnotation, eu))
            if label_uri is not None:
                g.add((eu, DEL.annotationTarget, label_uri))
            if action == "cleared":
                add(g, eu, DEL.actionType, "cleared")
                add(g, eu, RDFS.comment, "The participant withdrew their previous evaluation of this comment.", lang="en")
            elif action == "endorsed":
                add(g, eu, DEL.actionType, "no_problem")
                add(g, eu, DEL.hasProblem, False)
            else:
                add(g, eu, DEL.actionType, "problem_flagged" if f.get("has_problem") else "no_problem")
                add(g, eu, DEL.hasProblem, bool(f.get("has_problem")))
            if f.get("taxonomy_id"):
                g.add((eu, RDF.type, DEL.FallacyAnnotation))
                g.add((eu, DEL.identifiesFallacy, fallacy_type_uri(f["taxonomy_id"])))
                add(g, eu, DEL.annotationLabel, f["taxonomy_id"])
            add(g, eu, DEL.rationale, f.get("free_text"))
        report.imported("pilot_peer_flags")

    # ---- Events -> recorded responses to AI feedback ----------------------------
    feedback_shown_matched = 0
    for e in events:
        report.read("pilot_events")
        name = e.get("event_name")
        if not in_window(e.get("created_at")):
            report.excluded("pilot_events", "created outside the pilot window")
            continue
        if name in EXCLUDED_EVENTS:
            report.excluded("pilot_events", EXCLUDED_EVENTS[name])
            continue
        if name not in RESPONSE_EVENTS and name != SHOWN_EVENT:
            report.excluded("pilot_events", f"event type not mapped: {name}")
            continue
        props = e.get("properties") or {}
        code = e.get("participant_code")
        if code not in code_to_uri:
            report.excluded("pilot_events", "participant not imported")
            continue
        final_text = props.get("finalText") or ""
        kind = props.get("kind")
        candidates = task_index.get((code, e.get("topic_id"), kind, final_text)) if kind else None
        if not candidates:
            # fall back: same participant/topic, any kind, same text
            candidates = [
                tid for (c, tp, _k, txt), ids in task_index.items() if c == code and tp == e.get("topic_id") and txt == final_text for tid in ids
            ]
        if name == SHOWN_EVENT:
            # 'Shown' fires before submission: match on the text that was reviewed
            candidates = reviewed_index.get((code, e.get("topic_id"), props.get("reviewedText") or "")) or []
            if candidates and t_has_feedback(g, candidates[0]):
                add_datetime(g, feedback_uri(candidates[0]), DEL.presentedAt, e.get("created_at"))
                feedback_shown_matched += 1
                report.imported("pilot_events")
            else:
                report.excluded("pilot_events", "'Suggestion Shown' without a submitted contribution (text edited or abandoned)")
            continue
        ru = response_uri(e["id"])
        g.add((ru, RDF.type, DEL.AnnotationResponse))
        g.add((ru, RDF.type, DEL.HumanAnnotation))
        add(g, ru, DEL.identifier, f"event-{e['id']}")
        add(g, ru, DEL.sourceTable, "pilot_events")
        add(g, ru, DEL.sourceRecordId, str(e["id"]))
        add(g, ru, DEL.actionType, RESPONSE_EVENTS[name])
        add(g, ru, DEL.actionReason, props.get("reason"))
        add_datetime(g, ru, DEL.timestamp, e.get("created_at"))
        add(g, ru, DEL.experimentalCondition, e.get("condition"))
        add(g, ru, DEL.reviewDurationMs, props.get("reviewDurationMs"), datatype=XSD.integer)
        add(g, ru, DEL.annotationMethod, "participant_action_log")
        g.add((ru, PROV.wasAttributedTo, code_to_uri[code]))
        g.add((ru, PROV.wasGeneratedBy, activity))
        if candidates:
            tid = candidates[0]
            g.add((ru, DEL.annotates, task_uri(tid)))
            g.add((task_uri(tid), DEL.hasAnnotation, ru))
            if t_has_feedback(g, tid):
                g.add((ru, DEL.respondsToAnnotation, feedback_uri(tid)))
                g.add((feedback_uri(tid), DEL.hasAnnotation, ru))
            if len(candidates) > 1:
                report.warn(f"event {e['id']}: ambiguous task match ({candidates}); linked to {tid}")
        else:
            add(g, ru, RDFS.comment, "Recorded action on AI feedback for a text that was not submitted as a contribution.", lang="en")
            add(g, ru, DEL.reviewedText, props.get("reviewedText"), lang="en")
            g.add((ru, DEL.annotates, topic_uri(e["topic_id"])) if e.get("topic_id") else (ru, DEL.annotates, PROCESS_URI))
            report.warn(f"event {e['id']} ({name}): no matching contribution; attached to topic")
        report.imported("pilot_events")
    report.notes["feedback_presentedAt_from_shown_events"] = feedback_shown_matched

    # ---- Process statistics (computed) ----------------------------------------
    dates = [parse_datetime(t.get("created_at")) for t in task_by_id.values()]
    if dates:
        add(g, PROCESS_URI, DEL.startDate, min(dates).isoformat(), datatype=XSD.dateTime)
        add(g, PROCESS_URI, DEL.endDate, max(dates).isoformat(), datatype=XSD.dateTime)
        add(g, PROCESS_URI, DCTERMS.date, min(dates).date().isoformat(), datatype=XSD.date)
    report.notes["pilot_window"] = [cfg["pilot_window_start"], cfg["pilot_window_end"]]
    report.notes["seeds"] = len(seeds)
    return g


def t_has_feedback(g: Graph, task_id: int) -> bool:
    return (feedback_uri(task_id), RDF.type, DEL.AIFeedback) in g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(REPO_ROOT / "config/integration/delibai.local.json"))
    ap.add_argument("--output", default=str(SOURCES_DIR / "delibai_pilot_kg.ttl"))
    ap.add_argument("--report", default=str(REPO_ROOT / "data/delibai/reconciliation_report.json"))
    ap.add_argument("--screening-report", default=str(REPO_ROOT / "data/delibai/screening_report.json"))
    args = ap.parse_args()

    cfg = load_json(Path(args.config))
    if not cfg.get("pseudonym_salt") or cfg["pseudonym_salt"].startswith("REPLACE"):
        print("ERROR: set a private pseudonym_salt in the local config", file=sys.stderr)
        return 2

    report = Report(SOURCE_KEY, IMPORT_VERSION, MAPPING_VERSION)
    screening = {"texts_screened": 0, "flagged": [], "policy": "documented in data/delibai/README.md"}
    g = build_graph(cfg, report, screening)
    if screening["flagged"]:
        report.warn(f"{len(screening['flagged'])} texts matched personal-data patterns - review before publishing")
    write_graph(g, Path(args.output))
    report.notes["output"] = args.output
    report.write(Path(args.report), g)
    Path(args.screening_report).write_text(json.dumps(screening, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report.to_dict(g), indent=2, ensure_ascii=False))
    return 1 if screening["flagged"] else 0


if __name__ == "__main__":
    sys.exit(main())
