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


# Từ vựng này chỉ tạo truy vấn fallback/local. Nó không phải câu trả lời mẫu.
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
    "ho chieu", "xuat nhap canh", "thi thuc", "ly lich tu phap", "khieu nai", "to cao", "don thu", "khoi kien", "toa an", "thi hanh an", "trieu tap", "dieu tra", "luat su", "dat dai", "tranh chap dat", "nha o", "thue nha", "ly hon", "thua ke", "hop dong", "vay tien", "no tien", "lao dong", "bao hiem xa hoi", "bhxh", "thue", "hoa don", "khai sinh", "khai tu", "ket hon", "ho tich", "tai khoan bi hack", "mat zalo", "mat facebook", "o nhiem", "tieng on", "karaoke", "loa keo", "xay dung", "phong chay", "chua chay", "pccc", "co bac", "bao luc gia dinh", "xam hai tre em", "mat nguoi", "that lac nguoi", "vu khi", "cong cu ho tro", "phao", "phat giao thong", "phat nguoi", "giay phep lai xe",
]


def _contextual_question(question, history):
    previous_user_turns = [
        str(x.get("content") or "").strip()
        for x in history
        if x.get("role") == "user" and str(x.get("content") or "").strip()
    ]
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


def _sanitize_plan(candidate, baseline, contextual):
    """Giữ planner AI trong vai trò tạo truy vấn; không cho nó tạo căn cứ pháp lý."""
    result = dict(baseline)
    if not isinstance(candidate, dict):
        return result

    result["is_legal"] = bool(candidate.get("is_legal") or baseline.get("is_legal"))
    queries = []
    for value in list(candidate.get("search_queries") or []) + list(baseline.get("search_queries") or []):
        value = str(value or "").strip()
        if value and value not in queries:
            queries.append(value[:220])
    if contextual and contextual not in queries:
        queries.append(contextual[:220])
    result["search_queries"] = queries[:4]

    # Chỉ chấp nhận số Điều thực sự xuất hiện trong hội thoại, tránh planner tự bịa.
    explicit_in_text = set(re.findall(r"\bdieu\s+(\d+[a-z]?)\b", _norm(contextual)))
    refs = []
    for item in candidate.get("explicit_references") or []:
        article = str((item or {}).get("article") or "").lower().strip()
        if article in explicit_in_text:
            refs.append({"law_hint": str((item or {}).get("law_hint") or "")[:120], "article": article})
    for item in baseline.get("explicit_references") or []:
        if item not in refs:
            refs.append(item)
    result["explicit_references"] = refs[:4]

    result["needs_clarification"] = bool(candidate.get("needs_clarification", False))
    question = candidate.get("clarification_question")
    result["clarification_question"] = str(question).strip()[:280] if question else None
    complexity = candidate.get("complexity")
    result["complexity"] = complexity if complexity in ("simple", "complex") else baseline.get("complexity", "simple")
    reasons = [str(x or "").strip()[:120] for x in candidate.get("complexity_reasons") or [] if str(x or "").strip()]
    result["complexity_reasons"] = reasons[:3]
    return result


def plan(question, history, dynamic=False, safety_identifier=None):
    contextual = _contextual_question(question, history)
    baseline = quick_plan(contextual)

    # Zalo Dynamic tuyệt đối không tốn thêm model call: planner cục bộ + retrieval.
    if dynamic:
        return baseline

    system = """
Bạn là bộ lập kế hoạch truy xuất nguồn cho CAX PƠNG DRANG AI CORE.
Không trả lời người dân, không kết luận tội danh, không tự viết nội dung pháp luật.
Nhiệm vụ duy nhất: hiểu câu hỏi mới trong mạch hội thoại, xác định có cần nguồn pháp luật/TTHC hay không, và tạo tối đa 4 truy vấn ngắn để tìm đúng nguồn.
Nếu người dân chỉ nói thêm một dữ kiện ngắn như tỷ lệ thương tích, dùng dao, có camera, hãy hiểu đó có thể là phần tiếp theo của vụ việc trước.
Chỉ ghi explicit_references khi chính người dân đã nêu rõ số Điều. Không tự đoán số Điều.
Đánh dấu complexity=complex khi phải kết hợp nhiều nhánh pháp lý, nhiều văn bản, nhiều tình tiết có thể thay đổi kết quả, hoặc cần đối chiếu ngoại lệ.
""".strip()
    user = f"Ngữ cảnh hội thoại cần lập kế hoạch truy xuất:\n{contextual}"
    try:
        candidate = chat_structured(
            model=PLANNER_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            schema_name="legal_search_plan",
            schema=PLAN_SCHEMA,
            reasoning_effort="low",
            timeout=min(CORE_TIMEOUT_SECONDS, 4.0),
            temperature=0.0,
            max_completion_tokens=320,
            safety_identifier=safety_identifier,
        )
        return _sanitize_plan(candidate, baseline, contextual)
    except Exception:
        # Provider/planner không bao giờ được làm hỏng khả năng trả lời cốt lõi.
        return baseline
