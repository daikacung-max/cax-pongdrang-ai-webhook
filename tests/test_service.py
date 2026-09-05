import unittest
import uuid
from unittest.mock import patch

from core.service import core


class DynamicServiceTests(unittest.TestCase):
    def test_unsupported_article_fails_closed_after_one_model_call(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch("core.service.answer_dynamic_text", return_value="Người kia chắc chắn phạm Điều 148." ) as model:
            result = core.chat(user_id, "Tôi bị người khác đánh.", dynamic=True)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "verification_failed")
        self.assertNotIn("Điều 148", result["answer"])
        self.assertTrue(any("134" in unit_id for unit_id in result["meta"]["retrieved_unit_ids"]))

    def test_article_134_new_injury_percentage_is_not_ignored(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value="Anh/chị có thể cho biết người đã đánh là ai không?",
        ):
            result = core.chat(user_id, "Kết quả thương tích là 5%.", dynamic=True)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "weak_answer")
        self.assertIn("5%", result["answer"])


if __name__ == "__main__":
    unittest.main()
