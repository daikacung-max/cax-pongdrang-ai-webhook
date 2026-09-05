from flask import Flask, request, jsonify
from pathlib import Path
from collections import deque
from threading import Lock
import json, os, re, time, unicodedata, requests

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
KB = json.loads((BASE_DIR/"knowledge_base.json").read_text(encoding="utf-8"))

UNIT = KB["unit"]["name"]
HOTLINE = KB["unit"]["hotline"]
VERSION = KB["version"]
SOURCES = {x["id"]:x for x in KB.get("sources",[])}
EXACT = KB.get("exact_articles",{})
CARDS = KB.get("cards",[])

BLHS_INDEX_FILE = BASE_DIR / "source_index" / "Bộ luật Hình sự năm 2025 - chỉ mục điều luật.json"
try:
    BLHS_INDEX = json.loads(BLHS_INDEX_FILE.read_text(encoding="utf-8"))
    BLHS_ARTICLES = {
        str(item.get("article")): item
        for item in BLHS_INDEX.get("articles", [])
        if item.get("article")
    }
except Exception:
    BLHS_INDEX = {}
    BLHS_ARTICLES = {}

GROQ_API_KEY = "".join((os.getenv("GROQ_API_KEY") or "").split())
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
TIMEOUT = 1.45

MAX_HISTORY = 6
MAX_MESSAGES = 4
TARGET_CHARS = 620
MAX_TOTAL = 2350
PENDING_TTL = 25

HTTP = requests.Session()
pending_questions = deque()
conversation_history = {}
seen_ids = {}
state_lock = Lock()

def norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ","d")
    text = re.sub(r"[^a-z0-9\s]"," ",text)
    return re.sub(r"\s+"," ",text).strip()

def clean(text):
    text = str(text or "").strip()
    for mark in ("```","**","__","`","*"):
        text = text.replace(mark,"")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*","",text)
    text = re.sub(r"(?m)^\s*>\s?","",text)
    text = text.replace("Cục Công an xã Pơng Drang", "Công an xã Pơng Drang")
    text = text.replace("Cục Công an xã", "Công an xã")
    text = text.replace("Công an xã Pơng Drang tỉnh Đắk Lắk", "Công an xã Pơng Drang, tỉnh Đắk Lắk")
    text = re.sub(r"[ \t]+"," ",text)
    text = re.sub(r"\n{3,}","\n\n",text)
    return text.strip()

def split_messages(text):
    text = clean(text)
    if len(text) > MAX_TOTAL:
        text = text[:MAX_TOTAL]
        p = max(text.rfind(". "), text.rfind("? "), text.rfind("! "), text.rfind("; "), text.rfind("\n"))
        if p > 1200:
            text = text[:p+1]
    if len(text) <= TARGET_CHARS:
        return [text]
    sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
    out, cur = [], ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        candidate = s if not cur else cur + " " + s
        if len(candidate) <= TARGET_CHARS:
            cur = candidate
        else:
            if cur: out.append(cur)
            cur = s
    if cur: out.append(cur)
    if len(out) <= MAX_MESSAGES:
        return out
    result = out[:MAX_MESSAGES-1]
    result.append(" ".join(out[MAX_MESSAGES-1:])[:820].strip())
    return result[:MAX_MESSAGES]

def chatbot_response(text):
    return jsonify({
        "version":"chatbot",
        "content":{"messages":[{"type":"text","text":x} for x in split_messages(text) if x]}
    }),200

def detect_law(question):
    q = norm(question)
    if any(x in q for x in ["bo luat hinh su","blhs","hinh su"]):
        return "BLHS"
    if any(x in q for x in ["bo luat to tung hinh su","bltths","to tung hinh su"]):
        return "BLTTHS"
    if any(x in q for x in ["luat xu ly vi pham hanh chinh","xlvphc","vi pham hanh chinh"]):
        return "XLVPHC"
    return None

DEFAULT_ARTICLE_LAW = {
    "133":"BLHS","134":"BLHS","140":"BLHS","173":"BLHS","174":"BLHS",
    "175":"BLHS","178":"BLHS","256a":"BLHS","318":"BLHS",
    "145":"BLTTHS","146":"BLTTHS"
}

def exact_article_answer(question):
    q = norm(question)
    m = re.search(r"\bdieu\s+(\d+[a-z]?)\b", q)
    if not m:
        return None

    art = m.group(1)
    law = detect_law(question) or DEFAULT_ARTICLE_LAW.get(art)

    # BLHS: LUÔN ưu tiên chỉ mục được trích trực tiếp từ PDF toàn văn.
    if law == "BLHS" and art in BLHS_ARTICLES:
        item = BLHS_ARTICLES[art]
        title = clean(item.get("title", ""))
        raw = clean(item.get("raw_text", ""))

        if not raw:
            return f"Điều {art} Bộ luật Hình sự: {title}."

        # Khi người dân chỉ hỏi "Điều X là tội gì/quy định gì", trả đúng tên Điều trước.
        short_query = any(x in q for x in [
            "toi gi", "quy dinh gi", "la gi", "ten toi", "noi dung dieu"
        ])

        if short_query:
            return (
                f"Điều {art} Bộ luật Hình sự: {title}. "
                f"Nội dung chi tiết được hệ thống tra trực tiếp từ toàn văn Bộ luật Hình sự năm 2025."
            )

        # Nếu hỏi cụ thể hơn thì model sẽ được cấp nguyên điều luật ở bước sau,
        # không dùng summary thủ công.
        return None

    # Các luật khác vẫn dùng exact_articles còn lại trong KB.
    if not law:
        return None
    item = (EXACT.get(law) or {}).get(art)
    if not item:
        return None

    law_name = {
        "BLHS":"Bộ luật Hình sự",
        "BLTTHS":"Bộ luật Tố tụng hình sự",
        "XLVPHC":"Luật Xử lý vi phạm hành chính"
    }.get(law, law)

    parts = [
        f"Điều {art} {law_name}: {item['title']}.",
        item["summary"]
    ]
    if item.get("warning"):
        parts.append(item["warning"])
    return clean(" ".join(parts))


def blhs_context_for_question(question, top_k=3):
    """
    Truy xuất trực tiếp từ toàn văn các Điều BLHS.
    Ưu tiên: số Điều nêu rõ -> tiêu đề -> độ trùng từ khóa trong văn bản.
    """
    q = norm(question)
    qt = {w for w in q.split() if len(w) >= 2}
    ranked = []

    explicit = re.search(r"\bdieu\s+(\d+[a-z]?)\b", q)
    explicit_art = explicit.group(1) if explicit else None

    for art, item in BLHS_ARTICLES.items():
        title = norm(item.get("title", ""))
        raw = norm(item.get("raw_text", ""))
        score = 0.0

        if explicit_art == art:
            score += 1000.0

        title_tokens = set(title.split())
        raw_tokens = set(raw.split())

        score += len(qt & title_tokens) * 8.0
        score += len(qt & raw_tokens) * 0.35

        # Một số từ trọng tâm phổ biến
        if "thuong tich" in q and "thuong tich" in title:
            score += 40
        if "trom" in q and "trom cap tai san" in title:
            score += 40
        if "lua dao" in q and "lua dao chiem doat tai san" in title:
            score += 40
        if "lam dung tin nhiem" in q and "lam dung tin nhiem chiem doat tai san" in title:
            score += 40
        if "gây rối" in question.lower() and "gây rối trật tự công cộng" in item.get("title","").lower():
            score += 40
        if "ma túy" in question.lower() and "ma túy" in item.get("title","").lower():
            score += 15

        if score > 0:
            ranked.append((score, item))

    ranked.sort(key=lambda x: x[0], reverse=True)

    blocks = []
    for score, item in ranked[:top_k]:
        raw = item.get("raw_text", "")
        # Giữ đủ rộng để model đọc điều luật, nhưng không đẩy toàn bộ 277 trang vào một request.
        if len(raw) > 9000:
            raw = raw[:9000]
        blocks.append(
            f"[BLHS Điều {item.get('article')}: {item.get('title','')}]\n{raw}"
        )

    return "\n\n".join(blocks)

def card_score(question, card):
    q = norm(question)
    qt = set(q.split())
    score = 0
    for kw in card.get("keywords",[]):
        k = norm(kw)
        if k in q:
            score += 9
        kt = set(k.split())
        score += len(qt & kt) * 1.5
    return score

def retrieve_cards(question, top_k=3):
    ranked = [(card_score(question,c),c) for c in CARDS]
    ranked = [(s,c) for s,c in ranked if s>0]
    ranked.sort(key=lambda x:x[0], reverse=True)
    return ranked[:top_k]

LEGAL_HINTS = [
    "phap luat","bo luat","luat ","dieu ","nghi dinh","thong tu","xu phat",
    "toi pham","khoi to","to giac","tam tru","thuong tru","dang ky xe",
    "can cuoc","vneid","ma tuy","cong an","thu tuc","tham quyen"
]

def is_legal(question):
    q = norm(question)
    return any(x in q for x in LEGAL_HINTS)

def wants_contact(question):
    q = norm(question)
    return any(x in q for x in [
        "so dien thoai","truc ban","lien he","goi cong an","bao an","trinh bao",
        "to giac","bao tin toi pham"
    ])

def contact_answer():
    return f"Số điện thoại trực ban {UNIT}: {HOTLINE}. Anh/chị có thể liên hệ số này để trình báo, phản ánh hoặc trao đổi thông tin cần thiết."

GENERAL_SYSTEM = f"""
Bạn là Trợ lý AI của {UNIT}.
Số điện thoại trực ban: {HOTLINE}.

YÊU CẦU:
1. Trả lời linh hoạt tất cả câu hỏi hợp pháp của người dân: pháp luật, TTHC, ANTT,
kiến thức phổ thông, công nghệ, đời sống, soạn thảo và các nội dung phù hợp khác.
2. Tiếng Việt tự nhiên, ngắn gọn, đúng trọng tâm, diễn đạt thuần thục.
3. Nội dung thuộc Công an/pháp luật: văn phong chuẩn mực, khách quan, dễ hiểu, phục vụ Nhân dân.
4. Không tự xưng là "Cục Công an xã". Tên đơn vị duy nhất là "{UNIT}".
5. Không dùng Markdown, không dùng dấu *, **, #.
6. Không trình bày chuỗi suy luận nội bộ.
7. Câu đơn giản trả lời 1-3 câu. Câu phức tạp: kết luận trước, sau đó tối đa 3-4 ý.
"""

LEGAL_RULES = """
QUY TẮC PHÁP LÝ HYBRID:
- VERIFIED_CONTEXT là dữ liệu đã kiểm tra từ nguồn chính thức, dùng làm mốc pháp lý.
- Được phép diễn giải linh hoạt, giải thích dễ hiểu, đưa hướng dẫn thực tế và nêu dữ kiện cần làm rõ.
- KHÔNG bị buộc phải lặp nguyên văn VERIFIED_CONTEXT.
- Tuy nhiên mọi chi tiết chính xác như số điều, khoản, mức phạt, thời hạn, lệ phí, thẩm quyền,
tên văn bản phải bám VERIFIED_CONTEXT; nếu context không có thì không được tự bịa.
- Nếu context chưa đủ, vẫn được trả lời nguyên tắc chung bằng ngôn ngữ linh hoạt,
nhưng phải tránh gắn số điều/khoản hoặc mức tiền cụ thể chưa được xác minh.
- Không kết luận một cá nhân phạm tội chỉ từ lời kể một phía.
"""

def context_from_cards(ranked):
    blocks=[]
    for score,c in ranked:
        if score < 5:
            continue
        srcs=[]
        for sid in c.get("sources",[]):
            s=SOURCES.get(sid)
            if s:
                srcs.append(f"{s.get('number','')} {s.get('name','')}".strip())
        blocks.append(
            f"[{c['id']}]\n"
            + "\n".join("- "+f for f in c.get("facts",[]))
            + ("\nNguồn: "+"; ".join(srcs) if srcs else "")
        )
    return "\n\n".join(blocks)

def call_groq(question, history, legal=False, context=""):
    system = GENERAL_SYSTEM
    if legal:
        system += "\n" + LEGAL_RULES

        # Nếu câu hỏi thuộc hình sự hoặc có nhắc Điều BLHS, nạp trực tiếp toàn văn điều luật liên quan.
        qn = norm(question)
        criminal_hint = any(x in qn for x in [
            "bo luat hinh su", "blhs", "toi pham", "hinh su", "thuong tich",
            "trom", "lua dao", "lam dung tin nhiem", "gây rối", "ma tuy"
        ]) or bool(re.search(r"\bdieu\s+(\d+[a-z]?)\b", qn))

        if criminal_hint:
            blhs_context = blhs_context_for_question(question, top_k=3)
            if blhs_context:
                system += (
                    "\nBLHS_FULLTEXT_CONTEXT - TRÍCH TRỰC TIẾP TỪ PDF NGƯỜI DÙNG CUNG CẤP:"
                    "\n" + blhs_context +
                    "\nQUY TẮC: với nội dung hình sự, ưu tiên tuyệt đối BLHS_FULLTEXT_CONTEXT; "
                    "không được thay tên Điều, tội danh, ngưỡng, khung hình phạt bằng trí nhớ riêng."
                )

        if context:
            system += "\nVERIFIED_CONTEXT:\n" + context
        else:
            system += (
                "\nHiện chưa có VERIFIED_CONTEXT đủ gần câu hỏi. "
                "Hãy trả lời nguyên tắc chung một cách hữu ích, nhưng tuyệt đối không tự nêu số điều, "
                "mức phạt, lệ phí, thời hạn hoặc thẩm quyền cụ thể nếu không chắc chắn."
            )
    messages=[{"role":"system","content":system}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role":"user","content":question})
    payload={
        "model":MODEL,
        "messages":messages,
        "temperature":0.12 if legal else 0.35,
        "max_completion_tokens":420,
        "reasoning_effort":"low"
    }
    r=HTTP.post(
        GROQ_URL,
        headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
        json=payload,
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return clean(r.json()["choices"][0]["message"]["content"])

def purge():
    now=time.time()
    while pending_questions and now-pending_questions[0].get("time",0)>PENDING_TTL:
        pending_questions.popleft()
    for mid,ts in list(seen_ids.items()):
        if now-ts>120:
            seen_ids.pop(mid,None)

@app.route("/",methods=["GET"])
def home():
    return f"{UNIT} - Hybrid Legal Flexible V4",200

@app.route("/health",methods=["GET"])
def health():
    return jsonify({
        "status":"ok",
        "mode":"hybrid_full_blhs_v5",
        "kb_version":VERSION.get("version"),
        "snapshot":VERSION.get("snapshot"),
        "unit":UNIT,
        "hotline":HOTLINE,
        "exact_article_router":True,
        "blhs_fulltext_loaded":bool(BLHS_ARTICLES),
        "blhs_article_count":len(BLHS_ARTICLES),
        "flexible_general_ai":True,
        "hybrid_legal_ai":True,
        "plain_text_only":True,
        "max_messages":MAX_MESSAGES,
        "groq":bool(GROQ_API_KEY)
    }),200

@app.route("/zalo/webhook",methods=["GET","POST"])
def webhook():
    if request.method=="GET":
        return "OK",200
    data=request.get_json(silent=True) or {}
    if data.get("event_name")=="user_send_text":
        sender=data.get("sender") or {}
        message=data.get("message") or {}
        sid=str(sender.get("id") or "").strip()
        text=str(message.get("text") or "").strip()
        mid=str(message.get("msg_id") or "").strip()
        if sid and text:
            with state_lock:
                purge()
                if mid and mid in seen_ids:
                    return jsonify({"success":True,"duplicate":True}),200
                if mid:
                    seen_ids[mid]=time.time()
                pending_questions.append({"sender_id":sid,"text":text,"time":time.time()})
                conversation_history.setdefault(sid,[])
                while len(pending_questions)>50:
                    pending_questions.popleft()
    return jsonify({"success":True}),200

@app.route("/zalo/ai",methods=["GET","POST"])
def ai():
    with state_lock:
        purge()
        item=pending_questions.popleft() if pending_questions else None
    if not item:
        return chatbot_response("Anh/chị vui lòng nhập nội dung cần hỗ trợ.")

    sid=item["sender_id"]
    question=item["text"]

    # 1. Liên hệ đơn vị: trả trực tiếp
    if wants_contact(question) and any(x in norm(question) for x in ["so dien thoai","truc ban","lien he","goi cong an"]):
        answer=contact_answer()
        return chatbot_response(answer)

    # 2. Điều luật cụ thể: route chính xác trước mọi semantic search
    exact=exact_article_answer(question)
    if exact:
        if wants_contact(question):
            exact += f" Trực ban {UNIT}: {HOTLINE}."
        return chatbot_response(exact)

    legal=is_legal(question)
    ranked=retrieve_cards(question) if legal else []
    context=context_from_cards(ranked)

    with state_lock:
        history=list(conversation_history.get(sid,[]))

    try:
        answer=call_groq(question,history,legal=legal,context=context)

        # Thêm số trực ban khi tình huống thực sự cần liên hệ/trình báo.
        if wants_contact(question) and HOTLINE not in answer:
            answer += f" Nếu cần trình báo hoặc trao đổi trực tiếp, số trực ban {UNIT}: {HOTLINE}."

        with state_lock:
            conversation_history.setdefault(sid,[])
            conversation_history[sid].extend([
                {"role":"user","content":question},
                {"role":"assistant","content":answer}
            ])
            conversation_history[sid]=conversation_history[sid][-MAX_HISTORY:]

        return chatbot_response(answer)

    except requests.exceptions.RequestException:
        # Nếu Groq lỗi nhưng có card, trả các fact đã xác minh thay vì câu lỗi chung.
        if ranked:
            best=ranked[0][1]
            facts=" ".join(best.get("facts",[]))
            if wants_contact(question):
                facts += f" Số trực ban {UNIT}: {HOTLINE}."
            return chatbot_response(facts)
        return chatbot_response(
            f"Trợ lý AI hiện chưa kết nối được dịch vụ xử lý. Anh/chị có thể thử lại hoặc liên hệ trực ban {UNIT}: {HOTLINE}."
        )
    except Exception:
        return chatbot_response(
            f"Trợ lý AI hiện chưa xử lý được yêu cầu này. Số trực ban {UNIT}: {HOTLINE}."
        )

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
