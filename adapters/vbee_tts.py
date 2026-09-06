"""Vbee AIVoice Text-to-Speech adapter.

This module deliberately keeps Vbee isolated from the legal/chat core. If Vbee is
not configured or temporarily unavailable, the rest of CAX Pơng Drang AI Core
continues to run normally.
"""

from __future__ import annotations

from collections import OrderedDict
import hmac
import logging
import os
import re
import threading
from typing import Any

import requests
from flask import Blueprint, jsonify, request, url_for


log = logging.getLogger(__name__)
blueprint = Blueprint("vbee", __name__)

VBEE_API_BASE = os.getenv("VBEE_API_BASE", "https://vbee.vn/api/v1").rstrip("/")
VBEE_APP_ID = os.getenv("VBEE_APP_ID", "").strip()
VBEE_ACCESS_TOKEN = os.getenv("VBEE_ACCESS_TOKEN", "").strip()
VBEE_VOICE_CODE = os.getenv("VBEE_VOICE_CODE", "").strip()
VBEE_TTS_API_TOKEN = os.getenv("VBEE_TTS_API_TOKEN", "").strip()
VBEE_CALLBACK_SECRET = os.getenv("VBEE_CALLBACK_SECRET", "").strip()
VBEE_AUDIO_TYPE = os.getenv("VBEE_AUDIO_TYPE", "mp3").strip().lower() or "mp3"
VBEE_SPEED_RATE = float(os.getenv("VBEE_SPEED_RATE", "0.95"))
VBEE_BITRATE = int(os.getenv("VBEE_BITRATE", "128"))
VBEE_MAX_CHARS = int(os.getenv("VBEE_MAX_CHARS", "10000"))
VBEE_TIMEOUT_SECONDS = float(os.getenv("VBEE_TIMEOUT_SECONDS", "15"))

_CALLBACK_CACHE_MAX = 100
_callback_cache: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_callback_lock = threading.Lock()


class VbeeError(RuntimeError):
    pass


def configured() -> bool:
    return bool(VBEE_APP_ID and VBEE_ACCESS_TOKEN and VBEE_VOICE_CODE)


def callback_secured() -> bool:
    return bool(VBEE_CALLBACK_SECRET)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {VBEE_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _authorized() -> bool:
    """Protect quota-consuming endpoints with a separate local API token."""
    if not VBEE_TTS_API_TOKEN:
        return False
    supplied = str(request.headers.get("Authorization") or "").strip()
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    return hmac.compare_digest(supplied, VBEE_TTS_API_TOKEN)


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    # Remove lightweight Markdown that should not be spoken aloud.
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _safe_speed(value: Any) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        speed = VBEE_SPEED_RATE
    # Conservative range that remains natural for Vietnamese speech.
    return min(1.9, max(0.5, speed))


def submit_tts(
    text: str,
    *,
    callback_url: str,
    voice_code: str | None = None,
    speed_rate: float | None = None,
    audio_type: str | None = None,
) -> dict[str, Any]:
    if not configured():
        raise VbeeError("Vbee chưa được cấu hình đầy đủ trên máy chủ.")

    clean = _clean_text(text)
    if not clean:
        raise VbeeError("Văn bản trống.")
    if len(clean) > VBEE_MAX_CHARS:
        raise VbeeError(f"Văn bản vượt giới hạn {VBEE_MAX_CHARS} ký tự cho một lượt.")

    chosen_audio = str(audio_type or VBEE_AUDIO_TYPE).strip().lower()
    if chosen_audio not in {"mp3", "wav"}:
        chosen_audio = "mp3"

    payload = {
        "app_id": VBEE_APP_ID,
        "response_type": "indirect",
        "callback_url": callback_url,
        "input_text": clean,
        "voice_code": str(voice_code or VBEE_VOICE_CODE).strip(),
        "audio_type": chosen_audio,
        "bitrate": VBEE_BITRATE,
        "speed_rate": _safe_speed(speed_rate),
    }

    try:
        response = requests.post(
            f"{VBEE_API_BASE}/tts",
            headers=_auth_headers(),
            json=payload,
            timeout=VBEE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise VbeeError("Không kết nối được dịch vụ Vbee.") from exc
    except ValueError as exc:
        raise VbeeError("Vbee trả về dữ liệu không hợp lệ.") from exc

    if data.get("status") != 1:
        error_code = str(data.get("error_code") or "VBEE_ERROR")
        error_message = str(data.get("error_message") or "Vbee từ chối yêu cầu.")
        raise VbeeError(f"{error_code}: {error_message}")

    result = data.get("result") or {}
    request_id = str(result.get("request_id") or "").strip()
    if not request_id:
        raise VbeeError("Vbee không trả về request_id.")
    return result


def get_tts_status(request_id: str) -> dict[str, Any]:
    request_id = str(request_id or "").strip()
    if not request_id:
        raise VbeeError("request_id không hợp lệ.")
    if not VBEE_ACCESS_TOKEN:
        raise VbeeError("Vbee chưa được cấu hình trên máy chủ.")

    with _callback_lock:
        cached = _callback_cache.get(request_id)
        if cached:
            return dict(cached)

    try:
        response = requests.get(
            f"{VBEE_API_BASE}/tts/{request_id}",
            headers=_auth_headers(),
            timeout=VBEE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise VbeeError("Không kiểm tra được trạng thái Vbee.") from exc
    except ValueError as exc:
        raise VbeeError("Vbee trả về dữ liệu không hợp lệ.") from exc

    if data.get("status") != 1:
        raise VbeeError(str(data.get("error_message") or data.get("error_code") or "Vbee error"))
    return data.get("result") or {}


@blueprint.get("/vbee/health")
def health():
    return jsonify({
        "status": "ok",
        "provider": "vbee",
        "configured": configured(),
        "callback_secured": callback_secured(),
        "voice_configured": bool(VBEE_VOICE_CODE),
        "audio_type": VBEE_AUDIO_TYPE,
        "speed_rate": VBEE_SPEED_RATE,
        "max_chars": VBEE_MAX_CHARS,
    }), 200


@blueprint.post("/api/tts")
def create_audio():
    if not _authorized():
        return jsonify({"error": "Không được phép."}), 401
    if not configured():
        return jsonify({"error": "Vbee chưa được cấu hình đầy đủ."}), 503
    if not callback_secured():
        return jsonify({"error": "Callback Vbee chưa được bảo vệ."}), 503

    data = request.get_json(silent=True) or {}
    text = _clean_text(data.get("text"))
    if not text:
        return jsonify({"error": "text là bắt buộc."}), 400

    callback_url = url_for(
        "vbee.callback",
        key=VBEE_CALLBACK_SECRET,
        _external=True,
    )
    try:
        result = submit_tts(
            text,
            callback_url=callback_url,
            voice_code=data.get("voice_code"),
            speed_rate=data.get("speed_rate"),
            audio_type=data.get("audio_type"),
        )
    except VbeeError as exc:
        log.warning("Vbee create failed: %s", type(exc).__name__)
        return jsonify({"error": str(exc)}), 502

    return jsonify({
        "provider": "vbee",
        "request_id": result.get("request_id"),
        "status": result.get("status") or "IN_PROGRESS",
        "characters": result.get("characters"),
        "voice_code": result.get("voice_code") or data.get("voice_code") or VBEE_VOICE_CODE,
        "audio_type": result.get("audio_type") or data.get("audio_type") or VBEE_AUDIO_TYPE,
        "speed_rate": result.get("speed_rate") or data.get("speed_rate") or VBEE_SPEED_RATE,
        "audio_link": result.get("audio_link"),
    }), 202


@blueprint.get("/api/tts/<request_id>")
def audio_status(request_id: str):
    if not _authorized():
        return jsonify({"error": "Không được phép."}), 401
    try:
        result = get_tts_status(request_id)
    except VbeeError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"provider": "vbee", **result}), 200


@blueprint.post("/vbee/callback")
def callback():
    """Receive asynchronous Vbee output through an unguessable callback URL."""
    supplied_key = str(request.args.get("key") or "").strip()
    if not VBEE_CALLBACK_SECRET or not hmac.compare_digest(supplied_key, VBEE_CALLBACK_SECRET):
        return jsonify({"success": False}), 401

    data = request.get_json(silent=True) or {}
    app_id = str(data.get("app_id") or "").strip()
    request_id = str(data.get("request_id") or "").strip()
    if not VBEE_APP_ID or not app_id or not hmac.compare_digest(app_id, VBEE_APP_ID):
        return jsonify({"success": False}), 401
    if not request_id:
        return jsonify({"success": False}), 400

    safe_result = {
        "request_id": request_id,
        "status": data.get("status"),
        "audio_link": data.get("audio_link"),
        "audio_type": data.get("audio_type"),
        "characters": data.get("characters"),
        "voice_code": data.get("voice_code"),
        "speed_rate": data.get("speed_rate"),
        "created_at": data.get("created_at"),
    }
    with _callback_lock:
        _callback_cache[request_id] = safe_result
        _callback_cache.move_to_end(request_id)
        while len(_callback_cache) > _CALLBACK_CACHE_MAX:
            _callback_cache.popitem(last=False)

    log.info("Vbee callback request_id=%s status=%s", request_id, data.get("status"))
    return jsonify({"success": True}), 200
