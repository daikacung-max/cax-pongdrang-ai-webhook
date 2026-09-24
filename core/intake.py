"""Phân loại tiếp nhận cho bản demo, không trích xuất hay lưu giá trị dữ liệu cá nhân.

Module này chỉ trả về mã nhóm việc, các trường còn thiếu và hàng đợi nghiệp vụ
gợi ý. Việc tạo/đẩy hồ sơ thật phải được thực hiện ở cổng cán bộ có phân quyền.

Nguyên tắc hội thoại: lịch sử giúp hiểu câu nối, nhưng một chủ đề mới rõ ràng
không được kế thừa trạng thái tiếp nhận của chủ đề cũ.
"""

import re
import unicodedata

from core.team_routing import team_for_queue


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%\s]", " ", text)).strip()
    return text.replace("vne id", "vneid").replace("vnied", "vneid").replace("vned", "vneid")


def _contains_phrase(text, phrase):
    phrase = _norm(phrase)
    if not phrase:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, str(text or "")) is not None


PROCEDURES = (
    {
        "code": "identity_card_under14", "name": "Cấp thẻ căn cước cho người dưới 14 tuổi",
        "queue": "ADMIN_IDENTITY", "source_ready": True,
        "keywords": ("duoi 14", "tre em", "con toi", "be nha toi"),
        "fields": (("age_group", "người cần làm căn cước hiện dưới 06 tuổi hay từ đủ 06 đến dưới 14 tuổi", ("duoi 6", "6 tuoi", "duoi 14", "13 tuoi", "12 tuoi", "11 tuoi", "10 tuoi", "9 tuoi", "8 tuoi", "7 tuoi")),),
    },
    {
        "code": "identity_card_reissue", "name": "Cấp lại thẻ căn cước bị mất hoặc hư hỏng",
        "queue": "ADMIN_IDENTITY", "source_ready": True,
        "keywords": ("mat can cuoc", "mat cccd", "cap lai can cuoc", "cap lai cccd", "can cuoc hu hong", "cccd hu hong"),
        "fields": (("reissue_reason", "anh/chị bị mất thẻ hay thẻ bị hư hỏng không sử dụng được", ("mat", "hu hong", "khong su dung duoc")),),
    },
    {
        "code": "identity_card", "name": "Căn cước: cấp, đổi, cấp lại hoặc điều chỉnh thông tin",
        "queue": "ADMIN_IDENTITY", "source_ready": False,
        "keywords": ("can cuoc", "cccd", "can cuoc cong dan"),
        "fields": (("request_type", "anh/chị cần cấp mới, đổi, cấp lại hay điều chỉnh thông tin", ("cap moi", "cap lai", "doi", "dieu chinh")),),
    },
    {
        "code": "vneid", "name": "Tài khoản định danh điện tử VNeID",
        "queue": "ADMIN_IDENTITY", "source_ready": True,
        "keywords": ("vneid", "dinh danh dien tu", "tai khoan dinh danh", "muc do 1", "muc do 2"),
        "fields": (("level", "anh/chị cần hỗ trợ VNeID mức 1 hay mức 2", ("muc 1", "muc 2", "muc do 1", "muc do 2")),),
    },
    {
        "code": "residence", "name": "Cư trú: thường trú, tạm trú hoặc xác nhận cư trú",
        "queue": "ADMIN_RESIDENCE", "source_ready": True,
        "keywords": ("tam tru", "thuong tru", "cu tru", "nhap khau", "xac nhan cu tru"),
        "fields": (
            ("request_type", "anh/chị cần đăng ký tạm trú, thường trú hay xác nhận thông tin cư trú", ("tam tru", "thuong tru", "xac nhan")),
            ("accommodation", "chỗ ở của anh/chị là nhà của mình, ở cùng người thân hay đi thuê", ("nha cua", "nguoi than", "thue", "o cung", "o tro", "o nho")),
        ),
    },
    {
        "code": "vehicle_registration", "name": "Đăng ký xe mô tô, xe gắn máy",
        "queue": "VEHICLE_REGISTRATION", "source_ready": True,
        "keywords": ("dang ky xe", "xe may", "xe mo to", "xe gan may", "bien so", "sang ten xe"),
        "fields": (("request_type", "anh/chị cần đăng ký lần đầu, sang tên hay cấp đổi giấy tờ xe", ("lan dau", "mua xe moi", "sang ten", "cap doi")),),
    },
    {
        "code": "noise_report", "name": "Phản ánh tiếng ồn, karaoke ảnh hưởng khu dân cư",
        "queue": "PUBLIC_ORDER_INTAKE", "source_ready": True,
        "keywords": ("karaoke", "loa keo", "tieng on", "on ao", "hat to"),
        "fields": (("time_place", "việc gây ồn đang xảy ra ở đâu và vào thời điểm nào", ("hom nay", "hom qua", "luc", "gio", "tai", "nha", "thon", "buon")),),
    },
    {
        "code": "community_dispute", "name": "Mâu thuẫn, xích mích trong khu dân cư",
        "queue": "COMMUNITY_DISPUTE_INTAKE", "source_ready": False,
        "keywords": ("mau thuan", "xich mich", "cai nhau", "tranh chap hang xom", "va cham hang xom"),
        "fields": (("time_place", "mâu thuẫn xảy ra ở đâu và vào thời điểm nào", ("hom nay", "hom qua", "luc", "gio", "tai", "nha", "thon", "buon")),),
    },
    {
        "code": "gambling_report", "name": "Thông tin về cá độ, cá cược hoặc đánh bạc",
        "queue": "CRIME_INTAKE", "source_ready": True,
        "keywords": ("ca do", "ca cuoc", "danh bac", "co bac"),
        "fields": (("time_place", "sự việc xảy ra hoặc đang diễn ra ở đâu và vào thời điểm nào", ("hom nay", "hom qua", "luc", "gio", "tai", "nha", "quan", "dia diem")),),
    },
    {
        "code": "crime_report", "name": "Tố giác, tin báo về tội phạm",
        "queue": "CRIME_INTAKE", "source_ready": True,
        "keywords": ("to giac", "tin bao toi pham", "trinh bao toi pham", "bi de doa", "de doa", "bi trom"),
        "fields": (
            ("incident_type", "sự việc chính anh/chị muốn trình báo là gì", ("lua dao", "danh", "de doa", "trom", "mat")),
            ("time_place", "sự việc xảy ra khi nào và ở đâu", ("hom nay", "hom qua", "ngay", "tai", "luc")),
        ),
    },
    {
        "code": "fraud_transfer", "name": "Lừa đảo chuyển khoản",
        "queue": "CRIME_INTAKE", "source_ready": False,
        "keywords": ("lua dao chuyen khoan", "bi lua", "chuyen tien", "chuyen khoan", "bi scam"),
        "fields": (
            ("transaction_time", "anh/chị chuyển khoản vào thời điểm nào", ("hom nay", "hom qua", "ngay", "luc", "gio")),
            ("evidence", "anh/chị còn lưu giao dịch, tin nhắn hoặc chứng cứ liên quan không", ("sao ke", "tin nhan", "so tai khoan", "anh chup", "anh hien truong", "chung tu", "camera", "video", "clip", "nguoi chung kien", "bien so", "tai lieu")),
        ),
    },
    {
        "code": "assault_evidence", "name": "Bị hành hung, thương tích và chứng cứ",
        "queue": "CRIME_INTAKE", "source_ready": True,
        "keywords": ("bi danh", "nguoi khac danh", "bi hanh hung", "thuong tich", "dung dao", "camera", "video"),
        "fields": (
            ("injury", "anh/chị đã đi khám hoặc có kết quả thương tích chưa", ("thuong tich", "%", "di kham", "giay chung thuong")),
            ("evidence", "anh/chị còn lưu video, ảnh, tin nhắn hoặc thông tin người biết sự việc không", ("camera", "video", "clip", "anh chup", "anh hien truong", "tin nhan", "nguoi chung kien", "tai lieu")),
        ),
    },
    {
        "code": "lost_document", "name": "Trình báo mất giấy tờ hoặc tài sản",
        "queue": "ADMIN_INTAKE", "source_ready": False,
        "keywords": ("mat giay to", "mat can cuoc", "mat cccd", "mat tai san", "mat dien thoai", "mat xe", "that lac"),
        "fields": (
            ("lost_item", "anh/chị bị mất loại giấy tờ hoặc tài sản nào", ("can cuoc", "cccd", "giay", "tai san", "dien thoai", "xe")),
            ("time_place", "anh/chị mất vào khi nào và ở khu vực nào", ("hom nay", "hom qua", "ngay", "tai", "luc")),
        ),
    },
)


def _conversation_text(question, history):
    user_turns = [str(item.get("content") or "") for item in (history or []) if item.get("role") == "user"]
    return _norm(" ".join((user_turns + [str(question or "")])[-5:]))


def _matches(text):
    return [item for item in PROCEDURES if any(keyword in text for keyword in item["keywords"])]


def _latest_intake(history):
    for item in reversed(history or []):
        if item.get("role") != "assistant":
            continue
        intake = (item.get("meta") or {}).get("intake") or {}
        if intake.get("conversation_mode") == "intake_requested":
            return intake
        # Once an assistant turn is not in intake mode, an older request must
        # not leak forward through it.
        return {}
    return {}


def _requests_intake(question, history, chosen_code, current_has_topic):
    current = _norm(question)
    advice_markers = ("la gi", "nhu the nao", "can gi", "thu tuc", "hoi", "huong dan")
    explicit_markers = (
        "toi muon nop ho so", "muon nop ho so", "nop ho so", "gui ho so", "tao ho so",
        "tiep nhan ho so", "can can bo xu ly", "chuyen can bo", "toi muon dang ky",
        "cho toi dang ky", "toi muon trinh bao", "can trinh bao", "toi muon to giac",
        "can to giac", "yeu cau tiep nhan", "can cong an tiep nhan", "cong an tiep nhan trinh bao",
        "toi muon bao cong an", "muon bao cong an", "bao cong an", "goi cong an",
    )
    if any(_contains_phrase(current, marker) for marker in explicit_markers):
        return True
    if any(_contains_phrase(current, marker) for marker in advice_markers):
        return False

    previous = _latest_intake(history)
    if not previous:
        return False
    if current_has_topic and previous.get("procedure_code") != chosen_code:
        return False
    # A short answer to the one question currently being collected inherits the
    # intake request. A new explicit topic above already resets it.
    return len(current.split()) <= 12 and previous.get("procedure_code") == chosen_code


def _choose(matches, text):
    by_code = {item["code"]: item for item in matches}
    uncertain_theft = any(x in text for x in (
        "khong xac dinh bi trom", "khong xac dinh co bi trom",
        "chua xac dinh bi trom", "chua xac dinh co bi trom",
        "khong ro bi trom", "khong ro co bi trom",
    ))
    if "identity_card_reissue" in by_code:
        return by_code["identity_card_reissue"]
    if uncertain_theft and "lost_document" in by_code:
        return by_code["lost_document"]
    if any(x in text for x in ("lua dao chuyen khoan", "bi lua", "chuyen tien", "chuyen khoan", "bi scam")) and "fraud_transfer" in by_code:
        return by_code["fraud_transfer"]
    if any(x in text for x in ("bi danh", "nguoi khac danh", "bi hanh hung", "thuong tich", "dung dao")) and "assault_evidence" in by_code:
        return by_code["assault_evidence"]
    if any(x in text for x in ("karaoke", "loa keo", "tieng on", "on ao")) and "noise_report" in by_code:
        return by_code["noise_report"]
    if any(x in text for x in ("mau thuan", "xich mich", "cai nhau", "tranh chap hang xom", "va cham hang xom")) and "community_dispute" in by_code:
        return by_code["community_dispute"]
    if any(x in text for x in ("ca do", "ca cuoc", "danh bac", "co bac")) and "gambling_report" in by_code:
        return by_code["gambling_report"]
    if any(x in text for x in ("bi trom", "bi de doa", "de doa", "to giac", "trinh bao toi pham", "tin bao toi pham")) and "crime_report" in by_code:
        return by_code["crime_report"]
    if any(x in text for x in ("mat dien thoai", "mat xe", "mat tai san", "mat giay to", "that lac")) and "lost_document" in by_code:
        return by_code["lost_document"]
    return max(matches, key=lambda item: (len(item["keywords"]), item["source_ready"]))


def assess(question, history):
    current = _norm(question)
    combined = _conversation_text(question, history)
    current_matches = _matches(current)
    matches = current_matches or _matches(combined)
    if not matches:
        return {
            "procedure_code": "unclassified", "source_ready": False,
            "conversation_mode": "advice_only", "handoff_status": "not_requested",
            "handoff_queue": None, "handling_team": None,
            "missing_field_ids": [], "next_question": None,
        }

    classification_text = current if current_matches else combined
    chosen = _choose(matches, classification_text)
    # Missing fields may be satisfied by previous turns only when this is a true
    # continuation. For a new explicit topic, stale facts from another subject
    # are not allowed to satisfy it.
    field_text = combined if not current_matches else current
    missing = [field for field in chosen["fields"] if not any(cue in field_text for cue in field[2])]
    intake_requested = _requests_intake(
        question, history, chosen["code"], current_has_topic=bool(current_matches)
    )
    if not intake_requested:
        conversation_mode, handoff_status = "advice_only", "not_requested"
    elif missing:
        conversation_mode, handoff_status = "intake_requested", "needs_information"
    else:
        conversation_mode, handoff_status = "intake_requested", "ready_for_officer"
    queue = chosen["queue"]
    return {
        "procedure_code": chosen["code"],
        "procedure_name": chosen["name"],
        "source_ready": bool(chosen["source_ready"]) and not (
            chosen["code"] == "vehicle_registration" and any(x in classification_text for x in ("sang ten", "cap doi"))
        ),
        "conversation_mode": conversation_mode,
        "handoff_status": handoff_status,
        "handoff_queue": queue,
        "handling_team": team_for_queue(queue),
        "missing_field_ids": [field[0] for field in missing],
        "next_question": missing[0][1] if intake_requested and missing else None,
    }


def prompt_hint(intake):
    question = intake.get("next_question")
    if intake.get("conversation_mode") != "intake_requested" or not question:
        return ""
    return (
        "Người dân đã yêu cầu Công an tiếp nhận/báo tin. Hãy ưu tiên hướng dẫn hành động ngay, "
        "không bắt họ tự đánh giá mức độ nghiêm trọng hoặc tự phân loại pháp lý. "
        f"Nếu còn cần một dữ kiện để tiếp nhận, chỉ hỏi: '{question}'. "
        "Không nêu mã thủ tục, mã hàng đợi hay trạng thái nội bộ."
    )
