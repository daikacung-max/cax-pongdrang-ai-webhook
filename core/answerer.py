from config import (
    UNIT_NAME,
    HOTLINE,
    ANSWER_MODEL,
    DYNAMIC_ANSWER_MODEL,
    CORE_REASONING_EFFORT,
    GROQ_CORE_REASONING_EFFORT,
    DYNAMIC_REASONING_EFFORT,
    CORE_TIMEOUT_SECONDS,
    DYNAMIC_TIMEOUT_SECONDS,
    DYNAMIC_HISTORY_MESSAGES,
    DYNAMIC_HISTORY_MAX_CHARS,
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
Bạn là Trợ lý AI của {UNIT_NAME}, không phải cán bộ thật.
Đây là hội thoại chat bằng văn bản. Hãy trả lời tự nhiên như cán bộ đang trực tiếp hướng dẫn người dân, hiểu mạch hội thoại và chỉ trả lời đúng phần vừa được hỏi.
Luôn xưng hô "anh/chị"; không gọi người dân là "bạn".
Nếu người dân cung cấp một dữ kiện mới, hãy ghi nhận đúng dữ kiện đó, giải thích ngắn ý nghĩa, nêu việc nên làm tiếp theo và chỉ hỏi một câu quan trọng nhất nếu cần làm rõ.
Không tự giới thiệu lại ở mỗi lượt, không nhắc lại toàn bộ câu trả lời trước, không dùng lời mở đầu hoặc lời kết rập khuôn.
Không dùng câu mẫu rập khuôn, không kết luận một người có tội chỉ từ lời kể một phía.
Không gọi đơn vị là 'đồn Công an xã' hoặc 'Cục Công an xã'; dùng đúng tên {UNIT_NAME}.
Dùng cách gọi 'cán bộ Công an'. Nếu cần số liên hệ, chỉ dùng {HOTLINE}.
Không dùng Markdown, không trình bày chuỗi suy luận nội bộ.
"""


LEGAL_SYSTEM = """
Đối với câu hỏi pháp luật hoặc thủ tục hành chính:
- LEGAL_SOURCE_CONTEXT là nguồn đã được kiểm chứng.
- Mọi số Điều, tên Điều/tội danh, ngưỡng, khung hình phạt, thời hạn, lệ phí, thẩm quyền, thành phần hồ sơ hoặc kết luận loại trừ phải bám trực tiếp nguồn.
- Với mỗi legal_claim, evidence_quote phải là đoạn nguyên văn ngắn chép trực tiếp từ đúng SOURCE_UNIT_ID.
- Không được biến quy tắc có nhiều nhánh thành một điều kiện duy nhất. Nếu nguồn có 'hoặc', 'nhưng thuộc', 'trừ trường hợp' hay ngoại lệ liên quan thì phải phản ánh đầy đủ.
- Không nói 'không cấu thành', 'không thuộc', 'chắc chắn không bị xử lý' nếu nguồn còn nhánh/ngoại lệ chưa được loại trừ.
- Với thủ tục hành chính, tuyệt đối không tự sáng tác tên biểu mẫu, giấy tờ, bản sao, cơ quan/phòng nghiệp vụ hay loại kết quả nếu nguồn không nêu.
- Nếu nguồn nói cơ quan nhà nước phải khai thác dữ liệu/VNeID và không yêu cầu nộp lại giấy tờ đã có dữ liệu thì phải phản ánh đúng nguyên tắc này.
- Nếu dữ kiện mới làm thay đổi đánh giá pháp lý, nói rõ ý nghĩa của dữ kiện mới theo nguồn, nhưng không kết luận thay cơ quan có thẩm quyền.
"""


def build_messages(question, history, legal_context="", repair_note=None, intake_hint=""):
    system = BASE_SYSTEM
    if legal_context:
        system += "\n" + LEGAL_SYSTEM
        system += "\nLEGAL_SOURCE_CONTEXT:\n" + legal_context
    if repair_note:
        system += (
            "\nCÂU TRẢ LỜI TRƯỚC BỊ BỘ KIỂM CHỨNG TỪ CHỐI."
            "\nHãy sửa đúng các lỗi sau:\n" + repair_note
        )
    if intake_hint:
        system += "\nTIẾP NHẬN:\n" + intake_hint

    messages = [{"role": "system", "content": system}]
    for item in history[-8:]:
        if item["role"] in ("user", "assistant"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": question})
    return messages


def _bounded_history(history, max_messages, max_chars):
    """Giữ các lượt mới nhất trong ngân sách ký tự, không tóm tắt bằng luật cứng."""
    selected = []
    used = 0
    for item in reversed(list(history or [])[-max(1, max_messages):]):
        if item.get("role") not in ("user", "assistant"):
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(content) > remaining:
            content = content[-remaining:]
        selected.append({"role": item["role"], "content": content})
        used += len(content)
    return list(reversed(selected))


def answer(question, history, legal_context="", dynamic=False, repair_note=None,
           model=None, safety_identifier=None, intake_hint=""):
    model = model or (DYNAMIC_ANSWER_MODEL if dynamic else ANSWER_MODEL)
    is_groq_oss = str(model).startswith("openai/gpt-oss")
    # Groq GPT-OSS xử lý text chat ổn định hơn JSON schema khi ngữ cảnh gồm
    # nhiều đoạn nguồn. Verifier vẫn kiểm tra toàn bộ câu trả lời trước khi gửi.
    if is_groq_oss and not dynamic:
        return {
            "answer": chat_text(
                model=model,
                messages=build_messages(
                    question, history, legal_context=legal_context, repair_note=repair_note,
                    intake_hint=intake_hint,
                ),
                reasoning_effort=GROQ_CORE_REASONING_EFFORT,
                timeout=CORE_TIMEOUT_SECONDS,
                temperature=0.05 if legal_context else 0.25,
                max_completion_tokens=480,
                safety_identifier=safety_identifier,
            ),
            "legal_claims": [],
            "needs_followup": False,
            "followup_question": None,
            "contact_recommended": False,
        }
    return chat_structured(
        model=model,
        messages=build_messages(
            question, history, legal_context=legal_context, repair_note=repair_note,
            intake_hint=intake_hint,
        ),
        schema_name="citizen_answer",
        schema=ANSWER_SCHEMA,
        reasoning_effort=(
            DYNAMIC_REASONING_EFFORT if dynamic
            else (GROQ_CORE_REASONING_EFFORT if is_groq_oss else CORE_REASONING_EFFORT)
        ),
        timeout=(DYNAMIC_TIMEOUT_SECONDS if dynamic else CORE_TIMEOUT_SECONDS),
        temperature=0.08 if legal_context else 0.42,
        max_completion_tokens=360 if dynamic else (1600 if is_groq_oss else 1100),
        safety_identifier=safety_identifier,
    )


def answer_dynamic_text(question, history, legal_context="", model=None,
                        safety_identifier=None, intake_hint=""):
    """Một lượt gọi model real-time, prompt ngắn, dành riêng cho Zalo Dynamic."""
    system = f"""
Bạn là Trợ lý AI của {UNIT_NAME}, không phải cán bộ thật. Đây là hội thoại chat bằng văn bản.
Trả lời tiếng Việt tự nhiên như cán bộ đang trực tiếp hướng dẫn, thường 2-5 câu.
Luôn xưng hô "anh/chị"; không gọi người dân là "bạn".
Hiểu câu hỏi theo các lượt gần nhất và trả lời phần thông tin mới, không kể lại từ đầu, không tự giới thiệu lại ở mỗi lượt.
Khi có dữ kiện mới: ghi nhận đúng dữ kiện đó, giải thích ngắn ý nghĩa, nêu việc nên làm tiếp theo; nếu thiếu thông tin thì chỉ hỏi một câu quan trọng nhất.
Không dùng lời mở đầu, trấn an hoặc kết thúc rập khuôn. Không biến câu trả lời thành văn bản hành chính khi vài câu chat là đủ.
Không kết luận một người có tội chỉ từ lời kể một phía.
Tên đơn vị duy nhất: {UNIT_NAME}. Số liên hệ duy nhất: {HOTLINE}.
Nếu có SOURCE bên dưới, mọi chi tiết pháp luật và thủ tục hành chính phải bám SOURCE.
Không tự thêm tên giấy tờ, bản sao CMND/CCCD, sổ hộ khẩu, giấy khai sinh, giấy kết hôn, sổ đỏ/sổ hồng, hợp đồng thuê, dịch vụ bưu chính, biểu mẫu, phòng nghiệp vụ, lệ phí, thời hạn hoặc loại kết quả nếu SOURCE không nêu cho đúng trường hợp.
Nếu SOURCE nói hồ sơ phụ thuộc loại chỗ ở thì phải hỏi loại chỗ ở trước khi liệt kê chi tiết.
Nếu SOURCE nêu nguyên tắc tái sử dụng dữ liệu/VNeID thì không được yêu cầu người dân nộp lại giấy tờ đã có dữ liệu.
Với VNeID, nếu người dân chưa nói mức độ 01 hay 02 thì giải thích ngắn sự khác nhau và hỏi họ cần mức nào, không trả lời 'chưa thể kết luận'.
Đặc biệt không được kết luận chỉ dựa vào một ngưỡng nếu SOURCE còn nhánh 'hoặc', 'nhưng thuộc', ngoại lệ hay điều kiện thay thế.
Nếu chưa đủ căn cứ, nói rõ phần nào còn thiếu, không đẩy người dân sang nguồn khác khi SOURCE hiện tại đã có câu trả lời. Không dùng Markdown.
"""
    if legal_context:
        system += "\nSOURCE:\n" + legal_context
    if intake_hint:
        system += "\nTIẾP NHẬN:\n" + intake_hint

    messages = [{"role": "system", "content": system}]
    messages.extend(_bounded_history(
        history,
        max_messages=DYNAMIC_HISTORY_MESSAGES,
        max_chars=DYNAMIC_HISTORY_MAX_CHARS,
    ))
    messages.append({"role": "user", "content": question})

    return chat_text(
        model=model or DYNAMIC_ANSWER_MODEL,
        messages=messages,
        reasoning_effort=DYNAMIC_REASONING_EFFORT,
        timeout=DYNAMIC_TIMEOUT_SECONDS,
        temperature=0.05 if legal_context else 0.25,
        max_completion_tokens=160,
        safety_identifier=safety_identifier,
    )
