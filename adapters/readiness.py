from flask import Blueprint, jsonify

from config import (
    DATABASE_URL,
    ENABLE_DEMO_CONSOLE,
    GROQ_API_KEY,
    HISTORY_HMAC_SECRET,
    OPENAI_API_KEY,
    MODEL_ROUTING_MODE,
    PERSISTENCE_REQUIRED,
    PRODUCTION_MODE,
    ZALO_WEBHOOK_ENABLED,
    ZALO_WEBHOOK_SIGNATURE_REQUIRED,
    ZALO_APP_ID,
    ZALO_OA_SECRET_KEY,
    ZALO_OA_ACCESS_TOKEN,
    ZALO_OA_REFRESH_TOKEN,
    ZALO_APP_SECRET_KEY,
    ZALO_DIRECT_REPLY_ENABLED,
    ZALO_REPLY_MODE,
)
from core.history import persistence_ready as history_persistence_ready
from core.zalo_jobs import operational_ready as zalo_dispatch_persistence_ready
from core.zalo_token_store import (
    operational_ready as zalo_token_persistence_ready,
    refresh_token_available as zalo_refresh_token_available,
)


blueprint = Blueprint("ai_core_readiness", __name__)


def _state():
    signature_secret_ready = bool(ZALO_OA_SECRET_KEY)
    signature_config_complete = bool(ZALO_APP_ID and ZALO_OA_SECRET_KEY)
    provider_ready = bool(GROQ_API_KEY or OPENAI_API_KEY)
    oauth_credentials_ready = bool(ZALO_APP_ID and ZALO_APP_SECRET_KEY)
    durable_refresh_token_ready = bool(zalo_refresh_token_available(ZALO_OA_REFRESH_TOKEN))
    oauth_refresh_ready = bool(oauth_credentials_ready and durable_refresh_token_ready)
    direct_reply_ready = bool(ZALO_OA_ACCESS_TOKEN or oauth_refresh_ready)
    token_persistence = bool(zalo_token_persistence_ready())
    dispatch_persistence = bool(zalo_dispatch_persistence_ready())
    history_persistence = bool(history_persistence_ready())
    end_to_end_reply_ready = bool(
        ZALO_WEBHOOK_ENABLED
        and signature_secret_ready
        and ZALO_DIRECT_REPLY_ENABLED
        and direct_reply_ready
        and token_persistence
        and dispatch_persistence
    )
    return {
        "production_mode": bool(PRODUCTION_MODE),
        "model_routing_mode": MODEL_ROUTING_MODE,
        "groq_provider_ready": bool(GROQ_API_KEY),
        "openai_provider_ready": bool(OPENAI_API_KEY),
        "provider_ready": provider_ready,
        "persistence_required": bool(PERSISTENCE_REQUIRED),
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
        "zalo_refresh_token_present": durable_refresh_token_ready,
        "zalo_oauth_credentials_ready": oauth_credentials_ready,
        "zalo_oauth_refresh_ready": oauth_refresh_ready,
        "zalo_token_persistence_ready": token_persistence,
        "zalo_dispatch_persistence_ready": dispatch_persistence,
        "zalo_end_to_end_reply_ready": end_to_end_reply_ready,
    }


@blueprint.get("/health/readiness")
def readiness():
    """Operational facts without exposing any credential or identifier."""
    return jsonify(_state()), 200


@blueprint.get("/health/go-live")
def go_live():
    """Fail closed until all conditions for official public operation are met."""
    state = _state()
    checks = {
        "production_mode": state["production_mode"],
        "llm_provider": state["provider_ready"],
        "persistent_history": state["history_persistence_ready"],
        "zalo_webhook": state["zalo_webhook_enabled"],
        "zalo_signature": state["zalo_signature_required"] and state["zalo_signature_ready"],
        "zalo_direct_reply": state["zalo_direct_reply_enabled"] and state["zalo_direct_reply_ready"],
        "zalo_oauth_refresh": state["zalo_oauth_refresh_ready"],
        "zalo_refresh_persistence": state["zalo_token_persistence_ready"],
        "zalo_durable_dispatch": state["zalo_dispatch_persistence_ready"],
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
