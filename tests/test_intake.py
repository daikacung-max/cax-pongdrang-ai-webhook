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
        self.assertIn("đã đi khám", prompt_hint(result))

    def test_unclassified_goes_to_human_triage(self):
        result = assess("Xin chào", [])
        self.assertEqual(result["handoff_status"], "needs_human_triage")
        self.assertEqual(result["handoff_queue"], "GENERAL_INTAKE")
        self.assertNotIn("procedure_name", result)


if __name__ == "__main__":
    unittest.main()
