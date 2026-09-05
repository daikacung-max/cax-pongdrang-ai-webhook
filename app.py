from flask import Flask, request, jsonify
from collections import deque
from threading import Lock
from pathlib import Path
import json
import os
import re
import time
import requests

from legal_guard import (
    UNIT,
    HOTLINE,
    is_legal_question,
    retrieve_legal_context,
    exact_article_direct_answer,
    finalize_answer,
    selftest as guard_selftest,
)

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
KB = json.loads((BASE_DIR / "knowledge_base.json").read_text(encoding="utf-8"))

GROQ_API_KEY = "".join((os.getenv("GROQ_API_KEY") or "").split())
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"

# Zalo Dynamic cần nhanh. AI vẫn được "nói tự nhiên", không ép template.
TIMEOUT_SECONDS = 1.45
MAX_HISTORY = 6
MAX_MESSAGES = 4
TARGET_CHARS = 650
MAX_TOTAL_CHARS = 2400
PENDING_TTL = 25

HTTP = requests.Session()
pending_questions = deque()
conversation_history = {}
seen_message_ids = {}
state_lock = Lock()


GENERAL_SYSTEM = f"""
Bạn là Trợ lý AI của {UNIT}.

Mục tiêu là trò chuyện tự nhiên với người dân, giống một trợ lý thật:
- Hiểu câu hỏi theo ngữ cảnh, trả lời đúng điều người dân đang cần.
- Không đọc câu trả lời mẫu, không lặp một công thức cố định.
- Không mở đầu mọi câu bằng "Công an xã hướng dẫn như sau".
- Câu hỏi đơn giản trả lời thẳng, thường 1-3 câu.
- Câu hỏi phức tạp giải thích mạch lạc, ưu tiên điều thiết thực trước.
- Có thể hỏi lại một câu ngắn nếu thiếu dữ kiện quan trọng.
- Dùng tiếng Việt tự nhiên, chuẩn mực, thân thiện, văn phong Công an khi nội dung thuộc ANTT/pháp luật.
- Không dùng Markdown, không dùng dấu *, **, #.
- Không trình bày chuỗi suy luận nội bộ.
- Tên đơn vị chính xác: {UNIT}.
- Nếu cần cung cấp số điện thoại liên hệ, chỉ được dùng số trực ban {HOTLINE}.
"""


LEGAL_SYSTEM = """
Khi câu hỏi liên quan pháp luật:
1. LEGAL_SOURCE_CONTEXT bên dưới là nguồn pháp lý đã được hệ thống truy xuất.
2. Hãy dùng nguồn đó để bảo đảm đúng điều luật, tên tội, điều kiện, thời hạn hoặc thẩm quyền.
3. Bạn ĐƯỢC PHÉP diễn đạt tự nhiên, giải thích, liên hệ tình huống và hướng dẫn người dân. Không cần chép nguyên văn nguồn.
4. Không được tự sáng tác số Điều, tên tội, mức phạt, thời hạn, lệ phí hoặc thẩm quyền ngoài nguồn.
5. Nếu nguồn chưa đủ cho một chi tiết cụ thể, hãy nói theo nguyên tắc chung hoặc hỏi thêm, không bịa để lấp chỗ trống.
6. Không kết luận một người "phạm tội" chỉ từ lời kể một phía; dùng cách diễn đạt phù hợp như "có thể được xem xét", "cần xác minh", "nếu đủ dấu hiệu".
7. Đừng biến câu trả lời thành danh sách tội danh nếu người dân chỉ đang hỏi cần làm gì.
8. Với người bị đánh: ưu tiên hướng dẫn bảo vệ sức khỏe, lưu chứng cứ, trình báo; chỉ giải thích Điều 134 khi phù hợp với câu hỏi, không gán thêm tội danh vô căn cứ.
"""


def norm(text):
    text = str(text or "").lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def wants_contact(question):
    q = norm(question)
    return any(x in q for x in [
        "số điện thoại", "trực ban", "liên hệ", "gọi công an",
        "trình báo", "tố giác", "báo tin", "phản ánh"
    ])


def split_messages(text):
    text = str(text or "").strip()

    if len(text) > MAX_TOTAL_CHARS:
        clipped = text[:MAX_TOTAL_CHARS]
        pos = max(
            clipped.rfind(". "),
            clipped.rfind("? "),
            clipped.rfind("! "),
            clipped.rfind("; "),
            clipped.rfind("\n")
        )
        if pos > 1300:
            clipped = clipped[:pos + 1]
        text = clipped.strip()

    if len(text) <= TARGET_CHARS:
        return [text]

    sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
    result = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        candidate = sentence if not current else current + " " + sentence

        if len(candidate) <= TARGET_CHARS:
            current = candidate
        else:
            if current:
                result.append(current)
            current = sentence

    if current:
        result.append(current)

    if len(result) <= MAX_MESSAGES:
        return result

    merged = result[:MAX_MESSAGES - 1]
    tail = " ".join(result[MAX_MESSAGES - 1:])
    merged.append(tail[:820].strip())
    return merged[:MAX_MESSAGES]


def chatbot_response(text):
    return jsonify({
        "version": "chatbot",
        "content": {
            "messages": [
                {"type": "text", "text": part}
                for part in split_messages(text)
                if part
            ]
        }
    }), 200


def purge_state():
    now = time.time()

    while (
        pending_questions
        and now - pending_questions[0].get("time", 0) > PENDING_TTL
    ):
        pending_questions.popleft()

    for msg_id, seen_at in list(seen_message_ids.items()):
        if now - seen_at > 120:
            seen_message_ids.pop(msg_id, None)


def call_groq(question, history, legal=False, legal_context=""):
    system = GENERAL_SYSTEM

    if legal:
        system += "\n" + LEGAL_SYSTEM

        if legal_context:
            system += (
                "\nLEGAL_SOURCE_CONTEXT:\n"
                + legal_context
            )
        else:
            system += """
LEGAL_SOURCE_CONTEXT hiện chưa có dữ liệu đủ gần câu hỏi.
Vẫn hỗ trợ người dân bằng kiến thức tổng quát và hướng dẫn thực tế,
nhưng không được nêu số Điều, mức phạt, lệ phí, thời hạn hoặc thẩm quyền cụ thể nếu không có nguồn.
"""

    messages = [{"role": "system", "content": system}]

    # Giữ lịch sử để hội thoại thật sự có ngữ cảnh.
    # Prompt đã quy định lịch sử không phải nguồn pháp lý.
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": question})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.12 if legal else 0.42,
        "max_completion_tokens": 430,
        "reasoning_effort": "low",
    }

    response = HTTP.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    return (
        response.json()
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )


@app.route("/", methods=["GET"])
def home():
    return f"{UNIT} - Conversational Legal V7", 200


@app.route("/health", methods=["GET"])
def health():
    test = guard_selftest()
    return jsonify({
        "status": "ok",
        "mode": "conversational_legal_guard_v7",
        "unit": UNIT,
        "hotline": HOTLINE,
        "groq": bool(GROQ_API_KEY),
        "natural_conversation": True,
        "legal_source_retrieval": True,
        "legal_output_guard": True,
        "blhs_fulltext": True,
        "selftest_passed": bool(test.get("passed")),
        "max_messages": MAX_MESSAGES,
    }), 200


@app.route("/selftest", methods=["GET"])
def selftest():
    return jsonify(guard_selftest()), 200


@app.route("/zalo/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "OK", 200

    data = request.get_json(silent=True) or {}

    if data.get("event_name") == "user_send_text":
        sender = data.get("sender") or {}
        message = data.get("message") or {}

        sender_id = str(sender.get("id") or "").strip()
        text = str(message.get("text") or "").strip()
        msg_id = str(message.get("msg_id") or "").strip()

        if sender_id and text:
            with state_lock:
                purge_state()

                if msg_id and msg_id in seen_message_ids:
                    return jsonify({"success": True, "duplicate": True}), 200

                if msg_id:
                    seen_message_ids[msg_id] = time.time()

                pending_questions.append({
                    "sender_id": sender_id,
                    "text": text,
                    "time": time.time(),
                })

                conversation_history.setdefault(sender_id, [])

                while len(pending_questions) > 50:
                    pending_questions.popleft()

    return jsonify({"success": True}), 200


@app.route("/zalo/ai", methods=["GET", "POST"])
def ai():
    with state_lock:
        purge_state()
        item = pending_questions.popleft() if pending_questions else None

    if not item:
        return chatbot_response("Anh/chị vui lòng nhập nội dung cần hỗ trợ.")

    sender_id = item["sender_id"]
    question = item["text"]

    # Lookup Điều luật đơn giản có thể trả trực tiếp từ văn bản gốc.
    direct = exact_article_direct_answer(question)
    if direct:
        direct = finalize_answer(
            direct,
            legal=True,
            contact_relevant=wants_contact(question),
        )
        return chatbot_response(direct)

    legal = is_legal_question(question)

    legal_meta = {
        "context": "",
        "allowed_blhs_articles": [],
        "top_blhs_article": None,
    }

    if legal:
        legal_meta = retrieve_legal_context(question)

    with state_lock:
        history = list(conversation_history.get(sender_id, []))

    try:
        raw_answer = call_groq(
            question,
            history,
            legal=legal,
            legal_context=legal_meta.get("context", ""),
        )

        answer = finalize_answer(
            raw_answer,
            legal=legal,
            allowed_blhs_articles=legal_meta.get("allowed_blhs_articles", []),
            top_blhs_article=legal_meta.get("top_blhs_article"),
            contact_relevant=wants_contact(question),
        )

        with state_lock:
            conversation_history.setdefault(sender_id, [])
            conversation_history[sender_id].extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ])
            conversation_history[sender_id] = (
                conversation_history[sender_id][-MAX_HISTORY:]
            )

        return chatbot_response(answer)

    except requests.exceptions.RequestException:
        if legal and legal_meta.get("top_blhs_article"):
            art = legal_meta["top_blhs_article"]
            title = legal_meta.get("top_blhs_title") or ""
            fallback = (
                f"Vụ việc cần được xem xét theo tình tiết thực tế. "
                f"Nội dung có liên quan đến Điều {art} Bộ luật Hình sự: {title}. "
                "Để xác định có đủ dấu hiệu xử lý hình sự hay không, cần làm rõ thương tích, "
                "hành vi, công cụ sử dụng và các chứng cứ liên quan."
            )
            fallback = finalize_answer(
                fallback,
                legal=True,
                allowed_blhs_articles=[art],
                top_blhs_article=art,
                contact_relevant=wants_contact(question),
            )
            return chatbot_response(fallback)

        return chatbot_response(
            f"Trợ lý AI đang tạm thời chưa kết nối được dịch vụ xử lý. "
            f"Người dân có thể liên hệ trực ban {UNIT} qua số {HOTLINE}."
        )

    except Exception:
        return chatbot_response(
            f"Trợ lý AI hiện chưa xử lý được nội dung này. "
            f"Người dân có thể liên hệ trực ban {UNIT} qua số {HOTLINE}."
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
