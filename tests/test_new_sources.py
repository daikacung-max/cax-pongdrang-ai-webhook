import unittest

from app import ensure_legal_db
from core.planner import plan
from core.retrieval import retrieve
from core.verifier import grounded_dynamic_fallback


class NewVerifiedSourcesTests(unittest.TestCase):

    def test_karaoke_noise_uses_article_9_source_without_a_fixed_hour_rule(self):
        plan = {"is_legal": True, "search_queries": ["Hàng xóm hát karaoke ồn ào thì xử lý sao?"]}
        units = retrieve(plan, "Hàng xóm hát karaoke ồn ào thì xử lý sao?")
        self.assertTrue(units)
        self.assertTrue(all(unit["document_id"] == "NOISE_KARAOKE_282_2025" for unit in units))
        response = grounded_dynamic_fallback("Hàng xóm hát karaoke ồn ào thì xử lý sao?", units)
        self.assertIn("không nên được hiểu là chỉ sau một mốc giờ", response)
        self.assertIn("xác minh", response)
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

    def test_lost_identity_card_uses_only_provincial_reissue_source(self):
        question = "Tôi bị mất căn cước"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(any(unit["document_id"] == "CITIZEN_ID_REISSUE_PROVINCIAL_2026" for unit in units))
        self.assertFalse(any(unit["document_id"] == "BLHS_2025" for unit in units))
        answer = grounded_dynamic_fallback(question, units)
        self.assertIn("Công an cấp tỉnh", answer)
        self.assertIn("07 ngày làm việc", answer)
        self.assertNotIn("đủ 14 tuổi chưa", answer)
        self.assertNotIn("Công an xã Pơng Drang trực tiếp cấp lại", answer)

    def test_over14_new_identity_card_uses_only_provincial_source(self):
        question = "Tôi cần cấp căn cước lần đầu, đã đủ 14 tuổi"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(any(unit["document_id"] == "CITIZEN_ID_OVER14_PROVINCIAL_2026" for unit in units))
        self.assertFalse(any(unit["document_id"] == "BLHS_2025" for unit in units))
        answer = grounded_dynamic_fallback(question, units)
        self.assertIn("Công an cấp tỉnh", answer)
        self.assertIn("07 ngày làm việc", answer)

    def test_identity_renewal_uses_its_own_provincial_source(self):
        question = "Tôi cần đổi căn cước"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(all(unit["document_id"] == "CITIZEN_ID_RENEWAL_PROVINCIAL_2026" for unit in units))
        answer = grounded_dynamic_fallback(question, units)
        self.assertIn("Công an cấp tỉnh", answer)
        self.assertIn("07 ngày làm việc", answer)


if __name__ == "__main__":
    unittest.main()
