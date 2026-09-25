"""Artifact-first source registry for CAX PƠNG DRANG AI CORE.

The 19 titles and Notebook framing come from the user-supplied HTML artifact.
`document_ids` are only verification/update adapters. They may change as law
changes, but they do not replace or rename the user's artifact sources.
"""

from core.artifact_core import (
    ARTIFACT_ORIGIN,
    ARTIFACT_SOURCE_COUNT,
    ARTIFACT_SNAPSHOT_DATE,
    ARTIFACT_TITLE,
    SOURCE_TITLES,
)

NOTEBOOK_TITLE = ARTIFACT_TITLE
NOTEBOOK_SOURCE_COUNT = ARTIFACT_SOURCE_COUNT
NOTEBOOK_SNAPSHOT_DATE = ARTIFACT_SNAPSHOT_DATE


def _source(index, source_id, domains, document_ids):
    return {
        "id": source_id,
        "index": index,
        "title": SOURCE_TITLES[index - 1],
        "domains": list(domains),
        "origin": ARTIFACT_ORIGIN,
        # Compatibility field consumed by existing UI/retrieval. Semantically
        # these are support/update documents, not a replacement for the source.
        "document_ids": list(document_ids),
        "support_document_ids": list(document_ids),
    }


SOURCES = [
    _source(1, "nb01-permanent-residence", ["permanent_residence"], ["RESIDENCE_CURRENT_2026", "RESIDENCE_PERMANENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(2, "nb02-delete-permanent-residence", ["delete_permanent_residence", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(3, "nb03-temporary-residence", ["temporary_residence"], ["RESIDENCE_CURRENT_2026", "TTHC_TEMP_RESIDENCE_2026", "RESIDENCE_GUIDANCE_2026", "RESIDENCE_VNEID_ONLINE_2026", "RESIDENCE_VNEID_APP_STEPS_2026"]),
    _source(4, "nb04-extend-temporary-residence", ["extend_temporary_residence", "temporary_residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(5, "nb05-household-split", ["household_split", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(6, "nb06-adjust-residence", ["adjust_residence", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(7, "nb07-declare-residence-information", ["declare_residence_information", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(8, "nb08-residence-confirmation", ["residence_confirmation"], ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(9, "nb09-delete-temporary-residence", ["delete_temporary_residence", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(10, "nb10-temporary-absence", ["temporary_absence", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(11, "nb11-stay-notification", ["stay_notification", "residence"], ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"]),
    _source(12, "nb12-vehicle-registration", ["vehicle", "vehicle_transfer", "vehicle_management"], ["VEHICLE_CURRENT_2026", "VEHICLE_REGISTRATION_2026", "VEHICLE_TRANSFER_LOCAL_2026"]),
    _source(13, "nb13-immigration", ["passport", "immigration"], ["PASSPORT_CURRENT_2026"]),
    _source(14, "nb14-security-business", ["security_business"], ["SECURITY_BUSINESS_CURRENT_2026"]),
    _source(15, "nb15-electronic-identity", ["vneid", "electronic_identity"], ["VNEID_2026", "VNEID_SIM_GUIDANCE_2026"]),
    _source(16, "nb16-citizen-identity-card", ["identity_under14", "identity_reissue", "identity_over14_new", "identity_renewal", "identity_data", "identity_general", "citizen_identity_card"], ["CITIZEN_ID_5230_COMMUNE_2026"]),
    _source(17, "nb17-weapons-explosives-tools", ["weapons_management", "weapons_explosives_tools"], ["WEAPONS_CURRENT_2026"]),
    _source(18, "nb18-criminal-record", ["criminal_record"], ["CRIMINAL_RECORD_CURRENT_2026"]),
    _source(19, "nb19-driving-licence", ["driving_licence"], ["DRIVING_LICENCE_CURRENT_2026"]),
]

# Exact unit-to-artifact mapping for shared support documents. Without this,
# many residence procedures would all appear to cite source #1 just because
# they share RESIDENCE_CURRENT_2026 as an update/verification document.
UNIT_SOURCE_INDEX = {
    "RESIDENCE_CURRENT_2026:permanent": 1,
    "RESIDENCE_NOTEBOOK_2026:delete_permanent": 2,
    "RESIDENCE_CURRENT_2026:temporary": 3,
    "RESIDENCE_NOTEBOOK_2026:extend_temporary": 4,
    "RESIDENCE_NOTEBOOK_2026:split_household": 5,
    "RESIDENCE_NOTEBOOK_2026:adjust": 6,
    "RESIDENCE_NOTEBOOK_2026:declare": 7,
    "RESIDENCE_CURRENT_2026:confirmation": 8,
    "RESIDENCE_NOTEBOOK_2026:delete_temporary": 9,
    "RESIDENCE_NOTEBOOK_2026:temporary_absence": 10,
    "RESIDENCE_NOTEBOOK_2026:stay_notification": 11,
}


def source_catalog():
    return [dict(item) for item in SOURCES]


def source_for_document(document_id):
    document_id = str(document_id or "")
    if document_id.startswith("KB_"):
        try:
            from core.knowledge_base import get_document
            item = get_document(document_id)
            if item:
                return {
                    "id": document_id,
                    "index": int(item["source_index"]),
                    "title": item["title"],
                    "domains": [],
                    "origin": item.get("source_url") or item.get("issuer") or "Tài liệu cán bộ đã duyệt",
                    "document_ids": [document_id],
                    "support_document_ids": [document_id],
                }
        except Exception:
            return None
    for source in SOURCES:
        if document_id in source["document_ids"]:
            return dict(source)
    return None


def source_for_unit_id(unit_id):
    unit_id = str(unit_id or "")
    if unit_id in UNIT_SOURCE_INDEX:
        return dict(SOURCES[UNIT_SOURCE_INDEX[unit_id] - 1])
    document_id = unit_id.split(":", 1)[0]
    return source_for_document(document_id)


def used_sources_for_unit_ids(unit_ids):
    seen = set()
    result = []
    for unit_id in unit_ids or []:
        source = source_for_unit_id(unit_id)
        if source and source["id"] not in seen:
            seen.add(source["id"])
            result.append(source)
    return result


def source_ids_for_domain(domain):
    return [s["id"] for s in SOURCES if domain in s["domains"]]


assert len(SOURCES) == NOTEBOOK_SOURCE_COUNT
assert [s["title"] for s in SOURCES] == list(SOURCE_TITLES)
