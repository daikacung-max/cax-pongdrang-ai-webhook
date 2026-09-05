from config import (
    UNIT_NAME,
    HOTLINE,
    ANSWER_MODEL,
    DYNAMIC_ANSWER_MODEL,
    CORE_REASONING_EFFORT,
    DYNAMIC_REASONING_EFFORT,
    CORE_TIMEOUT_SECONDS,
    DYNAMIC_TIMEOUT_SECONDS,
)
from core.llm import chat_structured, chat_text


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "legal_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_unit_id": {"type": "string"},
                    "article": {"type": ["string", "null"]},
                    "official_title": {"type": ["string", "null"]},
                    "claim": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                },
                "required": [
                    "source_unit_id", "article", "official_title",
                    "claim", "evidence_quote"
                ],
                "additionalProperties": False,
            },
            "maxItems": 6,
        },
        "needs_followup": {"type": "boolean"},
        "followup_question": {"type": ["string", "null"]},
        "contact_recommended": {"type": "boolean"},
    },
    "required": [
        "answer", "legal_claims", "needs_followup",
        "followup_question", "contact_recommended"
    ],
    "additionalProperties": False,
}


BASE_SYSTEM = f"""
Bạn là Trợ lý AI của {UNIT_NAME}.
Hãy trò chuyện tự nhiên, hiểu mạch hội thoại, trả lời đúng phần người dân vừa hỏi.
Không dùng câu mẫu rập khuôn, không kết luận một người có tội chỉ từ lời kể một phía.
Không gọi đơn vị là 'đồn Công an xã' hoặc 'Cục Công an xã'; dùng đúng tên {UNIT_NAME}.
Dùng cách gọi 'cán bộ Công an'. Nếu cần số liên hệ, chỉ dùng {HOTLINE}.
Không dùng Markdown, không trình bày chuỗi suy luận nội bộ.
"""


LEGAL_SYSTEM = """
Đối với câu hỏi pháp luật:
- LEGAL_SOURCE_CONTEXT là nguồn pháp lý đã truy xuất.
- Mọi số Điều, tên Điều/tội danh, ngưỡng, khung hình phạt, thời hạn, lệ phí, thẩm quyền hoặc kết luận loại trừ phải bám trực tiếp nguồn.
- Với mỗi legal_claim, evidence_quote phải là đoạn nguyên văn ngắn chép trực tiếp từ đúng SOURCE_UNIT_ID.
- Không được biến quy tắc có nhiều nhánh thành một điều kiện duy nhất. Nếu nguồn có 'hoặc', 'nhưng thuộc', 'trừ trường hợp' hay ngoại lệ liên quan thì phải phản ánh đầy đủ.
- Không nói 'không cấu thành', 'không thuộc', 'chắc chắn không bị xử lý' nếu nguồn còn nhánh/ngoại lệ chưa được loại trừ.
- Nếu dữ kiện mới làm thay đổi đánh giá pháp lý, nói rõ ý nghĩa của dữ kiện mới theo nguồn, nhưng không kết luận thay cơ quan có thẩm quyền.
"""


def build_messages(question, history, legal_context="", repair_note=None):
    system = BASE_SYSTEM
    if legal_context:
        system += "\n" + LEGAL_SYSTEM
        system += "\nLEGAL_SOURCE_CONTEXT:\n" + legal_context
    if repair_note:
        system += (
            "\nCÂU TRẢ LỜI TRƯỚC BỊ BỘ KIỂM CHỨNG TỪ CHỐI."
            "\nHãy sửa đúng các lỗi sau:\n" + repair_note
        )

    messages = [{"role": "system", "content": system}]
    for item in history[-8:]:
        if item["role"] in ("user", "assistant"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": question})
    return messages


def answer(question, history, legal_context="", dynamic=False, repair_note=None):
    model = DYNAMIC_ANSWER_MODEL if dynamic else ANSWER_MODEL
    return chat_structured(
        model=model,
        messages=build_messages(
            question, history, legal_context=legal_context, repair_note=repair_note
        ),
        schema_name="citizen_answer",
        schema=ANSWER_SCHEMA,
        reasoning_effort=(DYNAMIC_REASONING_EFFORT if dynamic else CORE_REASONING_EFFORT),
        timeout=(DYNAMIC_TIMEOUT_SECONDS if dynamic else CORE_TIMEOUT_SECONDS),
        temperature=0.08 if legal_context else 0.42,
        max_completion_tokens=420 if dynamic else 1100,
    )


def answer_dynamic_text(question, history, legal_context=""):
    """Một lượt gọi 20B, prompt ngắn, dành riêng cho giới hạn dưới 2 giây của Zalo Dynamic."""
    system = f"""
Bạn là Trợ lý AI của {UNIT_NAME}. Trả lời bằng tiếng Việt tự nhiên, ngắn gọn, thường 2-5 câu.
Hiểu câu hỏi theo các lượt hội thoại gần nhất và trả lời phần thông tin mới, không kể lại từ đầu.
Không kết luận một người có tội chỉ từ lời kể một phía.
Tên đơn vị duy nhất: {UNIT_NAME}. Số liên hệ duy nhất: {HOTLINE}.
Nếu có SOURCE bên dưới, mọi số Điều, tên tội, ngưỡng và kết luận pháp lý phải bám SOURCE.
Đặc biệt không được kết luận chỉ dựa vào một ngưỡng nếu SOURCE còn nhánh 'hoặc', 'nhưng thuộc', ngoại lệ hay điều kiện thay thế.
Nếu chưa đủ căn cứ, nói 'chưa thể kết luận' và giải thích điều gì cần làm rõ.
Không dùng Markdown.
"""
    if legal_context:
        system += "\nSOURCE:\n" + legal_context

    messages = [{"role": "system", "content": system}]
    for item in history[-4:]:
        if item["role"] in ("user", "assistant"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": question})

    return chat_text(
        model=DYNAMIC_ANSWER_MODEL,
        messages=messages,
        reasoning_effort=DYNAMIC_REASONING_EFFORT,
        timeout=DYNAMIC_TIMEOUT_SECONDS,
        temperature=0.08 if legal_context else 0.35,
        max_completion_tokens=260,
    )
