import unittest

from app import ensure_legal_db
from core.answerer import _bounded_history
from core.planner import plan
from core.retrieval import retrieve
from core.verifier import grounded_dynamic_fallback


class ConversationContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def setUp(self):
        self.history = [
            {"role": "user", "content": "Tôi bị người khác đánh, tôi phải làm gì?"},
            {"role": "assistant", "content": "Anh/chị nên đi khám và lưu chứng cứ."},
            {"role": "user", "content": "Tôi bị thương 5%."},
            {"role": "assistant", "content": "Tỷ lệ này chưa đủ để loại trừ trách nhiệm hình sự."},
            {"role": "user", "content": "Người kia dùng dao."},
            {"role": "assistant", "content": "Cần làm rõ đặc điểm và cách sử dụng con dao."},
        ]

    def test_four_turn_context_retrieves_article_134(self):
        search_plan = plan("Tôi có video camera, giờ cần làm gì?", self.history, dynamic=True)
        self.assertTrue(search_plan["is_legal"])
        units = retrieve(search_plan, "Tôi có video camera, giờ cần làm gì?")
        self.assertTrue(any(str(unit.get("article")) == "134" for unit in units))

    def test_dynamic_history_keeps_recent_chat_within_budget(self):
        bounded = _bounded_history(self.history, max_messages=8, max_chars=3000)
        self.assertEqual(bounded, self.history)

    def test_camera_fallback_preserves_evidence(self):
        units = retrieve(
            plan("Tôi có video camera", self.history, dynamic=True),
            "Tôi có video camera",
        )
        answer = grounded_dynamic_fallback("Tôi có video camera", units)
        self.assertIn("giữ nguyên file gốc", answer)
        self.assertIn("sao lưu", answer)


if __name__ == "__main__":
    unittest.main()
