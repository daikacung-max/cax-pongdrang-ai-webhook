"""Planner enrichment for the user artifact.

A message owned by one of the 19 artifact sources is always treated as a
source-grounded public-administration question. The model may still generate
search hints, but it cannot route the question outside the artifact silently.
"""

from core.artifact_router import source_for_question


def enrich_plan(question, base_plan):
    plan = dict(base_plan or {})
    source = source_for_question(question)
    if not source:
        return plan
    queries = [str(x).strip() for x in (plan.get("search_queries") or []) if str(x).strip()]
    if str(question or "").strip() not in queries:
        queries.insert(0, str(question or "").strip())
    plan.update({
        "is_legal": True,
        "domain": (source.get("domains") or [None])[0],
        "artifact_source_id": source["id"],
        "artifact_source_title": source["title"],
        "artifact_source_index": source["index"],
        "search_queries": queries[:4],
    })
    return plan
