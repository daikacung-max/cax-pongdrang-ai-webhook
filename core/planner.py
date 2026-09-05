import re
import unicodedata

from config import PLANNER_MODEL, CORE_TIMEOUT_SECONDS
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
    },
    "required": ["is_legal", "search_queries", "explicit_references", "needs_clarification", "clarification_question"],
    "additionalProperties": False,
}


def _norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9%\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Từ vựng này chỉ dùng để tạo truy vấn tìm nguồn, không phải câu trả lời mẫu.
SEARCH_VOCAB = [
    (["bi danh", "danh nguoi", "bi thuong", "thuong tich", "dung dao", "hung khi"],
     "Tội cố ý gây thương tích hoặc gây tổn hại cho sức khỏe của người khác"),
    (["trom", "mat tai san", "lay trom"], "trộm cắp tài sản"),
    (["lua dao", "bi lua"], "lừa đảo chiếm đoạt tài sản"),
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
]

LEGAL_HINTS = [
    "luat", "bo luat", "dieu ", "xu phat", "toi pham", "cong an", "tam tru", "thuong tru", "cu tru",
    "dang ky xe", "can cuoc", "to giac", "thuong tich", "bi thuong", "bi danh", "dung dao", "hung khi",
    "bi lua", "trom", "ma tuy", "khoi to", "tham quyen", "truy cuu", "thu tuc", "ho so", "vneid",
    "dinh danh dien tu", "tai khoan dinh danh", "xe mo to", "xe may", "xe gan may", "bien so xe", "ho khau", "nhap khau",
]


def _contextual_question(question, history):
    previous_user_turns = [
        str(x.get("content") or "").strip()
        for x in history[-6:]
        if x.get("role") == "user" and str(x.get("content") or "").strip()
    ]
    context = previous_user_turns[-2:] + [str(question or "").strip()]
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
    return {
        "is_legal": any(x in q for x in LEGAL_HINTS),
        "search_queries": queries[:4],
        "explicit_references": refs[:4],
        "needs_clarification": False,
        "clarification_question": None,
    }


def plan(question, history, dynamic=False):
    contextual = _contextual_question(question, history)

    # Zalo Dynamic cần tốc độ; dùng planner cục bộ trên cả ngữ cảnh hội thoại.
    if dynamic:
        return quick_plan(contextual)

    system = """
Bạn là bộ lập kế hoạch tìm nguồn cho trợ lý AI của Công an xã.
Bạn không trả lời pháp luật và không kết luận tội danh. Chỉ xác định câu hỏi có cần nguồn pháp luật/TTHC không và tạo 1-4 truy vấn ngắn.
Hiểu câu hỏi mới trong mạch hội thoại; dữ kiện ngắn có thể tiếp tục lượt trước. Nếu người dân nêu Điều luật rõ ràng, ghi số Điều vào explicit_references.
"""
    history_text = "\n".join(f"{x['role']}: {x['content']}" for x in history[-6:])
    user = f"Lịch sử gần nhất:\n{history_text}\n\nCâu hỏi mới:\n{question}"
    try:
        return chat_structured(
            model=PLANNER_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            schema_name="legal_search_plan",
            schema=PLAN_SCHEMA,
            reasoning_effort="low",
            timeout=min(CORE_TIMEOUT_SECONDS, 5),
            temperature=0.1,
            max_completion_tokens=220,
        )
    except Exception:
        return quick_plan(contextual)
