from flask import Flask, request, jsonify
from pathlib import Path
from collections import deque
from threading import Lock
import json, os, re, time, unicodedata, requests

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
KB_FILE = BASE_DIR / "knowledge_base.json"

GROQ_API_KEY = "".join((os.getenv("GROQ_API_KEY") or "").split())
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GENERAL_MODEL = "openai/gpt-oss-20b"
GROQ_TIMEOUT_SECONDS = 1.45

MAX_ZALO_MESSAGES = 4
TARGET_MESSAGE_CHARS = 650
MAX_TOTAL_CHARS = 2400
MAX_HISTORY_MESSAGES = 4
PENDING_TTL_SECONDS = 25

HTTP = requests.Session()

try:
    KB = json.loads(KB_FILE.read_text(encoding="utf-8"))
except Exception:
    KB = {}

VERSION = KB.get("version", {})
SYSTEM_PROMPT = KB.get("system_prompt", "")
SOURCES = {str(x.get("id")): x for x in KB.get("sources", []) if x.get("id")}
CHUNKS = KB.get("chunks", [])
ROUTER = KB.get("router", {"rules": []})

conversation_history = {}
pending_questions = deque()
seen_message_ids = {}
state_lock = Lock()

def normalize_text(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

STOP = {
    "toi","ban","anh","chi","la","va","voi","cua","co","khong","duoc","cho","ve",
    "thi","the","nao","gi","can","muon","hoi","mot","nhung","cac","nay","do","o",
    "tai","den","tu","khi","lam","xin"
}

def token_set(text):
    return {w for w in normalize_text(text).split() if len(w) >= 2 and w not in STOP}

def clean_plain_text(text):
    text = str(text or "").strip()
    for mark in ("```","**","__","`","*"):
        text = text.replace(mark, "")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def split_zalo_messages(text):
    text = clean_plain_text(text)
    if len(text) > MAX_TOTAL_CHARS:
        cut = text[:MAX_TOTAL_CHARS]
        pos = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cut.rfind("; "), cut.rfind("\n"))
        text = cut[:pos+1].strip() if pos > int(MAX_TOTAL_CHARS*0.6) else cut.strip()

    if len(text) <= TARGET_MESSAGE_CHARS:
        return [text]

    sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
    units, current = [], ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        candidate = s if not current else current + " " + s
        if len(candidate) <= TARGET_MESSAGE_CHARS:
            current = candidate
        else:
            if current:
                units.append(current)
            current = s
    if current:
        units.append(current)

    if len(units) <= MAX_ZALO_MESSAGES:
        return units

    result = units[:MAX_ZALO_MESSAGES-1]
    tail = " ".join(units[MAX_ZALO_MESSAGES-1:])
    if len(tail) > int(TARGET_MESSAGE_CHARS*1.3):
        tail = tail[:int(TARGET_MESSAGE_CHARS*1.3)]
        p = max(tail.rfind(". "), tail.rfind("? "), tail.rfind("! "), tail.rfind("; "))
        if p > 350:
            tail = tail[:p+1]
    result.append(tail.strip())
    return result[:MAX_ZALO_MESSAGES]

def chatbot_response(text):
    parts = [p for p in split_zalo_messages(text) if p]
    return jsonify({
        "version": "chatbot",
        "content": {"messages": [{"type":"text","text":p} for p in parts]}
    }), 200

def detect_domains(question):
    q = normalize_text(question)
    found = []
    for rule in ROUTER.get("rules", []):
        score = 0
        for kw in rule.get("keywords", []):
            n = normalize_text(kw)
            if n and n in q:
                score += max(3, len(n.split())*2)
        if score:
            found.append((score, rule.get("domain","")))
    found.sort(reverse=True)
    return [d for _,d in found[:3] if d]

LEGAL_DOMAINS = {
    "cu_tru","dang_ky_xe","can_cuoc","vneid","to_tung_hinh_su","hinh_su",
    "xu_ly_vphc","ma_tuy","giao_thong","dat_dai","pccc","vu_khi",
    "khieu_nai_to_cao","nguoi_chua_thanh_nien","an_ninh_mang","bi_mat_nha_nuoc",
    "thi_hanh_an_hinh_su","tam_giu_tam_giam"
}

LEGAL_HINTS = [
    "phap luat","dieu luat","nghi dinh","thong tu","bo luat","luat ",
    "xu phat","muc phat","tham quyen","thu tuc","cong an","khoi to",
    "toi pham","to giac","can cuoc","tam tru","thuong tru","dang ky xe","vneid"
]

def is_legal(question, domains):
    if any(d in LEGAL_DOMAINS for d in domains):
        return True
    q = normalize_text(question)
    return any(x in q for x in LEGAL_HINTS)

def chunk_score(question, chunk, domains):
    qn = normalize_text(question)
    qt = token_set(question)
    score = 0.0

    if chunk.get("domain") in domains:
        score += 8.0

    for p in chunk.get("exact_patterns", []):
        pn = normalize_text(p)
        if pn and (pn in qn or qn in pn):
            score += 35.0
        else:
            pt = token_set(p)
            if pt:
                overlap = len(qt & pt) / max(1, len(pt))
                if overlap >= 0.75:
                    score += 22.0
                elif overlap >= 0.5:
                    score += 10.0

    for kw in chunk.get("keywords", []):
        kn = normalize_text(kw)
        if kn and kn in qn:
            score += 7.0
        kt = token_set(kw)
        if kt:
            score += len(qt & kt) * 1.5

    title_tokens = token_set(chunk.get("title",""))
    answer_tokens = token_set(chunk.get("verified_answer",""))
    score += len(qt & title_tokens) * 2.5
    score += len(qt & answer_tokens) * 0.5
    return score

def retrieve_verified(question, domains, top_k=3):
    ranked = []
    for ch in CHUNKS:
        s = chunk_score(question, ch, domains)
        if s > 0:
            ranked.append((s, ch))
    ranked.sort(key=lambda x:x[0], reverse=True)
    return ranked[:top_k]

def source_labels(chunk):
    labels = []
    for sid in chunk.get("source_ids", []):
        src = SOURCES.get(str(sid))
        if not src:
            continue
        num = src.get("number","")
        title = src.get("title","")
        labels.append((num + " " + title).strip())
    return labels

def deterministic_answer(question, ranked):
    if not ranked:
        return None

    score, best = ranked[0]
    if not best.get("answerable", False):
        return None

    # Chỉ dùng câu trả lời đóng khi độ khớp cao.
    if score >= 22:
        return clean_plain_text(best.get("verified_answer",""))
    return None

def verified_context(ranked):
    blocks = []
    for score, ch in ranked:
        if score < 12 or not ch.get("answerable", False):
            continue
        facts = ch.get("verified_facts") or []
        refs = ch.get("article_refs") or []
        blocks.append(
            "CHUNK " + str(ch.get("id")) + "\n"
            "ĐIỂM KHỚP: " + str(round(score,1)) + "\n"
            "NỘI DUNG ĐÃ XÁC MINH: " + str(ch.get("verified_answer","")) + "\n"
            "SỰ KIỆN ĐÃ XÁC MINH: " + " | ".join(facts) + "\n"
            "CĂN CỨ ĐƯỢC PHÉP NÊU: " + " | ".join(refs) + "\n"
            "CẤM SUY DIỄN: " + " | ".join(ch.get("prohibited_claims") or [])
        )
    return "\n\n".join(blocks)

SAFE_REFUSAL = (
    "Nội dung này hiện chưa có căn cứ đủ chi tiết đã được xác minh trong cơ sở tri thức của hệ thống. "
    "Để tránh cung cấp sai quy định, Công an xã Pơng Drang đề nghị anh/chị nêu rõ tình huống cụ thể "
    "hoặc liên hệ cán bộ phụ trách/tra cứu nguồn chính thức của Bộ Công an. Hệ thống không tự suy đoán điều luật, "
    "mức phạt, thời hạn, lệ phí hoặc thẩm quyền khi chưa có nguồn đã xác minh."
)

def ask_general(question, history):
    if not GROQ_API_KEY:
        return "Dịch vụ AI hiện chưa được cấu hình."
    prompt = (
        "Bạn là Trợ lý AI Công an xã Pơng Drang. Với câu hỏi không thuộc pháp luật, trả lời bằng tiếng Việt tự nhiên, "
        "ngắn gọn, đúng trọng tâm, lịch sự. Không dùng Markdown, không dùng dấu *. "
        "Không tự biến câu hỏi phổ thông thành văn bản hành chính."
    )
    messages = [{"role":"system","content":prompt}]
    messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role":"user","content":question})
    payload = {
        "model": GENERAL_MODEL, "messages": messages, "temperature": 0.3,
        "max_completion_tokens": 320, "reasoning_effort":"low"
    }
    r = HTTP.post(GROQ_URL, headers={
        "Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"
    }, json=payload, timeout=GROQ_TIMEOUT_SECONDS)
    r.raise_for_status()
    return clean_plain_text(r.json()["choices"][0]["message"]["content"])

def ask_legal_locked(question, history, ranked):
    fixed = deterministic_answer(question, ranked)
    if fixed:
        return fixed, "deterministic"

    context = verified_context(ranked)
    if not context:
        return SAFE_REFUSAL, "refusal"

    if not GROQ_API_KEY:
        # Không có model thì trả chunk tốt nhất thay vì tự sáng tạo.
        for _, ch in ranked:
            if ch.get("answerable"):
                return clean_plain_text(ch.get("verified_answer","")), "kb_only"
        return SAFE_REFUSAL, "refusal"

    prompt = (
        SYSTEM_PROMPT + "\n\n"
        "NHIỆM VỤ LẦN NÀY: Chỉ được diễn đạt lại dữ liệu trong VERIFIED_CONTEXT. "
        "Không được thêm bất kỳ quy định pháp luật nào từ trí nhớ riêng. "
        "Nếu câu hỏi vượt quá dữ liệu, hãy nói phần nào chưa đủ căn cứ. "
        "Không dùng Markdown.\n\nVERIFIED_CONTEXT:\n" + context
    )
    messages = [{"role":"system","content":prompt}]
    # Pháp lý không đưa câu trả lời cũ của model vào làm nguồn pháp luật.
    messages.append({"role":"user","content":question})
    payload = {
        "model": GENERAL_MODEL, "messages": messages, "temperature":0.0,
        "max_completion_tokens":420, "reasoning_effort":"low"
    }
    r = HTTP.post(GROQ_URL, headers={
        "Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"
    }, json=payload, timeout=GROQ_TIMEOUT_SECONDS)
    r.raise_for_status()
    answer = clean_plain_text(r.json()["choices"][0]["message"]["content"])
    return answer, "source_locked_model"

def purge_state(now=None):
    now = now or time.time()
    while pending_questions and now - pending_questions[0].get("time",0) > PENDING_TTL_SECONDS:
        pending_questions.popleft()
    for mid, ts in list(seen_message_ids.items()):
        if now-ts > 120:
            seen_message_ids.pop(mid, None)

@app.route("/", methods=["GET"])
def home():
    return "CAX Pơng Drang Legal Verified V3", 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":"ok",
        "mode":"legal_verified_v3",
        "kb_version":VERSION.get("version"),
        "verified_at":VERSION.get("verified_at"),
        "source_locked_legal":True,
        "fail_closed":True,
        "upcoming_excluded":bool(VERSION.get("upcoming_excluded")),
        "chunks":len(CHUNKS),
        "answerable_chunks":sum(1 for x in CHUNKS if x.get("answerable")),
        "sources":len(SOURCES),
        "groq":bool(GROQ_API_KEY),
        "general_model":GENERAL_MODEL,
        "web_search_runtime":False,
        "max_messages":MAX_ZALO_MESSAGES
    }), 200

@app.route("/zalo/webhook", methods=["GET","POST"])
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
                    return jsonify({"success":True,"duplicate":True}), 200
                if msg_id:
                    seen_message_ids[msg_id] = time.time()
                pending_questions.append({
                    "sender_id":sender_id, "text":text, "msg_id":msg_id, "time":time.time()
                })
                conversation_history.setdefault(sender_id, [])
                while len(pending_questions) > 50:
                    pending_questions.popleft()
            print("QUESTION RECEIVED LEN:", len(text), flush=True)
    return jsonify({"success":True}), 200

@app.route("/zalo/ai", methods=["GET","POST"])
def zalo_ai():
    with state_lock:
        purge_state()
        item = pending_questions.popleft() if pending_questions else None

    if not item:
        return chatbot_response("Anh/chị vui lòng nhập nội dung cần hỗ trợ.")

    sender_id = item["sender_id"]
    question = item["text"]
    domains = detect_domains(question)
    legal = is_legal(question, domains)

    try:
        if legal:
            ranked = retrieve_verified(question, domains)
            answer, mode = ask_legal_locked(question, [], ranked)
            print(
                "LEGAL ANSWER MODE:", mode,
                "DOMAINS:", ",".join(domains),
                "TOP:", ranked[0][1].get("id") if ranked else "NONE",
                "SCORE:", round(ranked[0][0],1) if ranked else 0,
                flush=True
            )
        else:
            with state_lock:
                history = list(conversation_history.get(sender_id, []))
            answer = ask_general(question, history)
            mode = "general_model"

        with state_lock:
            conversation_history.setdefault(sender_id, [])
            conversation_history[sender_id].extend([
                {"role":"user","content":question},
                {"role":"assistant","content":answer}
            ])
            conversation_history[sender_id] = conversation_history[sender_id][-MAX_HISTORY_MESSAGES:]

        return chatbot_response(answer)

    except requests.exceptions.RequestException as e:
        print("AI REQUEST ERROR:", type(e).__name__, flush=True)
        if legal:
            ranked = retrieve_verified(question, domains)
            fixed = deterministic_answer(question, ranked)
            if fixed:
                return chatbot_response(fixed)
            for score, ch in ranked:
                if score >= 12 and ch.get("answerable"):
                    return chatbot_response(ch.get("verified_answer",""))
            return chatbot_response(SAFE_REFUSAL)
        return chatbot_response("Trợ lý AI hiện chưa kết nối được dịch vụ xử lý. Anh/chị vui lòng thử lại.")

    except Exception as e:
        print("AI ERROR:", type(e).__name__, flush=True)
        return chatbot_response(SAFE_REFUSAL if legal else "Trợ lý AI hiện chưa xử lý được yêu cầu này.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
