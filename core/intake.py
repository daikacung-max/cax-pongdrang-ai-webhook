"""Phân loại tiếp nhận cho bản demo, không trích xuất hay lưu giá trị dữ liệu cá nhân.

Module này chỉ trả về mã nhóm việc, các trường còn thiếu và hàng đợi nghiệp vụ
gợi ý. Việc tạo/đẩy hồ sơ thật phải được thực hiện ở cổng cán bộ có phân quyền.
"""

import re
import unicodedata


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%\s]", " ", text)).strip()


# `source_ready=False` có nghĩa AI chỉ được ghi nhận nhu cầu và hướng dẫn chuyển
# cán bộ; không được tự tư vấn chi tiết thủ tục khi kho nguồn chưa được duyệt.
PROCEDURES = (
    {
        "code": "identity_card_under14",
        "name": "Cấp thẻ căn cước cho người dưới 14 tuổi",
        "queue": "ADMIN_IDENTITY",
        "source_ready": True,
        # Không đưa "căn cước"/"CCCD" vào đây: chúng quá rộng và sẽ lấn các
        # tình huống như mất thẻ, cấp lại hoặc đổi thẻ của người lớn.
        "keywords": ("duoi 14", "tre em", "con toi", "be nha toi"),
        "fields": (
            ("age_group", "người cần làm căn cước hiện dưới 06 tuổi hay từ đủ 06 đến dưới 14 tuổi", ("duoi 6", "6 tuoi", "duoi 14", "13 tuoi", "12 tuoi", "11 tuoi", "10 tuoi", "9 tuoi", "8 tuoi", "7 tuoi")),
        ),
    },
    {
        "code": "identity_card",
        "name": "Căn cước: cấp, đổi, cấp lại hoặc điều chỉnh thông tin",
        "queue": "ADMIN_IDENTITY",
        "source_ready": False,
        "keywords": ("can cuoc", "cccd", "can cuoc cong dan"),
        "fields": (
            ("request_type", "anh/chị cần cấp mới, đổi, cấp lại hay điều chỉnh thông tin", ("cap moi", "cap lai", "doi", "dieu chinh")),
        ),
    },
    {
        "code": "vneid",
        "name": "Tài khoản định danh điện tử VNeID",
        "queue": "ADMIN_IDENTITY",
        "source_ready": True,
        "keywords": ("vneid", "dinh danh dien tu", "tai khoan dinh danh", "muc do 1", "muc do 2"),
        "fields": (
            ("level", "anh/chị cần hỗ trợ VNeID mức 1 hay mức 2", ("muc 1", "muc 2", "muc do 1", "muc do 2")),
        ),
    },
    {
        "code": "residence",
        "name": "Cư trú: thường trú, tạm trú hoặc xác nhận cư trú",
        "queue": "ADMIN_RESIDENCE",
        "source_ready": True,
        "keywords": ("tam tru", "thuong tru", "cu tru", "nhap khau", "xac nhan cu tru"),
        "fields": (
            ("request_type", "anh/chị cần đăng ký tạm trú, thường trú hay xác nhận thông tin cư trú", ("tam tru", "thuong tru", "xac nhan")),
            ("accommodation", "chỗ ở của anh/chị là nhà của mình, ở cùng người thân hay đi thuê", ("nha cua", "nguoi than", "thue", "o cung")),
        ),
    },
    {
        "code": "vehicle_registration",
        "name": "Đăng ký xe mô tô, xe gắn máy",
        "queue": "VEHICLE_REGISTRATION",
        "source_ready": True,
        "keywords": ("dang ky xe", "xe may", "xe mo to", "xe gan may", "bien so", "sang ten xe"),
        "fields": (
            ("request_type", "anh/chị cần đăng ký lần đầu, sang tên hay cấp đổi giấy tờ xe", ("lan dau", "mua xe moi", "sang ten", "cap doi")),
        ),
    },
    {
        "code": "crime_report",
        "name": "Tố giác, tin báo về tội phạm",
        "queue": "CRIME_INTAKE",
        "source_ready": True,
        "keywords": ("to giac", "tin bao toi pham", "trinh bao toi pham", "bi de doa", "de doa", "bi trom"),
        "fields": (
            ("incident_type", "sự việc chính anh/chị muốn trình báo là gì", ("lua dao", "danh", "de doa", "trom", "mat")),
            ("time_place", "sự việc xảy ra khi nào và ở đâu", ("hom nay", "hom qua", "ngay", "tai", "o " , "luc")),
        ),
    },
    {
        "code": "fraud_transfer",
        "name": "Lừa đảo chuyển khoản",
        "queue": "CRIME_INTAKE",
        "source_ready": False,
        "keywords": ("lua dao chuyen khoan", "bi lua", "chuyen tien", "chuyen khoan", "bi scam"),
        "fields": (
            ("transaction_time", "anh/chị chuyển khoản vào thời điểm nào", ("hom nay", "hom qua", "ngay", "luc", "gio")),
            ("evidence", "anh/chị còn lưu giao dịch, tin nhắn hoặc số tài khoản liên quan không", ("sao ke", "tin nhan", "so tai khoan", "anh chup", "chung tu")),
        ),
    },
    {
        "code": "assault_evidence",
        "name": "Bị hành hung, thương tích và chứng cứ",
        "queue": "CRIME_INTAKE",
        "source_ready": True,
        "keywords": ("bi danh", "nguoi khac danh", "bi hanh hung", "thuong tich", "dung dao", "camera", "video"),
        "fields": (
            ("injury", "anh/chị đã đi khám hoặc có kết quả thương tích chưa", ("thuong tich", "%", "di kham", "giay chung thuong")),
            ("evidence", "anh/chị còn lưu video, ảnh, tin nhắn hoặc thông tin người biết sự việc không", ("camera", "video", "clip", "anh chup", "tin nhan", "nguoi chung kien")),
        ),
    },
    {
        "code": "lost_document",
        "name": "Trình báo mất giấy tờ hoặc tài sản",
        "queue": "ADMIN_INTAKE",
        "source_ready": False,
        "keywords": ("mat giay to", "mat can cuoc", "mat cccd", "mat tai san", "mat dien thoai", "mat xe", "that lac"),
        "fields": (
            ("lost_item", "anh/chị bị mất loại giấy tờ hoặc tài sản nào", ("can cuoc", "cccd", "giay", "tai san", "dien thoai", "xe")),
            ("time_place", "anh/chị mất vào khi nào và ở khu vực nào", ("hom nay", "hom qua", "ngay", "tai", "o ", "luc")),
        ),
    },
)


def _conversation_text(question, history):
    user_turns = [
        str(item.get("content") or "")
        for item in (history or [])
        if item.get("role") == "user"
    ]
    return _norm(" ".join((user_turns + [str(question or "")])[-5:]))


def _requests_intake(question, text):
    """Chỉ mở luồng hồ sơ khi người dân thể hiện ý định tiếp nhận rõ ràng.

    Việc hỏi "thủ tục là gì" hoặc "cần những gì" luôn là tư vấn, dù hệ thống
    đã nhận diện đúng nhóm nghiệp vụ. Không suy diễn nhu cầu chuyển cán bộ.
    """
    current = _norm(question)
    if any(marker in current for marker in ("la gi", "nhu the nao", "can gi", "thu tuc", "hoi", "huong dan")):
        return False
    explicit_markers = (
        "toi muon nop ho so", "muon nop ho so", "nop ho so", "gui ho so",
        "tao ho so", "tiep nhan ho so", "can can bo xu ly", "chuyen can bo",
        "toi muon dang ky", "cho toi dang ky", "toi muon trinh bao",
        "can trinh bao", "toi muon to giac", "can to giac", "yeu cau tiep nhan",
    )
    return any(marker in text for marker in explicit_markers)


def assess(question, history):
    """Trả metadata không chứa nội dung hay giá trị dữ liệu của người dân."""
    text = _conversation_text(question, history)
    matches = [
        item for item in PROCEDURES
        if any(keyword in text for keyword in item["keywords"])
    ]
    if not matches:
        return {
            "procedure_code": "unclassified",
            "source_ready": False,
            "conversation_mode": "advice_only",
            "handoff_status": "not_requested",
            "handoff_queue": None,
            "missing_field_ids": [],
            "next_question": None,
        }

    by_code = {item["code"]: item for item in matches}
    # Tin báo sự việc luôn ưu tiên hơn thủ tục có cùng tên tài sản (ví dụ mất xe
    # không phải là yêu cầu đăng ký xe). Những nhánh cụ thể vẫn ưu tiên tiếp.
    if any(x in text for x in ("bi trom", "bi de doa", "de doa")) and "crime_report" in by_code:
        chosen = by_code["crime_report"]
    elif any(x in text for x in ("mat dien thoai", "mat xe", "mat tai san")) and "lost_document" in by_code:
        chosen = by_code["lost_document"]
    else:
        # Ưu tiên nhóm cụ thể hơn nhóm tố giác chung khi cùng xuất hiện trong mạch chat.
        chosen = max(matches, key=lambda item: (len(item["keywords"]), item["source_ready"]))
    missing = [field for field in chosen["fields"] if not any(cue in text for cue in field[2])]
    intake_requested = _requests_intake(question, text)
    if not intake_requested:
        conversation_mode = "advice_only"
        handoff_status = "not_requested"
    elif missing:
        conversation_mode = "intake_requested"
        handoff_status = "needs_information"
    else:
        conversation_mode = "intake_requested"
        handoff_status = "ready_for_officer"
    return {
        "procedure_code": chosen["code"],
        "procedure_name": chosen["name"],
        "source_ready": bool(chosen["source_ready"]) and not (
            chosen["code"] == "vehicle_registration" and any(x in text for x in ("sang ten", "cap doi"))
        ),
        "conversation_mode": conversation_mode,
        "handoff_status": handoff_status,
        "handoff_queue": chosen["queue"],
        "missing_field_ids": [field[0] for field in missing],
        "next_question": missing[0][1] if intake_requested and missing else None,
    }


def prompt_hint(intake):
    """Hướng dẫn hội thoại ngắn; không để mô hình lộ mã hàng đợi nội bộ."""
    question = intake.get("next_question")
    if intake.get("conversation_mode") != "intake_requested" or not question:
        return ""
    return (
        "Mạch tiếp nhận đang thiếu một dữ kiện. Nếu câu trả lời cần làm rõ thêm, "
        f"ưu tiên chỉ hỏi: '{question}'. Không nêu mã thủ tục, mã hàng đợi hay trạng thái nội bộ."
    )
