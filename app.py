from flask import Flask, request, jsonify
from pathlib import Path
from collections import deque
from threading import Lock
import json
import os
import re
import time
import unicodedata
import requests

app = Flask(__name__)

# =========================================================
# BẢN THI CÔNG AN TỈNH — ƯU TIÊN ỔN ĐỊNH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
KB_FILE = BASE_DIR / "knowledge_base.json"

GROQ_API_KEY = "".join(
    (os.getenv("GROQ_API_KEY") or "").split()
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model 20B đã được kiểm tra thực tế với luồng Zalo Dynamic.
# Chọn tốc độ + độ ổn định thay vì ép reasoning dài.
MODEL = "openai/gpt-oss-20b"

# Dynamic API cần phản hồi rất nhanh.
GROQ_TIMEOUT_SECONDS = 1.45

MAX_HISTORY_MESSAGES = 6
MAX_ZALO_CHARS = 1050
PENDING_TTL_SECONDS = 25

# Tái sử dụng kết nối HTTP để giảm độ trễ.
HTTP = requests.Session()


# =========================================================
# NẠP KNOWLEDGE BASE
# =========================================================

try:
    KB = json.loads(
        KB_FILE.read_text(encoding="utf-8")
    )
except Exception:
    KB = {}

SOURCES_LIST = KB.get("sources", [])
SOURCES = {
    str(item.get("id")): item
    for item in SOURCES_LIST
    if item.get("id")
}
CHUNKS = KB.get("chunks", [])
ROUTER = KB.get("router", {"rules": []})
VERSION = KB.get("version", {})

KB_SYSTEM_PROMPT = KB.get(
    "system_prompt",
    "Không được bịa căn cứ pháp luật."
)

print(
    "COMPETITION MODE READY:",
    "GROQ:", bool(GROQ_API_KEY),
    "KB:", bool(CHUNKS),
    "CHUNKS:", len(CHUNKS),
    "SOURCES:", len(SOURCES),
    "MODEL:", MODEL,
    flush=True
)


# =========================================================
# BỘ NHỚ TẠM
# =========================================================

conversation_history = {}
pending_questions = deque()
seen_message_ids = {}

state_lock = Lock()


# =========================================================
# CHUẨN HÓA
# =========================================================

def normalize_text(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)

    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) != "Mn"
    )

    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


STOP_WORDS = {
    "toi", "ban", "anh", "chi", "la", "va", "voi", "cua",
    "co", "khong", "duoc", "cho", "ve", "thi", "the", "nao",
    "gi", "can", "muon", "hoi", "mot", "nhung", "cac", "nay",
    "do", "o", "tai", "den", "tu", "khi"
}


def tokens(text):
    return {
        word
        for word in normalize_text(text).split()
        if len(word) >= 2
        and word not in STOP_WORDS
    }


# =========================================================
# PHÂN LOẠI CÂU HỎI
# =========================================================

def detect_domains(question):
    q = normalize_text(question)
    matched = []

    for rule in ROUTER.get("rules", []):
        score = 0

        for keyword in rule.get("keywords", []):
            kw = normalize_text(keyword)

            if kw and kw in q:
                score += max(
                    2,
                    len(kw.split())
                )

        if score > 0:
            matched.append(
                (score, rule.get("domain", ""))
            )

    matched.sort(reverse=True)

    result = []

    for _, domain in matched:
        if domain and domain not in result:
            result.append(domain)

    return result[:3]


LEGAL_DOMAINS = {
    "hinh_su",
    "to_tung_hinh_su",
    "ma_tuy",
    "hanh_chinh",
    "cu_tru",
    "can_cuoc_vneid",
    "giao_thong",
    "dat_dai",
    "pccc_vu_khi_mang",
    "dinh_danh_dien_tu",
    "dang_ky_xe",
    "pccc",
    "an_ninh_mang",
    "bi_mat_nha_nuoc",
}


def is_legal_or_police_question(
    question,
    domains
):
    if any(
        domain in LEGAL_DOMAINS
        for domain in domains
    ):
        return True

    q = normalize_text(question)

    keywords = [
        "cong an",
        "phap luat",
        "dieu luat",
        "bo luat",
        "nghi dinh",
        "thong tu",
        "xu phat",
        "toi pham",
        "khoi to",
        "to giac",
        "tam tru",
        "thuong tru",
        "can cuoc",
        "vneid",
        "ma tuy",
        "dat dai",
        "dang ky xe",
        "pccc",
        "an ninh trat tu",
    ]

    return any(
        keyword in q
        for keyword in keywords
    )


# =========================================================
# RAG CỤC BỘ
# =========================================================

def chunk_score(
    question,
    chunk,
    domains
):
    q_normalized = normalize_text(
        question
    )

    q_tokens = tokens(
        question
    )

    title = normalize_text(
        chunk.get("title", "")
    )

    content = normalize_text(
        chunk.get("content", "")
    )

    keyword_text = " ".join(
        normalize_text(item)
        for item in chunk.get(
            "keywords",
            []
        )
    )

    chunk_tokens = tokens(
        title
        + " "
        + keyword_text
        + " "
        + content
    )

    score = 0.0

    score += (
        len(
            q_tokens
            & chunk_tokens
        )
        * 2.4
    )

    for keyword in chunk.get(
        "keywords",
        []
    ):
        kw = normalize_text(
            keyword
        )

        if kw and kw in q_normalized:
            score += 5.5

    if (
        chunk.get("domain")
        in domains
    ):
        score += 5.0

    for word in q_tokens:
        if word in title:
            score += 0.8

    return score


def retrieve_chunks(
    question,
    domains,
    top_k=4
):
    ranked = []

    for chunk in CHUNKS:
        score = chunk_score(
            question,
            chunk,
            domains
        )

        if score > 0:
            ranked.append(
                (score, chunk)
            )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        item[1]
        for item in ranked[:top_k]
    ]


def compact_rag_context(
    chunks_found
):
    blocks = []

    for chunk in chunks_found:
        source_labels = []

        for source_id in chunk.get(
            "source_ids",
            []
        ):
            source = SOURCES.get(
                str(source_id)
            )

            if not source:
                continue

            label = (
                f"{source.get('number', '')} "
                f"{source.get('title', '')}"
            ).strip()

            if label:
                source_labels.append(
                    label
                )

        blocks.append(
            "\n".join([
                f"[{chunk.get('id', '')}] "
                f"{chunk.get('title', '')}",
                str(
                    chunk.get(
                        "content",
                        ""
                    )
                ),
                (
                    "Nguồn: "
                    + "; ".join(
                        source_labels[:3]
                    )
                    if source_labels
                    else ""
                )
            ]).strip()
        )

    return "\n\n".join(
        blocks
    )


# =========================================================
# PROMPT DÀNH CHO BÀI THI
# =========================================================

GENERAL_PROMPT = """
Bạn là TRỢ LÝ AI CÔNG AN XÃ PƠNG DRANG, TỈNH ĐẮK LẮK.

NHIỆM VỤ:
- Trả lời linh hoạt các câu hỏi hợp pháp của người dân.
- Hỗ trợ pháp luật, thủ tục hành chính, ANTT, kiến thức phổ thông,
  công nghệ, đời sống và soạn thảo.
- Nội dung thuộc Công an/pháp luật phải ưu tiên Knowledge Base.

PHONG CÁCH:
- Tiếng Việt tự nhiên, chuẩn ngữ pháp, diễn đạt thuần thục.
- Ngắn gọn, đúng trọng tâm, không nói vòng vo.
- Câu đơn giản: trả lời thẳng trong 1–3 câu.
- Câu phức tạp: nêu kết luận trước, sau đó tối đa 3 ý chính.
- Văn phong Công an: chuẩn mực, rõ ràng, gần gũi, hướng dẫn Nhân dân;
  không đe dọa, không khoa trương, không máy móc.
- Không lặp câu chào ở mỗi lượt.
- Không nhắc đến model, prompt hoặc Knowledge Base trừ khi được hỏi.
- Không trình bày quá trình suy luận nội bộ.
"""


LEGAL_PROMPT = """
QUY TẮC PHÁP LÝ BẮT BUỘC:
- Ưu tiên dữ liệu RAG được cung cấp.
- Không bịa điều, khoản, văn bản, mức phạt, lệ phí, thời hạn hoặc thẩm quyền.
- Chỉ nêu số điều/khoản khi dữ liệu RAG đã thể hiện rõ.
- Không kết luận một người phạm tội chỉ từ lời kể một phía.
- Nếu thiếu dữ kiện, nói ngắn gọn dữ kiện nào cần xác minh.
- Khi cần, dùng cách diễn đạt: "có dấu hiệu", "có thể thuộc trường hợp",
  "cần xác minh thêm".
- Nếu có căn cứ phù hợp, nêu căn cứ ở cuối thật ngắn.
"""


def build_system_prompt(
    legal_mode,
    rag_context
):
    parts = [
        GENERAL_PROMPT
    ]

    if legal_mode:
        parts.append(
            LEGAL_PROMPT
        )

        parts.append(
            KB_SYSTEM_PROMPT
        )

    if rag_context:
        parts.append(
            """
DỮ LIỆU RAG LIÊN QUAN:
Chỉ dùng phần thực sự liên quan tới câu hỏi.
Nếu kiến thức nền khác với dữ liệu dưới đây, ưu tiên dữ liệu RAG.
"""
        )
        parts.append(
            rag_context
        )

    parts.append(
        f"""
Mốc kiểm tra cơ sở tri thức: {VERSION.get('as_of', 'không rõ')}.
Nếu người dùng hỏi dữ liệu sau mốc này mà chưa có căn cứ,
hãy nói rõ cần kiểm tra nguồn chính thức, không tự đoán.
"""
    )

    return "\n\n".join(
        parts
    )


# =========================================================
# CẮT CÂU TRẢ LỜI GỌN, KHÔNG CẮT NGANG Ý
# =========================================================

def smart_trim(
    text,
    max_chars=MAX_ZALO_CHARS
):
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        str(text or "").strip()
    )

    if len(text) <= max_chars:
        return text

    clipped = text[:max_chars]

    candidates = [
        clipped.rfind(". "),
        clipped.rfind("? "),
        clipped.rfind("! "),
        clipped.rfind("\n"),
    ]

    cut = max(candidates)

    if cut >= int(
        max_chars * 0.60
    ):
        clipped = clipped[
            :cut + 1
        ]

    return (
        clipped.rstrip()
        + "…"
    )


# =========================================================
# FALLBACK TỪ KNOWLEDGE BASE
# =========================================================

def kb_fallback_answer(
    chunks_found
):
    if not chunks_found:
        return (
            "Trợ lý AI đang tạm thời chưa kết nối được dịch vụ xử lý. "
            "Anh/chị vui lòng thử lại sau ít giây."
        )

    best = chunks_found[0]

    content = str(
        best.get(
            "content",
            ""
        )
    ).strip()

    source_labels = []

    for source_id in best.get(
        "source_ids",
        []
    ):
        source = SOURCES.get(
            str(source_id)
        )

        if not source:
            continue

        number = str(
            source.get(
                "number",
                ""
            )
        ).strip()

        title = str(
            source.get(
                "title",
                ""
            )
        ).strip()

        if number:
            source_labels.append(
                number
            )
        elif title:
            source_labels.append(
                title
            )

    answer = (
        "Công an xã Pơng Drang hướng dẫn: "
        + content
    )

    if source_labels:
        answer += (
            "\nCăn cứ: "
            + ", ".join(
                source_labels[:2]
            )
            + "."
        )

    return smart_trim(
        answer
    )


# =========================================================
# GỌI GROQ — ĐƯỜNG NHANH
# =========================================================

def ask_groq(
    question,
    history
):
    domains = detect_domains(
        question
    )

    legal_mode = (
        is_legal_or_police_question(
            question,
            domains
        )
    )

    chunks_found = (
        retrieve_chunks(
            question,
            domains,
            top_k=4
        )
        if legal_mode
        else []
    )

    rag_context = (
        compact_rag_context(
            chunks_found
        )
    )

    system_prompt = (
        build_system_prompt(
            legal_mode,
            rag_context
        )
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(
        history[
            -MAX_HISTORY_MESSAGES:
        ]
    )

    messages.append({
        "role": "user",
        "content": question
    })

    headers = {
        "Authorization":
            f"Bearer {GROQ_API_KEY}",
        "Content-Type":
            "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature":
            0.08
            if legal_mode
            else 0.35,
        "max_completion_tokens": 260,
        "reasoning_effort": "low",
    }

    response = HTTP.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=GROQ_TIMEOUT_SECONDS
    )

    if response.status_code >= 400:
        try:
            error_data = (
                response.json()
            )

            error_message = (
                error_data
                .get("error", {})
                .get("message")
            )
        except Exception:
            error_message = (
                response.text[:250]
            )

        print(
            "GROQ ERROR:",
            response.status_code,
            str(
                error_message
            )[:250],
            flush=True
        )

        response.raise_for_status()

    data = response.json()

    answer = (
        data.get(
            "choices",
            [{}]
        )[0]
        .get(
            "message",
            {}
        )
        .get(
            "content",
            ""
        )
        .strip()
    )

    if not answer:
        raise RuntimeError(
            "Empty AI response"
        )

    return (
        smart_trim(answer),
        {
            "legal_mode":
                legal_mode,
            "domains":
                domains,
            "chunks":
                [
                    item.get("id")
                    for item
                    in chunks_found
                ],
            "fallback_chunks":
                chunks_found,
        }
    )


# =========================================================
# FORMAT ZALO
# =========================================================

def chatbot_response(text):
    return jsonify({
        "version": "chatbot",
        "content": {
            "messages": [
                {
                    "type": "text",
                    "text": str(text)
                }
            ]
        }
    }), 200


# =========================================================
# QUẢN LÝ HÀNG ĐỢI
# =========================================================

def purge_state(
    now=None
):
    now = now or time.time()

    while pending_questions:
        first = (
            pending_questions[0]
        )

        if (
            now
            - first.get(
                "time",
                0
            )
            <= PENDING_TTL_SECONDS
        ):
            break

        pending_questions.popleft()

    expired_ids = [
        msg_id
        for msg_id, seen_at
        in seen_message_ids.items()
        if (
            now - seen_at
            > 120
        )
    ]

    for msg_id in expired_ids:
        seen_message_ids.pop(
            msg_id,
            None
        )


def pop_pending_question():
    with state_lock:
        purge_state()

        if not pending_questions:
            return None

        return (
            pending_questions
            .popleft()
        )


# =========================================================
# HEALTH
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return """
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="zalo-platform-site-verification"
      content="OiMc2EZKV28O_zyYtDbQAHRNrNRweGyWD34u" />
<title>Trợ lý AI Công an xã Pơng Drang</title>
</head>
<body>
<h3>Trợ lý AI Công an xã Pơng Drang</h3>
<p>Competition Stable Mode: active</p>
</body>
</html>
""", 200, {
        "Content-Type":
            "text/html; charset=utf-8"
    }


@app.route(
    "/health",
    methods=["GET"]
)
def health():
    return jsonify({
        "status": "ok",
        "mode":
            "competition_stable",
        "groq":
            bool(GROQ_API_KEY),
        "kb_loaded":
            bool(CHUNKS),
        "kb_version":
            VERSION.get("version"),
        "kb_as_of":
            VERSION.get("as_of"),
        "chunks":
            len(CHUNKS),
        "sources":
            len(SOURCES),
        "model":
            MODEL,
        "web_search":
            False,
        "background_queue":
            False,
    }), 200


@app.route(
    "/kb/status",
    methods=["GET"]
)
def kb_status():
    return jsonify({
        "loaded":
            bool(CHUNKS),
        "name":
            VERSION.get("name"),
        "version":
            VERSION.get("version"),
        "as_of":
            VERSION.get("as_of"),
        "next_review":
            VERSION.get(
                "next_mandatory_review"
            ),
        "chunks":
            len(CHUNKS),
        "sources":
            len(SOURCES),
    }), 200


# =========================================================
# ZALO WEBHOOK
# =========================================================

@app.route(
    "/zalo/webhook",
    methods=["GET", "POST"]
)
def zalo_webhook():
    if request.method == "GET":
        return "OK", 200

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    if (
        data.get("event_name")
        == "user_send_text"
    ):
        sender = (
            data.get("sender")
            or {}
        )

        message = (
            data.get("message")
            or {}
        )

        sender_id = str(
            sender.get("id")
            or ""
        ).strip()

        text = str(
            message.get("text")
            or ""
        ).strip()

        msg_id = str(
            message.get("msg_id")
            or ""
        ).strip()

        if sender_id and text:
            with state_lock:
                purge_state()

                # Chặn webhook trùng.
                if (
                    msg_id
                    and msg_id
                    in seen_message_ids
                ):
                    return jsonify({
                        "success": True,
                        "duplicate": True
                    }), 200

                if msg_id:
                    seen_message_ids[
                        msg_id
                    ] = time.time()

                pending_questions.append({
                    "sender_id":
                        sender_id,
                    "msg_id":
                        msg_id,
                    "text":
                        text,
                    "time":
                        time.time(),
                })

                conversation_history.setdefault(
                    sender_id,
                    []
                )

                while (
                    len(
                        pending_questions
                    )
                    > 50
                ):
                    pending_questions.popleft()

            # Không log nội dung/PII.
            print(
                "QUESTION RECEIVED:",
                "LENGTH:",
                len(text),
                "QUEUE:",
                len(
                    pending_questions
                ),
                flush=True
            )

    return jsonify({
        "success": True
    }), 200


# =========================================================
# DYNAMIC -> RAG -> GROQ
# =========================================================

@app.route(
    "/zalo/ai",
    methods=["GET", "POST"]
)
def zalo_ai():
    item = (
        pop_pending_question()
    )

    if not item:
        return chatbot_response(
            "Anh/chị vui lòng nhập nội dung cần hỗ trợ."
        )

    sender_id = (
        item["sender_id"]
    )

    question = (
        item["text"]
    )

    with state_lock:
        history = list(
            conversation_history.get(
                sender_id,
                []
            )
        )

    # Chuẩn bị sẵn RAG để nếu AI lỗi vẫn có câu trả lời từ KB.
    domains = detect_domains(
        question
    )

    legal_mode = (
        is_legal_or_police_question(
            question,
            domains
        )
    )

    fallback_chunks = (
        retrieve_chunks(
            question,
            domains,
            top_k=2
        )
        if legal_mode
        else []
    )

    started = time.time()

    try:
        answer, trace = ask_groq(
            question,
            history
        )

        elapsed = round(
            time.time()
            - started,
            2
        )

        with state_lock:
            conversation_history.setdefault(
                sender_id,
                []
            )

            conversation_history[
                sender_id
            ].extend([
                {
                    "role": "user",
                    "content": question
                },
                {
                    "role": "assistant",
                    "content": answer
                },
            ])

            conversation_history[
                sender_id
            ] = (
                conversation_history[
                    sender_id
                ][
                    -MAX_HISTORY_MESSAGES:
                ]
            )

        print(
            "AI SUCCESS:",
            "SECONDS:",
            elapsed,
            "LEGAL:",
            trace["legal_mode"],
            "DOMAINS:",
            ",".join(
                trace["domains"]
            ),
            "CHUNKS:",
            ",".join(
                trace["chunks"]
            ),
            flush=True
        )

        return chatbot_response(
            answer
        )

    except (
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
        requests.exceptions.RequestException
    ) as error:
        print(
            "AI FAST FALLBACK:",
            type(error).__name__,
            flush=True
        )

        return chatbot_response(
            kb_fallback_answer(
                fallback_chunks
            )
        )

    except Exception as error:
        print(
            "AI FALLBACK:",
            type(error).__name__,
            flush=True
        )

        return chatbot_response(
            kb_fallback_answer(
                fallback_chunks
            )
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
