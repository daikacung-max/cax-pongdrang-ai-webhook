from config import (
    UNIT_NAME,
    HOTLINE,
    ANSWER_MODEL,
    CORE_REASONING_EFFORT,
    DYNAMIC_REASONING_EFFORT,
    CORE_TIMEOUT_SECONDS,
    DYNAMIC_TIMEOUT_SECONDS,
)
from core.llm import chat_structured


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
                },
                "required": ["source_unit_id", "article", "official_title", "claim"],
                "additionalProperties": False,
            },
            "maxItems": 10,
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

Hãy trò chuyện với người dân như một trợ lý AI thực thụ:
- hiểu câu hỏi và lịch sử cuộc trò chuyện;
- trả lời trực tiếp, tự nhiên, dễ hiểu;
- không dùng câu mẫu rập khuôn;
- không liệt kê hàng loạt tội danh khi không cần;
- nếu thiếu dữ kiện quan trọng, có thể hỏi lại một câu ngắn;
- không kết luận một người có tội chỉ từ lời kể một phía;
- không trình bày chuỗi suy luận nội bộ;
- chỉ xuất nội dung trả lời cho người dân trong trường answer;
- không dùng Markdown, không dùng dấu *, **, #.

Tên đơn vị chính xác là: {UNIT_NAME}.
Nếu cần cung cấp số điện thoại liên hệ, số duy nhất được dùng là: {HOTLINE}.
"""

LEGAL_SYSTEM = """
Đối với câu hỏi pháp luật:
- LEGAL_SOURCE_CONTEXT là nguồn được truy xuất từ kho văn bản.
- Hãy phân tích linh hoạt, nhưng mọi chi tiết cụ thể như số Điều, tên Điều/tội danh,
  ngưỡng định lượng, khung hình phạt, thời hạn, lệ phí, thẩm quyền phải có căn cứ
  trong LEGAL_SOURCE_CONTEXT.
- Mỗi chi tiết pháp lý cụ thể mà bạn dựa vào phải khai báo trong legal_claims
  và source_unit_id phải đúng ID có trong context.
- official_title nếu nêu phải đúng tiêu đề trong nguồn.
- Nếu nguồn chưa đủ để nêu một chi tiết chính xác, đừng bịa. Hãy giải thích ở mức
  nguyên tắc hoặc hỏi thêm.
- Kho văn bản là nguồn pháp lý. Bạn vẫn được dùng năng lực ngôn ngữ, suy luận và
  hiểu tình huống để giải thích, gợi ý bước tiếp theo, và duy trì cuộc trò chuyện.
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
    return chat_structured(
        model=ANSWER_MODEL,
        messages=build_messages(
            question, history, legal_context=legal_context, repair_note=repair_note
        ),
        schema_name="citizen_answer",
        schema=ANSWER_SCHEMA,
        reasoning_effort=(DYNAMIC_REASONING_EFFORT if dynamic else CORE_REASONING_EFFORT),
        timeout=(DYNAMIC_TIMEOUT_SECONDS if dynamic else CORE_TIMEOUT_SECONDS),
        temperature=0.18 if legal_context else 0.45,
        max_completion_tokens=520 if dynamic else 1000,
    )
