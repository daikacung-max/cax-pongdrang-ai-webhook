"""Stable WSGI entrypoint for CAX PƠNG DRANG AI CORE.

The implementation lives in :mod:`app_core`. After optional integrations are
mounted, ``app`` is aliased to that runtime module so legacy imports/patches and
production routes always reference the same state.
"""

import hashlib
import hmac
import os
import sys

import app_core as _app_core
import core.service as _service_module
from adapters.vbee_tts import blueprint as vbee_blueprint
from adapters.readiness import blueprint as readiness_blueprint
from adapters.self_test import blueprint as self_test_blueprint
from adapters.demo_ai import blueprint as demo_ai_blueprint
from adapters.zalo_oa_api import ZaloOAClient
from config import (
    LOCAL_BIND_HOST,
    ZALO_APP_ID,
    ZALO_APP_SECRET_KEY,
    ZALO_OA_ACCESS_TOKEN,
    ZALO_OA_REFRESH_TOKEN,
)
from core.artifact_planner import enrich_plan as enrich_artifact_plan
from core.current_knowledge import ensure_current_knowledge
from core.current_fallback import grounded_dynamic_fallback as current_grounded_fallback
from core.llm import LLMError, LLMTimeout
from core.notebook_current_sources import ensure_notebook_current_sources
from core.notebook_retrieval import retrieve as notebook_retrieve
from core.source_guard import merge_verification


_original_ensure_legal_db = _app_core.ensure_legal_db


def _ensure_legal_db_with_current_sources():
    _original_ensure_legal_db()
    ensure_current_knowledge()
    ensure_notebook_current_sources()


_app_core.ensure_legal_db = _ensure_legal_db_with_current_sources
ensure_current_knowledge()
ensure_notebook_current_sources()

# Artifact-first planner: an input that belongs to one of the 19 sources can no
# longer be silently reclassified outside the user's work by an LLM planner.
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

# Artifact-first retrieval. Current official documents are only support/update
# data behind the selected artifact source.
_service_module.retrieve = notebook_retrieve

# Dynamic and API-boundary fallbacks must use the current verification layer.
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

# Runtime OA client supports both a pre-provisioned access token and OAuth v4
# refresh credentials. This lets direct reply recover automatically when an
# access token expires without changing the AI Core path.
_app_core.zalo_oa_client = ZaloOAClient(
    ZALO_OA_ACCESS_TOKEN,
    refresh_token=ZALO_OA_REFRESH_TOKEN,
    app_id=ZALO_APP_ID,
    app_secret=ZALO_APP_SECRET_KEY,
)


def _resilient_direct_zalo_reply(user_id, text, trace_id):
    """Reply through OA and never turn a transient AI failure into silence.

    If the model/provider times out, OA still receives a short safe operational
    notice with the one approved hotline. OA transport errors are intentionally
    re-raised because pretending a message was delivered would be worse than a
    visible delivery failure in telemetry.
    """
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

if "vbee_tts" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(vbee_blueprint)
if "ai_core_readiness" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(readiness_blueprint)
if "ai_core_self_test" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(self_test_blueprint)
if "ai_core_demo_ai" not in _app_core.app.blueprints:
    _app_core.app.register_blueprint(demo_ai_blueprint)

sys.modules[__name__] = _app_core


if __name__ == "__main__":
    _app_core.app.run(host=LOCAL_BIND_HOST, port=int(os.getenv("PORT", "10000")))
