import unittest
import uuid
from unittest.mock import patch

from core.llm import LLMError
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

    def test_full_core_provider_error_returns_grounded_fallback(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch("core.service.generate_answer", side_effect=LLMError("provider rejected")):
            result = core.chat(user_id, "Tôi bị mất căn cước, cần làm gì?", dynamic=False)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "llm_error")
        self.assertEqual(result["meta"]["path"], "full_core_grounded_fallback")
        self.assertNotIn("AI Core chưa xử lý", result["answer"])

    def test_full_core_repair_error_returns_grounded_fallback(self):
        user_id = "service-test-" + uuid.uuid4().hex
        rejected_draft = {
            "answer": "Bạn nên lưu giữ video camera nếu có.",
            "legal_claims": [],
            "needs_followup": False,
            "followup_question": None,
            "contact_recommended": False,
        }
        with patch(
            "core.service.generate_answer",
            side_effect=[rejected_draft, LLMError("repair rejected")],
        ) as model:
            result = core.chat(user_id, "Tôi bị người khác đánh.", dynamic=False)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "llm_error")
        self.assertEqual(result["meta"]["path"], "full_core_grounded_fallback")


if __name__ == "__main__":
    unittest.main()
