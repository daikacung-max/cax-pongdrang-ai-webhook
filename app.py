from flask import Flask, request, jsonify
import json
import os
import requests
import time

app = Flask(__name__)


# =========================================================
# GROQ API
# =========================================================

GROQ_API_KEY = "".join(
    (os.getenv("GROQ_API_KEY") or "").split()
)

print(
    "GROQ KEY LOADED:",
    bool(GROQ_API_KEY),
    flush=True
)


# =========================================================
# LƯU TẠM CÂU HỎI MỚI NHẤT CỦA NGƯỜI DÙNG
# =========================================================

latest_questions = {}


# =========================================================
# HƯỚNG DẪN CHO AI
# =========================================================

SYSTEM_PROMPT = """
Bạn là Trợ lý ảo của Công an xã Pơng Drang, tỉnh Đắk Lắk.

Nhiệm vụ của bạn là hỗ trợ người dân về:
- thủ tục hành chính thuộc phạm vi Công an xã;
- cư trú, thường trú, tạm trú;
- căn cước;
- tài khoản định danh điện tử VNeID;
- dịch vụ công;
- tuyên truyền, phòng ngừa vi phạm pháp luật;
- thông tin liên hệ và hướng dẫn chung của Công an xã.

YÊU CẦU BẮT BUỘC:

1. Trả lời hoàn toàn bằng tiếng Việt.
2. Văn phong lịch sự, rõ ràng, dễ hiểu.
3. Trả lời ngắn gọn, đi thẳng vào câu hỏi.
4. Không tự bịa điều luật, nghị định, thông tư, lệ phí,
   thời hạn, thành phần hồ sơ hoặc thẩm quyền giải quyết.
5. Khi không chắc chắn về quy định pháp luật hiện hành,
   phải nói rõ người dân cần liên hệ Công an xã để được
   kiểm tra chính xác.
6. Không yêu cầu người dân cung cấp mật khẩu, mã OTP,
   mã PIN hoặc thông tin bảo mật.
7. Không được tự kết luận một người có tội, vi phạm pháp luật
   hoặc phải chịu trách nhiệm hình sự.
8. Không cung cấp thông tin nghiệp vụ nội bộ của lực lượng Công an.
9. Không hướng dẫn cách né tránh, chống đối hoặc vô hiệu hóa
   hoạt động của cơ quan Công an.
10. Nếu câu hỏi không liên quan đến chức năng hỗ trợ của
    Công an xã Pơng Drang, giải thích ngắn gọn và hướng người dân
    đến cơ quan phù hợp.
11. Nếu chưa đủ thông tin để trả lời chính xác, hãy hỏi lại
    một câu ngắn để làm rõ.
12. Không khẳng định một quy định pháp luật là chính xác nếu
    chưa có dữ liệu đáng tin cậy trong hệ thống.

Cuối câu trả lời không cần lặp lại lời chào.
"""


# =========================================================
# GỌI GROQ AI
# =========================================================

def ask_groq(question):

    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY chưa được cấu hình")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-oss-20b",

        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": question
            }
        ],

        "temperature": 0.2,
        "max_completion_tokens": 250
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=1.55
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
        raise Exception("Groq không trả về nội dung")

    # Giới hạn để phù hợp tin nhắn Zalo
    return answer[:1400]


# =========================================================
# TRANG CHỦ + XÁC MINH DOMAIN ZALO
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

<h3>
Trợ lý AI Công an xã Pơng Drang đang hoạt động
</h3>

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
        "service": "CAX Pong Drang AI"
    }), 200


# =========================================================
# NHẬN WEBHOOK TỪ ZALO
# =========================================================

@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():

    if request.method == "GET":
        return "OK", 200

    data = request.get_json(silent=True) or {}

    event_name = data.get("event_name")

    if event_name == "user_send_text":

        sender = data.get("sender") or {}
        message = data.get("message") or {}

        sender_id = str(
            sender.get("id") or ""
        ).strip()

        user_id_by_app = str(
            data.get("user_id_by_app") or ""
        ).strip()

        text = str(
            message.get("text") or ""
        ).strip()

        if text:

            item = {
                "text": text,
                "time": time.time()
            }

            if sender_id:
                latest_questions[sender_id] = item

            if user_id_by_app:
                latest_questions[user_id_by_app] = item

            print(
                "ZALO QUESTION RECEIVED:",
                "YES",
                "LENGTH:",
                len(text),
                flush=True
            )

    return jsonify({
        "success": True
    }), 200


# =========================================================
# DYNAMIC API ZALO -> GROQ
# =========================================================

@app.route("/zalo/ai", methods=["GET", "POST"])
def zalo_ai():

    # Bản thử nghiệm:
    # lấy câu hỏi mới nhất vừa nhận được từ Zalo Webhook
    item = None

    if latest_questions:
        item = max(
            latest_questions.values(),
            key=lambda x: x.get("time", 0)
        )

    if not item:
        return chatbot_response(
            "Anh/chị vui lòng nhập lại nội dung cần hỗ trợ."
        )

    # Không sử dụng câu hỏi quá cũ
    if time.time() - item.get("time", 0) > 120:
        return chatbot_response(
            "Anh/chị vui lòng gửi lại câu hỏi để hệ thống hỗ trợ."
        )

    question = item.get("text", "").strip()

    if not question:
        return chatbot_response(
            "Anh/chị vui lòng nhập nội dung cần hỗ trợ."
        )

    try:
        answer = ask_groq(question)

        print(
            "GROQ ANSWER: SUCCESS",
            flush=True
        )

        return chatbot_response(answer)

    except requests.exceptions.Timeout:

        print(
            "GROQ ERROR: TIMEOUT",
            flush=True
        )

        return chatbot_response(
            "Hệ thống đang xử lý chậm. "
            "Anh/chị vui lòng gửi lại câu hỏi sau ít giây."
        )

    except requests.exceptions.HTTPError as e:

        print(
            "GROQ HTTP ERROR:",
            e.response.status_code
            if e.response is not None
            else "UNKNOWN",
            flush=True
        )

        return chatbot_response(
            "Trợ lý AI hiện tạm thời chưa phản hồi được. "
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
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
