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
# CẤU HÌNH CHUNG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
GROQ_API_KEY = "".join(
    (os.getenv("GROQ_API_KEY") or "").split()
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

FAST_MODEL = "openai/gpt-oss-20b"
WEB_MODEL = "groq/compound-mini"

MAX_ZALO_CHARS = 1800
MAX_HISTORY_MESSAGES = 6
PENDING_TTL_SECONDS = 30

# Dynamic API của Zalo yêu cầu phản hồi dưới 2 giây.
# Giữ timeout thấp để còn thời gian trả fallback.
GROQ_TIMEOUT_SECONDS = 1.55


# =========================================================
# NẠP KNOWLEDGE BASE TỪ 1 FILE
# =========================================================

KB_FILE = BASE_DIR / "knowledge_base.json"

try:
    KB = json.loads(KB_FILE.read_text(encoding="utf-8"))
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
    "Bạn là Trợ lý AI Công an xã Pơng Drang. Không bịa căn cứ pháp luật."
)

print(
    "KB LOADED:",
    bool(CHUNKS),
    "CHUNKS:",
    len(CHUNKS),
    "SOURCES:",
    len(SOURCES),
    "GROQ:",
    bool(GROQ_API_KEY),
    flush=True
)


# =========================================================
# BỘ NHỚ TẠM
# =========================================================

# Lưu lịch sử theo sender_id do Webhook cung cấp.
conversation_history = {}

# Hàng đợi giúp ghép câu hỏi vừa vào Webhook với lần Dynamic kế tiếp.
# Đây an toàn hơn cách "lấy câu hỏi mới nhất toàn hệ thống",
# nhưng vẫn chỉ là giải pháp tạm khi Zalo Dynamic không truyền user_id.
pending_questions = deque()

state_lock = Lock()


# =========================================================
# CHUẨN HÓA VĂN BẢN / TOKEN
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
    "toi", "ban", "anh", "chi", "la", "va", "voi", "cua", "co", "khong",
    "duoc", "cho", "ve", "thi", "the", "nao", "gi", "can", "muon", "hoi",
    "mot", "nhung", "cac", "nay", "do", "o", "tai", "den", "tu", "khi"
}


def tokens(text):
    return {
        w for w in normalize_text(text).split()
        if len(w) >= 2 and w not in STOP_WORDS
    }


# =========================================================
# NHẬN DIỆN LĨNH VỰC
# =========================================================

def detect_domains(question):
    q = normalize_text(question)
    matched = []

    for rule in ROUTER.get("rules", []):
        score = 0
        for kw in rule.get("keywords", []):
            nkw = normalize_text(kw)
            if nkw and nkw in q:
                score += max(2, len(nkw.split()))

        if score > 0:
            matched.append((score, rule.get("domain", "")))

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


def is_legal_or_police_question(question, domains):
    if any(d in LEGAL_DOMAINS for d in domains):
        return True

    q = normalize_text(question)
    police_words = [
        "cong an", "phap luat", "dieu luat", "nghi dinh", "thong tu",
        "xu phat", "toi pham", "khoi to", "to giac", "tam tru", "can cuoc",
        "vneid", "ma tuy", "dat dai", "dang ky xe", "pccc"
    ]
    return any(word in q for word in police_words)


# =========================================================
# TRUY XUẤT RAG CỤC BỘ
# =========================================================

def chunk_score(question, chunk, domains):
    qn = normalize_text(question)
    qt = tokens(question)

    title = normalize_text(chunk.get("title", ""))
    content = normalize_text(chunk.get("content", ""))
    ck = " ".join(
        normalize_text(x)
        for x in chunk.get("keywords", [])
    )

    ct = tokens(title + " " + ck + " " + content)

    score = 0.0

    # Giao nhau token
    score += len(qt & ct) * 2.2

    # Khớp keyword cụm
    for kw in chunk.get("keywords", []):
        nkw = normalize_text(kw)
        if nkw and nkw in qn:
            score += 5.0

    # Ưu tiên domain
    if chunk.get("domain") in domains:
        score += 5.0

    # Khớp tiêu đề
    for word in qt:
        if word in title:
            score += 0.8

    return score


def retrieve_chunks(question, domains, top_k=6):
    ranked = []

    for chunk in CHUNKS:
        score = chunk_score(question, chunk, domains)
        if score > 0:
            ranked.append((score, chunk))

    ranked.sort(key=lambda x: x[0], reverse=True)

    return [item[1] for item in ranked[:top_k]]


def format_rag_context(chunks_found):
    if not chunks_found:
        return ""

    blocks = []

    for c in chunks_found:
        source_lines = []
        for sid in c.get("source_ids", []):
            s = SOURCES.get(str(sid))
            if not s:
                continue

            line = (
                f"{sid}: {s.get('title', '')}; "
                f"{s.get('number', '')}; "
                f"cơ quan: {s.get('issuer', '')}; "
                f"trạng thái: {s.get('effective_status', '')}; "
                f"kiểm tra: {s.get('checked_at', '')}; "
                f"URL: {s.get('url', '')}"
            )
            source_lines.append(line)

        blocks.append(
            "\n".join([
                f"[CHUNK {c.get('id', '')}]",
                f"Lĩnh vực: {c.get('domain', '')}",
                f"Tiêu đề: {c.get('title', '')}",
                f"Nội dung: {c.get('content', '')}",
                "Nguồn:",
                *source_lines,
            ])
        )

    return "\n\n".join(blocks)


# =========================================================
# XÁC ĐỊNH CẦN TRA WEB HAY KHÔNG
# =========================================================

LIVE_WORDS = [
    "hom nay",
    "hien nay",
    "hien tai",
    "bay gio",
    "moi nhat",
    "cap nhat",
    "con hieu luc",
    "co hieu luc",
    "muc phat",
    "phat bao nhieu",
    "le phi",
    "thoi han",
    "tham quyen",
    "ho so can gi",
    "lam o dau",
    "bieu mau",
    "gia vang",
    "ty gia",
    "thoi tiet",
    "tin tuc",
    "lich thi dau",
    "ket qua bong da",
]


def needs_live_web(question, chunks_found):
    q = normalize_text(question)

    if any(word in q for word in LIVE_WORDS):
        return True

    years = re.findall(r"\b20\d{2}\b", q)
    if any(int(y) >= 2026 for y in years):
        return True

    if any(c.get("requires_live_check") for c in chunks_found):
        # Chỉ ép live nếu câu hỏi thực sự hỏi dữ kiện pháp lý cụ thể.
        legal_detail_words = [
            "dieu", "khoan", "diem", "muc phat", "phat", "thoi han",
            "tham quyen", "ho so", "le phi", "hieu luc", "can cu"
        ]
        if any(word in q for word in legal_detail_words):
            return True

    return False


def contains_sensitive_data(question):
    q = normalize_text(question)

    if any(x in q for x in ["mat khau", "password", "otp", "ma pin"]):
        return True

    # Chuỗi số dài có thể là CCCD / tài khoản / điện thoại.
    return bool(re.search(r"\b\d{9,16}\b", str(question)))


# =========================================================
# XÂY PROMPT
# =========================================================

GENERAL_PROMPT = """
Bạn là Trợ lý AI đa năng của Công an xã Pơng Drang, tỉnh Đắk Lắk.

Ngoài các nội dung pháp luật và Công an, bạn có thể hỗ trợ kiến thức phổ thông,
học tập, công nghệ, đời sống và soạn thảo.

Khi câu hỏi thuộc lĩnh vực pháp luật/Công an:
- ưu tiên tuyệt đối KNOWLEDGE BASE và nguồn chính thức được cung cấp;
- không bịa điều, khoản, văn bản, mức phạt, lệ phí, thời hạn hoặc thẩm quyền;
- nếu chưa đủ căn cứ thì nói rõ chưa đủ dữ kiện;
- dùng văn phong chuẩn mực, chuyên nghiệp, dễ hiểu;
- không tự kết luận một người có tội.

Khi câu hỏi thông thường:
- trả lời tự nhiên, hữu ích, không cần quá hành chính.

Không yêu cầu người dùng gửi mật khẩu, OTP, PIN hoặc dữ liệu nhạy cảm không cần thiết.
"""


def build_system_prompt(question, legal_mode, rag_context, web_required):
    parts = [GENERAL_PROMPT]

    if legal_mode:
        parts.append(KB_SYSTEM_PROMPT)

    if rag_context:
        parts.append(
            """
DƯỚI ĐÂY LÀ KNOWLEDGE BASE ĐÃ ĐƯỢC CHUẨN HÓA.
Chỉ sử dụng chunk có liên quan.
Nếu kiến thức nền của bạn khác với KB, ưu tiên KB.
Không được biến metadata nguồn thành một kết luận mà nguồn không hỗ trợ.
"""
        )
        parts.append(rag_context)

    if web_required:
        parts.append(
            """
CÂU HỎI NÀY CẦN DỮ LIỆU CẬP NHẬT.
Hãy dùng tìm kiếm web nếu hệ thống cho phép.
Nếu là pháp luật Việt Nam, chỉ ưu tiên nguồn chính thức.
Kiểm tra ngày ban hành/ngày hiệu lực/văn bản sửa đổi trước khi khẳng định.
"""
        )

    return "\n\n".join(parts)


# =========================================================
# GỌI GROQ
# =========================================================

OFFICIAL_LEGAL_DOMAINS = [
    "vanban.chinhphu.vn",
    "chinhphu.vn",
    "congbao.chinhphu.vn",
    "bocongan.gov.vn",
    "vanban.bocongan.gov.vn",
    "dichvucong.bocongan.gov.vn",
    "moj.gov.vn",
    "quochoi.vn",
]


def ask_groq(question, history):
    domains = detect_domains(question)
    legal_mode = is_legal_or_police_question(question, domains)

    chunks_found = (
        retrieve_chunks(question, domains, top_k=6)
        if legal_mode else []
    )

    rag_context = format_rag_context(chunks_found)

    web_required = (
        needs_live_web(question, chunks_found)
        and not contains_sensitive_data(question)
    )

    system_prompt = build_system_prompt(
        question,
        legal_mode,
        rag_context,
        web_required
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    messages.extend(history[-MAX_HISTORY_MESSAGES:])

    messages.append({
        "role": "user",
        "content": question
    })

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    web_used = False
    web_attempted = False
    web_error = None

    # =====================================================
    # 1) NẾU CẦN DỮ LIỆU MỚI: THỬ COMPOUND MINI TỐI GIẢN
    # =====================================================
    if web_required:
        web_attempted = True

        web_payload = {
            "model": WEB_MODEL,
            "messages": messages,
        }

        try:
            web_response = requests.post(
                GROQ_URL,
                headers=headers,
                json=web_payload,
                timeout=1.65
            )

            if web_response.status_code < 400:
                web_data = web_response.json()

                web_answer = (
                    web_data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                if web_answer:
                    web_used = True

                    if len(web_answer) > MAX_ZALO_CHARS:
                        web_answer = (
                            web_answer[:MAX_ZALO_CHARS - 20].rstrip()
                            + "\n…"
                        )

                    return web_answer, {
                        "domains": domains,
                        "legal_mode": legal_mode,
                        "web_required": True,
                        "web_attempted": True,
                        "web_used": True,
                        "web_error": None,
                        "chunks": [c.get("id") for c in chunks_found],
                    }

            try:
                err = web_response.json()
                web_error = (
                    err.get("error", {}).get("message")
                    if isinstance(err, dict)
                    else None
                )
            except Exception:
                web_error = web_response.text[:250]

            print(
                "WEB SEARCH FALLBACK:",
                web_response.status_code,
                str(web_error)[:250],
                flush=True
            )

        except requests.exceptions.Timeout:
            web_error = "timeout"
            print(
                "WEB SEARCH FALLBACK: TIMEOUT",
                flush=True
            )

        except Exception as e:
            web_error = type(e).__name__
            print(
                "WEB SEARCH FALLBACK:",
                type(e).__name__,
                flush=True
            )

    # =====================================================
    # 2) FAST MODEL + KNOWLEDGE BASE
    #    Luôn là đường dự phòng để Zalo không bị im/lỗi.
    # =====================================================

    fallback_note = ""

    if web_required and not web_used:
        fallback_note = f"""
LƯU Ý QUAN TRỌNG:
Hệ thống vừa không truy xuất được web thời gian thực.
Chỉ được trả lời từ Knowledge Base hiện có và kiến thức chắc chắn.
Knowledge Base có mốc kiểm tra: {VERSION.get("as_of", "không rõ")}.
Nếu câu hỏi phụ thuộc quy định mới hơn mốc này hoặc cần xác nhận hiện hành,
hãy nói rõ cần kiểm tra lại nguồn chính thức, KHÔNG tự suy đoán.
"""

    fast_messages = [
        {
            "role": "system",
            "content": system_prompt + "\n\n" + fallback_note
        }
    ]

    fast_messages.extend(history[-MAX_HISTORY_MESSAGES:])
    fast_messages.append({
        "role": "user",
        "content": question
    })

    fast_payload = {
        "model": FAST_MODEL,
        "messages": fast_messages,
        "temperature": 0.18 if legal_mode else 0.45,
        "max_completion_tokens": 300,
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=fast_payload,
        timeout=1.55
    )

    if response.status_code >= 400:
        try:
            err = response.json()
            err_message = (
                err.get("error", {}).get("message")
                if isinstance(err, dict)
                else None
            )
        except Exception:
            err_message = response.text[:300]

        print(
            "GROQ API ERROR:",
            response.status_code,
            str(err_message)[:300],
            flush=True
        )

        response.raise_for_status()

    data = response.json()

    answer = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not answer:
        raise RuntimeError("Groq không trả về nội dung")

    if len(answer) > MAX_ZALO_CHARS:
        answer = answer[:MAX_ZALO_CHARS - 20].rstrip() + "\n…"

    return answer, {
        "domains": domains,
        "legal_mode": legal_mode,
        "web_required": web_required,
        "web_attempted": web_attempted,
        "web_used": False,
        "web_error": web_error,
        "chunks": [c.get("id") for c in chunks_found],
    }


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
# HÀNG ĐỢI CÂU HỎI
# =========================================================

def purge_old_pending(now=None):
    now = now or time.time()

    while pending_questions:
        first = pending_questions[0]
        if now - first.get("time", 0) <= PENDING_TTL_SECONDS:
            break
        pending_questions.popleft()


def pop_pending_question():
    with state_lock:
        purge_old_pending()

        if not pending_questions:
            return None

        # FIFO: Dynamic kế tiếp lấy câu hỏi Webhook cũ nhất đang chờ.
        return pending_questions.popleft()


# =========================================================
# HOME + HEALTH + KB STATUS
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
<h3>Trợ lý AI Công an xã Pơng Drang đang hoạt động</h3>
<p>Knowledge Base RAG: active</p>
</body>
</html>
""", 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "groq": bool(GROQ_API_KEY),
        "kb_loaded": bool(CHUNKS),
        "kb_version": VERSION.get("version"),
        "kb_as_of": VERSION.get("as_of"),
        "chunks": len(CHUNKS),
        "sources": len(SOURCES),
        "fast_model": FAST_MODEL,
        "web_model": WEB_MODEL,
    }), 200


@app.route("/kb/status", methods=["GET"])
def kb_status():
    return jsonify({
        "loaded": bool(CHUNKS),
        "name": VERSION.get("name"),
        "version": VERSION.get("version"),
        "as_of": VERSION.get("as_of"),
        "next_review": VERSION.get("next_mandatory_review"),
        "chunks": len(CHUNKS),
        "sources": len(SOURCES),
    }), 200


# =========================================================
# WEBHOOK ZALO
# =========================================================

@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():
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
            item = {
                "sender_id": sender_id,
                "msg_id": msg_id,
                "text": text,
                "time": time.time(),
            }

            with state_lock:
                purge_old_pending()
                pending_questions.append(item)
                conversation_history.setdefault(sender_id, [])

                # Giới hạn queue phòng lỗi
                while len(pending_questions) > 100:
                    pending_questions.popleft()

            # Không log nội dung/PII
            print(
                "ZALO QUESTION RECEIVED: YES",
                "LENGTH:", len(text),
                "QUEUE:", len(pending_questions),
                flush=True
            )

    return jsonify({"success": True}), 200


# =========================================================
# DYNAMIC API -> RAG -> GROQ
# =========================================================

@app.route("/zalo/ai", methods=["GET", "POST"])
def zalo_ai():
    item = pop_pending_question()

    if not item:
        return chatbot_response(
            "Anh/chị vui lòng nhập nội dung cần hỗ trợ."
        )

    sender_id = item["sender_id"]
    question = item["text"]

    with state_lock:
        history = list(
            conversation_history.get(sender_id, [])
        )

    try:
        answer, trace = ask_groq(question, history)

        with state_lock:
            conversation_history.setdefault(sender_id, [])
            conversation_history[sender_id].extend([
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ])
            conversation_history[sender_id] = (
                conversation_history[sender_id][-MAX_HISTORY_MESSAGES:]
            )

        print(
            "AI ANSWER: SUCCESS",
            "LEGAL:", trace["legal_mode"],
            "WEB_REQUIRED:", trace["web_required"],
            "WEB_USED:", trace.get("web_used", False),
            "DOMAINS:", ",".join(trace["domains"]),
            "CHUNKS:", ",".join(trace["chunks"]),
            flush=True
        )

        return chatbot_response(answer)

    except requests.exceptions.Timeout:
        print("AI ERROR: TIMEOUT", flush=True)

        return chatbot_response(
            "Hệ thống đang truy xuất dữ liệu cập nhật hơi lâu. "
            "Anh/chị vui lòng gửi lại câu hỏi sau ít giây."
        )

    except requests.exceptions.HTTPError as e:
        status = (
            e.response.status_code
            if e.response is not None
            else "UNKNOWN"
        )

        print(
            "AI HTTP ERROR:",
            status,
            flush=True
        )

        return chatbot_response(
            "Trợ lý AI hiện chưa truy xuất được dữ liệu. "
            "Anh/chị vui lòng thử lại."
        )

    except Exception as e:
        print(
            "AI ERROR:",
            type(e).__name__,
            flush=True
        )

        return chatbot_response(
            "Hệ thống trợ lý đang tạm thời gián đoạn. "
            "Anh/chị vui lòng thử lại."
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
