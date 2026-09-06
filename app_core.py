from flask import Flask, request, jsonify, render_template
from pathlib import Path
import logging
import time
import re
import os
import hmac
import hashlib

from config import (
    UNIT_NAME,
    HOTLINE,
    ANSWER_MODEL,
    DYNAMIC_ANSWER_MODEL,
    DYNAMIC_CANDIDATE_MODEL,
    FULL_CORE_CANDIDATE_MODEL,
    ESCALATION_MODEL,
    MAX_ZALO_MESSAGES,
    TARGET_ZALO_CHARS,
    MAX_ZALO_TOTAL_CHARS,
    ENABLE_DEMO_CONSOLE,
    LOCAL_BIND_HOST,
    OFFICER_API_TOKEN,
    PRODUCTION_MODE,
    ZALO_WEBHOOK_ENABLED,
    ZALO_WEBHOOK_SIGNATURE_REQUIRED,
    ZALO_APP_ID,
    ZALO_OA_SECRET_KEY,
)
from core import cases, db
from core.ingest import import_article_index
from core.verified_sources import ensure_verified_sources
from core.service import core
from core.demo import respond as demo_respond
from core.llm import LLMError, LLMTimeout
from core.providers import provider_name_for_model
from core.telemetry import log_zalo_latency, new_trace_id
from core.verifier import grounded_dynamic_fallback
from adapters.zalo import pending

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
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

    sentence_parts = re.split(r"(?<=[.!?;])\s+|\n+", text)
    parts = []
    for part in sentence_parts:
        part = part.strip()
        while len(part) > TARGET_ZALO_CHARS:
            cut = part.rfind(" ", 0, TARGET_ZALO_CHARS + 1)
            if cut < int(TARGET_ZALO_CHARS * 0.5):
                cut = TARGET_ZALO_CHARS
            parts.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            parts.append(part)
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


def _demo_enabled():
    return bool(ENABLE_DEMO_CONSOLE)


def _valid_demo_session(value):
    return bool(re.fullmatch(r"[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}", str(value or "").lower()))


def _officer_authorized():
    """Cổng nội bộ không hoạt động nếu chưa cấu hình bí mật cán bộ."""
    if not OFFICER_API_TOKEN:
        return False
    supplied = str(request.headers.get("Authorization") or "")
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    return hmac.compare_digest(supplied, OFFICER_API_TOKEN)


def _valid_zalo_webhook_signature(data, raw_body):
    """Xác thực webhook OA theo X-ZEvent-Signature của Zalo.

    Zalo ký SHA-256 của ``appId + data + timeStamp + OAsecretKey``. ``data``
    phải là nguyên văn JSON body nhận được, do đó không serialize lại JSON trước
    khi kiểm tra. Chế độ local/demo có thể tắt yêu cầu chữ ký; Render pilot và
    production phải bật nó trước khi đăng ký webhook tại Zalo.
    """
    if not ZALO_WEBHOOK_SIGNATURE_REQUIRED:
        return True
    if not ZALO_APP_ID or not ZALO_OA_SECRET_KEY:
        return False

    app_id = str((data or {}).get("app_id") or "").strip()
    timestamp = str((data or {}).get("timestamp") or "").strip()
    supplied = str(request.headers.get("X-ZEvent-Signature") or "").strip()
    if supplied.lower().startswith("mac="):
        supplied = supplied[4:].strip()
    if not app_id or not timestamp or not supplied:
        return False
    if not hmac.compare_digest(app_id, ZALO_APP_ID):
        return False

    signed_value = f"{app_id}{raw_body}{timestamp}{ZALO_OA_SECRET_KEY}".encode("utf-8")
    expected = hashlib.sha256(signed_value).hexdigest()
    return hmac.compare_digest(supplied.lower(), expected)


def _zalo_dynamic_uid():
    """Read only a user identifier from common Dynamic-action envelopes.

    Dynamic must never consume an unscoped pending message: that could pair one
    person's question with another person's reply.  We deliberately do not
    accept message text here; the signed webhook remains the sole message
    source.
    """
    data = request.get_json(silent=True) or {}
    sender = data.get("sender") or {}
    user = data.get("user") or {}
    nested = data.get("data") or {}
    candidates = (
        request.args.get("uid"),
        request.args.get("user_id"),
        request.headers.get("X-Zalo-User-ID"),
        data.get("uid"),
        data.get("user_id"),
        sender.get("id"),
        user.get("id"),
        nested.get("uid"),
        nested.get("user_id"),
    )
    for value in candidates:
        value = str(value or "").strip()
        if value:
            return value
    return ""


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
        "core_answer_provider": provider_name_for_model(ANSWER_MODEL),
        "dynamic_answer_provider": provider_name_for_model(DYNAMIC_ANSWER_MODEL),
        "dynamic_candidate_model": DYNAMIC_CANDIDATE_MODEL,
        "full_core_candidate_model": FULL_CORE_CANDIDATE_MODEL,
        "escalation_model": ESCALATION_MODEL,
        "history_backend": s.get("history_backend"),
        "dynamic_mode": "single_call_grounded_verified",
        "demo_console_enabled": _demo_enabled(),
        "production_mode": PRODUCTION_MODE,
        "officer_intake_ready": bool(OFFICER_API_TOKEN),
    }), 200


@app.route("/demo", methods=["GET"])
def demo_console():
    if not _demo_enabled():
        return "Not found", 404
    return render_template("demo.html"), 200


@app.route("/demo/api/history", methods=["GET"])
def demo_history():
    if not _demo_enabled():
        return jsonify({"error": "Not found"}), 404
    session_id = str(request.args.get("session_id") or "").strip().lower()
    if not _valid_demo_session(session_id):
        return jsonify({"error": "session_id demo không hợp lệ."}), 400
    history = db.get_history(session_id, limit=20)
    return jsonify({
        "messages": [
            {"role": item["role"], "content": item["content"]}
            for item in history if item.get("role") in ("user", "assistant")
        ]
    }), 200


@app.route("/demo/api/chat", methods=["POST"])
def demo_chat():
    if not _demo_enabled():
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id") or "").strip().lower()
    message = str(data.get("message") or "").strip()
    if not _valid_demo_session(session_id) or not message:
        return jsonify({"error": "session_id demo và message là bắt buộc."}), 400
    if len(message) > 1500:
        return jsonify({"error": "Tin nhắn demo quá dài."}), 400
    try:
        return jsonify(demo_respond(session_id, message)), 200
    except Exception as exc:
        app.logger.error("Demo console error type=%s", type(exc).__name__)
        return jsonify({"error": "Demo chưa xử lý được yêu cầu này."}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or "").strip()
    message = str(data.get("message") or "").strip()
    if not user_id or not message:
        return jsonify({"error": "user_id và message là bắt buộc."}), 400
    try:
        result = core.chat(user_id, message, dynamic=False)
        result.pop("_telemetry", None)
        return jsonify(result), 200
    except (LLMError, LLMTimeout) as exc:
        # Lớp biên API không được lộ lỗi kỹ thuật nếu một nhánh provider ngoài
        # dự kiến còn sót lại. Không dùng nguồn chưa kiểm chứng ở đây.
        app.logger.error("AI Core safe fallback type=%s", type(exc).__name__)
        return jsonify({
            "answer": grounded_dynamic_fallback(message, []),
            "meta": {
                "legal": False, "verified": False, "repaired": False,
                "dynamic": False, "path": "api_boundary_grounded_fallback",
            },
            "handoff": None,
        }), 200
    except Exception as exc:
        app.logger.error("AI Core API error type=%s", type(exc).__name__)
        return jsonify({
            "error": type(exc).__name__,
            "message": "AI Core chưa xử lý được yêu cầu này.",
        }), 500


@app.route("/internal/officer/cases", methods=["GET"])
def officer_cases():
    """Danh sách hồ sơ đã được người dân yêu cầu tiếp nhận.

    Endpoint này chỉ dành cho mạng/cổng cán bộ phía sau xác thực. Nó không trả
    Zalo ID; nội dung hội thoại không nằm trong bảng hồ sơ.
    """
    if not OFFICER_API_TOKEN:
        return jsonify({"error": "Cổng cán bộ chưa được cấu hình."}), 503
    if not _officer_authorized():
        return jsonify({"error": "Không được phép."}), 401
    return jsonify({"cases": cases.list_cases(
        queue_code=request.args.get("queue"),
        limit=request.args.get("limit", 50),
    )}), 200


@app.route("/zalo/webhook", methods=["GET", "POST"])
def zalo_webhook():
    if request.method == "GET":
        return "OK", 200
    if not ZALO_WEBHOOK_ENABLED:
        # Zalo validates webhook URLs with a POST request and accepts only 200.
        # Until the signed live integration is enabled, acknowledge configuration
        # without reading, storing, or queuing the supplied event.
        return jsonify({"success": True, "status": "webhook_configuration_pending"}), 200
    raw_body = request.get_data(cache=True, as_text=True)
    data = request.get_json(silent=True) or {}
    if not _valid_zalo_webhook_signature(data, raw_body):
        # Không log nội dung tin nhắn, Zalo ID, chữ ký hoặc secret.
        app.logger.warning("Rejected Zalo webhook with invalid signature")
        return jsonify({"success": False}), 401
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
    if not ZALO_WEBHOOK_ENABLED:
        return dynamic_response("Trợ lý AI đang ở chế độ pilot nội bộ, chưa nhận tin nhắn Zalo công khai.")
    request_started = time.perf_counter()
    trace_id = new_trace_id()
    uid = _zalo_dynamic_uid()
    if not uid:
        log_zalo_latency(app.logger, {
            "trace_id": trace_id,
            "pending_wait_ms": 0.0,
            "total_ms": round((time.perf_counter() - request_started) * 1000, 2),
            "fallback_reason": "pending_missing",
            "model_used": DYNAMIC_ANSWER_MODEL,
            "retrieved_unit_count": 0,
        })
        return dynamic_response(
            "Phiên trò chuyện chưa được liên kết. Anh/chị vui lòng gửi lại tin nhắn qua OA."
        )
    pending_started = time.perf_counter()
    item = pending.pop(user_id=uid)
    pending_wait_ms = round((time.perf_counter() - pending_started) * 1000, 2)
    if not item:
        log_zalo_latency(app.logger, {
            "trace_id": trace_id,
            "pending_wait_ms": pending_wait_ms,
            "total_ms": round((time.perf_counter() - request_started) * 1000, 2),
            "fallback_reason": "pending_missing",
            "model_used": DYNAMIC_ANSWER_MODEL,
            "retrieved_unit_count": 0,
        })
        return dynamic_response("Anh/chị vui lòng nhập câu hỏi cần hỗ trợ.")
    try:
        result = core.chat(item["user_id"], item["text"], dynamic=True, trace_id=trace_id)
        telemetry = result.pop("_telemetry", {})
        telemetry["pending_wait_ms"] = pending_wait_ms
        telemetry["total_ms"] = round((time.perf_counter() - request_started) * 1000, 2)
        log_zalo_latency(app.logger, telemetry)
        return dynamic_response(result["answer"])
    except Exception as exc:
        # Không ghi nội dung câu hỏi hoặc dữ liệu cá nhân vào log.
        log_zalo_latency(app.logger, {
            "trace_id": trace_id,
            "pending_wait_ms": pending_wait_ms,
            "total_ms": round((time.perf_counter() - request_started) * 1000, 2),
            "fallback_reason": "llm_timeout" if isinstance(exc, LLMTimeout) else "llm_error",
            "model_used": DYNAMIC_ANSWER_MODEL,
            "retrieved_unit_count": 0,
        })
        app.logger.error("Zalo AI Core error type=%s trace_id=%s", type(exc).__name__, trace_id)
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
    app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
