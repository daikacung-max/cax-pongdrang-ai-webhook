"""Authoritative artifact specification copied from the user-supplied Notebook HTML.

This module is the immutable product/core description of the user's work.
It intentionally contains only data that is actually visible in the supplied
HTML snapshot. External legal sources may verify/update answers, but must never
replace this artifact catalogue or silently rewrite its framing.
"""

ARTIFACT_ID = "CAX_PONG_DRANG_PUBLIC_ADMIN_NOTEBOOK"
ARTIFACT_ORIGIN = "user_supplied_work"
ARTIFACT_TITLE = "HÀNH CHÍNH CÔNG - CÔNG AN XÃ PƠNG DRANG"
ARTIFACT_SOURCE_COUNT = 19
ARTIFACT_SNAPSHOT_DATE = "2025-09-26"

SOURCE_TITLES = (
    "1. Đăng ký thường trú.pdf",
    "2. Xóa ĐK thường trú.pdf",
    "3. ĐK tạm trú.pdf",
    "4. Gia hạn tạm trú.pdf",
    "5. Tách hộ.pdf",
    "6. Điều chỉnh TT về CT.pdf",
    "7. Khai báo TT về CT.pdf",
    "8. Xác nhận TT về CT.pdf",
    "9. Xóa ĐK tạm trú.pdf",
    "10. Khai báo tạm vắng.pdf",
    "11. Thông báo lưu trú.pdf",
    "12. ĐK QL phương tiện Giao thông.pdf",
    "13. Xuất nhập cảnh.pdf",
    "14. Quản lý ngành nghề.pdf",
    "15. Định danh và XTĐT.pdf",
    "16. Cấp quản lý CCCD.pdf",
    "17. Quản lý VK VLN CCHT.pdf",
    "18. Lý lịch tư pháp.pdf",
    "19. Sát hạch cấp giấy phép lái xe.pdf",
)

# Notebook-generated summary visible in the supplied HTML. It is preserved as
# artifact metadata, not treated as a legal source by itself.
ARTIFACT_SUMMARY = (
    "Các tài liệu này cung cấp hướng dẫn chi tiết về các thủ tục hành chính "
    "thuộc thẩm quyền giải quyết của cơ quan Công an cấp xã và các đơn vị liên quan. "
    "Nội dung tập trung vào quy trình quản lý cư trú, bao gồm đăng ký thường trú, "
    "khai báo tạm vắng và thông báo lưu trú với các biểu mẫu và thời hạn cụ thể. "
    "Bên cạnh đó, nguồn tin còn làm rõ các bước đăng ký phương tiện giao thông, "
    "như cấp mới, đổi biển số định danh hoặc thu hồi giấy tờ xe đối với xe nhập khẩu "
    "và lắp ráp trong nước. Một phần nội dung cũng đề cập đến việc quản lý thiết bị "
    "phát tín hiệu cho xe ưu tiên và trình báo mất hộ chiếu phổ thông. Người dân có "
    "thể thực hiện các dịch vụ này bằng hình thức trực tiếp hoặc trực tuyến thông qua "
    "cổng dịch vụ công và ứng dụng VNeID. Những hướng dẫn này nhằm đảm bảo việc thực "
    "thi pháp luật về trật tự an toàn giao thông và quản lý dân cư được thống nhất, minh bạch."
)

SUGGESTED_QUESTIONS = (
    "Làm thế nào để đăng ký thường trú trực tuyến qua VneID?",
    "Các thủ tục cần thiết khi bị mất hộ chiếu phổ thông?",
    "Quy trình cấp biển số xe định danh lần đầu hiện nay?",
)

# Behaviour explicitly visible/inferable from the saved Notebook UI. These are
# product rules, not claims about law.
BEHAVIOUR = {
    "source_panel": True,
    "conversation_panel": True,
    "source_count": ARTIFACT_SOURCE_COUNT,
    "history_saved_between_sessions": True,
    "answers_rooted_in_selected_sources": True,
    "conversation_is_multi_turn": True,
}

# Each artifact source is assigned one stable semantic domain. The mapping is
# part of our implementation of the user's work and must remain stable even
# when the verification/update document behind a domain changes over time.
SOURCE_DOMAINS = {
    1: "permanent_residence",
    2: "delete_permanent_residence",
    3: "temporary_residence",
    4: "extend_temporary_residence",
    5: "household_split",
    6: "adjust_residence",
    7: "declare_residence_information",
    8: "residence_confirmation",
    9: "delete_temporary_residence",
    10: "temporary_absence",
    11: "stay_notification",
    12: "vehicle_management",
    13: "immigration",
    14: "security_business",
    15: "electronic_identity",
    16: "citizen_identity_card",
    17: "weapons_explosives_tools",
    18: "criminal_record",
    19: "driving_licence",
}


def artifact_manifest():
    return tuple({
        "index": index,
        "title": SOURCE_TITLES[index - 1],
        "domain": SOURCE_DOMAINS[index],
        "origin": ARTIFACT_ORIGIN,
    } for index in range(1, ARTIFACT_SOURCE_COUNT + 1))


def artifact_public_metadata():
    return {
        "artifact_id": ARTIFACT_ID,
        "origin": ARTIFACT_ORIGIN,
        "title": ARTIFACT_TITLE,
        "source_count": ARTIFACT_SOURCE_COUNT,
        "snapshot_date": ARTIFACT_SNAPSHOT_DATE,
        "summary": ARTIFACT_SUMMARY,
        "suggested_questions": list(SUGGESTED_QUESTIONS),
        "behaviour": dict(BEHAVIOUR),
    }


assert len(SOURCE_TITLES) == ARTIFACT_SOURCE_COUNT
assert set(SOURCE_DOMAINS) == set(range(1, ARTIFACT_SOURCE_COUNT + 1))
