from flask import Blueprint, jsonify

from config import (
    DATABASE_URL,
    ENABLE_DEMO_CONSOLE,
    GROQ_API_KEY,
    HISTORY_HMAC_SECRET,
    OPENAI_API_KEY,
    MODEL_ROUTING_MODE,
    PRODUCTION_MODE,
    ZALO_WEBHOOK_ENABLED,
    ZALO_WEBHOOK_SIGNATURE_REQUIRED,
    ZALO_APP_ID,
    ZALO_OA_SECRET_KEY,
    ZALO_OA_ACCESS_TOKEN,
    ZALO_OA_REFRESH_TOKEN,
    ZALO_OAUTH_REFRESH_READY,
    ZALO_DIRECT_REPLY_ENABLED,
    ZALO_REPLY_MODE,
)
from core.zalo_token_store import persistence_ready as zalo_token_persistence_ready


blueprint = Blueprint("ai_core_readiness", __name__)


def _state():
    signature_secret_ready = bool(ZALO_OA_SECRET_KEY)
    signature_config_complete = bool(ZALO_APP_ID and ZALO_OA_SECRET_KEY)
    provider_ready = bool(GROQ_API_KEY or OPENAI_API_KEY)
    direct_reply_ready = bool(ZALO_OA_ACCESS_TOKEN or ZALO_OAUTH_REFRESH_READY)
    token_persistence = bool(zalo_token_persistence_ready())
    history_persistence = bool(DATABASE_URL and HISTORY_HMAC_SECRET)
    end_to_end_reply_ready = bool(
        ZALO_WEBHOOK_ENABLED
        and signature_secret_ready
        and ZALO_DIRECT_REPLY_ENABLED
        and direct_reply_ready
    )
    return {
        "production_mode": bool(PRODUCTION_MODE),
        "model_routing_mode": MODEL_ROUTING_MODE,
        "groq_provider_ready": bool(GROQ_API_KEY),
        "openai_provider_ready": bool(OPENAI_API_KEY),
        "provider_ready": provider_ready,
        "history_persistence_ready": history_persistence,
        "demo_console_enabled": bool(ENABLE_DEMO_CONSOLE),
        "zalo_webhook_enabled": bool(ZALO_WEBHOOK_ENABLED),
        "zalo_signature_required": bool(ZALO_WEBHOOK_SIGNATURE_REQUIRED),
        "zalo_signature_ready": signature_config_complete,
        "zalo_signature_secret_ready": signature_secret_ready,
        "zalo_configured_app_id": bool(ZALO_APP_ID),
        "zalo_reply_mode": ZALO_REPLY_MODE,
        "zalo_direct_reply_enabled": bool(ZALO_DIRECT_REPLY_ENABLED),
        "zalo_direct_reply_ready": direct_reply_ready,
        "zalo_access_token_present": bool(ZALO_OA_ACCESS_TOKEN),
        "zalo_refresh_token_present": bool(ZALO_OA_REFRESH_TOKEN),
        "zalo_oauth_refresh_ready": bool(ZALO_OAUTH_REFRESH_READY),
        "zalo_token_persistence_ready": token_persistence,
        "zalo_end_to_end_reply_ready": end_to_end_reply_ready,
    }


@blueprint.get("/health/readiness")
def readiness():
    """Operational facts without exposing any credential or identifier."""
    return jsonify(_state()), 200


@blueprint.get("/health/go-live")
def go_live():
    """Fail closed until all conditions for official public operation are met.

    This endpoint is intentionally stricter than /health/readiness. A healthy
    pilot must not be mistaken for an officially launch-ready public service.
    """
    state = _state()
    checks = {
        "production_mode": state["production_mode"],
        "llm_provider": state["provider_ready"],
        "persistent_history": state["history_persistence_ready"],
        "zalo_webhook": state["zalo_webhook_enabled"],
        "zalo_signature": state["zalo_signature_required"] and state["zalo_signature_ready"],
        "zalo_direct_reply": state["zalo_direct_reply_enabled"] and state["zalo_direct_reply_ready"],
        # Access tokens are short lived. Official direct-reply operation needs
        # refresh credentials and durable encrypted rotation across restarts.
        "zalo_oauth_refresh": state["zalo_oauth_refresh_ready"],
        "zalo_refresh_persistence": state["zalo_token_persistence_ready"],
        # The public test console is a pre-production surface and should be
        # disabled before the OA is opened for official operation.
        "public_demo_disabled": not state["demo_console_enabled"],
    }
    blockers = [name for name, ok in checks.items() if not ok]
    ready = not blockers
    return jsonify({
        "status": "ready" if ready else "blocked",
        "ready_for_official_operation": ready,
        "checks": checks,
        "blockers": blockers,
    }), 200 if ready else 503
