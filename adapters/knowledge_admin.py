"""Authenticated officer console and API for curated knowledge sources."""

import hmac

from flask import Blueprint, current_app, jsonify, render_template, request

from config import OFFICER_API_TOKEN
from core.knowledge_base import (
    MAX_UPLOAD_BYTES,
    create_document,
    extract_upload,
    get_document,
    list_documents,
    search_approved,
    set_status,
)
from core.notebook_manifest import SOURCES

blueprint = Blueprint("officer_knowledge", __name__)


def _authorized():
    if not OFFICER_API_TOKEN:
        return None, (jsonify({"error": "Cổng quản lý kho tri thức chưa được cấu hình."}), 503)
    supplied = str(request.headers.get("Authorization") or "")
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    if not hmac.compare_digest(supplied, OFFICER_API_TOKEN):
        return None, (jsonify({"error": "Không được phép."}), 401)
    actor = str(request.headers.get("X-Officer-Name") or "Cán bộ").strip()[:120]
    return actor, None


@blueprint.before_request
def require_officer():
    if request.content_length and request.content_length > MAX_UPLOAD_BYTES + 128 * 1024:
        return jsonify({"error": "Yêu cầu vượt giới hạn kích thước cho phép."}), 413
    _, error = _authorized()
    if error:
        return error


@blueprint.get("/internal/officer/knowledge")
def knowledge_console():
    return render_template("knowledge_admin.html", sources=SOURCES)


@blueprint.get("/internal/officer/knowledge/api/documents")
def documents_list():
    return jsonify({"documents": list_documents(request.args.get("status"))})


@blueprint.post("/internal/officer/knowledge/api/documents")
def documents_create():
    try:
        data = request.form.to_dict() if request.files else (request.get_json(silent=True) or {})
        filename, digest, content = "", "", str(data.get("content") or "")
        upload = request.files.get("file") if request.files else None
        if upload:
            raw = upload.read(MAX_UPLOAD_BYTES + 1)
            try:
                filename, content, digest = extract_upload(upload.filename, raw)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            except Exception:
                current_app.logger.info("knowledge_upload_rejected reason=unreadable_file")
                return jsonify({"error": "Không đọc được tệp. Hãy kiểm tra định dạng và thử lại."}), 400
        item = create_document(
            title=data.get("title"), content=content,
            source_index=data.get("source_index"), source_url=data.get("source_url"),
            issuer=data.get("issuer"), document_number=data.get("document_number"),
            effective_from=data.get("effective_from"), effective_to=data.get("effective_to"),
            checked_at=data.get("checked_at"), original_name=filename, sha256=digest,
            notes=data.get("notes"),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"document": item, "message": "Đã lưu bản nháp. Tài liệu chưa được dùng để trả lời cho đến khi cán bộ duyệt."}), 201


@blueprint.get("/internal/officer/knowledge/api/documents/<doc_id>")
def document_detail(doc_id):
    item = get_document(doc_id, include_content=True)
    if not item:
        return jsonify({"error": "Không tìm thấy tài liệu."}), 404
    return jsonify({"document": item})


@blueprint.post("/internal/officer/knowledge/api/documents/<doc_id>/status")
def document_status(doc_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "")
    try:
        item = set_status(doc_id, status, actor=request.headers.get("X-Officer-Name", "Cán bộ"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not item:
        return jsonify({"error": "Không tìm thấy tài liệu."}), 404
    return jsonify({"document": item, "message": "Đã cập nhật trạng thái."})


@blueprint.post("/internal/officer/knowledge/api/search")
def knowledge_search():
    data = request.get_json(silent=True) or {}
    try:
        source_index = int(data.get("source_index"))
    except (TypeError, ValueError):
        return jsonify({"error": "Cần chọn nhóm nguồn."}), 400
    if not 1 <= source_index <= len(SOURCES):
        return jsonify({"error": "Nhóm nguồn không hợp lệ."}), 400
    return jsonify({"results": search_approved(data.get("query"), source_index, limit=8)})
