from flask import Flask, request, jsonify
import os
import re
import time
import requests
from threading import Lock


app = Flask(__name__)


# =========================================================
# CẤU HÌNH
# =========================================================

GROQ_API_KEY = "".join(
    (os.getenv("GROQ_API_KEY") or "").split()
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

print(
    "GROQ KEY LOADED:",
    bool(GROQ_API_KEY),
    flush=True
)


# =========================================================
# BỘ NHỚ TẠM
# =========================================================

# Câu hỏi mới nhất của từng người dùng
latest_questions = {}

# Lịch sử hội thoại của từng người
conversation_history = {}

# Câu trả lời đã tạo theo msg_id
answer_cache = {}

# Người vừa gửi câu hỏi gần nhất
latest_sender_id = None

memory_lock = Lock()


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Bạn là TRỢ LÝ AI CÔNG AN XÃ PƠNG DRANG, TỈNH ĐẮK LẮK.

VAI TRÒ:
Bạn là trợ lý thông tin điện tử phục vụ Nhân dân, hoạt động theo phong cách
chuyên nghiệp, chuẩn mực, chính xác của lực lượng Công an nhân dân.

I. NGUYÊN TẮC TRẢ LỜI

1. Trả lời bằng tiếng Việt chuẩn, rõ ràng, mạch lạc, lịch sự.
2. Văn phong hành chính - pháp lý, chuyên nghiệp nhưng phải dễ hiểu đối với người dân.
3. Không dùng từ ngữ suồng sã, đùa cợt hoặc biểu cảm không phù hợp.
4. Không phô trương, không sử dụng các câu mang tính đe dọa.
5. Không tự nhận mình là cán bộ có thẩm quyền ra quyết định.
6. Không được bịa quy định pháp luật, số điều, khoản, văn bản, thời hạn,
   mức phạt, lệ phí hoặc thành phần hồ sơ.
7. Khi chưa đủ căn cứ, phải nói rõ:
   "Hiện chưa có đủ thông tin để khẳng định chính xác nội dung này."
8. Với nội dung pháp luật và thủ tục hành chính, ưu tiên tuyệt đối:
   a) Kho tri thức đã được cung cấp cho hệ thống;
   b) Văn bản, nguồn thông tin chính thức của cơ quan Nhà nước;
   c) Chỉ sau đó mới sử dụng kiến thức nền của mô hình.
9. Nếu nội dung trong kho tri thức khác với kiến thức nền,
   phải sử dụng nội dung trong kho tri thức.
10. Không suy đoán trách nhiệm hình sự, hành chính của một cá nhân khi
    chưa đủ thông tin và căn cứ pháp luật.

II. PHONG CÁCH CÔNG AN

Khi trả lời nội dung thuộc lĩnh vực Công an, ưu tiên cách diễn đạt:

"Công an xã Pơng Drang hướng dẫn như sau:"
hoặc
"Đối với nội dung anh/chị hỏi, có thể tham khảo như sau:"

Sau đó trình bày:
1. Nội dung cần thực hiện.
2. Hồ sơ/điều kiện nếu có.
3. Cơ quan hoặc nơi thực hiện.
4. Lưu ý.
5. Căn cứ/nguồn nếu hệ thống có nguồn đáng tin cậy.

Không bắt buộc sử dụng đủ 5 mục nếu câu hỏi đơn giản.

III. HỎI ĐÁP ĐA NĂNG

Ngoài nội dung Công an, bạn có thể hỗ trợ:
- kiến thức phổ thông;
- học tập;
- công nghệ;
- đời sống;
- soạn thảo văn bản;
- giải thích khái niệm;
- thông tin thời sự khi có dữ liệu web mới.

Với các câu hỏi thông thường không thuộc lĩnh vực Công an,
sử dụng giọng văn chuyên nghiệp, thân thiện, không cần dùng văn phong công vụ quá cứng.

IV. THÔNG TIN CẬP NHẬT

Nếu câu hỏi liên quan:
- "hiện nay";
- "mới nhất";
- "hôm nay";
- văn bản đang có hiệu lực;
- mức phạt;
- thủ tục hành chính hiện hành;
- tin tức hoặc dữ liệu biến động;

thì phải ưu tiên dữ liệu cập nhật hoặc tìm kiếm web.

V. NGUỒN THÔNG TIN

Đối với pháp luật, ưu tiên nguồn:
- vanban.chinhphu.vn
- chinhphu.vn
- bocongan.gov.vn
- moj.gov.vn
- dichvucong.gov.vn
- các Cổng thông tin chính thức của cơ quan Nhà nước có thẩm quyền.

Không lấy bài mạng xã hội, diễn đàn hoặc blog cá nhân làm căn cứ pháp lý chính.

Nếu có nguồn, ghi ngắn gọn cuối câu trả lời:
"Nguồn tham khảo: ..."

VI. BẢO MẬT

Không yêu cầu người dân cung cấp:
- mật khẩu;
- OTP;
- mã PIN;
- thông tin bí mật;
- hồ sơ nghiệp vụ không cần thiết.

Không tiết lộ:
- thông tin nghiệp vụ nội bộ;
- dữ liệu cá nhân của người khác;
- bí mật Nhà nước;
- dữ liệu thuộc diện hạn chế công khai.

VII. ĐỘ DÀI

Ưu tiên câu trả lời từ 200 đến 1.200 ký tự.
Nếu nội dung dài, tóm tắt trước rồi hướng dẫn từng bước.

Mục tiêu cao nhất:
ĐÚNG NGUỒN - ĐÚNG QUY ĐỊNH - DỄ HIỂU - HỮU ÍCH CHO NHÂN DÂN.
"""


# =========================================================
# NHẬN BIẾT CÂU HỎI CẦN DỮ LIỆU MỚI
# =========================================================

def needs_web_search(question):

    q = question.lower()

    freshness_words = [
        "hôm nay",
        "hiện tại",
        "bây giờ",
        "mới nhất",
        "vừa mới",
        "gần đây",
        "cập nhật",
        "thời tiết",
        "giá vàng",
        "tỷ giá",
        "giá bitcoin",
        "giá btc",
        "giá xăng",
        "chứng khoán",
        "tin tức",
        "tin mới",
        "kết quả bóng đá",
        "lịch thi đấu",
        "đang xảy ra",
        "còn hiệu lực",
        "đang có hiệu lực",
        "văn bản mới",
        "nghị định mới",
        "thông tư mới",
        "quy định mới",
        "mức phạt hiện nay",
        "mức phạt hiện tại",
        "lệ phí hiện nay",
        "thủ tục hiện nay"
    ]

    legal_words = [
        "nghị định",
        "thông tư",
        "luật hiện hành",
        "điều luật",
        "mức phạt",
        "xử phạt bao nhiêu",
        "căn cứ pháp lý"
    ]

    for word in freshness_words + legal_words:
        if word in q:
            return True

    # Câu hỏi có năm 2026 trở đi thường nên kiểm tra web
    years = re.findall(r"\b20\d{2}\b", q)

    for year in years:
        if int(year) >= 2026:
            return True

    return False


# =========================================================
# PHÁT HIỆN DỮ LIỆU CÓ THỂ NHẠY CẢM
# =========================================================

def contains_sensitive_data(question):

    q = question.lower()

    dangerous_terms = [
        "mật khẩu",
        "password",
        "mã otp",
        "otp của tôi",
        "mã pin"
    ]

    if any(term in q for term in dangerous_terms):
        return True

    # Chuỗi số dài có thể là CCCD, tài khoản, điện thoại...
    if re.search(r"\b\d{9,16}\b", question):
        return True

    return False


# =========================================================
# GỌI GROQ
# =========================================================

def ask_groq(question, history=None):

    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY chưa được cấu hình")

    if history is None:
        history = []

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Chỉ giữ một số lượt hội thoại gần nhất
    messages.extend(history[-8:])

    messages.append({
        "role": "user",
        "content": question
    })

    use_web = (
        needs_web_search(question)
        and not contains_sensitive_data(question)
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "Groq-Model-Version": "latest"
    }

    # =====================================================
    # CHẾ ĐỘ TÌM WEB THỜI GIAN THỰC
    # =====================================================

    if use_web:

        web_instruction = """
Khi tìm web:
- ưu tiên nguồn chính thống và nguồn gốc;
- với pháp luật Việt Nam ưu tiên các website của Chính phủ,
  Bộ Công an, Bộ Tư pháp, Cổng Dịch vụ công và cơ quan Nhà nước;
- đối chiếu ngày đăng, ngày hiệu lực nếu có;
- không coi một blog hoặc bài mạng xã hội là căn cứ pháp lý;
- giữ nguồn/citation nếu hệ thống cung cấp.
"""

        messages.insert(
            1,
            {
                "role": "system",
                "content": web_instruction
            }
        )

        payload = {
            "model": "groq/compound-mini",
            "messages": messages,
            "temperature": 0.25,
            "max_completion_tokens": 350,
            "compound_custom": {
                "tools": {
                    "enabled_tools": [
                        "web_search"
                    ]
                }
            }
        }

    # =====================================================
    # CHẾ ĐỘ AI THÔNG THƯỜNG
    # =====================================================

    else:

        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": messages,
            "temperature": 0.45,
            "max_completion_tokens": 350,
            "reasoning_effort": "low"
        }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=1.65
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
        raise Exception("Groq không trả nội dung")

    # Giữ tin nhắn vừa phải cho Zalo
    return answer[:1800], use_web


# =========================================================
# FORMAT PHẢN HỒI ZALO
# =========================================================

def chatbot_response(text):

    return jsonify({
        "version": "chatbot",
        "content": {
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
    }), 200


# =========================================================
# TRANG CHỦ + META XÁC MINH ZALO
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return """
<!doctype html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <meta
        name="zalo-platform-site-verification"
        content="OiMc2EZKV28O_zyYtDbQAHRNrNRweGyWD34u"
    />
    <title>Trợ lý AI Công an xã Pơng Drang</title>
</head>
<body>
    <h3>Trợ lý AI Công an xã Pơng Drang đang hoạt động</h3>
</body>
</html>
""", 200, {
        "Content-Type": "text/html; charset=utf-8"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "groq": bool(GROQ_API_KEY),
        "service": "CAX Pong Drang AI",
        "ai_model": "openai/gpt-oss-20b",
        "realtime_search": "groq/compound-mini"
    }), 200


# =========================================================
# WEBHOOK ZALO
# =========================================================

@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():

    global latest_sender_id

    if request.method == "GET":
        return "OK", 200

    data = request.get_json(silent=True) or {}

    if data.get("event_name") == "user_send_text":

        sender = data.get("sender") or {}
        message = data.get("message") or {}

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

            item = {
                "text": text,
                "msg_id": msg_id,
                "time": time.time()
            }

            with memory_lock:

                latest_questions[sender_id] = item
                latest_sender_id = sender_id

                if sender_id not in conversation_history:
                    conversation_history[sender_id] = []

            # Không log nội dung người dân
            print(
                "ZALO QUESTION RECEIVED: YES",
                "LENGTH:",
                len(text),
                flush=True
            )

    return jsonify({
        "success": True
    }), 200


# =========================================================
# DYNAMIC API -> AI
# =========================================================

@app.route("/zalo/ai", methods=["GET", "POST"])
def zalo_ai():

    global latest_sender_id

    body = request.get_json(silent=True) or {}

    # Chỉ log cấu trúc request, không log dữ liệu người dân
    print(
        "DYNAMIC REQUEST:",
        "ARGS:",
        list(request.args.keys()),
        "BODY_KEYS:",
        list(body.keys()),
        flush=True
    )

    with memory_lock:

        sender_id = latest_sender_id

        if sender_id:
            item = latest_questions.get(sender_id)
            history = list(
                conversation_history.get(sender_id, [])
            )
        else:
            item = None
            history = []

    if not item:

        return chatbot_response(
            "Anh/chị vui lòng nhập nội dung cần hỗ trợ."
        )

    # Không dùng câu hỏi quá cũ
    if time.time() - item.get("time", 0) > 120:

        return chatbot_response(
            "Anh/chị vui lòng gửi lại câu hỏi để hệ thống hỗ trợ."
        )

    question = item.get("text", "").strip()
    msg_id = item.get("msg_id", "")

    if not question:

        return chatbot_response(
            "Anh/chị vui lòng nhập nội dung cần hỗ trợ."
        )

    # Nếu Dynamic gọi lại cùng một tin nhắn
    if msg_id:

        with memory_lock:
            cached = answer_cache.get(msg_id)

        if cached:
            return chatbot_response(cached)

    try:

        answer, used_web = ask_groq(
            question,
            history
        )

        if used_web:
            print(
                "GROQ ANSWER: SUCCESS + WEB SEARCH",
                flush=True
            )
        else:
            print(
                "GROQ ANSWER: SUCCESS",
                flush=True
            )

        with memory_lock:

            conversation_history.setdefault(
                sender_id,
                []
            )

            conversation_history[sender_id].append({
                "role": "user",
                "content": question
            })

            conversation_history[sender_id].append({
                "role": "assistant",
                "content": answer
            })

            # Chỉ lưu 8 message gần nhất
            conversation_history[sender_id] = (
                conversation_history[sender_id][-8:]
            )

            if msg_id:
                answer_cache[msg_id] = answer

                # Tránh cache phình mãi
                if len(answer_cache) > 200:
                    first_key = next(iter(answer_cache))
                    answer_cache.pop(first_key, None)

        return chatbot_response(answer)


    except requests.exceptions.Timeout:

        print(
            "GROQ ERROR: TIMEOUT",
            flush=True
        )

        return chatbot_response(
            "Hệ thống đang truy xuất dữ liệu hơi lâu. "
            "Anh/chị vui lòng gửi lại câu hỏi sau ít giây."
        )


    except requests.exceptions.HTTPError as e:

        status = (
            e.response.status_code
            if e.response is not None
            else "UNKNOWN"
        )

        print(
            "GROQ HTTP ERROR:",
            status,
            flush=True
        )

        return chatbot_response(
            "Trợ lý AI hiện tạm thời chưa truy xuất được dữ liệu. "
            "Anh/chị vui lòng thử lại."
        )


    except Exception as e:

        print(
            "GROQ ERROR:",
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

    app.run(
        host="0.0.0.0",
        port=10000
    )
