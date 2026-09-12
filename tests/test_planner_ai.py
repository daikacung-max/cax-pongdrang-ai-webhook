import unittest
from unittest.mock import patch

from core import planner


class PlannerAITests(unittest.TestCase):
    def test_dynamic_never_calls_llm(self):
        with patch("core.planner.chat_structured") as llm:
            result = planner.plan("Tôi muốn đăng ký tạm trú", [], dynamic=True)
        llm.assert_not_called()
        self.assertTrue(result["is_legal"])

    def test_full_core_sanitizes_invented_article(self):
        candidate = {
            "is_legal": True,
            "search_queries": ["đăng ký tạm trú"],
            "explicit_references": [{"law_hint": "luật", "article": "999"}],
            "needs_clarification": False,
            "clarification_question": None,
            "complexity": "complex",
            "complexity_reasons": ["multiple conditions"],
        }
        with patch("core.planner.chat_structured", return_value=candidate) as llm:
            result = planner.plan("Tôi muốn đăng ký tạm trú", [], dynamic=False, safety_identifier="h_test")
        llm.assert_called_once()
        self.assertTrue(result["is_legal"])
        self.assertEqual(result["explicit_references"], [])
        self.assertEqual(result["complexity"], "complex")

    def test_full_core_falls_back_if_planner_provider_fails(self):
        with patch("core.planner.chat_structured", side_effect=RuntimeError("provider down")):
            result = planner.plan("Tôi muốn đăng ký tạm trú", [], dynamic=False)
        self.assertTrue(result["is_legal"])


if __name__ == "__main__":
    unittest.main()
