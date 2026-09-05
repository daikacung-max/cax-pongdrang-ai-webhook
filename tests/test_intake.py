import unittest

from core.intake import assess, prompt_hint


class IntakeTests(unittest.TestCase):
    def test_vneid_level_two_is_classified_without_storing_value(self):
        result = assess("Tôi cần làm VNeID mức 2", [])
        self.assertEqual(result["procedure_code"], "vneid")
        self.assertEqual(result["handoff_queue"], "ADMIN_IDENTITY")
        self.assertTrue(result["source_ready"])
        self.assertEqual(result["missing_field_ids"], [])

    def test_assault_uses_prior_user_turns_for_intake(self):
        history = [{"role": "user", "content": "Tôi bị người khác đánh."}]
        result = assess("Người đó có dùng dao.", history)
        self.assertEqual(result["procedure_code"], "assault_evidence")
        self.assertIn("injury", result["missing_field_ids"])
        self.assertIn("evidence", result["missing_field_ids"])
        self.assertEqual(result["conversation_mode"], "advice_only")
        self.assertEqual(prompt_hint(result), "")

    def test_unclassified_goes_to_human_triage(self):
        result = assess("Xin chào", [])
        self.assertEqual(result["conversation_mode"], "advice_only")
        self.assertEqual(result["handoff_status"], "not_requested")
        self.assertIsNone(result["handoff_queue"])
        self.assertNotIn("procedure_name", result)

    def test_information_question_never_creates_a_case(self):
        result = assess("Làm VNeID mức 2 cần gì?", [])
        self.assertEqual(result["conversation_mode"], "advice_only")
        self.assertEqual(result["handoff_status"], "not_requested")
        self.assertEqual(result["next_question"], None)

    def test_explicit_procedure_request_waits_for_missing_information(self):
        result = assess("Tôi muốn nộp hồ sơ đăng ký tạm trú.", [])
        self.assertEqual(result["conversation_mode"], "intake_requested")
        self.assertEqual(result["handoff_status"], "needs_information")
        self.assertIn("accommodation", result["missing_field_ids"])
        self.assertIn("chỗ ở", prompt_hint(result))

    def test_explicit_request_can_be_ready_for_officer(self):
        result = assess("Tôi muốn nộp hồ sơ đăng ký tạm trú, hiện đang ở nhà thuê.", [])
        self.assertEqual(result["conversation_mode"], "intake_requested")
        self.assertEqual(result["handoff_status"], "ready_for_officer")


if __name__ == "__main__":
    unittest.main()
