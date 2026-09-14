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
    {
        "id": "nb01-permanent-residence",
        "title": "1. Đăng ký thường trú.pdf",
        "domains": ["permanent_residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_PERMANENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb02-delete-permanent-residence",
        "title": "2. Xóa ĐK thường trú.pdf",
        "domains": ["residence", "delete_permanent_residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb03-temporary-residence",
        "title": "3. ĐK tạm trú.pdf",
        "domains": ["temporary_residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "TTHC_TEMP_RESIDENCE_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb04-extend-temporary-residence",
        "title": "4. Gia hạn tạm trú.pdf",
        "domains": ["extend_temporary_residence", "temporary_residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb05-household-split",
        "title": "5. Tách hộ.pdf",
        "domains": ["household_split", "residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb06-adjust-residence",
        "title": "6. Điều chỉnh TT về CT.pdf",
        "domains": ["adjust_residence", "residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb07-declare-residence-information",
        "title": "7. Khai báo TT về CT.pdf",
        "domains": ["declare_residence_information", "residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb08-residence-confirmation",
        "title": "8. Xác nhận TT về CT.pdf",
        "domains": ["residence_confirmation"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb09-delete-temporary-residence",
        "title": "9. Xóa ĐK tạm trú.pdf",
        "domains": ["delete_temporary_residence", "residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb10-temporary-absence",
        "title": "10. Khai báo tạm vắng.pdf",
        "domains": ["temporary_absence", "residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb11-stay-notification",
        "title": "11. Thông báo lưu trú.pdf",
        "domains": ["stay_notification", "residence"],
        "document_ids": ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
    },
    {
        "id": "nb12-vehicle-registration",
        "title": "12. ĐK QL phương tiện Giao thông.pdf",
        "domains": ["vehicle", "vehicle_transfer"],
        "document_ids": ["VEHICLE_CURRENT_2026", "VEHICLE_REGISTRATION_2026", "VEHICLE_TRANSFER_LOCAL_2026"],
    },
    {
        "id": "nb13-immigration",
        "title": "13. Xuất nhập cảnh.pdf",
        "domains": ["passport", "immigration"],
        "document_ids": ["PASSPORT_CURRENT_2026"],
    },
    {
        "id": "nb14-security-business",
        "title": "14. Quản lý ngành nghề.pdf",
        "domains": ["security_business"],
        "document_ids": ["SECURITY_BUSINESS_CURRENT_2026"],
    },
    {
        "id": "nb15-electronic-identity",
        "title": "15. Định danh và XTĐT.pdf",
        "domains": ["vneid"],
        "document_ids": ["VNEID_2026", "VNEID_SIM_GUIDANCE_2026"],
    },
    {
        "id": "nb16-citizen-identity-card",
        "title": "16. Cấp quản lý CCCD.pdf",
        "domains": ["identity_under14", "identity_reissue", "identity_over14_new", "identity_renewal", "identity_data", "identity_general"],
        "document_ids": ["CITIZEN_ID_5230_COMMUNE_2026"],
    },
    {
        "id": "nb17-weapons-explosives-tools",
        "title": "17. Quản lý VK VLN CCHT.pdf",
        "domains": ["weapons_management"],
        "document_ids": ["WEAPONS_CURRENT_2026"],
    },
    {
        "id": "nb18-criminal-record",
        "title": "18. Lý lịch tư pháp.pdf",
        "domains": ["criminal_record"],
        "document_ids": ["CRIMINAL_RECORD_CURRENT_2026"],
    },
    {
        "id": "nb19-driving-licence",
        "title": "19. Sát hạch cấp giấy phép lái xe.pdf",
        "domains": ["driving_licence"],
        "document_ids": ["DRIVING_LICENCE_CURRENT_2026"],
    },
]


def source_catalog():
    return [dict(item) for item in SOURCES]


def source_for_document(document_id):
    document_id = str(document_id or "")
    for source in SOURCES:
        if document_id in source["document_ids"]:
            return dict(source)
    return None


def used_sources_for_unit_ids(unit_ids):
    seen = set()
    result = []
    for unit_id in unit_ids or []:
        document_id = str(unit_id or "").split(":", 1)[0]
        source = source_for_document(document_id)
        if source and source["id"] not in seen:
            seen.add(source["id"])
            result.append(source)
    return result


def source_ids_for_domain(domain):
    return [s["id"] for s in SOURCES if domain in s["domains"]]


assert len(SOURCES) == NOTEBOOK_SOURCE_COUNT
