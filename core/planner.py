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
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


SEARCH_VOCAB = [
    (["bi danh", "danh nguoi", "thuong tich"], "Tội cố ý gây thương tích hoặc gây tổn hại cho sức khỏe của người khác"),
    (["trom", "mat tai san", "lay trom"], "trộm cắp tài sản"),
    (["lua dao", "bi lua"], "lừa đảo chiếm đoạt tài sản"),
    (["vay khong tra", "muon khong tra"], "lạm dụng tín nhiệm chiếm đoạt tài sản"),
    (["doa giet", "de doa giet"], "đe dọa giết người"),
    (["dap pha", "huy hoai"], "hủy hoại cố ý làm hư hỏng tài sản"),
    (["gay roi"], "gây rối trật tự công cộng"),
    (["ma tuy"], "ma túy"),
]

LEGAL_HINTS = [
    "luat", "bo luat", "dieu ", "xu phat", "toi pham", "cong an",
    "tam tru", "thuong tru", "dang ky xe", "can cuoc", "to giac",
    "thuong tich", "bi danh", "bi lua", "trom", "ma tuy", "khoi to",
    "tham quyen",
]


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
    system = """
Bạn là bộ lập kế hoạch tìm kiếm cho trợ lý AI của Công an xã.
Bạn KHÔNG trả lời pháp luật và KHÔNG kết luận tội danh.
Nhiệm vụ duy nhất là xác định câu hỏi có cần tra pháp luật không và tạo 1-4 truy vấn ngắn để tìm đúng đoạn văn bản.
Nếu người dân nêu Điều luật rõ ràng, ghi số Điều vào explicit_references.
law_hint chỉ ghi tên luật/bộ luật nếu người dân thực sự nêu hoặc ngữ cảnh đủ rõ.
"""
    history_text = "\n".join(f"{x['role']}: {x['content']}" for x in history[-4:])
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
            timeout=(DYNAMIC_TIMEOUT_SECONDS * 0.45 if dynamic else min(CORE_TIMEOUT_SECONDS, 5)),
            temperature=0.1,
            max_completion_tokens=220,
        )
    except Exception:
        return quick_plan(question)
