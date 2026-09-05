import re
import unicodedata

from config import PLANNER_MODEL, CORE_TIMEOUT_SECONDS, DYNAMIC_TIMEOUT_SECONDS
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
                "properties": {
                    "law_hint": {"type": "string"},
                    "article": {"type": "string"}
                },
                "required": ["law_hint", "article"],
                "additionalProperties": False,
            },
            "maxItems": 4,
        },
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": ["string", "null"]},
    },
    "required": [
        "is_legal", "search_queries", "explicit_references",
        "needs_clarification", "clarification_question"
    ],
    "additionalProperties": False,
}


def _norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9%\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Chỉ là từ vựng tìm nguồn, không chứa câu trả lời pháp luật.
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
    (["tam tru", "dang ky tam tru", "ho so tam tru", "nha chu ho", "nha ong"],
     "Đăng ký tạm trú cơ quan cách thức thời hạn nguyên tắc hồ sơ cư trú VNeID"),
    (["thuong tru", "dang ky thuong tru"],
     "đăng ký thường trú cư trú Công an cấp xã"),
    (["xac nhan cu tru", "xac nhan thong tin cu tru"],
     "xác nhận thông tin cư trú Công an cấp xã"),
]

LEGAL_HINTS = [
    "luat", "bo luat", "dieu ", "xu phat", "toi pham", "cong an",
    "tam tru", "thuong tru", "cu tru", "dang ky xe", "can cuoc", "to giac",
    "thuong tich", "bi thuong", "bi danh", "dung dao", "hung khi",
    "bi lua", "trom", "ma tuy", "khoi to", "tham quyen", "truy cuu",
    "thu tuc", "ho so", "vneid",
]


def _contextual_question(question, history):
    """
    Ghép tối đa 2 lượt người dùng gần nhất với câu mới để giữ đúng ngữ cảnh.
    Không đưa câu trả lời cũ của AI vào truy vấn pháp luật để tránh tự khuếch đại lỗi.
    """
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

    # Dynamic cần tốc độ, dùng planner cục bộ trên cả ngữ cảnh hội thoại.
    if dynamic:
        return quick_plan(contextual)

    system = """
Bạn là bộ lập kế hoạch tìm kiếm cho trợ lý AI của Công an xã.
Bạn KHÔNG trả lời pháp luật và KHÔNG kết luận tội danh.
Nhiệm vụ duy nhất là xác định câu hỏi có cần tra nguồn pháp luật/thủ tục hành chính không và tạo 1-4 truy vấn ngắn để tìm đúng nguồn.
Hãy hiểu câu hỏi mới trong mạch hội thoại. Các đại từ hoặc dữ kiện ngắn có thể tiếp tục tình huống ở lượt trước.
Nếu người dân nêu Điều luật rõ ràng, ghi số Điều vào explicit_references.
law_hint chỉ ghi tên luật/bộ luật nếu người dân thực sự nêu hoặc ngữ cảnh đủ rõ.
"""
    history_text = "\n".join(f"{x['role']}: {x['content']}" for x in history[-6:])
    user = f"Lịch sử gần nhất:\n{history_text}\n\nCâu hỏi mới:\n{question}"
    try:
        return chat_structured(
            model=PLANNER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            schema_name="legal_search_plan",
            schema=PLAN_SCHEMA,
            reasoning_effort="low",
            timeout=min(CORE_TIMEOUT_SECONDS, 5),
            temperature=0.1,
            max_completion_tokens=220,
        )
    except Exception:
        return quick_plan(contextual)
