from flask import Flask, request, jsonify
from pathlib import Path
import re

from config import (
    UNIT_NAME,
    HOTLINE,
    ANSWER_MODEL,
    DYNAMIC_ANSWER_MODEL,
    MAX_ZALO_MESSAGES,
    TARGET_ZALO_CHARS,
    MAX_ZALO_TOTAL_CHARS,
)
from core import db
from core.ingest import import_article_index
from core.verified_sources import ensure_verified_sources
from core.service import core
from adapters.zalo import pending

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent


def ensure_legal_db():
    db.init_schema()

    # Chỉ nạp BLHS từ file gốc khi chưa có dữ liệu BLHS.
    if not db.get_article("BLHS_2025", "134"):
        index_path = BASE_DIR / "Bộ luật Hình sự năm 2025 - chỉ mục điều luật.json"
        pdf_path = BASE_DIR / "Bộ luật Hình sự năm 2025.pdf"
        if index_path.exists() and pdf_path.exists():
            import_article_index(
                index_path=index_path,
                document_id="BLHS_2025",
                title="Bộ luật Hình sự năm 2025",
                source_path=pdf_path,
                number="100/2015/QH13 (đã được sửa đổi, bổ sung)",
                issuer="Quốc hội",
                effective_from=None,
            )

    # Luôn đồng bộ các snapshot đã kiểm chứng từ nguồn chính thức.
    # Việc này không phụ thuộc việc BLHS đã có hay chưa.
    ensure_verified_sources()


ensure_legal_db()


def split_zalo_messages(text):
    text = str(text or "").strip()
    if len(text) > MAX_ZALO_TOTAL_CHARS:
        clipped = text[:MAX_ZALO_TOTAL_CHARS]
        pos = max(
            clipped.rfind(". "), clipped.rfind("? "), clipped.rfind("! "),
            clipped.rfind("; "), clipped.rfind("\n")
        )
        if pos > int(MAX_ZALO_TOTAL_CHARS * 0.6):
            clipped = clipped[:pos + 1]
        text = clipped.strip()

    if len(text) <= TARGET_ZALO_CHARS:
        return [text]

    parts = re.split(r"(?<=[.!?;])\s+|\n+", text)
    result = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        candidate = part if not current else current + " " + part
        if len(candidate) <= TARGET_ZALO_CHARS:
            current = candidate
        else:
            if current:
                result.append(current)
            current = part
    if current:
        result.append(current)

    if len(result) <= MAX_ZALO_MESSAGES:
        return result
    final = result[:MAX_ZALO_MESSAGES - 1]
    final.append(" ".join(result[MAX_ZALO_MESSAGES - 1:])[:820].strip())
    return final[:MAX_ZALO_MESSAGES]


def dynamic_response(text):
    return jsonify({
        "version": "chatbot",
        "content": {
            "messages": [
                {"type": "text", "text": part}
                for part in split_zalo_messages(text)
                if part
            ]
        }
    }), 200


@app.route("/", methods=["GET"])
def home():
    return f"{UNIT_NAME} - AI CORE", 200


@app.route("/health", methods=["GET"])
def health():
    ensure_legal_db()
    s = db.stats()
    article_134 = db.get_article("BLHS_2025", "134")
    return jsonify({
        "status": "ok",
        "mode": "CAX_PONG_DRANG_AI_CORE",
        "architecture": "plan_retrieve_answer_verify",
        "unit": UNIT_NAME,
        "hotline": HOTLINE,
        "database": s,
        "article_134_title": article_134[0]["title"] if article_134 else None,
        "residence_sources_loaded": s.get("documents", 0) >= 3,
        "real_conversation_api": "/api/chat",
        "zalo_dynamic_adapter": "/zalo/ai",
        "core_answer_model": ANSWER_MODEL,
        "dynamic_answer_model": DYNAMIC_ANSWER_MODEL,
        "dynamic_mode": "single_call_grounded_verified",
    }), 200


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or "").strip()
    message = str(data.get("message") or "").strip()
    if not user_id or not message:
        return jsonify({"error": "user_id và message là bắt buộc."}), 400
    try:
        result = core.chat(user_id, message, dynamic=False)
        return jsonify(result), 200
    except Exception as exc:
        app.logger.error("AI Core API error type=%s", type(exc).__name__)
        return jsonify({
            "error": type(exc).__name__,
            "message": "AI Core chưa xử lý được yêu cầu này.",
        }), 500


@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():
    if request.method == "GET":
        return "OK", 200
    data = request.get_json(silent=True) or {}
    if data.get("event_name") == "user_send_text":
        sender = data.get("sender") or {}
        message = data.get("message") or {}
        user_id = str(sender.get("id") or "").strip()
        text = str(message.get("text") or "").strip()
        msg_id = str(message.get("msg_id") or "").strip()
        if user_id and text:
            pending.push(user_id, text, msg_id=msg_id)
    return jsonify({"success": True}), 200


@app.route("/zalo/ai", methods=["GET", "POST"])
def zalo_dynamic():
    uid = str(
        request.args.get("uid")
        or request.headers.get("X-Zalo-User-ID")
        or ""
    ).strip()
    item = pending.pop(user_id=uid or None)
    if not item:
        return dynamic_response("Anh/chị vui lòng nhập câu hỏi cần hỗ trợ.")
    try:
        result = core.chat(item["user_id"], item["text"], dynamic=True)
        return dynamic_response(result["answer"])
    except Exception as exc:
        # Không ghi nội dung câu hỏi hoặc dữ liệu cá nhân vào log.
        app.logger.error("Zalo AI Core error type=%s detail=%s", type(exc).__name__, str(exc)[:160])
        return dynamic_response(
            f"Trợ lý AI tạm thời chưa hoàn tất được phần phân tích. "
            f"Nếu cần trao đổi trực tiếp, người dân có thể liên hệ trực ban "
            f"{UNIT_NAME} qua số {HOTLINE}."
        )


@app.route("/debug/article/<article>", methods=["GET"])
def debug_article(article):
    ensure_legal_db()
    rows = db.get_article("BLHS_2025", article)
    if not rows:
        return jsonify({"found": False, "article": article}), 404
    row = rows[0]
    return jsonify({
        "found": True,
        "article": row["article"],
        "title": row["title"],
        "document": row["document_title"],
        "unit_id": row["id"],
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
