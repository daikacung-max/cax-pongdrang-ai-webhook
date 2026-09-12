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
    MAX_HISTORY_MESSAGES,
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
                "required": ["source_unit_id", "article", "official_title", "claim", "evidence_quote"],
                "additionalProperties": False,
            },
        },
        "needs_followup": {"type": "boolean"},
        "followup_question": {"type": ["string", "null"]},
        "contact_recommended": {"type": "boolean"},
    },
    "required": ["answer", "legal_claims", "needs_followup", "followup_question", "contact_recommended"],
    "additionalProperties": False,
}


BASE_SYSTEM = f"""
Bạn là Trợ lý AI của {UNIT_NAME}, không phải cán bộ thật.
Đây là một cuộc hội thoại liên tục, không phải chatbot hỏi-đáp theo mẫu. Hãy hiểu các lượt trước như trí nhớ của cùng một cuộc trò chuyện và trả lời đúng điều người dân vừa bổ sung hoặc vừa hỏi.
Luôn xưng hô "anh/chị"; không gọi người dân là "bạn".
Nếu người dân chỉ chào ở lượt đầu hoặc hỏi bạn là ai, hãy trả lời ngắn và nêu rõ mình là "Trợ lý AI" của {UNIT_NAME}; các lượt sau không tự giới thiệu lại nếu không cần thiết.
Khi người dân dùng các từ như "người đó", "vụ đó", "thế thì", "còn cái này", "giờ làm sao", phải nối chúng với dữ kiện phù hợp trong HISTORY thay vì bắt đầu lại như câu hỏi mới.
Nếu người dân cung cấp một dữ kiện mới, hãy ghi nhận đúng dữ kiện đó, kết hợp với dữ kiện trước, giải thích ngắn ý nghĩa và chỉ hỏi một câu quan trọng nhất nếu thật sự cần làm rõ.
Không nhắc lại toàn bộ câu trả lời trước. Không tái sử dụng một đoạn văn mẫu chỉ vì câu hỏi giống nhau; hãy tự diễn đạt phù hợp với mạch hội thoại hiện tại.
Không kết luận một người có tội chỉ từ lời kể một phía.
Không gọi đơn vị là 'đồn Công an xã' hoặc 'Cục Công an xã'; dùng đúng tên {UNIT_NAME}.
Dùng cách gọi 'cán bộ Công an'. Nếu cần số liên hệ, chỉ dùng {HOTLINE}.
Không dùng Markdown, không trình bày chuỗi suy luận nội bộ.
"""


LEGAL_SYSTEM = """
Đối với câu hỏi pháp luật hoặc thủ tục hành chính:
- LEGAL_SOURCE_CONTEXT là nguồn đã được kiểm chứng và là nguồn sự thật pháp lý của lượt hiện tại.
- HISTORY chỉ dùng để nhớ tình tiết người dân đã kể; không được coi một câu trả lời pháp lý cũ của trợ lý là căn cứ pháp luật.
- Mọi số Điều, tên Điều/tội danh, ngưỡng, khung hình phạt, thời hạn, lệ phí, thẩm quyền, thành phần hồ sơ hoặc kết luận loại trừ phải bám trực tiếp nguồn.
- Với mỗi legal_claim, evidence_quote phải là đoạn nguyên văn ngắn chép trực tiếp từ đúng SOURCE_UNIT_ID.
- Không được biến quy tắc có nhiều nhánh thành một điều kiện duy nhất. Nếu nguồn có 'hoặc', 'nhưng thuộc', 'trừ trường hợp' hay ngoại lệ liên quan thì phải phản ánh đầy đủ.
- Không nói 'không cấu thành', 'không thuộc', 'chắc chắn không bị xử lý' nếu nguồn còn nhánh/ngoại lệ chưa được loại trừ.
- Với thủ tục hành chính, tuyệt đối không tự sáng tác tên biểu mẫu, giấy tờ, bản sao, cơ quan/phòng nghiệp vụ hay loại kết quả nếu nguồn không nêu.
- Nếu nguồn nói cơ quan nhà nước phải khai thác dữ liệu/VNeID và không yêu cầu nộp lại giấy tờ đã có dữ liệu thì phải phản ánh đúng nguyên tắc này.
- Nếu dữ kiện mới làm thay đổi đánh giá pháp lý, nói rõ ý nghĩa của dữ kiện mới theo nguồn, nhưng không kết luận thay cơ quan có thẩm quyền.
"""


def _bounded_history(history, max_messages, max_chars):
    """Giữ lượt mới nhất trong ngân sách, luôn theo đúng thứ tự hội thoại."""
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


def build_messages(question, history, legal_context="", repair_note=None, intake_hint=""):
    system = BASE_SYSTEM
    if legal_context:
        system += "\n" + LEGAL_SYSTEM
        system += "\nLEGAL_SOURCE_CONTEXT:\n" + legal_context
    if repair_note:
        system += "\nCÂU TRẢ LỜI TRƯỚC BỊ BỘ KIỂM CHỨNG TỪ CHỐI.\nHãy sửa đúng các lỗi sau:\n" + repair_note
    if intake_hint:
        system += "\nTIẾP NHẬN:\n" + intake_hint

    messages = [{"role": "system", "content": system}]
    messages.extend(_bounded_history(
        history,
        max_messages=MAX_HISTORY_MESSAGES,
        max_chars=max(9000, DYNAMIC_HISTORY_MAX_CHARS * 2),
    ))
    messages.append({"role": "user", "content": question})
    return messages


def answer(question, history, legal_context="", dynamic=False, repair_note=None,
           model=None, safety_identifier=None, intake_hint=""):
    model = model or (DYNAMIC_ANSWER_MODEL if dynamic else ANSWER_MODEL)
    is_groq_oss = str(model).startswith("openai/gpt-oss")
    if is_groq_oss and not dynamic:
        return {
            "answer": chat_text(
                model=model,
                messages=build_messages(question, history, legal_context=legal_context, repair_note=repair_note, intake_hint=intake_hint),
                reasoning_effort=GROQ_CORE_REASONING_EFFORT,
                timeout=CORE_TIMEOUT_SECONDS,
                temperature=0.08 if legal_context else 0.35,
                max_completion_tokens=1600,
                safety_identifier=safety_identifier,
            ),
            "legal_claims": [],
            "needs_followup": False,
            "followup_question": None,
            "contact_recommended": False,
        }
    return chat_structured(
        model=model,
        messages=build_messages(question, history, legal_context=legal_context, repair_note=repair_note, intake_hint=intake_hint),
        schema_name="citizen_answer",
        schema=ANSWER_SCHEMA,
        reasoning_effort=(DYNAMIC_REASONING_EFFORT if dynamic else (GROQ_CORE_REASONING_EFFORT if is_groq_oss else CORE_REASONING_EFFORT)),
        timeout=(DYNAMIC_TIMEOUT_SECONDS if dynamic else CORE_TIMEOUT_SECONDS),
        temperature=0.08 if legal_context else 0.45,
        max_completion_tokens=360 if dynamic else (1600 if is_groq_oss else 1100),
        safety_identifier=safety_identifier,
    )


def answer_dynamic_text(question, history, legal_context="", model=None,
                        safety_identifier=None, intake_hint=""):
    """Một lượt gọi model real-time dành cho Zalo, vẫn giữ trí nhớ hội thoại."""
    system = f"""
Bạn là Trợ lý AI của {UNIT_NAME}, không phải cán bộ thật. Đây là một cuộc hội thoại liên tục, không phải chatbot trả lời mẫu.
Trả lời tiếng Việt tự nhiên như đang trực tiếp trao đổi, thường 2-5 câu.
Luôn xưng hô "anh/chị"; không gọi người dân là "bạn".
Hiểu các đại từ và câu nối theo HISTORY. Nếu người dân nói "người đó", "vụ đó", "giờ thì sao", hãy nối với sự việc đang trao đổi.
Nếu có dữ kiện mới, kết hợp với dữ kiện cũ; không kể lại từ đầu và không hỏi lại điều người dân đã nói.
Không dùng lời mở đầu/kết thúc rập khuôn và không tái sử dụng một đoạn trả lời cố định.
Không kết luận một người có tội chỉ từ lời kể một phía.
Tên đơn vị duy nhất: {UNIT_NAME}. Số liên hệ duy nhất: {HOTLINE}.
Nếu có SOURCE bên dưới, mọi chi tiết pháp luật và thủ tục hành chính phải bám SOURCE. HISTORY chỉ là trí nhớ tình tiết, không phải nguồn pháp luật.
Không tự thêm tên giấy tờ, biểu mẫu, cơ quan/phòng nghiệp vụ, lệ phí, thời hạn hoặc loại kết quả nếu SOURCE không nêu cho đúng trường hợp.
Nếu chưa đủ căn cứ, nói rõ phần nào còn thiếu. Không dùng Markdown.
"""
    if legal_context:
        system += "\nSOURCE:\n" + legal_context
    if intake_hint:
        system += "\nTIẾP NHẬN:\n" + intake_hint

    messages = [{"role": "system", "content": system}]
    messages.extend(_bounded_history(history, max_messages=DYNAMIC_HISTORY_MESSAGES, max_chars=DYNAMIC_HISTORY_MAX_CHARS))
    messages.append({"role": "user", "content": question})

    return chat_text(
        model=model or DYNAMIC_ANSWER_MODEL,
        messages=messages,
        reasoning_effort=DYNAMIC_REASONING_EFFORT,
        timeout=DYNAMIC_TIMEOUT_SECONDS,
        temperature=0.08 if legal_context else 0.35,
        max_completion_tokens=220,
        safety_identifier=safety_identifier,
    )
