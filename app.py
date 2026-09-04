
from flask import Flask, request, jsonify
import json

app = Flask(__name__)


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


@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():
    if request.method == "GET":
        return "OK", 200

    data = request.get_json(silent=True) or {}

    print("\n========== ZALO WEBHOOK ==========", flush=True)
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)

    signature = request.headers.get("X-ZEvent-Signature")
    if signature:
        print("X-ZEvent-Signature:", signature, flush=True)

    print("==================================\n", flush=True)

    return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
