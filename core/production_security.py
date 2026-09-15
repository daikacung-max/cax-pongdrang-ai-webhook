"""Production HTTP hardening for CAX PƠNG DRANG AI CORE.

This module keeps security policy at the application boundary: request-size
limits, production-only route guards, lightweight abuse protection and response
headers. It does not alter legal reasoning or Notebook retrieval.
"""

from collections import defaultdict, deque
import hmac
import os
from threading import Lock
import time

from flask import jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from config import PRODUCTION_MODE


_API_CHAT_TOKEN = os.getenv("API_CHAT_TOKEN", "").strip()
_ENABLE_DEBUG_ENDPOINTS = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() in ("1", "true", "yes", "on")
_MAX_REQUEST_BYTES = max(4096, int(os.getenv("MAX_REQUEST_BYTES", "32768")))
_DEMO_RATE_PER_MINUTE = max(1, int(os.getenv("DEMO_RATE_PER_MINUTE", "20")))
_API_RATE_PER_MINUTE = max(1, int(os.getenv("API_RATE_PER_MINUTE", "60")))

_hits = defaultdict(deque)
_hits_lock = Lock()


def _client_key():
    # ProxyFix(x_for=1) makes remote_addr represent the client behind Render's
    # trusted edge proxy. We never log or persist this value.
    return str(request.remote_addr or "unknown")


def _allowed(bucket, limit, window_seconds=60):
    now = time.monotonic()
    cutoff = now - float(window_seconds)
    key = (bucket, _client_key())
    with _hits_lock:
        q = _hits[key]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= int(limit):
            return False
        q.append(now)
        if len(_hits) > 5000:
            stale = [k for k, values in _hits.items() if not values or values[-1] < cutoff]
            for old in stale[:1000]:
                _hits.pop(old, None)
        return True


def _bearer_token():
    value = str(request.headers.get("Authorization") or "").strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""


def register_production_security(app):
    """Attach idempotent production guards to a Flask app."""
    if app.extensions.get("cax_production_security"):
        return
    app.extensions["cax_production_security"] = True

    app.config["MAX_CONTENT_LENGTH"] = _MAX_REQUEST_BYTES
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.before_request
    def _production_request_guard():
        path = request.path or ""

        # Enforce the limit before a view function decides whether to parse the
        # body. This closes endpoints that could otherwise accept a large body
        # without touching request.data/request.json.
        content_length = request.content_length
        if content_length is not None and content_length > _MAX_REQUEST_BYTES:
            return jsonify({"error": "Yêu cầu vượt quá kích thước cho phép."}), 413

        if PRODUCTION_MODE and path.startswith("/debug/") and not _ENABLE_DEBUG_ENDPOINTS:
            return jsonify({"error": "Not found"}), 404

        if path == "/api/chat" and PRODUCTION_MODE:
            if not _API_CHAT_TOKEN:
                return jsonify({"error": "Not found"}), 404
            supplied = _bearer_token()
            if not supplied or not hmac.compare_digest(supplied, _API_CHAT_TOKEN):
                return jsonify({"error": "Không được phép."}), 401
            if not _allowed("api_chat", _API_RATE_PER_MINUTE):
                return jsonify({"error": "Quá nhiều yêu cầu. Vui lòng thử lại sau."}), 429

        if path in ("/demo/api/ai-chat", "/demo/api/chat"):
            if not _allowed("demo_chat", _DEMO_RATE_PER_MINUTE):
                return jsonify({"error": "Demo đang nhận quá nhiều yêu cầu. Vui lòng thử lại sau."}), 429

        return None

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if PRODUCTION_MODE:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith(("/api/", "/internal/", "/debug/", "/health", "/zalo/")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response
