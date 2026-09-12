import unittest
from unittest.mock import patch

from app import app
from core import cases
from core.answerer import build_messages


SESSION = "12345678-1234-1234-1234-1234567890ab"


class RealDemoAITests(unittest.TestCase):
    def test_full_core_prompt_keeps_longer_conversation_window(self):
        history = []
        for i in range(12):
            history.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"turn-{i}"})
        messages = build_messages("câu mới", history)
        joined = " ".join(x["content"] for x in messages)
        self.assertIn("turn-0", joined)
        self.assertIn("turn-11", joined)
        self.assertEqual(messages[-1]["content"], "câu mới")

    def test_demo_prefixed_user_never_creates_real_case(self):
        intake = {
            "handoff_status": "ready_for_officer",
            "procedure_code": "temporary_residence",
            "handoff_queue": "residence",
        }
        self.assertIsNone(cases.create_or_get_open("demo-ai:" + SESSION, intake))

    def test_demo_ai_route_calls_full_core_with_stable_demo_identity(self):
        import adapters.demo_ai as demo_ai
        old = demo_ai.ENABLE_DEMO_CONSOLE
        demo_ai.ENABLE_DEMO_CONSOLE = True
        calls = []

        def fake_chat(user_id, message, dynamic=False):
            calls.append((user_id, message, dynamic))
            return {
                "answer": "Câu trả lời AI sinh mới",
                "meta": {
                    "verified": True,
                    "path": "structured_verified",
                    "model": "openai/gpt-oss-120b",
                    "provider": "groq",
                    "retrieved_unit_ids": ["BLHS_2025:article:134"],
                    "intake": {"handoff_status": "not_requested"},
                },
                "handoff": None,
            }

        try:
            with patch.object(demo_ai.core, "chat", side_effect=fake_chat):
                with app.test_client() as client:
                    first = client.post("/demo/api/ai-chat", json={"session_id": SESSION, "message": "Tôi bị đánh"})
                    second = client.post("/demo/api/ai-chat", json={"session_id": SESSION, "message": "Người đó dùng dao"})
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(calls[0][0], "demo-ai:" + SESSION)
            self.assertEqual(calls[1][0], calls[0][0])
            self.assertFalse(calls[0][2])
            self.assertTrue(first.get_json()["memory"])
            self.assertEqual(first.get_json()["mode"], "full_ai_core")
        finally:
            demo_ai.ENABLE_DEMO_CONSOLE = old


if __name__ == "__main__":
    unittest.main()
