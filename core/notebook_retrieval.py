"""Artifact-first retrieval layered over current-law verification documents.

Routing follows the 19-source user artifact. The selected artifact source is the
primary semantic boundary. Current verified documents are support/update data
inside that boundary; they do not rename or replace the artifact source.
"""

from config import LEGAL_TOP_K
from core import db
from core.artifact_router import source_index_for_question
from core.notebook_manifest import SOURCES
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
    13: ["PASSPORT_CURRENT_2026:issue", "PASSPORT_CURRENT_2026:scope"],
    14: ["SECURITY_BUSINESS_CURRENT_2026:new_certificate", "SECURITY_BUSINESS_CURRENT_2026:scope"],
    17: ["WEAPONS_CURRENT_2026:support_tool_permit", "WEAPONS_CURRENT_2026:scope"],
    18: ["CRIMINAL_RECORD_CURRENT_2026:citizen"],
    19: ["DRIVING_LICENCE_CURRENT_2026:scope", "DRIVING_LICENCE_CURRENT_2026:test_center_type3"],
}

# Rich legacy retrievers already contain current sub-routing for these domains.
LEGACY_RICH_SOURCES = {12, 15, 16}


def _pack(source_index, question):
    source = SOURCES[source_index - 1]
    allowed_documents = {str(x) for x in source.get("support_document_ids") or source.get("document_ids") or []}
    result = []
    seen = set()
    for unit_id in PRIORITY_UNITS.get(source_index, []):
        unit = db.get_unit(unit_id)
        if unit and unit["id"] not in seen:
            item = dict(unit)
            item["_why"] = "artifact_priority"
            item["_artifact_source_id"] = source["id"]
            item["_artifact_source_title"] = source["title"]
            item["_score"] = 9500 - len(result)
            result.append(item)
            seen.add(item["id"])
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


def _tag_artifact(units, source_index):
    source = SOURCES[source_index - 1]
    tagged = []
    for unit in units:
        item = dict(unit)
        item["_artifact_source_id"] = source["id"]
        item["_artifact_source_title"] = source["title"]
        tagged.append(item)
    return tagged


def retrieve(plan, question):
    source_index = source_index_for_question(question)
    if source_index is None:
        # Out-of-artifact questions may still use safety/intake legal sources,
        # but they are not presented as part of the 19-source work.
        return legacy_retrieve(plan, question)

    if source_index in LEGACY_RICH_SOURCES:
        return _tag_artifact(legacy_retrieve(plan, question), source_index)
    return _pack(source_index, question)
