"""Artifact-first retrieval layered over current-law verification documents.

Routing follows the 19-source user artifact. The selected artifact source is the
primary semantic boundary. Current verified documents are support/update data
inside that boundary; they do not rename or replace the artifact source.
"""

from config import LEGAL_TOP_K
from core import db
from core.artifact_router import source_index_for_question
from core.notebook_manifest import SOURCES
from core.knowledge_base import search_approved
from core.retrieval import retrieve as legacy_retrieve


PRIORITY_UNITS = {
    1: ["RESIDENCE_CURRENT_2026:permanent", "RESIDENCE_CURRENT_2026:data_reuse"],
    2: ["RESIDENCE_NOTEBOOK_2026:delete_permanent", "RESIDENCE_CURRENT_2026:data_reuse"],
    3: ["RESIDENCE_CURRENT_2026:temporary", "RESIDENCE_CURRENT_2026:data_reuse"],
    4: ["RESIDENCE_NOTEBOOK_2026:extend_temporary", "RESIDENCE_CURRENT_2026:data_reuse"],
    5: ["RESIDENCE_NOTEBOOK_2026:split_household", "RESIDENCE_CURRENT_2026:data_reuse"],
    6: ["RESIDENCE_NOTEBOOK_2026:adjust", "RESIDENCE_CURRENT_2026:data_reuse"],
    7: ["RESIDENCE_NOTEBOOK_2026:declare", "RESIDENCE_CURRENT_2026:data_reuse"],
    8: ["RESIDENCE_CURRENT_2026:confirmation", "RESIDENCE_CURRENT_2026:data_reuse"],
    9: ["RESIDENCE_NOTEBOOK_2026:delete_temporary", "RESIDENCE_CURRENT_2026:data_reuse"],
    10: ["RESIDENCE_NOTEBOOK_2026:temporary_absence"],
    11: ["RESIDENCE_NOTEBOOK_2026:stay_notification"],
    12: ["VEHICLE_CURRENT_2026:first_domestic_online", "VEHICLE_CURRENT_2026:authority"],
    13: ["PASSPORT_CURRENT_2026:issue", "PASSPORT_CURRENT_2026:scope"],
    14: ["SECURITY_BUSINESS_CURRENT_2026:new_certificate", "SECURITY_BUSINESS_CURRENT_2026:scope"],
    15: ["VNEID_2026:overview", "VNEID_2026:level2", "VNEID_2026:level1"],
    16: ["CITIZEN_ID_5230_COMMUNE_2026:scope"],
    17: ["WEAPONS_CURRENT_2026:support_tool_permit", "WEAPONS_CURRENT_2026:scope"],
    18: ["CRIMINAL_RECORD_CURRENT_2026:citizen"],
    19: ["DRIVING_LICENCE_CURRENT_2026:scope", "DRIVING_LICENCE_CURRENT_2026:test_center_type3"],
}

# Rich legacy retrieval remains useful for nuanced sub-intents, but every result
# is filtered back through the artifact-selected support-document boundary.
LEGACY_RICH_SOURCES = {12, 15, 16}


def _allowed_documents(source_index):
    source = SOURCES[source_index - 1]
    return {str(x) for x in source.get("support_document_ids") or source.get("document_ids") or []}


def _pack(source_index, question):
    source = SOURCES[source_index - 1]
    allowed_documents = _allowed_documents(source_index)
    result = []
    seen = set()
    priority_ids = list(PRIORITY_UNITS.get(source_index, []))
    normalized_question = str(question or "").lower().replace("vne id", "vneid")
    if source_index == 3 and "vneid" in normalized_question:
        priority_ids = [
            "RESIDENCE_VNEID_APP_STEPS_2026:temporary_residence",
            "RESIDENCE_VNEID_ONLINE_2026:eligibility_and_tracking",
            *priority_ids,
        ]
    for unit_id in priority_ids:
        unit = db.get_unit(unit_id)
        if unit and str(unit.get("document_id") or "") in allowed_documents and unit["id"] not in seen:
            item = dict(unit)
            item["_why"] = "artifact_priority"
            item["_artifact_source_id"] = source["id"]
            item["_artifact_source_title"] = source["title"]
            item["_score"] = 9500 - len(result)
            result.append(item)
            seen.add(item["id"])
    # Officer-approved material is scoped to the selected Notebook source and
    # ranked ahead of broad lexical matches. Drafts/archived/expired material
    # never reaches this retrieval path.
    if len(result) < LEGAL_TOP_K:
        try:
            approved = search_approved(question, source_index, limit=LEGAL_TOP_K - len(result))
        except Exception:
            approved = []  # knowledge-store outages must not break citizen chat
        for unit in approved:
            if unit["id"] in seen:
                continue
            unit["_why"] = "officer_approved_knowledge"
            unit["_artifact_source_id"] = source["id"]
            unit["_artifact_source_title"] = source["title"]
            unit["_score"] = 8000 - len(result)
            result.append(unit)
            seen.add(unit["id"])
    if len(result) < LEGAL_TOP_K:
        for unit in db.search_like(question, limit=max(LEGAL_TOP_K * 5, 30)):
            if str(unit.get("document_id") or "") not in allowed_documents:
                continue
            if unit["id"] in seen:
                continue
            item = dict(unit)
            item["_why"] = "artifact_support_search"
            item["_artifact_source_id"] = source["id"]
            item["_artifact_source_title"] = source["title"]
            item["_score"] = 5000 - len(result)
            result.append(item)
            seen.add(item["id"])
            if len(result) >= LEGAL_TOP_K:
                break
    return result[:LEGAL_TOP_K]


def _bounded_legacy(plan, question, source_index):
    source = SOURCES[source_index - 1]
    allowed = _allowed_documents(source_index)
    bounded = []
    for unit in legacy_retrieve(plan, question):
        if str(unit.get("document_id") or "") not in allowed:
            continue
        item = dict(unit)
        item["_artifact_source_id"] = source["id"]
        item["_artifact_source_title"] = source["title"]
        bounded.append(item)
    if bounded:
        return bounded[:LEGAL_TOP_K]
    return _pack(source_index, question)


def _source_index_from_plan(plan):
    """Recover the artifact boundary for elliptical follow-ups.

    The planner already receives recent conversation history and places the
    contextual user turns in search_queries. If the current message is only
    "ở thuê", "ở trọ", "cái đó mất bao lâu"... it may contain no standalone
    procedure keyword. We therefore inherit the source from the planner's
    contextual queries instead of dropping back to an unrelated legacy domain.
    """
    try:
        explicit = int((plan or {}).get("artifact_source_index") or 0)
    except (TypeError, ValueError):
        explicit = 0
    if 1 <= explicit <= len(SOURCES):
        return explicit

    for query in (plan or {}).get("search_queries") or []:
        idx = source_index_for_question(query)
        if idx is not None:
            return idx
    return None


def retrieve(plan, question):
    # Current message wins when it explicitly names a procedure. For short
    # follow-ups, inherit the artifact boundary already established by context.
    source_index = source_index_for_question(question) or _source_index_from_plan(plan)
    if source_index is None:
        # Out-of-artifact questions may still use safety/intake legal sources,
        # but they are not presented as part of the 19-source work.
        return legacy_retrieve(plan, question)

    if source_index in LEGACY_RICH_SOURCES:
        return _bounded_legacy(plan, question, source_index)
    return _pack(source_index, question)
