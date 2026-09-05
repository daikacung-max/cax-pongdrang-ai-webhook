import unittest

from app import ensure_legal_db
from core.planner import plan
from core.retrieval import retrieve
from core.verifier import grounded_dynamic_fallback


class NewVerifiedSourcesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_under14_identity_uses_its_own_source(self):
        question = "Con tôi 10 tuổi cần làm căn cước"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(any(unit["document_id"] == "CITIZEN_ID_UNDER14_2026" for unit in units))
        self.assertFalse(any(unit["document_id"] == "VNEID_2026" for unit in units))

    def test_crime_report_source_supports_safe_fallback(self):
        question = "Tôi muốn tố giác một vụ việc"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(any(unit["document_id"] == "CRIME_REPORT_GUIDANCE_2025" for unit in units))
        answer = grounded_dynamic_fallback(question, units)
        self.assertIn("Công an cấp xã", answer)
        self.assertIn("giữ bí mật", answer)


if __name__ == "__main__":
    unittest.main()
