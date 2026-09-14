"""Source registry mirrored from the user's Gemini Notebook HTML snapshot.

The HTML snapshot contains the 19 source titles and Notebook behaviour metadata,
but not the raw PDF bytes. This module preserves the exact source catalogue and
maps each source group to current verified AI-Core document ids where available.

Never use a catalogue title by itself as legal evidence. Retrieval still relies
on active verified/current documents in the legal DB.
"""

NOTEBOOK_TITLE = "HÀNH CHÍNH CÔNG - CÔNG AN XÃ PƠNG DRANG"
NOTEBOOK_SOURCE_COUNT = 19
NOTEBOOK_SNAPSHOT_DATE = "2025-09-26"

SOURCES = [
    {"id":"nb01-permanent-residence","title":"1. Đăng ký thường trú.pdf","domains":["permanent_residence"],"document_ids":["RESIDENCE_PERMANENT_2026"]},
    {"id":"nb02-delete-permanent-residence","title":"2. Xóa ĐK thường trú.pdf","domains":["residence","delete_permanent_residence"],"document_ids":[]},
    {"id":"nb03-temporary-residence","title":"3. ĐK tạm trú.pdf","domains":["temporary_residence"],"document_ids":["TTHC_TEMP_RESIDENCE_2026"]},
    {"id":"nb04-extend-temporary-residence","title":"4. Gia hạn tạm trú.pdf","domains":["extend_temporary_residence","temporary_residence"],"document_ids":[]},
    {"id":"nb05-household-split","title":"5. Tách hộ.pdf","domains":["household_split","residence"],"document_ids":[]},
    {"id":"nb06-adjust-residence","title":"6. Điều chỉnh TT về CT.pdf","domains":["adjust_residence","residence"],"document_ids":[]},
    {"id":"nb07-declare-residence-information","title":"7. Khai báo TT về CT.pdf","domains":["declare_residence_information","residence"],"document_ids":[]},
    {"id":"nb08-residence-confirmation","title":"8. Xác nhận TT về CT.pdf","domains":["residence_confirmation"],"document_ids":[]},
    {"id":"nb09-delete-temporary-residence","title":"9. Xóa ĐK tạm trú.pdf","domains":["delete_temporary_residence","residence"],"document_ids":[]},
    {"id":"nb10-temporary-absence","title":"10. Khai báo tạm vắng.pdf","domains":["temporary_absence","residence"],"document_ids":[]},
    {"id":"nb11-stay-notification","title":"11. Thông báo lưu trú.pdf","domains":["stay_notification","residence"],"document_ids":[]},
    {"id":"nb12-vehicle-registration","title":"12. ĐK QL phương tiện Giao thông.pdf","domains":["vehicle","vehicle_transfer"],"document_ids":["VEHICLE_CURRENT_2026","VEHICLE_REGISTRATION_2026","VEHICLE_TRANSFER_LOCAL_2026"]},
    {"id":"nb13-immigration","title":"13. Xuất nhập cảnh.pdf","domains":["passport","immigration"],"document_ids":["PASSPORT_CURRENT_2026"]},
    {"id":"nb14-security-business","title":"14. Quản lý ngành nghề.pdf","domains":["security_business"],"document_ids":["SECURITY_BUSINESS_CURRENT_2026"]},
    {"id":"nb15-electronic-identity","title":"15. Định danh và XTĐT.pdf","domains":["vneid"],"document_ids":["VNEID_2026","VNEID_SIM_GUIDANCE_2026"]},
    {"id":"nb16-citizen-identity-card","title":"16. Cấp quản lý CCCD.pdf","domains":["identity_under14","identity_reissue","identity_over14_new","identity_renewal","identity_data","identity_general"],"document_ids":["CITIZEN_ID_5230_COMMUNE_2026"]},
    {"id":"nb17-weapons-explosives-tools","title":"17. Quản lý VK VLN CCHT.pdf","domains":["weapons_management"],"document_ids":["WEAPONS_CURRENT_2026"]},
    {"id":"nb18-criminal-record","title":"18. Lý lịch tư pháp.pdf","domains":["criminal_record"],"document_ids":["CRIMINAL_RECORD_CURRENT_2026"]},
    {"id":"nb19-driving-licence","title":"19. Sát hạch cấp giấy phép lái xe.pdf","domains":["driving_licence"],"document_ids":["DRIVING_LICENCE_CURRENT_2026"]},
]

_SOURCE_BY_ID = {item["id"]: item for item in SOURCES}

# One current residence document contains several procedures. Map its individual
# source units back to the exact PDF labels mirrored from the Notebook, so the UI
# cites source 9 for xóa tạm trú instead of ambiguously labelling it source 1.
_UNIT_SOURCE_IDS = {
    "RESIDENCE_NOTEBOOK_2026:permanent": "nb01-permanent-residence",
    "RESIDENCE_NOTEBOOK_2026:delete_permanent": "nb02-delete-permanent-residence",
    "RESIDENCE_NOTEBOOK_2026:temporary": "nb03-temporary-residence",
    "RESIDENCE_NOTEBOOK_2026:extend_temporary": "nb04-extend-temporary-residence",
    "RESIDENCE_NOTEBOOK_2026:split_household": "nb05-household-split",
    "RESIDENCE_NOTEBOOK_2026:adjust": "nb06-adjust-residence",
    "RESIDENCE_NOTEBOOK_2026:declare": "nb07-declare-residence-information",
    "RESIDENCE_NOTEBOOK_2026:confirmation": "nb08-residence-confirmation",
    "RESIDENCE_NOTEBOOK_2026:delete_temporary": "nb09-delete-temporary-residence",
    "RESIDENCE_NOTEBOOK_2026:temporary_absence": "nb10-temporary-absence",
    "RESIDENCE_NOTEBOOK_2026:stay_notification": "nb11-stay-notification",
    "RESIDENCE_CURRENT_2026:permanent": "nb01-permanent-residence",
    "RESIDENCE_CURRENT_2026:temporary": "nb03-temporary-residence",
    "RESIDENCE_CURRENT_2026:confirmation": "nb08-residence-confirmation",
}


def source_catalog():
    return [dict(item) for item in SOURCES]


def source_for_document(document_id):
    document_id = str(document_id or "")
    for source in SOURCES:
        if document_id in source["document_ids"]:
            return dict(source)
    return None


def source_for_unit_id(unit_id):
    unit_id = str(unit_id or "")
    source_id = _UNIT_SOURCE_IDS.get(unit_id)
    if source_id:
        return dict(_SOURCE_BY_ID[source_id])
    return source_for_document(unit_id.split(":", 1)[0])


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
