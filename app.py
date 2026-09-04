from flask import Flask, request, jsonify
import json
import os
import requests

app = Flask(__name__)

ZALO_ACCESS_TOKEN = os.getenv("ZALO_ACCESS_TOKEN")


@app.route("/", methods=["GET"])
def home():
    return """
<!doctype html>
<html lang="vi">
<head>
    <meta charset="utf-8">
    <meta name="zalo-platform-site-verification"
          content="OiMc2EZKV28O_zyYtDbQAHRNrNRweGyWD34u" />
    <title>Công an xã Pơng Drang - Webhook</title>
</head>
<body>
    <h3>Webhook Công an xã Pơng Drang đang hoạt động</h3>
</body>
</html>
""", 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "CAX Pong Drang Zalo Webhook"
    }), 200


def send_zalo_message(user_id, text):
    url = "https://openapi.zalo.me/v3.0/oa/message/cs"

    headers = {
        "access_token": ZALO_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "recipient": {
            "user_id": user_id
        },
        "message": {
            "text": text
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        print("ZALO SEND STATUS:", response.status_code, flush=True)
        print("ZALO SEND RESPONSE:", response.text, flush=True)

    except Exception as e:
        print("ZALO SEND ERROR:", str(e), flush=True)


@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():

    if request.method == "GET":
        return "OK", 200

    data = request.get_json(silent=True) or {}

    print("\n========== ZALO WEBHOOK ==========", flush=True)
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)

    event_name = data.get("event_name")

    if event_name == "user_send_text":

        sender = data.get("sender", {})
        user_id = sender.get("id")

        message = data.get("message", {})
        user_text = message.get("text", "")

        print("USER TEXT:", user_text, flush=True)

        if user_id and ZALO_ACCESS_TOKEN:
            send_zalo_message(
                user_id,
                "✅ Công an xã Pơng Drang đã nhận được tin nhắn của anh/chị. Đây là phản hồi thử nghiệm tự động từ hệ thống."
            )

    print("==================================\n", flush=True)

    return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
