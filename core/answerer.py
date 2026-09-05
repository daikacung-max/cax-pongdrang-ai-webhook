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
                    "evidence_quote": {"type": "string"},
                },
                "required": [
                    "source_unit_id", "article", "official_title",
                    "claim", "evidence_quote"
                ],
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
- hiểu câu hỏi trong toàn bộ mạch hội thoại gần nhất;
- nếu đây là câu hỏi nối tiếp, trả lời ngay phần thông tin MỚI người dân vừa bổ sung, không kể lại từ đầu những hướng dẫn đã nói ở lượt trước;
- trả lời trực tiếp, tự nhiên, dễ hiểu;
- không dùng câu mẫu rập khuôn;
- không liệt kê hàng loạt tội danh khi không cần;
- nếu thiếu dữ kiện quan trọng, có thể hỏi lại một câu ngắn;
- không kết luận một người có tội chỉ từ lời kể một phía;
- không trình bày chuỗi suy luận nội bộ;
- chỉ xuất nội dung trả lời cho người dân trong trường answer;
- không dùng Markdown, không dùng dấu *, **, #;
- không gọi đơn vị là 'đồn Công an xã'; phải dùng đúng tên {UNIT_NAME};
- dùng cách gọi 'cán bộ Công an', không dùng 'nhân viên công an';
- không mặc nhiên nói Công an xã 'tiến hành điều tra' mọi vụ việc. Khi cần, diễn đạt theo hướng tiếp nhận, xác minh ban đầu, xử lý hoặc chuyển cơ quan có thẩm quyền theo quy định;
- khi nói về thương tích, ưu tiên cách diễn đạt 'hồ sơ khám, chữa bệnh, kết quả khám, giấy ra viện hoặc tài liệu y tế liên quan' thay vì mặc định yêu cầu một loại 'giấy chứng nhận y tế'.

Tên đơn vị chính xác là: {UNIT_NAME}.
Nếu cần cung cấp số điện thoại liên hệ, số duy nhất được dùng là: {HOTLINE}.
"""

LEGAL_SYSTEM = """
Đối với câu hỏi pháp luật:
- LEGAL_SOURCE_CONTEXT là nguồn được truy xuất từ kho văn bản.
- Hãy dùng nguồn để trả lời đúng trọng tâm pháp lý của câu hỏi hiện tại, không chỉ đưa lời khuyên chung nếu nguồn đã trả lời được vấn đề người dân đang hỏi.
- Mọi chi tiết cụ thể như số Điều, tên Điều/tội danh, ngưỡng định lượng, khung hình phạt, thời hạn, lệ phí, thẩm quyền hoặc kết luận loại trừ trách nhiệm phải có căn cứ trực tiếp trong LEGAL_SOURCE_CONTEXT.
- Với MỖI legal_claim, evidence_quote phải là một đoạn NGUYÊN VĂN ngắn được chép trực tiếp từ đúng SOURCE_UNIT_ID và phải đủ để hỗ trợ claim đó. Không được tự viết lại evidence_quote.
- Không được rút gọn một quy tắc có nhiều nhánh thành chỉ một điều kiện. Nếu nguồn có cấu trúc 'A hoặc B', 'trừ trường hợp', 'dưới ngưỡng nhưng thuộc trường hợp...', phải giữ lại nhánh/ngoại lệ có liên quan đến dữ kiện người dân.
- Đặc biệt cẩn trọng với các câu tuyệt đối như 'không thuộc', 'không cấu thành', 'chắc chắn không bị xử lý'. Chỉ được nói như vậy khi nguồn và dữ kiện đã loại trừ toàn bộ các nhánh/ngoại lệ liên quan. Nếu chưa đủ, phải nói 'chưa thể kết luận' hoặc 'vẫn có thể được xem xét nếu...'.
- Nếu câu hỏi có một dữ kiện mới làm thay đổi cách đánh giá pháp lý, hãy nói rõ dữ kiện đó có ý nghĩa gì theo nguồn, nhưng không kết luận thay cơ quan có thẩm quyền.
- Mỗi chi tiết pháp lý cụ thể mà bạn dựa vào phải khai báo trong legal_claims và source_unit_id phải đúng ID có trong context.
- official_title nếu nêu phải đúng tiêu đề trong nguồn.
- Nếu nguồn chưa đủ để nêu một chi tiết chính xác, đừng bịa. Hãy giải thích ở mức nguyên tắc hoặc hỏi thêm.
- Kho văn bản là nguồn pháp lý. Bạn vẫn được dùng năng lực ngôn ngữ, suy luận và hiểu tình huống để giải thích, gợi ý bước tiếp theo, và duy trì cuộc trò chuyện.
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
        temperature=0.08 if legal_context else 0.42,
        max_completion_tokens=620 if dynamic else 1100,
    )
