import unittest
import os
from unittest.mock import patch

from flask import Flask

from adapters.forms import blueprint as forms_blueprint
import core.form_documents as forms


class CitizenFormDocumentTests(unittest.TestCase):
    def test_ordinary_residence_question_is_not_intercepted(self):
        self.assertEqual(
            forms.detect_form_type("Đăng ký tạm trú cần giấy tờ gì?", history=[]),
            "",
        )

    def test_blank_ct01_returns_short_lived_download_link(self):
        with patch.object(forms, "HISTORY_HMAC_SECRET", "test-secret"):
            result = forms.handle_form_request(
                "u1", "Cho tôi in mẫu CT01 trống", history=[]
            )
        self.assertTrue(result["ready"])
        self.assertEqual(result["form_type"], "ct01")
        self.assertIn("/forms/download/", result["download_url"])
        self.assertTrue(result["download_url"].endswith("/ct01.docx"))

    def test_blank_ct01_uses_instance_bound_database_key_when_form_secret_is_missing(self):
        with patch.object(forms, "HISTORY_HMAC_SECRET", ""):
            with patch.dict(os.environ, {"DATABASE_URL": "postgresql://runtime-secret"}, clear=False):
                result = forms.handle_form_request(
                    "u1", "Cho tôi in mẫu CT01 trống", history=[]
                )
        self.assertTrue(result["ready"])
        self.assertIn("/forms/download/", result["download_url"])

    def test_blank_ct01_uses_provider_secret_when_legacy_runtime_has_no_history_store(self):
        with patch.object(forms, "HISTORY_HMAC_SECRET", ""):
            with patch.dict(
                os.environ,
                {"FORM_LINK_SECRET": "", "DATABASE_URL": "", "GROQ_API_KEY": "gsk-runtime-secret"},
                clear=False,
            ):
                result = forms.handle_form_request(
                    "u1", "Cho tôi in mẫu CT01 trống", history=[]
                )
        self.assertTrue(result["ready"])
        self.assertIn("/forms/download/", result["download_url"])

    def test_ct01_collects_only_supplied_fields_and_exports(self):
        history = [{
            "role": "assistant",
            "content": "Tôi đang hỗ trợ điền CT01. Vui lòng gửi các dòng sau: Họ tên...",
        }]
        question = """Họ tên: Nguyễn Văn A
Ngày sinh: 01/01/1990
Số CCCD: 012345678901
Nơi ở hiện tại: xã Pơng Drang, tỉnh Đắk Lắk
Nội dung đề nghị: đăng ký tạm trú"""
        with patch.object(forms, "HISTORY_HMAC_SECRET", "test-secret"):
            result = forms.handle_form_request("u1", question, history=history)
            payload = forms.decode_payload(result["download_url"].split("/forms/download/", 1)[1].split("/", 1)[0])
            content, name = forms.render_docx(payload)
        self.assertTrue(result["ready"])
        self.assertGreater(len(content), 1000)
        self.assertEqual(name, "CT01-ho-tro-dien.docx")
        self.assertEqual(payload["fields"]["full_name"], "Nguyễn Văn A")
        self.assertEqual(payload["fields"]["phone"], "")

    def test_report_flow_accepts_free_prose_and_exports_a_draft_without_inventing_fields(self):
        with patch.object(forms, "HISTORY_HMAC_SECRET", "test-secret"):
            result = forms.handle_form_request(
                "u2",
                (
                    "Tôi muốn làm đơn trình báo. Tôi tên là Trần Văn B, CCCD 123456789012.\n"
                    "Hôm qua tôi bị lừa chuyển khoản 5 triệu đồng qua mạng và còn lưu tin nhắn."
                ),
                history=[],
            )
            payload = forms.decode_payload(result["download_url"].split("/forms/download/", 1)[1].split("/", 1)[0])
            content, name = forms.render_docx(payload)
        self.assertTrue(result["ready"])
        self.assertEqual(payload["fields"]["full_name"], "Trần Văn B")
        self.assertEqual(payload["fields"]["personal_id"], "123456789012")
        self.assertIn("bị lừa chuyển khoản", payload["fields"]["incident_content"])
        self.assertEqual(payload["fields"]["address"], "")
        self.assertEqual(name, "Don-trinh-bao.docx")
        self.assertGreater(len(content), 1000)

    def test_report_flow_requests_only_the_incident_when_no_facts_were_given(self):
        result = forms.handle_form_request("u2", "Giúp tôi tạo file Word đơn trình báo", history=[])
        self.assertFalse(result["ready"])
        self.assertEqual(result["missing"], ["incident_content"])
        self.assertIn("kể ngắn gọn sự việc", result["answer"])

    def test_download_endpoint_returns_docx_without_cache(self):
        app = Flask(__name__)
        app.register_blueprint(forms_blueprint)
        client = app.test_client()
        with patch.object(forms, "HISTORY_HMAC_SECRET", "test-secret"):
            token = forms.encode_payload({"form_type": "report", "fields": {"full_name": "A"}})
            response = client.get(f"/forms/download/{token}/don-trinh-bao.docx")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats", response.content_type)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertGreater(len(response.data), 1000)


if __name__ == "__main__":
    unittest.main()
