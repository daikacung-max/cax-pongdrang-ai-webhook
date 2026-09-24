import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import knowledge_base as kb


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "knowledge.db"
        self.db_path_patch = patch.object(kb, "DB_PATH", self.path)
        self.pg_patch = patch.object(kb, "DATABASE_URL", "")
        self.db_path_patch.start()
        self.pg_patch.start()
        kb._SCHEMA_READY = False
        kb.init_schema()

    def tearDown(self):
        self.db_path_patch.stop()
        self.pg_patch.stop()
        kb._SCHEMA_READY = False
        self.temp.cleanup()

    def _create(self, **overrides):
        fields = {
            "title": "Hướng dẫn cấp lại thẻ căn cước",
            "content": "Thủ tục cấp lại thẻ căn cước áp dụng khi thẻ bị mất hoặc hư hỏng. Người dân chọn cấp lại, kiểm tra thông tin và theo dõi mã hồ sơ.",
            "source_index": 16,
            "issuer": "Công an",
            "checked_at": "2026-09-24",
        }
        fields.update(overrides)
        return kb.create_document(**fields)

    def test_draft_is_not_retrieved_until_officer_approves(self):
        item = self._create()
        self.assertEqual(item["status"], "draft")
        self.assertEqual(kb.search_approved("thẻ căn cước cấp lại", 16), [])

        kb.set_status(item["id"], "approved", actor="Cán bộ thử nghiệm")
        results = kb.search_approved("thẻ căn cước cấp lại", 16)
        self.assertTrue(results)
        self.assertIn("căn cước", results[0]["text"].lower())

    def test_approved_document_is_limited_to_its_notebook_source(self):
        item = self._create()
        kb.set_status(item["id"], "approved")
        self.assertEqual(kb.search_approved("thẻ căn cước cấp lại", 15), [])

    def test_approval_requires_review_date_and_provenance(self):
        missing_date = self._create(checked_at="")
        with self.assertRaisesRegex(ValueError, "ngày cán bộ đối chiếu"):
            kb.set_status(missing_date["id"], "approved")

        missing_source = self._create(issuer="", original_name="")
        with self.assertRaisesRegex(ValueError, "cơ quan ban hành"):
            kb.set_status(missing_source["id"], "approved")

    def test_archived_or_expired_document_is_not_retrieved(self):
        archived = self._create(title="Tài liệu cấp lại căn cước cũ")
        kb.set_status(archived["id"], "approved")
        kb.set_status(archived["id"], "archived")
        self.assertEqual(kb.search_approved("thẻ căn cước cấp lại", 16), [])

        expired = self._create(title="Tài liệu cấp lại căn cước hết hạn", effective_to="2020-01-01")
        kb.set_status(expired["id"], "approved")
        self.assertEqual(kb.search_approved("thẻ căn cước cấp lại", 16), [])

    def test_non_https_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            self._create(source_url="http://example.test/source")


if __name__ == "__main__":
    unittest.main()
