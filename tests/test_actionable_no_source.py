import unittest

from config import HOTLINE
from core.clarification import clarification_for_unverified_topic
from core.verifier import grounded_dynamic_fallback


class ActionableNoSourceTests(unittest.TestCase):
    def test_gambling_report_gets_immediate_safe_action_guidance(self):
        answer = grounded_dynamic_fallback(
            "tôi biết một nhóm người đang đánh bạc, tôi phải làm gì",
            [],
        )
        lower = answer.lower()
        self.assertIn("đánh bạc", lower)
        self.assertIn(HOTLINE, answer)
        self.assertIn("không nên tự", lower)
        self.assertIn("thời điểm", lower)
        self.assertIn("địa điểm", lower)
        self.assertNotIn("chưa có nguồn", lower)
        self.assertNotIn("không có nguồn", lower)

    def test_drug_report_is_actionable_without_specialized_source(self):
        answer = grounded_dynamic_fallback(
            "tôi thấy một nhóm người có biểu hiện sử dụng ma túy",
            [],
        )
        lower = answer.lower()
        self.assertIn(HOTLINE, answer)
        self.assertIn("không tự tiếp cận", lower)
        self.assertNotIn("chưa có nguồn", lower)

    def test_unknown_topic_still_gets_a_useful_next_step(self):
        answer = clarification_for_unverified_topic(
            "tôi có một việc rất lạ muốn hỏi thì phải làm sao"
        )
        lower = answer.lower()
        self.assertTrue(answer.strip())
        self.assertIn("thủ tục", lower)
        self.assertIn("phản ánh", lower)
        self.assertNotIn("chưa có nguồn", lower)
        self.assertNotIn("không thể trả lời", lower)


if __name__ == "__main__":
    unittest.main()
