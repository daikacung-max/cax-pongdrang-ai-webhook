import re
import unicodedata

from config import PLANNER_MODEL, CORE_TIMEOUT_SECONDS, RETRIEVAL_HISTORY_USER_TURNS
from core.llm import chat_structured

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "is_legal": {"type": "boolean"},
        "search_queries": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "explicit_references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"law_hint": {"type": "string"}, "article": {"type": "string"}},
                "required": ["law_hint", "article"],
                "additionalProperties": False,
            },
            "maxItems": 4,
        },
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": ["string", "null"]},
        "complexity": {"type": "string", "enum": ["simple", "complex"]},
        "complexity_reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
    },
    "required": [
        "is_legal", "search_queries", "explicit_references", "needs_clarification",
        "clarification_question", "complexity", "complexity_reasons",
    ],
    "additionalProperties": False,
}


def _fix_common_typos(text):
    """Chuẩn hóa một số lỗi gõ rất thường gặp trước khi phân loại ý định."""
    q = str(text or "")
    replacements = {
        "thuong chu": "thuong tru",
        "thuong trú": "thuong tru",
        "tam chu": "tam tru",
        "vne id": "vneid",
        "vne-id": "vneid",
        "vned": "vneid",
        "vnied": "vneid",
        "can cuoc cong dan": "can cuoc",
        "ho khau thuong chu": "ho khau thuong tru",
    }
    for old, new in replacements.items():
        q = q.replace(old, new)
    return q


def _norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9%\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _fix_common_typos(text)


# Từ vựng này chỉ dùng để tạo truy vấn tìm nguồn, không phải câu trả lời mẫu.
SEARCH_VOCAB = [
    (["bi danh", "danh nguoi", "nguoi khac danh", "bi nguoi khac danh", "bi thuong", "thuong tich", "dung dao", "hung khi"],
     "Tội cố ý gây thương tích hoặc gây tổn hại cho sức khỏe của người khác"),
    (["trom", "mat tai san", "lay trom"], "trộm cắp tài sản"),
    (["lua dao", "bi lua", "bi lua chuyen khoan"], "lừa đảo chiếm đoạt tài sản"),
    (["vay khong tra", "muon khong tra"], "lạm dụng tín nhiệm chiếm đoạt tài sản"),
    (["doa giet", "de doa giet"], "đe dọa giết người"),
    (["dap pha", "huy hoai"], "hủy hoại cố ý làm hư hỏng tài sản"),
    (["gay roi"], "gây rối trật tự công cộng"),
    (["ma tuy"], "ma túy"),
    (["tam tru", "dang ky tam tru", "ho so tam tru"],
     "Đăng ký tạm trú Công an cấp xã 03 ngày làm việc nguyên tắc hồ sơ dữ liệu VNeID"),
    (["thuong tru", "dang ky thuong tru", "ho khau thuong tru", "nhap khau"],
     "Đăng ký thường trú Công an cấp xã 07 ngày làm việc thành phần hồ sơ phụ thuộc trường hợp chỗ ở"),
    (["xac nhan cu tru", "xac nhan thong tin cu tru"], "xác nhận thông tin cư trú Công an cấp xã"),
    (["vneid", "dinh danh dien tu", "tai khoan dinh danh", "muc do 1", "muc do 01", "muc do 2", "muc do 02"],
     "Cấp tài khoản định danh điện tử VNeID mức độ 01 mức độ 02 Công an xã căn cước số điện thoại chính chủ"),
    (["dang ky xe", "xe mo to", "xe may", "xe gan may", "bien so xe", "mua xe moi"],
     "Đăng ký lần đầu xe mô tô xe gắn máy Giấy khai đăng ký xe ĐKX10 giấy tờ chủ xe giấy tờ của xe"),
    (["tre em", "duoi 14", "con toi", "be nha toi"],
     "Cấp thẻ căn cước cho người dưới 14 tuổi thực hiện tại Công an cấp xã"),
    (["to giac", "tin bao toi pham", "trinh bao toi pham"],
     "Hướng dẫn tố giác báo tin về tội phạm Công an cấp xã"),
    (["karaoke", "hat karaoke", "loa keo", "tieng on", "on ao", "on nhieu"],
     "Nghị định 282/2025/NĐ-CP Điều 9 tiếng ồn karaoke bảo đảm sự yên tĩnh chung"),
]

LEGAL_HINTS = [
    "luat", "bo luat", "dieu ", "xu phat", "toi pham", "cong an", "tam tru", "thuong tru", "cu tru",
    "dang ky xe", "sang ten", "chuyen nhuong", "thu hoi", "can cuoc", "to giac", "thuong tich", "bi thuong", "bi danh", "nguoi khac danh", "hanh hung", "camera", "dung dao", "hung khi",
    "bi lua", "bi lua chuyen khoan", "nguoi lua dao", "chuyen tien", "chuyen khoan", "bi scam", "trom", "ma tuy", "khoi to", "tham quyen", "truy cuu", "thu tuc", "ho so", "vneid",
    "dinh danh dien tu", "tai khoan dinh danh", "xe mo to", "xe may", "xe gan may", "bien so xe", "ho khau", "nhap khau",
    # Các cụm dưới đây vẫn đi vào cổng fail-closed nếu chưa có nguồn được duyệt;
    # chúng không cho phép model tự trả lời chi tiết bằng kiến thức nền.
    "ho chieu", "xuat nhap canh", "thi thuc", "ly lich tu phap", "khieu nai", "to cao", "don thu", "khoi kien", "toa an", "thi hanh an", "trieu tap", "dieu tra", "luat su", "dat dai", "tranh chap dat", "nha o", "thue nha", "ly hon", "thua ke", "hop dong", "vay tien", "no tien", "lao dong", "bao hiem xa hoi", "bhxh", "thue", "hoa don", "khai sinh", "khai tu", "ket hon", "ho tich", "tai khoan bi hack", "mat zalo", "mat facebook", "o nhiem", "tieng on", "karaoke", "loa keo", "xay dung", "phong chay", "chua chay", "pccc", "co bac", "bao luc gia dinh", "xam hai tre em", "mat nguoi", "that lac nguoi", "vu khi", "cong cu ho tro", "phao", "phat giao thong", "phat nguoi", "giay phep lai xe",
]


def _contextual_question(question, history):
    previous_user_turns = [
        str(x.get("content") or "").strip()
        for x in history
        if x.get("role") == "user" and str(x.get("content") or "").strip()
    ]
    # Tính cả câu hiện tại trong ngân sách tối đa bốn lượt người dùng.
    context = (previous_user_turns + [str(question or "").strip()])[
        -max(1, RETRIEVAL_HISTORY_USER_TURNS):
    ]
    return " | ".join(x for x in context if x)


def quick_plan(question):
    q = _norm(question)
    refs = [
        {"law_hint": "", "article": m.group(1)}
        for m in re.finditer(r"\bdieu\s+(\d+[a-z]?)\b", q)
    ]
    queries = []
    for phrases, expansion in SEARCH_VOCAB:
        if any(p in q for p in phrases):
            queries.append(expansion)
    queries.append(question)
    complex_reasons = []
    if len(refs) > 1:
        complex_reasons.append("multiple_explicit_articles")
    return {
        "is_legal": any(x in q for x in LEGAL_HINTS),
        "search_queries": queries[:4],
        "explicit_references": refs[:4],
        "needs_clarification": False,
        "clarification_question": None,
        "complexity": "complex" if complex_reasons else "simple",
        "complexity_reasons": complex_reasons,
    }


def plan(question, history, dynamic=False, safety_identifier=None):
    contextual = _contextual_question(question, history)
    # Trong pilot, planner xác định bằng quy tắc trên ngữ cảnh gần nhất thay vì
    # để model tự viết truy vấn. Các nhóm nguồn đã duyệt đều có từ vựng/điều
    # kiện rõ ràng; cách này giữ nguyên luồng Planner -> FTS5 nhưng ngăn một
    # model phản hồi không ổn định kéo Điều luật không liên quan vào câu trả lời.
    # Những nội dung chưa có nguồn tiếp tục đi fail-closed.
    baseline = quick_plan(contextual)
    return baseline
