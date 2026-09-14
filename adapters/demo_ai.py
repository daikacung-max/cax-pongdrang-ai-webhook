"""Real AI Core preview for the internal demo console.

Unlike ``core.demo`` (deterministic acceptance preview), this adapter calls the
same Full AI Core used by the real API. A stable demo session id becomes a
conversation id, so the model receives previous turns and can converse
naturally. Demo-prefixed identities are blocked from creating intake cases in
``core.cases``.
"""

import re

from flask import Blueprint, jsonify, request

from config import ENABLE_DEMO_CONSOLE
from core import db
from core.notebook_manifest import (
    NOTEBOOK_SOURCE_COUNT,
    NOTEBOOK_TITLE,
    source_catalog,
    used_sources_for_unit_ids,
)
from core.service import core


blueprint = Blueprint("ai_core_demo_ai", __name__)
_SESSION_RE = re.compile(r"[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}")


def _session_id(value):
    value = str(value or "").strip().lower()
    return value if _SESSION_RE.fullmatch(value) else ""


def _demo_user(session_id):
    return "demo-ai:" + session_id


@blueprint.route("/demo/api/notebook-sources", methods=["GET"])
def notebook_sources():
    if not ENABLE_DEMO_CONSOLE:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "title": NOTEBOOK_TITLE,
        "source_count": NOTEBOOK_SOURCE_COUNT,
        "sources": source_catalog(),
        "note": "Danh mục 19 nguồn được mirror từ file Gemini Notebook; nội dung trả lời chỉ dùng các document hiện hành đã nạp và kiểm chứng.",
    }), 200


@blueprint.route("/demo/api/ai-chat", methods=["POST"])
def ai_chat():
    if not ENABLE_DEMO_CONSOLE:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    session_id = _session_id(data.get("session_id"))
    message = str(data.get("message") or "").strip()
    if not session_id or not message:
        return jsonify({"error": "session_id demo và message là bắt buộc."}), 400
    if len(message) > 3000:
        return jsonify({"error": "Tin nhắn thử nghiệm quá dài."}), 400

    result = core.chat(_demo_user(session_id), message, dynamic=False)
    result.pop("_telemetry", None)
    meta = result.get("meta") or {}
    unit_ids = list(meta.get("retrieved_unit_ids") or [])
    notebook_sources_used = used_sources_for_unit_ids(unit_ids)
    return jsonify({
        "answer": result.get("answer") or "",
        "mode": "full_ai_core",
        "memory": True,
        "verified": bool(meta.get("verified")),
        "path": meta.get("path"),
        "model": meta.get("model"),
        "provider": meta.get("provider"),
        # Keep internal unit ids for diagnostics only; the UI primarily renders
        # the user-facing Notebook source titles below.
        "sources": unit_ids,
        "notebook_sources": notebook_sources_used,
        "notebook_source_count": len(notebook_sources_used),
        "fallback": str(meta.get("path") or "").endswith("fallback"),
        "handoff_status": ((meta.get("intake") or {}).get("handoff_status") or "not_requested"),
        "note": "Full AI Core thật, có lịch sử theo phiên và trả lời bám nguồn Notebook hiện hành; phiên demo không tạo hồ sơ nghiệp vụ.",
    }), 200


@blueprint.route("/demo/api/ai-history", methods=["GET"])
def ai_history():
    if not ENABLE_DEMO_CONSOLE:
        return jsonify({"error": "Not found"}), 404
    session_id = _session_id(request.args.get("session_id"))
    if not session_id:
        return jsonify({"error": "session_id demo không hợp lệ."}), 400
    history = db.get_history(_demo_user(session_id), limit=20)
    return jsonify({
        "messages": [
            {"role": item["role"], "content": item["content"]}
            for item in history
            if item.get("role") in ("user", "assistant")
        ],
        "memory": True,
    }), 200
