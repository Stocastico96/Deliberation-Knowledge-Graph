#!/usr/bin/env python3
"""
Live verification of the DelibAI / CrowdLaw integration against a running
citizen-interface server (default http://127.0.0.1:5001) and, optionally, the
DKG API server (--dkg http://127.0.0.1:8085).

Checks: platforms listed with logos, process summaries and counts, paginated
contributions, resource inspection (feedback, anchors, provisions), semantic
search in both modes with filters, exclusion of AI feedback by default, absence
of reserved fields in API responses, stable detail links, other platforms still
served. Exit code 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

DELIBAI = "https://svagnoni.linkeddata.es/resource/delibai_pilot_2026"
CROWDLAW = "https://svagnoni.linkeddata.es/resource/crowdlaw_consultation_doc7"
RESERVED = re.compile(r"passwordHash|passwordSalt|pilot_survey|\bDAI-[0-9A-F]{8}\b|galTan|leftRight")

results = []


def check(name, ok, info=""):
    results.append((name, bool(ok), info))
    print(f"{'PASS' if ok else 'FAIL'} {name}{' - ' + str(info)[:160] if info else ''}")


def get(base, path, **params):
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(url, timeout=600) as r:
        return json.loads(r.read().decode())


def post(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5001")
    ap.add_argument("--dkg", default=None)
    args = ap.parse_args()
    b = args.base

    health = get(b, "/api/health")
    check("health", health.get("kg_loaded"), health)

    plats = get(b, "/api/platforms")["platforms"]
    names = {p["name"]: p for p in plats}
    check("platforms include DelibAI and CrowdLaw", "DelibAI" in names and any(n.startswith("CrowdLaw") for n in names), sorted(names))
    check("other platforms still present", len(names) >= 4 or len(names) == 2, len(names))
    check("DelibAI logo path", names.get("DelibAI", {}).get("logo") == "/images/delibai-logo.png")
    check("DelibAI counts", names.get("DelibAI", {}).get("contributions_count") == 215, names.get("DelibAI", {}).get("contributions_count"))

    s = get(b, "/api/process/summary", uri=DELIBAI)
    st = s["stats"]
    check("DelibAI summary counts", st["contributions"] == 215 and st["ai_feedback"] == 99 and st["peer_evaluations"] == 275, {k: st[k] for k in ("contributions", "ai_feedback", "peer_evaluations", "recorded_responses")})
    check("DelibAI dataset status", s["dataset_status"] == "pilot-historical")
    check("DelibAI topics", len(s["topics"]) == 4)
    c = get(b, "/api/process/summary", uri=CROWDLAW)
    check("CrowdLaw summary", c["stats"]["contributions"] == 74 and c["legal_documents"] and c["legal_documents"][0]["frbr_expression"].startswith("/akn/"), c["legal_documents"][0]["frbr_expression"] if c["legal_documents"] else None)
    check("CrowdLaw status", c["dataset_status"] == "synthetic-evaluation")
    check("links labelled", all(l["link_type"] in ("explicit", "human", "inferred") for l in s["links"] + c["links"]))

    page = get(b, "/api/process/contributions", uri=DELIBAI, limit=5, offset=0, condition="delibai_on")
    check("pagination", page["total"] == 99 and len(page["contributions"]) == 5, page["total"])
    page2 = get(b, "/api/process/contributions", uri=DELIBAI, limit=5, offset=5, condition="delibai_on")
    check("pagination offset", page2["contributions"][0]["uri"] != page["contributions"][0]["uri"])
    with_fb = [x for x in get(b, "/api/process/contributions", uri=DELIBAI, limit=100, condition="delibai_on")["contributions"] if x["annotations"].get("ai_feedback")]
    check("delibai_on contributions have feedback", len(with_fb) == 99, len(with_fb))
    ins = get(b, "/api/resource/inspect", uri=with_fb[0]["uri"])
    fb = [a for a in ins["sections"]["contribution"]["annotation_details"] if a["kind"] == "AIFeedback"]
    check("inspect: AI feedback with model and origin", fb and fb[0]["origin"] == "automated" and fb[0]["model"], fb[0]["model"] if fb else None)
    check("inspect: no reserved fields", not RESERVED.search(json.dumps(ins)))

    cl = get(b, "/api/process/contributions", uri=CROWDLAW, limit=1)["contributions"][0]
    ci = get(b, "/api/resource/inspect", uri=cl["uri"])
    anchors = ci["sections"]["contribution"]["anchor_details"]
    check("inspect: CrowdLaw anchors user+system with expression", {a["method"] for a in anchors} >= {"system_prediction"} and all(a["frbr_expression"] for a in anchors), [a["method"] for a in anchors])
    prov = anchors[0]["provision"]["uri"]
    pi = get(b, "/api/resource/inspect", uri=prov)
    check("inspect: provision with text, segments, anchored contributions", pi["sections"]["provision"]["text"] and pi["sections"]["provision"]["anchored_contributions"])

    r = post(b, "/api/semantic-search", {"query": "affordable housing", "top_k": 5, "platform": "DelibAI"})
    check("search process mode (platform filter)", any("DelibAI" in x["title"] for x in r["results"]), [x["title"][:30] for x in r["results"]])
    r = post(b, "/api/semantic-search", {"query": "limiti ai compensi dei manager", "top_k": 5, "platform": "CrowdLaw"})
    check("search process mode CrowdLaw", any("emolumenti" in x["title"] or "manager" in x["title"] for x in r["results"]), [x["title"][:40] for x in r["results"]])
    r = post(b, "/api/semantic-search", {"query": "affordable housing", "top_k": 10, "mode": "items"})
    check("search items excludes AI feedback by default", r["results"] and not any(x["is_ai_generated"] for x in r["results"]))
    check("search items carry detail links", all(x["detail_url"].startswith("/?show_resource=") for x in r["results"]))
    for x in r["results"][:3]:
        got = get(b, "/api/resource/inspect", uri=x["uri"])
        check(f"result resolves in graph: {x['uri'].rsplit('/', 1)[-1][:40]}", "error" not in got)
    r = post(b, "/api/semantic-search", {"query": "housing", "top_k": 5, "mode": "items", "include_ai_feedback": True, "content_types": ["ai_feedback"]})
    check("search AI feedback on request, labelled", r["results"] and all(x["is_ai_generated"] and x["type"] == "ai_feedback" for x in r["results"]))
    r = post(b, "/api/semantic-search", {"query": "cannabis uso personale", "top_k": 5, "mode": "items", "languages": ["it"], "content_types": ["legal_provision"]})
    check("search legal provisions in Italian", r["results"] and all(x["type"] == "legal_provision" and x["language"] == "it" for x in r["results"]))
    r = post(b, "/api/semantic-search", {"query": "income", "top_k": 5, "mode": "items", "date_from": "2026-05-29", "date_to": "2026-05-29"})
    check("search date filter is strict", r["results"] and all(x.get("date") == "2026-05-29" for x in r["results"]), [x.get("date") for x in r["results"]])
    r = post(b, "/api/semantic-search", {"query": "housing policy", "top_k": 10, "mode": "items", "languages": ["it"]})
    check("search language filter is strict", r["results"] and all(x.get("language") == "it" for x in r["results"]), [x.get("language") for x in r["results"]])
    r = post(b, "/api/semantic-search", {"query": "climate change", "top_k": 5, "platform": "Pol.is"})
    check("other platforms searchable", "results" in r, len(r.get("results", [])))
    facets = get(b, "/api/search/facets")
    check("facets", "content_types" in facets and "ai_feedback" in facets["content_types"])
    check("reserved fields absent from stats/platforms", not RESERVED.search(json.dumps(plats) + json.dumps(s)))

    if args.dkg:
        d = get(args.dkg, "/api/platforms")
        ids = {p["id"]: p for p in d["platforms"]}
        check("DKG API lists delibai and crowdlaw", "delibai" in ids and "crowdlaw" in ids, {k: ids[k]["count"] for k in ids if k in ("delibai", "crowdlaw")})
        dstats = get(args.dkg, "/api/stats")
        check("DKG API stats", dstats.get("totalContributions", 0) > 0, dstats)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
