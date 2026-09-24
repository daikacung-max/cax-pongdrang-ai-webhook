"""Secure short-lived download endpoint for citizen-generated DOCX files."""

from io import BytesIO

from flask import Blueprint, jsonify, send_file

from core.form_documents import decode_download_token, render_docx


blueprint = Blueprint("citizen_forms", __name__)


@blueprint.get("/forms/download/<path:token>/<filename>")
def download_form(token, filename):
    try:
        payload = decode_download_token(token)
        content, safe_name = render_docx(payload)
    except Exception:
        return jsonify({"error": "Liên kết biểu mẫu không hợp lệ hoặc đã hết hạn."}), 404

    response = send_file(
        BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=safe_name,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
