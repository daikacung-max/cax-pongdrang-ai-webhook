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
from config import LOCAL_BIND_HOST
from core.artifact_planner import enrich_plan as enrich_artifact_plan
from core.current_knowledge import ensure_current_knowledge
from core.current_fallback import grounded_dynamic_fallback as current_grounded_fallback
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
    """Validate Zalo's documented SHA-256 webhook signature.

    The app_id participating in the signature is the app_id carried by the
    signed webhook payload itself. A stale/mistyped local ZALO_APP_ID must not
    reject an otherwise cryptographically valid event. The OA secret remains
    mandatory, so accepting app-id drift does not bypass signature security.
    """
    if not _app_core.ZALO_WEBHOOK_SIGNATURE_REQUIRED:
        return True
    secret = str(_app_core.ZALO_OA_SECRET_KEY or "").strip()
    if not secret:
        return False

    incoming_app_id = str((data or {}).get("app_id") or "").strip()
    timestamp = str((data or {}).get("timestamp") or "").strip()
    supplied = str(_app_core.request.headers.get("X-ZEvent-Signature") or "").strip()
    if supplied.lower().startswith("mac="):
        supplied = supplied[4:].strip()
    if not incoming_app_id or not timestamp or not supplied:
        return False

    signed_value = f"{incoming_app_id}{raw_body}{timestamp}{secret}".encode("utf-8")
    expected = hashlib.sha256(signed_value).hexdigest()
    valid = hmac.compare_digest(supplied.lower(), expected)
    configured_app_id = str(_app_core.ZALO_APP_ID or "").strip()
    if valid and configured_app_id and not hmac.compare_digest(incoming_app_id, configured_app_id):
        # Safe operational signal only. Never log either identifier or the secret.
        _app_core.app.logger.warning("zalo_webhook signature_valid config_app_id_drift=true")
    return valid


# Replace the stricter legacy validator at runtime. The route in app_core looks
# up this module-global function on every request, so production and tests share
# the same behavior.
_app_core._valid_zalo_webhook_signature = _official_zalo_signature

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
