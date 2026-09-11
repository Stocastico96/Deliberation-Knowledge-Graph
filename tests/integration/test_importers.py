"""
Tests for the DelibAI / CrowdLaw integration.

Run:  venv/bin/python3 -m pytest tests/integration -q

They exercise the source graphs produced by the importers (mapping correctness,
reconcilable counts, referential integrity, reserved fields, idempotency) and the
example SPARQL queries. Tests needing the source data are skipped when the
snapshot files are not available on this machine.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "integration"))
import common  # noqa: E402

DEL = Namespace("https://w3id.org/deliberation/ontology#")
RES = Namespace("https://svagnoni.linkeddata.es/resource/")
SRC = ROOT / "knowledge_graph" / "sources"
DELIBAI_TTL = SRC / "delibai_pilot_kg.ttl"
CROWDLAW_TTL = SRC / "crowdlaw_kg.ttl"
LINKS_TTL = SRC / "crosslinks_delibai_crowdlaw_kg.ttl"
DELIBAI_CFG = ROOT / "config" / "integration" / "delibai.local.json"
DELIBAI_INPUT = Path("/home/svagnoni/delibai_analysis/dkg_export")
CROWDLAW_DB = Path("/home/svagnoni/portale-cittadino-mvp/backend/data/app.db")


def load(path: Path) -> Graph:
    g = Graph()
    g.parse(str(path), format="turtle")
    return g


@pytest.fixture(scope="module")
def delibai() -> Graph:
    if not DELIBAI_TTL.exists():
        pytest.skip("delibai source graph not built")
    return load(DELIBAI_TTL)


@pytest.fixture(scope="module")
def crowdlaw() -> Graph:
    if not CROWDLAW_TTL.exists():
        pytest.skip("crowdlaw source graph not built")
    return load(CROWDLAW_TTL)


# ---------------------------------------------------------------------------
# common helpers
# ---------------------------------------------------------------------------
def test_slug_is_deterministic_and_safe():
    assert common.slug("Art. 1. (Regolamentazione)") == "art_1_regolamentazione"
    assert common.slug("/akn/it/bill/propostaDiLegge/2016-11-11/12/ita@") == "akn_it_bill_propostadilegge_2016_11_11_12_ita"
    assert common.slug("x" * 200) == common.slug("x" * 200)
    assert len(common.slug("x" * 200)) <= 80


def test_pseudonym_requires_salt_and_is_stable():
    with pytest.raises(ValueError):
        common.pseudonym("DAI-1", "")
    assert common.pseudonym("DAI-1", "s") == common.pseudonym("DAI-1", "s")
    assert common.pseudonym("DAI-1", "s") != common.pseudonym("DAI-1", "t")
    assert common.pseudonym("DAI-1", "s") != common.pseudonym("DAI-2", "s")


def test_screening_detects_patterns():
    assert common.screen_text("write me at john@example.org") == ["email"]
    assert "phone" in common.screen_text("call +39 333 1234567 now")
    assert common.screen_text("A comment about housing policy.") == []


def test_datetime_parsing_handles_postgres_offsets():
    dt = common.parse_datetime("2026-05-07 14:44:19.039+00")
    assert dt is not None and dt.utcoffset().total_seconds() == 0


# ---------------------------------------------------------------------------
# DelibAI source graph
# ---------------------------------------------------------------------------
def test_delibai_counts_match_report(delibai):
    report = json.loads((ROOT / "data/delibai/reconciliation_report.json").read_text())
    t = report["tables"]
    process = RES["delibai_pilot_2026"]
    contribs = set(delibai.objects(process, DEL.hasContribution))
    assert len(contribs) == t["pilot_task_responses"]["imported"] + t["seed_comments"]["imported"]
    assert sum(1 for _ in delibai.subjects(RDF.type, DEL.AIFeedback)) == t["ai_feedback"]["imported"]
    evals = sum(1 for _ in delibai.subjects(RDF.type, DEL.PeerEvaluation))
    responses = sum(1 for s in delibai.subjects(RDF.type, DEL.AnnotationResponse) if (s, DEL.sourceTable, None) in delibai)
    assert evals + responses == t["pilot_peer_flags"]["imported"] + t["pilot_events"]["imported"] - report["notes"]["feedback_presentedAt_from_shown_events"]
    # read = imported + excluded + failed for every table
    for name, row in t.items():
        if row["read"]:
            assert row["read"] == row["imported"] + row["excluded"] + row["failed"], name


def test_delibai_reserved_data_absent(delibai):
    ttl = DELIBAI_TTL.read_text(encoding="utf-8")
    assert "passwordHash" not in ttl and "passwordSalt" not in ttl
    assert "survey" not in ttl.lower().replace("pilot_survey_responses", "")
    # original participant codes (DAI-XXXXXXXX) must not appear anywhere
    assert not re.search(r"\bDAI-[0-9A-F]{8}\b", ttl)
    # surveys are explicitly excluded in the report
    report = json.loads((ROOT / "data/delibai/reconciliation_report.json").read_text())
    assert report["tables"]["pilot_survey_responses"]["imported"] == 0


def test_delibai_referential_integrity(delibai):
    process = RES["delibai_pilot_2026"]
    for c in delibai.objects(process, DEL.hasContribution):
        assert (c, RDF.type, DEL.Contribution) in delibai
        assert (c, DEL.text, None) in delibai
        author = delibai.value(c, DEL.madeBy)
        assert author is not None and (author, RDF.type, DEL.Participant) in delibai
        for parent in delibai.objects(c, DEL.responseTo):
            assert (parent, RDF.type, DEL.Contribution) in delibai, parent
        topic = delibai.value(c, DEL.hasTopic)
        assert (topic, RDF.type, DEL.Topic) in delibai
    for a in delibai.subjects(DEL.annotates, None):
        for target in delibai.objects(a, DEL.annotates):
            assert (target, RDF.type, None) in delibai, f"dangling annotation target {target}"
    for r in delibai.subjects(DEL.respondsToAnnotation, None):
        for target in delibai.objects(r, DEL.respondsToAnnotation):
            assert (target, RDF.type, None) in delibai


def test_delibai_layers_are_separated(delibai):
    for fb in delibai.subjects(RDF.type, DEL.AIFeedback):
        assert (fb, RDF.type, DEL.AutomatedAnnotation) in delibai
        assert (fb, DEL.model, None) in delibai
        agent = delibai.value(fb, PROV.wasAttributedTo)
        assert (agent, RDF.type, DEL.ArtificialAgent) in delibai
    for ev in delibai.subjects(RDF.type, DEL.PeerEvaluation):
        assert (ev, RDF.type, DEL.HumanAnnotation) in delibai
        assert (ev, RDF.type, DEL.AutomatedAnnotation) not in delibai
    # seeds are attributed to the research team, participants' texts to participants
    for s in delibai.subjects(DEL.contributionSource, None):
        src = str(delibai.value(s, DEL.contributionSource))
        author = delibai.value(s, DEL.madeBy)
        if src == "seed":
            assert author == RES["delibai_research_team"]
        else:
            assert author != RES["delibai_research_team"]


def test_delibai_no_inferred_acceptance(delibai):
    """Only explicitly logged actions exist; every response has an actionType."""
    for r in delibai.subjects(RDF.type, DEL.AnnotationResponse):
        assert delibai.value(r, DEL.actionType) is not None


@pytest.mark.skipif(not (DELIBAI_CFG.exists() and DELIBAI_INPUT.exists()), reason="source snapshot not available")
def test_delibai_import_is_idempotent(tmp_path):
    out = tmp_path / "delibai.ttl"
    cmd = [sys.executable, str(ROOT / "scripts/integration/import_delibai.py"), "--output", str(out), "--report", str(tmp_path / "r.json"), "--screening-report", str(tmp_path / "s.json")]
    subprocess.run(cmd, check=False, capture_output=True)
    g1 = load(out)
    subprocess.run(cmd, check=False, capture_output=True)
    g2 = load(out)
    assert len(g1) == len(g2)
    assert set(g1) == set(g2)
    merged = Graph()
    merged += g1
    merged += g2
    assert len(merged) == len(g1)


# ---------------------------------------------------------------------------
# CrowdLaw source graph
# ---------------------------------------------------------------------------
def test_crowdlaw_counts_match_report(crowdlaw):
    report = json.loads((ROOT / "data/crowdlaw/reconciliation_report.json").read_text())
    t = report["tables"]
    contribs = set(crowdlaw.subjects(RDF.type, DEL.Contribution))
    assert len(contribs) == t["comments"]["imported"] == 146
    assert sum(1 for _ in crowdlaw.subjects(RDF.type, DEL.DeliberationProcess)) == t["documents"]["imported"] == 3
    assert t["documents"]["read"] == 16 and t["comments"]["read"] == 194
    anchors = set(crowdlaw.subjects(RDF.type, DEL.LegalResourceAnchor))
    assert len(anchors) == t["anchors_user"]["imported"] + t["anchors_system"]["imported"]


def test_crowdlaw_anchor_semantics(crowdlaw):
    for a in crowdlaw.subjects(RDF.type, DEL.LegalResourceAnchor):
        method = str(crowdlaw.value(a, DEL.anchorMethod))
        assert method in {"user_selection", "user_declared", "system_prediction"}
        prov = crowdlaw.value(a, DEL.anchorProvision)
        expr = crowdlaw.value(a, DEL.anchorExpression)
        assert (prov, RDF.type, DEL.LegalProvision) in crowdlaw
        assert (expr, RDF.type, DEL.LegalExpression) in crowdlaw
        # the provision belongs to the anchored expression (version)
        assert crowdlaw.value(prov, DEL.partOfExpression) == expr
        if method == "system_prediction":
            assert crowdlaw.value(a, DEL.confidence) is not None
            assert crowdlaw.value(a, DEL.model) is not None
        else:
            assert crowdlaw.value(a, DEL.confidence) is None
    # a comment never anchors two different expressions
    for c in crowdlaw.subjects(RDF.type, DEL.Contribution):
        exprs = {crowdlaw.value(a, DEL.anchorExpression) for a in crowdlaw.objects(c, DEL.hasAnchor)}
        assert len(exprs) <= 1


def test_crowdlaw_stance_is_independent_from_proposal(crowdlaw):
    """A negative stance must not imply a removal request."""
    for c in crowdlaw.subjects(RDF.type, DEL.Contribution):
        ops = {str(o) for o in crowdlaw.objects(c, DEL.proposedOperation)}
        if ops:
            assert ops <= {"modify", "remove"}
            assert (c, DEL.proposesChangeTo, None) in crowdlaw
        stances = {str(crowdlaw.value(a, DEL.stanceLabel)) for a in crowdlaw.objects(c, DEL.hasAnnotation) if (a, RDF.type, DEL.StanceAnnotation) in crowdlaw}
        if "contro" in stances and not ops:
            assert (c, DEL.proposesChangeTo, None) not in crowdlaw


def test_crowdlaw_stance_provenance(crowdlaw):
    for s in crowdlaw.subjects(RDF.type, DEL.StanceAnnotation):
        method = str(crowdlaw.value(s, DEL.annotationMethod))
        if method == "seed_ground_truth":
            assert (s, RDF.type, DEL.HumanAnnotation) in crowdlaw
            assert crowdlaw.value(s, PROV.wasAttributedTo) == RES["crowdlaw_research_team"]
        else:
            assert (s, RDF.type, DEL.AutomatedAnnotation) in crowdlaw
        assert crowdlaw.value(s, DEL.stanceLabel) is not None


def test_crowdlaw_legal_hierarchy(crowdlaw):
    for e in crowdlaw.subjects(RDF.type, DEL.LegalExpression):
        work = crowdlaw.value(e, DEL.expressionOf)
        assert (work, RDF.type, DEL.LegalWork) in crowdlaw
        assert crowdlaw.value(e, DEL.frbrExpressionUri) is not None
        assert str(crowdlaw.value(e, DCTERMS.language)) == "it"
        provisions = [p for p in crowdlaw.subjects(DEL.partOfExpression, e) if crowdlaw.value(p, DEL.segmentIndex) is None]
        assert provisions, f"expression without articles {e}"
        for p in provisions:
            assert crowdlaw.value(p, DEL.eId) is not None
            assert crowdlaw.value(p, DEL.text) is not None


def test_crowdlaw_excluded_test_data_absent(crowdlaw):
    texts = [str(t) for t in crowdlaw.objects(None, DEL.text)]
    assert not any("commaaaa" in t for t in texts)
    assert (RES["crowdlaw_consultation_doc1"], RDF.type, None) not in crowdlaw


@pytest.mark.skipif(not CROWDLAW_DB.exists(), reason="source database not available")
def test_crowdlaw_import_is_idempotent(tmp_path):
    out = tmp_path / "crowdlaw.ttl"
    cmd = [sys.executable, str(ROOT / "scripts/integration/import_crowdlaw.py"), "--output", str(out), "--report", str(tmp_path / "r.json")]
    subprocess.run(cmd, check=True, capture_output=True)
    g1 = load(out)
    subprocess.run(cmd, check=True, capture_output=True)
    g2 = load(out)
    assert set(g1) == set(g2)


# ---------------------------------------------------------------------------
# Links, provenance and queries
# ---------------------------------------------------------------------------
def test_links_are_marked_inferred_with_method_and_score():
    if not LINKS_TTL.exists():
        pytest.skip("links not built")
    g = load(LINKS_TTL)
    links = list(g.subjects(RDF.type, DEL.ProcessLink))
    assert links
    for l in links:
        assert str(g.value(l, DEL.linkType)) == "inferred"
        assert g.value(l, DEL.similarity) is not None
        assert g.value(l, DEL.annotationMethod) is not None
        assert g.value(l, DEL.annotationMethodVersion) is not None
        assert g.value(l, DEL.model) is not None
    # no explicit DelibAI-CrowdLaw link is invented
    for l in links:
        s, t = str(g.value(l, DEL.linkSource)), str(g.value(l, DEL.linkTarget))
        assert not ("delibai" in s and "crowdlaw" in t and str(g.value(l, DEL.linkType)) == "explicit")


def test_provenance_present(delibai, crowdlaw):
    for g, ds in ((delibai, RES["dataset_delibai_pilot_2026"]), (crowdlaw, RES["dataset_crowdlaw_evaluation_2026"])):
        assert g.value(ds, DEL.datasetStatus) is not None
        assert g.value(ds, DEL.importVersion) is not None
        act = g.value(ds, PROV.wasGeneratedBy)
        assert (act, RDF.type, DEL.ImportActivity) in g
        for c in g.subjects(RDF.type, DEL.Contribution):
            assert g.value(c, PROV.wasGeneratedBy) == act


def test_ontology_module_declares_used_terms(delibai, crowdlaw):
    onto = Graph()
    onto.parse(str(ROOT / "ontologies/ontology.ttl"), format="turtle")
    onto.parse(str(ROOT / "ontologies/deliberation-annotations.ttl"), format="turtle")
    declared = {str(s) for s in onto.subjects(RDF.type, None) if str(s).startswith(str(DEL))}
    used = set()
    for g in (delibai, crowdlaw):
        for s, p, o in g:
            if str(p).startswith(str(DEL)):
                used.add(str(p))
            if p == RDF.type and str(o).startswith(str(DEL)):
                used.add(str(o))
    # terms already used ad hoc by the existing KG (ISWC exporter) are tolerated
    legacy = {str(DEL[t]) for t in ("platform", "topicWords", "metricName", "metricValue", "metricType", "stanceLabel", "similarity", "rank")}
    missing = sorted(u for u in used - declared - legacy)
    assert not missing, f"undeclared DEL terms: {missing}"


def test_example_queries_run(delibai, crowdlaw):
    g = Graph()
    g += delibai
    g += crowdlaw
    if LINKS_TTL.exists():
        g.parse(str(LINKS_TTL), format="turtle")
    for q in sorted((ROOT / "queries/integration").glob("*.rq")):
        rows = list(g.query(q.read_text()))
        assert rows, f"query returned nothing: {q.name}"
