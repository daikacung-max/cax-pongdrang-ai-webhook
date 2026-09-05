from flask import Flask, request, jsonify
from pathlib import Path
from threading import Lock, Thread
from queue import Queue, Empty
import json
import os
import re
import time
import unicodedata
import requests

app = Flask(__name__)

# =========================================================
# CẤU HÌNH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
KB_FILE = BASE_DIR / "knowledge_base.json"

GROQ_API_KEY = "".join(
    (os.getenv("GROQ_API_KEY") or "").split()
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model chất lượng cao
AI_MODEL = "openai/gpt-oss-120b"

# Trí nhớ hội thoại
MAX_HISTORY_MESSAGES = 8

# Câu trả lời Zalo: ngắn gọn, đúng trọng tâm
MAX_ANSWER_CHARS = 1000

# Worker được phép suy luận lâu hơn vì chạy ngay từ Webhook,
# không nằm trong request Dynamic API.
AI_TIMEOUT_SECONDS = 15.0


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
    "SYSTEM READY:",
    "GROQ:", bool(GROQ_API_KEY),
    "KB:", bool(CHUNKS),
    "CHUNKS:", len(CHUNKS),
    "SOURCES:", len(SOURCES),
    flush=True
)


# =========================================================
# BỘ NHỚ VÀ HÀNG ĐỢI
# =========================================================

conversation_history = {}

work_queue = Queue()
completed_queue = Queue()

state_lock = Lock()


# =========================================================
# CHUẨN HÓA VĂN BẢN
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
    "toi", "ban", "anh", "chi", "la", "va", "voi",
    "cua", "co", "khong", "duoc", "cho", "ve",
    "thi", "the", "nao", "gi", "can", "muon",
    "hoi", "mot", "nhung", "cac", "nay", "do",
    "o", "tai", "den", "tu", "khi"
}


def tokens(text):
    return {
        word
        for word in normalize_text(text).split()
        if len(word) >= 2 and word not in STOP_WORDS
    }


# =========================================================
# PHÂN LOẠI LĨNH VỰC
# =========================================================

def detect_domains(question):
    q = normalize_text(question)
    matched = []

    for rule in ROUTER.get("rules", []):
        score = 0

        for keyword in rule.get("keywords", []):
            kw = normalize_text(keyword)

            if kw and kw in q:
                score += max(2, len(kw.split()))

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


def is_legal_question(question, domains):
    if any(domain in LEGAL_DOMAINS for domain in domains):
        return True

    q = normalize_text(question)

    keywords = [
        "cong an",
        "phap luat",
        "dieu luat",
        "nghi dinh",
        "thong tu",
        "xu phat",
        "toi pham",
        "khoi to",
        "to giac",
        "tam tru",
        "can cuoc",
        "vneid",
        "ma tuy",
        "dat dai",
        "dang ky xe",
        "pccc",
    ]

    return any(word in q for word in keywords)


# =========================================================
# RAG — TÌM KIẾN KHO TRI THỨC
# =========================================================

def chunk_score(question, chunk, domains):
    q_normalized = normalize_text(question)
    q_tokens = tokens(question)

    title = normalize_text(
        chunk.get("title", "")
    )

    content = normalize_text(
        chunk.get("content", "")
    )

    keyword_text = " ".join(
        normalize_text(x)
        for x in chunk.get("keywords", [])
    )

    chunk_tokens = tokens(
        title + " " + keyword_text + " " + content
    )

    score = 0.0

    score += len(q_tokens & chunk_tokens) * 2.2

    for keyword in chunk.get("keywords", []):
        kw = normalize_text(keyword)

        if kw and kw in q_normalized:
            score += 5.0

    if chunk.get("domain") in domains:
        score += 5.0

    for word in q_tokens:
        if word in title:
            score += 0.8

    return score


def retrieve_chunks(question, domains, top_k=8):
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


def format_rag_context(chunks_found):
    blocks = []

    for chunk in chunks_found:
        source_lines = []

        for source_id in chunk.get(
            "source_ids",
            []
        ):
            source = SOURCES.get(
                str(source_id)
            )

            if not source:
                continue

            source_lines.append(
                f"{source_id}: "
                f"{source.get('title', '')}; "
                f"{source.get('number', '')}; "
                f"{source.get('issuer', '')}; "
                f"trạng thái: "
                f"{source.get('effective_status', '')}; "
                f"kiểm tra: "
                f"{source.get('checked_at', '')}"
            )

        blocks.append(
            "\n".join([
                f"[{chunk.get('id', '')}]",
                f"Tiêu đề: {chunk.get('title', '')}",
                f"Nội dung: {chunk.get('content', '')}",
                "Nguồn:",
                *source_lines
            ])
        )

    return "\n\n".join(blocks)


# =========================================================
# NHẬN BIẾT THÔNG TIN CÓ TÍNH THỜI ĐIỂM
# =========================================================

FRESHNESS_WORDS = [
    "hom nay",
    "hien nay",
    "hien tai",
    "bay gio",
    "moi nhat",
    "cap nhat",
    "con hieu luc",
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
]


def needs_freshness_warning(
    question,
    chunks_found
):
    q = normalize_text(question)

    if any(
        word in q
        for word in FRESHNESS_WORDS
    ):
        return True

    years = re.findall(
        r"\b20\d{2}\b",
        q
    )

    if any(
        int(year) >= 2026
        for year in years
    ):
        return True

    if any(
        chunk.get("requires_live_check")
        for chunk in chunks_found
    ):
        detail_words = [
            "dieu",
            "khoan",
            "diem",
            "phat",
            "thoi han",
            "tham quyen",
            "ho so",
            "le phi",
            "hieu luc",
            "can cu",
        ]

        if any(
            word in q
            for word in detail_words
        ):
            return True

    return False


# =========================================================
# PROMPT CHẤT LƯỢNG CAO
# =========================================================

GENERAL_STYLE_PROMPT = """
Bạn là TRỢ LÝ AI CÔNG AN XÃ PƠNG DRANG, TỈNH ĐẮK LẮK.

MỤC TIÊU:
Trả lời linh hoạt tất cả câu hỏi hợp pháp như một trợ lý AI đa năng,
nhưng giữ phong thái chuyên nghiệp, chuẩn mực, chín chắn và dễ hiểu.

PHONG CÁCH BẮT BUỘC:
- Tiếng Việt tự nhiên, thuần thục, đúng ngữ pháp.
- Câu chữ gọn, mạch lạc, đúng trọng tâm.
- Không nói vòng vo, không lặp ý, không viết bài quá dài.
- Không dùng giọng máy móc hoặc khuôn mẫu cứng nhắc.
- Không lạm dụng tiêu đề.
- Không mở đầu bằng lời chào ở mọi câu trả lời.
- Không dùng quá nhiều biểu tượng.
- Không nói “theo tôi”, “có lẽ” nếu đang trả lời nội dung pháp lý cần căn cứ.
- Nếu câu hỏi đơn giản: trả lời thẳng trong 1–3 câu.
- Nếu câu hỏi phức tạp: kết luận ngắn trước, sau đó tối đa 3–4 ý chính.
- Độ dài mục tiêu khoảng 250–800 ký tự; chỉ dài hơn khi thật sự cần.

PHONG CÁCH CÔNG AN:
- Với nội dung thuộc pháp luật, ANTT, TTHC hoặc nghiệp vụ phục vụ Nhân dân,
  sử dụng giọng văn chuẩn mực, rõ trách nhiệm, không đe dọa, không khoa trương.
- Có thể dùng: “Công an xã Pơng Drang hướng dẫn như sau:” khi phù hợp,
  nhưng không bắt buộc lặp ở mọi câu.
- Dùng “anh/chị” khi hướng dẫn người dân.
- Không tự nhận mình là người có thẩm quyền ra quyết định.

CÂU HỎI NGOÀI LĨNH VỰC CÔNG AN:
- Vẫn trả lời bình thường về kiến thức, học tập, công nghệ, đời sống,
  soạn thảo và các chủ đề hợp pháp khác.
- Không ép câu trả lời phổ thông thành văn bản hành chính.

CHẤT LƯỢNG:
- Phân tích kỹ trong nội bộ trước khi trả lời.
- Tự kiểm tra lại kết luận.
- Không trình bày chuỗi suy luận nội bộ.
- Chỉ xuất câu trả lời cuối cùng, súc tích và đã được kiểm tra.
"""


def build_prompt(
    question,
    legal_mode,
    rag_context,
    freshness_needed
):
    prompt = GENERAL_STYLE_PROMPT

    if legal_mode:
        prompt += "\n\n" + KB_SYSTEM_PROMPT

        prompt += """
QUY TẮC PHÁP LÝ:
- Ưu tiên Knowledge Base được cung cấp.
- Không bịa điều, khoản, văn bản, mức phạt, lệ phí, thời hạn hoặc thẩm quyền.
- Không kết luận một người có tội chỉ từ thông tin một phía.
- Nếu thiếu dữ kiện, nói rõ dữ kiện nào cần bổ sung.
- Khi KB có nguồn, nêu căn cứ ngắn gọn, không chép dài.
"""

    if rag_context:
        prompt += """
\nKNOWLEDGE BASE LIÊN QUAN:
Dữ liệu dưới đây đã được truy xuất cho câu hỏi này.
Nếu kiến thức nền khác với dữ liệu này, ưu tiên Knowledge Base.
"""
        prompt += "\n" + rag_context

    if freshness_needed:
        prompt += f"""
\nLƯU Ý TÍNH CẬP NHẬT:
Knowledge Base được kiểm tra đến {VERSION.get('as_of', 'không rõ')}.
Nếu câu hỏi phụ thuộc dữ liệu có thể thay đổi sau mốc này,
chỉ khẳng định phần đã có căn cứ. Phần chưa chắc chắn phải nói rõ
cần kiểm tra nguồn chính thức, tuyệt đối không tự đoán.
"""

    return prompt


# =========================================================
# RÚT GỌN VÀ CHIA CÂU TRẢ LỜI CHO ZALO
# =========================================================

def smart_trim(text, max_chars=MAX_ANSWER_CHARS):
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        str(text or "").strip()
    )

    if len(text) <= max_chars:
        return text

    clipped = text[:max_chars]

    # Cắt ở dấu kết thúc câu gần nhất
    positions = [
        clipped.rfind(". "),
        clipped.rfind("? "),
        clipped.rfind("! "),
        clipped.rfind("\n"),
    ]

    cut = max(positions)

    if cut >= int(max_chars * 0.65):
        clipped = clipped[:cut + 1]

    return clipped.rstrip() + "…"


def split_smooth_messages(
    text,
    max_messages=3,
    target_chars=360
):
    """
    Zalo Dynamic không stream token như ChatGPT.
    Hàm này chia câu trả lời thành 1–3 bong bóng ngắn,
    để trải nghiệm đọc mềm và tự nhiên hơn.
    """
    text = text.strip()

    if len(text) <= target_chars:
        return [text]

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    units = []

    for paragraph in paragraphs:
        if len(paragraph) <= target_chars:
            units.append(paragraph)
            continue

        sentences = re.split(
            r"(?<=[.!?])\s+",
            paragraph
        )

        current = ""

        for sentence in sentences:
            candidate = (
                sentence
                if not current
                else current + " " + sentence
            )

            if (
                len(candidate) <= target_chars
                or not current
            ):
                current = candidate
            else:
                units.append(current.strip())
                current = sentence

        if current.strip():
            units.append(current.strip())

    if len(units) <= max_messages:
        return units

    # Gộp phần còn lại vào bong bóng cuối
    result = units[:max_messages - 1]
    tail = " ".join(
        units[max_messages - 1:]
    ).strip()

    result.append(
        smart_trim(
            tail,
            max_chars=target_chars * 2
        )
    )

    return result


def chatbot_response(text):
    parts = split_smooth_messages(
        smart_trim(text)
    )

    return jsonify({
        "version": "chatbot",
        "content": {
            "messages": [
                {
                    "type": "text",
                    "text": part
                }
                for part in parts
            ]
        }
    }), 200


# =========================================================
# GỌI GROQ — REASONING HIGH
# =========================================================

def ask_groq(question, history):
    domains = detect_domains(question)

    legal_mode = is_legal_question(
        question,
        domains
    )

    chunks_found = (
        retrieve_chunks(
            question,
            domains,
            top_k=8
        )
        if legal_mode
        else []
    )

    rag_context = format_rag_context(
        chunks_found
    )

    freshness_needed = (
        needs_freshness_warning(
            question,
            chunks_found
        )
    )

    system_prompt = build_prompt(
        question,
        legal_mode,
        rag_context,
        freshness_needed
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(
        history[-MAX_HISTORY_MESSAGES:]
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
        "model": AI_MODEL,
        "messages": messages,
        "temperature":
            0.10 if legal_mode else 0.35,
        "max_completion_tokens": 650,
        "reasoning_effort": "high",
        "include_reasoning": False,
    }

    started = time.time()

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=AI_TIMEOUT_SECONDS
    )

    elapsed = round(
        time.time() - started,
        2
    )

    if response.status_code >= 400:
        try:
            data = response.json()

            error_message = (
                data.get("error", {})
                .get("message")
            )
        except Exception:
            error_message = (
                response.text[:300]
            )

        print(
            "GROQ ERROR:",
            response.status_code,
            str(error_message)[:300],
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
        raise RuntimeError(
            "AI không trả về nội dung"
        )

    answer = smart_trim(answer)

    trace = {
        "domains": domains,
        "legal_mode": legal_mode,
        "freshness_needed": freshness_needed,
        "chunks": [
            chunk.get("id")
            for chunk in chunks_found
        ],
        "seconds": elapsed,
    }

    return answer, trace


# =========================================================
# WORKER AI XỬ LÝ NỀN
# =========================================================

def ai_worker():
    while True:
        item = work_queue.get()

        try:
            sender_id = item["sender_id"]
            question = item["text"]

            with state_lock:
                history = list(
                    conversation_history.get(
                        sender_id,
                        []
                    )
                )

            answer, trace = ask_groq(
                question,
                history
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
                ] = conversation_history[
                    sender_id
                ][-MAX_HISTORY_MESSAGES:]

            completed_queue.put({
                "sender_id": sender_id,
                "answer": answer,
                "trace": trace,
            })

            print(
                "AI READY:",
                "SECONDS:",
                trace["seconds"],
                "LEGAL:",
                trace["legal_mode"],
                "FRESHNESS:",
                trace["freshness_needed"],
                "DOMAINS:",
                ",".join(trace["domains"]),
                "CHUNKS:",
                ",".join(trace["chunks"]),
                flush=True
            )

        except requests.exceptions.Timeout:
            print(
                "AI WORKER TIMEOUT",
                flush=True
            )

            completed_queue.put({
                "sender_id":
                    item.get("sender_id", ""),
                "answer":
                    "Hệ thống đang cần thêm thời gian "
                    "để phân tích nội dung. "
                    "Anh/chị vui lòng thử lại sau ít giây.",
                "trace": {},
            })

        except requests.exceptions.HTTPError as e:
            status = (
                e.response.status_code
                if e.response is not None
                else "UNKNOWN"
            )

            print(
                "AI WORKER HTTP ERROR:",
                status,
                flush=True
            )

            completed_queue.put({
                "sender_id":
                    item.get("sender_id", ""),
                "answer":
                    "Trợ lý AI hiện chưa xử lý được "
                    "nội dung này. Anh/chị vui lòng thử lại.",
                "trace": {},
            })

        except Exception as e:
            print(
                "AI WORKER ERROR:",
                type(e).__name__,
                flush=True
            )

            completed_queue.put({
                "sender_id":
                    item.get("sender_id", ""),
                "answer":
                    "Hệ thống trợ lý đang tạm thời "
                    "gián đoạn. Anh/chị vui lòng thử lại.",
                "trace": {},
            })

        finally:
            work_queue.task_done()


Thread(
    target=ai_worker,
    daemon=True,
    name="cax-pongdrang-ai-worker"
).start()


# =========================================================
# HOME / HEALTH
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
<p>RAG Quality v1.5</p>
</body>
</html>
""", 200, {
        "Content-Type":
            "text/html; charset=utf-8"
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "groq": bool(GROQ_API_KEY),
        "kb_loaded": bool(CHUNKS),
        "kb_version":
            VERSION.get("version"),
        "kb_as_of":
            VERSION.get("as_of"),
        "chunks": len(CHUNKS),
        "sources": len(SOURCES),
        "model": AI_MODEL,
        "reasoning_effort": "high",
        "mode": "background_reasoning",
        "response_style":
            "concise_police_professional",
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
        ) or {}
    )

    if (
        data.get("event_name")
        == "user_send_text"
    ):
        sender = (
            data.get("sender") or {}
        )

        message = (
            data.get("message") or {}
        )

        sender_id = str(
            sender.get("id") or ""
        ).strip()

        text = str(
            message.get("text") or ""
        ).strip()

        msg_id = str(
            message.get("msg_id") or ""
        ).strip()

        if sender_id and text:
            with state_lock:
                conversation_history.setdefault(
                    sender_id,
                    []
                )

            work_queue.put({
                "sender_id": sender_id,
                "msg_id": msg_id,
                "text": text,
                "time": time.time(),
            })

            print(
                "QUESTION RECEIVED:",
                "YES",
                "LENGTH:",
                len(text),
                "QUEUE:",
                work_queue.qsize(),
                flush=True
            )

    return jsonify({
        "success": True
    }), 200


# =========================================================
# ZALO DYNAMIC
# =========================================================

@app.route(
    "/zalo/ai",
    methods=["GET", "POST"]
)
def zalo_ai():
    try:
        # Dynamic chỉ lấy kết quả đã suy luận ở nền.
        # Chờ ngắn để vẫn nằm trong giới hạn Zalo.
        result = completed_queue.get(
            timeout=1.20
        )

        answer = result.get(
            "answer",
            "Anh/chị vui lòng gửi lại câu hỏi."
        )

        trace = (
            result.get("trace")
            or {}
        )

        print(
            "DYNAMIC READY:",
            "AI_SECONDS:",
            trace.get("seconds"),
            flush=True
        )

        completed_queue.task_done()

        return chatbot_response(answer)

    except Empty:
        print(
            "DYNAMIC NOT READY",
            flush=True
        )

        return chatbot_response(
            "🤖 Trợ lý AI vẫn đang phân tích "
            "và đối chiếu thông tin. "
            "Anh/chị vui lòng chờ thêm ít giây."
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
