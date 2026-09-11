#!/usr/bin/env python3
"""
Shared helpers for the DelibAI / CrowdLaw integration importers.

Conventions (same as the rest of the DKG):
  * instance namespace  https://svagnoni.linkeddata.es/resource/
  * ontology namespace  https://w3id.org/deliberation/ontology#  (prefix del:)
  * every importer writes ONE source graph (Turtle) plus a JSON reconciliation
    report; the merge step (merge_source_into_kg.py) is the only thing that
    touches knowledge_graph/deliberation_kg.ttl.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, PROV, RDF, RDFS, SKOS, XSD

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RES = Namespace("https://svagnoni.linkeddata.es/resource/")
EUROVOC_LABEL = Namespace("https://w3id.org/deliberation/eurovoc-label/")

REPO_ROOT = Path(__file__).resolve().parents[2]
KG_DIR = REPO_ROOT / "knowledge_graph"
SOURCES_DIR = KG_DIR / "sources"
REPORTS_DIR = REPO_ROOT / "data"


def bind_namespaces(g: Graph) -> None:
    g.bind("del", DEL)
    g.bind("res", RES)
    g.bind("dct", DCTERMS)
    g.bind("dcat", DCAT)
    g.bind("foaf", FOAF)
    g.bind("prov", PROV)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)
    g.bind("rdfs", RDFS)
    g.bind("eurovocLabel", EUROVOC_LABEL)


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(value: Any, max_len: int = 80) -> str:
    """Deterministic, URI-safe slug (lowercase ascii, '_' separators)."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    text = _SLUG_RE.sub("_", text.lower()).strip("_")
    if len(text) > max_len:
        digest = hashlib.sha1(text.encode()).hexdigest()[:8]
        text = f"{text[: max_len - 9]}_{digest}"
    return text or "x"


def res(local: str) -> URIRef:
    return RES[local]


def pseudonym(value: str, salt: str, length: int = 12) -> str:
    """Salted, deterministic pseudonym. The salt must live outside the repo."""
    if not salt:
        raise ValueError("A non-empty pseudonym salt is required")
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:length]


# ---------------------------------------------------------------------------
# Literal helpers
# ---------------------------------------------------------------------------
def add(g: Graph, s: URIRef, p: URIRef, value: Any, datatype: URIRef | None = None, lang: str | None = None) -> bool:
    """Add a literal if value is not None/empty. Returns True when added."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, bool):
        g.add((s, p, Literal(value)))
        return True
    if datatype is not None:
        g.add((s, p, Literal(value, datatype=datatype)))
    elif lang:
        g.add((s, p, Literal(value, lang=lang)))
    else:
        g.add((s, p, Literal(value)))
    return True


def add_datetime(g: Graph, s: URIRef, p: URIRef, value: Any) -> bool:
    dt = parse_datetime(value)
    if dt is None:
        return False
    g.add((s, p, Literal(dt.isoformat(), datatype=XSD.dateTime)))
    return True


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace(" ", "T", 1)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # postgres style "+00" -> "+00:00"
    if re.search(r"[+-]\d\d$", text):
        text = text + ":00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Personal-data screening (documented publication condition for pilot texts)
# ---------------------------------------------------------------------------
_PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "phone": re.compile(r"(?<!\d)(\+?\d[\d \-]{7,}\d)(?!\d)"),
    "url": re.compile(r"https?://\S+|www\.\S+", re.I),
    "handle": re.compile(r"(?<!\w)@\w{3,}"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    "self_identification": re.compile(
        r"\b(my name is|mi chiamo|i am called|i live in|abito in|codice fiscale|tax code|passport number)\b", re.I
    ),
}


def screen_text(text: str) -> list[str]:
    """Return the list of PII pattern names matched by the text (empty = clean)."""
    if not text:
        return []
    hits = []
    for name, pattern in _PII_PATTERNS.items():
        if pattern.search(text):
            hits.append(name)
    return hits


# ---------------------------------------------------------------------------
# Reconciliation report
# ---------------------------------------------------------------------------
class Report:
    """Counts records read / imported / excluded / failed, plus warnings."""

    def __init__(self, source: str, import_version: str, mapping_version: str):
        self.source = source
        self.import_version = import_version
        self.mapping_version = mapping_version
        self.started_at = now_iso()
        self.tables: dict[str, dict[str, int]] = {}
        self.exclusions: dict[str, dict[str, int]] = {}
        self.warnings: list[str] = []
        self.notes: dict[str, Any] = {}

    def table(self, name: str) -> dict[str, int]:
        return self.tables.setdefault(name, {"read": 0, "imported": 0, "excluded": 0, "failed": 0})

    def read(self, name: str, n: int = 1) -> None:
        self.table(name)["read"] += n

    def imported(self, name: str, n: int = 1) -> None:
        self.table(name)["imported"] += n

    def excluded(self, name: str, reason: str, n: int = 1) -> None:
        self.table(name)["excluded"] += n
        bucket = self.exclusions.setdefault(name, {})
        bucket[reason] = bucket.get(reason, 0) + n

    def failed(self, name: str, message: str) -> None:
        self.table(name)["failed"] += 1
        self.warnings.append(f"{name}: {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self, graph: Graph | None = None) -> dict[str, Any]:
        out = {
            "source": self.source,
            "import_version": self.import_version,
            "mapping_version": self.mapping_version,
            "started_at": self.started_at,
            "finished_at": now_iso(),
            "tables": self.tables,
            "exclusions": self.exclusions,
            "warnings": self.warnings,
            "notes": self.notes,
        }
        if graph is not None:
            out["triples"] = len(graph)
            out["entities_by_type"] = count_types(graph)
        return out

    def write(self, path: Path, graph: Graph | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(graph), indent=2, ensure_ascii=False), encoding="utf-8")


def count_types(g: Graph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _s, _p, o in g.triples((None, RDF.type, None)):
        key = str(o).replace(str(DEL), "del:").replace(str(PROV), "prov:").replace(str(DCAT), "dcat:")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Import provenance
# ---------------------------------------------------------------------------
def add_import_provenance(
    g: Graph,
    *,
    source_key: str,
    dataset_uri: URIRef,
    title: str,
    description: str,
    import_version: str,
    mapping_version: str,
    snapshot_date: str | None,
    script_name: str,
    dataset_status: str,
    landing_page: str | None = None,
    license_uri: str | None = None,
) -> URIRef:
    """Adds a dcat:Dataset for the source and a del:ImportActivity for this run."""
    activity = res(f"{source_key}_import_{slug(import_version)}")
    g.add((dataset_uri, RDF.type, DCAT.Dataset))
    add(g, dataset_uri, DCTERMS.title, title, lang="en")
    add(g, dataset_uri, DCTERMS.description, description, lang="en")
    add(g, dataset_uri, DEL.datasetStatus, dataset_status)
    add(g, dataset_uri, DEL.importVersion, import_version)
    add(g, dataset_uri, DEL.mappingVersion, mapping_version)
    if snapshot_date:
        add_datetime(g, dataset_uri, DEL.sourceSnapshotDate, snapshot_date)
    if landing_page:
        g.add((dataset_uri, DCAT.landingPage, URIRef(landing_page)))
    if license_uri:
        g.add((dataset_uri, DCTERMS.license, URIRef(license_uri)))
    g.add((dataset_uri, PROV.wasGeneratedBy, activity))
    g.add((activity, RDF.type, DEL.ImportActivity))
    g.add((activity, RDF.type, PROV.Activity))
    add(g, activity, RDFS.label, f"Import of {title} ({import_version})", lang="en")
    add(g, activity, DEL.importVersion, import_version)
    add(g, activity, DEL.mappingVersion, mapping_version)
    # No wall-clock timestamp in the graph: it would make every run differ and
    # break idempotency. The run time is recorded in the reconciliation report.
    add(g, activity, DEL.annotationMethod, script_name)
    return activity


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_graph(g: Graph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(path), format="turtle")
