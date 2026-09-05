import unittest
import uuid
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import app, ensure_legal_db
from core import cases
from core.service import core


class IntakeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()
        cls._temporary_dir = tempfile.TemporaryDirectory()
        cls._path_patch = patch("core.cases.DB_PATH", Path(cls._temporary_dir.name) / "cases.db")
        cls._path_patch.start()
        cases.init_schema()

    @classmethod
    def tearDownClass(cls):
        cls._path_patch.stop()
        cls._temporary_dir.cleanup()

    def test_ready_request_creates_one_persistent_case(self):
        intake = {
            "handoff_status": "ready_for_officer",
            "procedure_code": "residence",
            "handoff_queue": "ADMIN_RESIDENCE",
        }
        user_id = "synthetic-case-" + uuid.uuid4().hex
        answer, first = core._record_ready_intake(user_id, intake, "Đã ghi nhận.")
        self.assertTrue(first["created"])
        self.assertTrue(first["case_id"].startswith("CAX-"))
        self.assertIn(first["case_id"], answer)

        repeated_answer, repeated = core._record_ready_intake(user_id, intake, "Đã ghi nhận.")
        self.assertFalse(repeated["created"])
        self.assertEqual(first["case_id"], repeated["case_id"])
        self.assertNotIn("mã " + first["case_id"], repeated_answer)

    def test_internal_case_list_requires_a_configured_token(self):
        with app.test_client() as client:
            disabled = client.get("/internal/officer/cases")
        self.assertEqual(disabled.status_code, 503)

        with patch("app.OFFICER_API_TOKEN", "test-officer-token"):
            with app.test_client() as client:
                denied = client.get("/internal/officer/cases")
                allowed = client.get("/internal/officer/cases", headers={"Authorization": "Bearer test-officer-token"})
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("cases", allowed.get_json())

    def test_pilot_mode_does_not_create_a_case(self):
        intake = {
            "handoff_status": "ready_for_officer",
            "procedure_code": "residence",
            "handoff_queue": "ADMIN_RESIDENCE",
        }
        with patch("core.service.ENABLE_INTAKE_CASES", False):
            answer, handoff = core._record_ready_intake("synthetic-pilot-" + uuid.uuid4().hex, intake, "Đã ghi nhận.")
        self.assertIsNone(handoff)
        self.assertIn("bản thử nghiệm", answer)


if __name__ == "__main__":
    unittest.main()
