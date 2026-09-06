import unittest
from unittest.mock import patch

from core import llm
from core.providers.router import provider_name_for_model


class FakeResponse:
    def json(self):
        return {"choices": [{"message": {"content": "Xin chào anh/chị."}}]}


class FakeProvider:
    def __init__(self):
        self.payload = None

    def complete(self, payload, timeout):
        self.payload = payload
        return FakeResponse()


class ProviderTests(unittest.TestCase):
    def test_model_router(self):
        self.assertEqual(provider_name_for_model("openai/gpt-oss-20b"), "groq")
        self.assertEqual(provider_name_for_model("gpt-5.6-luna"), "openai")
        self.assertEqual(provider_name_for_model("gpt-5.6-terra"), "openai")

    def test_gpt56_payload_uses_reasoning_and_safety_identifier(self):
        provider = FakeProvider()
        with patch("core.llm.provider_for_model", return_value=provider):
            text = llm.chat_text(
                "gpt-5.6-luna",
                [{"role": "user", "content": "Chào"}],
                reasoning_effort="none",
                safety_identifier="h1_test",
            )
        self.assertEqual(text, "Xin chào anh/chị.")
        self.assertEqual(provider.payload["reasoning_effort"], "none")
        self.assertEqual(provider.payload["safety_identifier"], "h1_test")
        self.assertNotIn("temperature", provider.payload)

    def test_full_groq_answer_uses_text_mode(self):
        with patch("core.answerer.chat_text", return_value="Anh/chị nên giữ lại video camera.") as text_call:
            from core.answerer import answer
            result = answer("Tôi có camera", [], legal_context="SOURCE", model="openai/gpt-oss-20b")
        self.assertEqual(result["answer"], "Anh/chị nên giữ lại video camera.")
        self.assertEqual(result["legal_claims"], [])
        text_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
