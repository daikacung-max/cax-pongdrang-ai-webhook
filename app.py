"""Stable WSGI entrypoint for CAX PƠNG DRANG AI CORE."""

import hashlib
import hmac
import os
import secrets
import sys
import time
from urllib.parse import urlencode

from flask import redirect
import app_core as _app_core
import core.service as _service_module
from adapters.vbee_tts import blueprint as vbee_blueprint
from adapters.readiness import blueprint as readiness_blueprint
from adapters.self_test import blueprint as self_test_blueprint
from adapters.demo_ai import blueprint as demo_ai_blueprint
from adapters.forms import blueprint as citizen_forms_blueprint
from adapters.zalo_oa_api import ZaloOAClient
from config import (
    LOCAL_BIND_HOST,
    PERSISTENCE_REQUIRED,
    ZALO_APP_ID,
    ZALO_APP_SECRET_KEY,
    ZALO_OA_ACCESS_TOKEN,
    ZALO_OA_REFRESH_TOKEN,
    ZALO_OAUTH_CALLBACK_URL,
)
from core import db as _form_db
from core.artifact_planner import enrich_plan as enrich_artifact_plan
from core.current_knowledge import ensure_current_knowledge
from core.current_fallback import grounded_dynamic_fallback as current_grounded_fallback
from core.form_documents import handle_form_request
from core.llm import LLMError, LLMTimeout
from core.notebook_current_sources import ensure_notebook_current_sources
from core.notebook_retrieval import retrieve as notebook_retrieve
from core.privacy import delete_zalo_subject_data
from core.history import persistence_ready as history_persistence_ready
from core.production_security import register_production_security
from core.source_guard import merge_verification
from core.zalo_jobs import (
    delete_for_user as delete_zalo_jobs_for_user,
    enqueue as enqueue_zalo_reply,
    operational_ready as zalo_dispatch_persistence_ready,
    start_worker as start_zalo_worker,
)
from core.zalo_token_store import (
    load_refresh_token,
    operational_ready as zalo_token_persistence_ready,
    save_refresh_token,
)


_original_ensure_legal_db = _app_core.ensure_legal_db


def _ensure_legal_db_with_current_sources():
    _original_ensure_legal_db()
    ensure_current_knowledge()
    ensure_notebook_current_sources()


_app_core.ensure_legal_db = _ensure_legal_db_with_current_sources
ensure_current_knowledge()
ensure_notebook_current_sources()

_original_service_plan = _service_module.plan


def _artifact_first_plan(question, history, dynamic=False, safety_identifier=None):
    base = _original_service_plan(
        question,
        history,
        dynamic=dynamic,
        safety_identifier=safety_identifier,
    )
    return enrich_artifact_plan(question, base)


_service_module.plan = _artifact_first_plan
_service_module.retrieve = notebook_retrieve
_service_module.grounded_dynamic_fallback = current_grounded_fallback
_app_core.grounded_dynamic_fallback = current_grounded_fallback

_original_service_verify = _service_module.verify
_original_service_verify_dynamic = _service_module.verify_dynamic_text


def _verify_with_source_guard(draft, retrieved_units, question=""):
    result = _original_service_verify(draft, retrieved_units, question=question)
    return merge_verification(result, (draft or {}).get("answer", ""), retrieved_units)


def _verify_dynamic_with_source_guard(answer, retrieved_units, question=""):
    result = _original_service_verify_dynamic(answer, retrieved_units, question=question)
    return merge_verification(result, answer, retrieved_units)


_service_module.verify = _verify_with_source_guard
_service_module.verify_dynamic_text = _verify_dynamic_with_source_guard

# Form/document generation is strictly opt-in. If the citizen is not explicitly
# asking to print/fill/export a form, the original AI Core call is untouched.
_original_core_chat = _app_core.core.chat


def _chat_with_citizen_forms(user_id, question, dynamic=False, trace_id=None):
    history = _form_db.get_history(str(user_id or ""), limit=20)
    try:
        form_result = handle_form_request(user_id, question, history=history)
    except RuntimeError:
        form_result = None
    if not form_result:
        return _original_core_chat(user_id, question, dynamic=dynamic, trace_id=trace_id)

    answer = str(form_result.get("answer") or "").strip()
    meta = {
        "legal": False,
        "retrieved_unit_ids": [],
        "verified": True,
        "repaired": False,
        "verification_errors": [],
        "dynamic": bool(dynamic),
        "path": "citizen_form_assistant",
        "form_type": form_result.get("form_type"),
        "form_ready": bool(form_result.get("ready")),
        "download_url": form_result.get("download_url"),
        "model": "deterministic-form-engine",
        "provider": "local",
        "intake": {"handoff_status": "not_requested"},
        "handoff": None,
    }
    _form_db.add_message(user_id, "user", str(question or ""), meta={"path": "citizen_form_assistant"})
    _form_db.add_message(user_id, "assistant", answer, meta=meta)
    return {"answer": answer, "meta": meta, "handoff": None, "_telemetry": {}}


_app_core.core.chat = _chat_with_citizen_forms


def _official_zalo_signature(data, raw_body):
    """Validate Zalo's documented SHA-256 webhook signature."""
    if not _app_core.ZALO_WEBHOOK_SIGNATURE_REQUIRED:
        return True

    secret = str(_app_core.ZALO_OA_SECRET_KEY or "").strip()
    if not secret:
        _app_core.app.logger.warning("zalo_webhook signature_reject reason=missing_secret")
        return False

    incoming_app_id = str((data or {}).get("app_id") or "").strip()
    timestamp = str((data or {}).get("timestamp") or "").strip()
    supplied = str(_app_core.request.headers.get("X-ZEvent-Signature") or "").strip()
    if supplied.lower().startswith("mac="):
        supplied = supplied[4:].strip()
    if not incoming_app_id or not timestamp or not supplied:
        _app_core.app.logger.warning("zalo_webhook signature_reject reason=missing_signed_fields")
        return False

    signed_value = f"{incoming_app_id}{raw_body}{timestamp}{secret}".encode("utf-8")
    expected = hashlib.sha256(signed_value).hexdigest()
    valid = hmac.compare_digest(supplied.lower(), expected)
    if not valid:
        _app_core.app.logger.warning("zalo_webhook signature_reject reason=digest_mismatch")
        return False

    configured_app_id = str(_app_core.ZALO_APP_ID or "").strip()
    if configured_app_id and not hmac.compare_digest(incoming_app_id, configured_app_id):
        _app_core.app.logger.warning("zalo_webhook signature_valid config_app_id_drift=true")
    return True


_app_core._valid_zalo_webhook_signature = _official_zalo_signature

_original_zalo_webhook = _app_core.app.view_functions.get("zalo_webhook")


def _hardened_zalo_webhook():
    """Handle privacy and durable direct-reply dispatch before legacy routing."""
    if _app_core.request.method != "POST" or not _app_core.ZALO_WEBHOOK_ENABLED:
        return _original_zalo_webhook()

    raw_body = _app_core.request.get_data(cache=True, as_text=True)
    # Zalo Developers verifies a webhook URL with an empty POST before it
    # begins delivering signed OA events.  There is no user payload to trust
    # or process in that probe, so acknowledge it immediately while keeping
    # signature verification mandatory for every non-empty webhook event.
    if not raw_body.strip():
        _app_core._log_zalo_webhook("verification_probe", "")
        return _app_core.jsonify({"success": True, "status": "verification_probe"}), 200

    data = _app_core.request.get_json(silent=True) or {}
    event_name = str(data.get("event_name") or "").strip()

    if event_name == "user_withdraw":
        if not _app_core._valid_zalo_webhook_signature(data, raw_body):
            _app_core._log_zalo_webhook("rejected_signature", event_name)
            return _app_core.jsonify({"success": False}), 401
        for field in ("user_id", "user_id_by_app"):
            value = str(data.get(field) or "").strip()
            if value:
                _app_core.pending.purge_user(value)
                delete_zalo_jobs_for_user(value)
        delete_zalo_subject_data(data)
        _app_core._log_zalo_webhook("subject_data_deleted", event_name)
        return _app_core.jsonify({"success": True}), 200

    if (
        event_name == "user_send_text"
        and _app_core.ZALO_DIRECT_REPLY_ENABLED
        and zalo_dispatch_persistence_ready()
    ):
        if not _app_core._valid_zalo_webhook_signature(data, raw_body):
            _app_core._log_zalo_webhook("rejected_signature", event_name)
            return _app_core.jsonify({"success": False}), 401
        sender = data.get("sender") or {}
        message = data.get("message") or {}
        user_id = str(sender.get("id") or "").strip()
        text = str(message.get("text") or "").strip()
        msg_id = str(message.get("msg_id") or "").strip()
        if not user_id or not text:
            _app_core._log_zalo_webhook("ignored_empty", event_name)
            return _app_core.jsonify({"success": True}), 200
        event_key = msg_id or hashlib.sha256(raw_body.encode("utf-8")).hexdigest()
        try:
            queued = enqueue_zalo_reply(event_key, user_id, text)
        except Exception as exc:
            _app_core.app.logger.error("zalo_dispatch enqueue_failed type=%s", type(exc).__name__)
            queued = False
        if not queued:
            _app_core._log_zalo_webhook("queue_unavailable", event_name)
            return _app_core.jsonify({"success": False}), 503
        _app_core._log_zalo_webhook("queued", event_name)
        return _app_core.jsonify({"success": True}), 200

    return _original_zalo_webhook()


if _original_zalo_webhook is not None:
    _app_core.app.view_functions["zalo_webhook"] = _hardened_zalo_webhook

_durable_token_store = zalo_token_persistence_ready()
_durable_dispatch_store = zalo_dispatch_persistence_ready()
if PERSISTENCE_REQUIRED and not (
    history_persistence_ready() and _durable_token_store and _durable_dispatch_store
):
    raise RuntimeError("Production persistence is required but Postgres or encryption is unavailable")
_runtime_refresh_token = load_refresh_token(ZALO_OA_REFRESH_TOKEN)
_app_core.zalo_oa_client = ZaloOAClient(
    ZALO_OA_ACCESS_TOKEN,
    refresh_token=_runtime_refresh_token,
    app_id=ZALO_APP_ID,
    app_secret=ZALO_APP_SECRET_KEY,
    persist_refresh_token=save_refresh_token if _durable_token_store else None,
)


_OAUTH_STATE_TTL_SECONDS = 600


def _oauth_state(timestamp=None, nonce=None):
    """Make a short-lived signed state without keeping OAuth state in memory."""
    timestamp = int(timestamp or time.time())
    nonce = str(nonce or secrets.token_urlsafe(18))
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(
        ZALO_APP_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"


def _valid_oauth_state(value):
    try:
        timestamp, nonce, supplied = str(value or "").split(".", 2)
        issued_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    if not nonce or abs(time.time() - issued_at) > _OAUTH_STATE_TTL_SECONDS:
        return False
    expected = _oauth_state(timestamp=issued_at, nonce=nonce).rsplit(".", 1)[1]
    return hmac.compare_digest(str(supplied), expected)


@_app_core.app.get("/zalo/oauth/start")
def zalo_oauth_start():
    """Begin OA authorization without placing tokens in URLs or logs."""
    if not (ZALO_APP_ID and ZALO_APP_SECRET_KEY and ZALO_OAUTH_CALLBACK_URL):
        return _app_core.jsonify({"success": False, "reason": "oauth_not_configured"}), 503
    query = urlencode({
        "app_id": ZALO_APP_ID,
        "redirect_uri": ZALO_OAUTH_CALLBACK_URL,
        "state": _oauth_state(),
    })
    return redirect(f"https://oauth.zaloapp.com/v4/oa/permission?{query}")


@_app_core.app.get("/zalo/oauth/callback")
def zalo_oauth_callback():
    """Exchange a Zalo OA authorization code and persist only encrypted state."""
    code = str(_app_core.request.args.get("code") or "").strip()
    state = str(_app_core.request.args.get("state") or "").strip()
    if not code or not _valid_oauth_state(state):
        return _app_core.jsonify({"success": False, "reason": "oauth_callback_rejected"}), 400
    try:
        _app_core.zalo_oa_client.bootstrap_from_authorization_code(code)
    except Exception as exc:
        _app_core.app.logger.warning("zalo_oauth bootstrap_failed type=%s", type(exc).__name__)
        return _app_core.jsonify({"success": False, "reason": "oauth_exchange_failed"}), 502
    return _app_core.jsonify({"success": True, "status": "oauth_authorized"}), 200


def _resilient_direct_zalo_reply(user_id, text, trace_id):
    """Reply through OA and never turn a transient AI failure into silence."""
    if not _app_core.ZALO_DIRECT_REPLY_ENABLED:
        return False
    try:
        result = _app_core.core.chat(user_id, text, dynamic=True, trace_id=trace_id)
        result.pop("_telemetry", None)
        answer = result["answer"]
    except (LLMError, LLMTimeout):
        _app_core.app.logger.warning("zalo_direct_reply ai_fallback=true")
        answer = (
            f"Trợ lý AI tạm thời chưa hoàn tất được phần phân tích. "
            f"Anh/chị có thể gửi lại tin nhắn hoặc liên hệ trực ban "
            f"{_app_core.UNIT_NAME} qua số {_app_core.HOTLINE}."
        )
    _app_core.zalo_oa_client.send_text(user_id, answer)
    return True


_app_core._direct_zalo_reply = _resilient_direct_zalo_reply

if _app_core.ZALO_DIRECT_REPLY_ENABLED and _durable_dispatch_store:
    start_zalo_worker(
        lambda user_id, text: _resilient_direct_zalo_reply(
            user_id, text, _app_core.new_trace_id()
        ),
        logger=_app_core.app.logger,
    )

if "vbee_tts" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(vbee_blueprint)
if "ai_core_readiness" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(readiness_blueprint)
if "ai_core_self_test" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(self_test_blueprint)
if "ai_core_demo_ai" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(demo_ai_blueprint)
if "citizen_forms" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(citizen_forms_blueprint)

register_production_security(_app_core.app)

sys.modules[__name__] = _app_core


if __name__ == "__main__":
    _app_core.app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
