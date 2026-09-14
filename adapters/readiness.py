from flask import Blueprint, jsonify

from config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    MODEL_ROUTING_MODE,
    PRODUCTION_MODE,
    ZALO_WEBHOOK_ENABLED,
    ZALO_WEBHOOK_SIGNATURE_REQUIRED,
    ZALO_APP_ID,
    ZALO_OA_SECRET_KEY,
    ZALO_OA_ACCESS_TOKEN,
    ZALO_DIRECT_REPLY_ENABLED,
    ZALO_REPLY_MODE,
)


blueprint = Blueprint("ai_core_readiness", __name__)


@blueprint.get("/health/readiness")
def readiness():
    """Operational readiness without exposing any credential or identifier."""
    signature_secret_ready = bool(ZALO_OA_SECRET_KEY)
    signature_config_complete = bool(ZALO_APP_ID and ZALO_OA_SECRET_KEY)
    direct_reply_ready = bool(ZALO_OA_ACCESS_TOKEN)
    # We only call Zalo end-to-end ready when this service itself can send the
    # reply back through OA API. Dynamic mode can still be used by a separately
    # configured Zalo consumer, but that external configuration is not
    # observable from Render and therefore must not be reported as proven here.
    end_to_end_reply_ready = bool(
        ZALO_WEBHOOK_ENABLED and signature_secret_ready and
        ZALO_DIRECT_REPLY_ENABLED and direct_reply_ready
    )
    return jsonify({
        "production_mode": bool(PRODUCTION_MODE),
        "model_routing_mode": MODEL_ROUTING_MODE,
        "groq_provider_ready": bool(GROQ_API_KEY),
        "openai_provider_ready": bool(OPENAI_API_KEY),
        "zalo_webhook_enabled": bool(ZALO_WEBHOOK_ENABLED),
        "zalo_signature_required": bool(ZALO_WEBHOOK_SIGNATURE_REQUIRED),
        "zalo_signature_ready": signature_config_complete,
        "zalo_signature_secret_ready": signature_secret_ready,
        "zalo_configured_app_id": bool(ZALO_APP_ID),
        "zalo_reply_mode": ZALO_REPLY_MODE,
        "zalo_direct_reply_enabled": bool(ZALO_DIRECT_REPLY_ENABLED),
        "zalo_direct_reply_ready": direct_reply_ready,
        "zalo_end_to_end_reply_ready": end_to_end_reply_ready,
    }), 200
