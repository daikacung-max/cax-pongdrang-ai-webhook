import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from adapters.knowledge_admin import blueprint
from core import knowledge_base as kb


class KnowledgeAdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(kb, "DB_PATH", Path(self.temp.name) / "admin.db")
        self.pg_patch = patch.object(kb, "DATABASE_URL", "")
        self.token_patch = patch("adapters.knowledge_admin.OFFICER_API_TOKEN", "test-officer-token")
        self.db_patch.start()
        self.pg_patch.start()
        self.token_patch.start()
        kb._SCHEMA_READY = False
        app = Flask(__name__, template_folder="../templates")
        app.register_blueprint(blueprint)
        self.client = app.test_client()
        self.headers = {"Authorization": "Bearer test-officer-token", "X-Officer-Name": "Cán bộ thử"}

    def tearDown(self):
        self.db_patch.stop()
        self.pg_patch.stop()
        self.token_patch.stop()
        kb._SCHEMA_READY = False
        self.temp.cleanup()

    def test_management_requires_officer_token(self):
        response = self.client.get("/internal/officer/knowledge")
        self.assertEqual(response.status_code, 401)

        page = self.client.get("/internal/officer/knowledge", headers=self.headers)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Kho tri thức CAX Pơng Drang".encode(), page.data)

    def test_officer_can_add_approve_and_search_source_bounded_document(self):
        payload = {
            "title": "Hướng dẫn cấp lại căn cước",
            "content": "Cấp lại thẻ căn cước được thực hiện khi thẻ bị mất hoặc hư hỏng. Người dân chọn thủ tục cấp lại và theo dõi mã hồ sơ.",
            "source_index": 16,
            "issuer": "Công an",
            "checked_at": "2026-09-24",
        }
        added = self.client.post("/internal/officer/knowledge/api/documents", json=payload, headers=self.headers)
        self.assertEqual(added.status_code, 201)
        document_id = added.get_json()["document"]["id"]

        approved = self.client.post(
            f"/internal/officer/knowledge/api/documents/{document_id}/status",
            json={"status": "approved"}, headers=self.headers,
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.get_json()["document"]["approved_by"], "Cán bộ thử")

        found = self.client.post(
            "/internal/officer/knowledge/api/search",
            json={"source_index": 16, "query": "thẻ căn cước cấp lại"}, headers=self.headers,
        )
        self.assertEqual(found.status_code, 200)
        self.assertTrue(found.get_json()["results"])


if __name__ == "__main__":
    unittest.main()
