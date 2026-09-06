import threading
import time
import unittest
import hashlib
from unittest.mock import patch

from adapters.zalo import PendingZaloMessages
from app import app, split_zalo_messages
from core.llm import LLMError


class ZaloAdapterTests(unittest.TestCase):
    def test_disabled_webhook_acknowledges_configuration_without_processing(self):
        payload = {
            "event_name": "user_send_text",
            "sender": {"id": "user-1"},
            "message": {"text": "Xin chào"},
        }
        with patch("app.ZALO_WEBHOOK_ENABLED", False), patch("app.pending.push") as push:
            with app.test_client() as client:
                response = client.post("/zalo/webhook", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "webhook_configuration_pending")
        push.assert_not_called()

    def test_pending_wait_handles_get_before_webhook(self):
        queue = PendingZaloMessages()

        def push_later():
            time.sleep(0.05)
            queue.push("user-1", "Xin chào", msg_id="msg-1")

        thread = threading.Thread(target=push_later)
        thread.start()
        item = queue.pop(user_id="user-1", wait_seconds=0.5)
        thread.join()
        self.assertIsNotNone(item)
        self.assertEqual(item["text"], "Xin chào")

    def test_zalo_response_remains_text_chat(self):
        parts = split_zalo_messages("Anh/chị vui lòng giữ nguyên file camera và sao lưu thêm một bản.")
        self.assertEqual(len(parts), 1)
        self.assertIsInstance(parts[0], str)

    def test_long_sentence_is_split_within_zalo_limit(self):
        parts = split_zalo_messages("từ " * 500)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(part) <= 650 for part in parts))

    def test_pending_missing_keeps_dynamic_contract(self):
        with app.test_client() as client:
            response = client.get("/zalo/ai?uid=missing-test-user")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["content"]["messages"][0]["type"], "text")

    def test_health_and_article_134(self):
        with app.test_client() as client:
            health = client.get("/health")
            article = client.get("/debug/article/134")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json()["status"], "ok")
        self.assertEqual(article.status_code, 200)
        self.assertTrue(article.get_json()["found"])

    def test_api_chat_provider_error_returns_safe_text(self):
        with patch("app.core.chat", side_effect=LLMError("provider failed")):
            with app.test_client() as client:
                response = client.post("/api/chat", json={
                    "user_id": "synthetic-test-user", "message": "Tôi bị người khác đánh",
                })
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["meta"]["path"], "api_boundary_grounded_fallback")
        self.assertIn("anh/chị", body["answer"].lower())

    def test_signed_zalo_webhook_accepts_official_formula(self):
        body = (
            '{"app_id":"test-app","sender":{"id":"user-1"},'
            '"event_name":"user_send_text","message":{"text":"Xin chào","msg_id":"m-1"},'
            '"timestamp":"123"}'
        )
        signature = hashlib.sha256(f"test-app{body}123test-secret".encode("utf-8")).hexdigest()
        with patch("app.ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch("app.ZALO_APP_ID", "test-app"), \
             patch("app.ZALO_OA_SECRET_KEY", "test-secret"):
            with app.test_client() as client:
                response = client.post(
                    "/zalo/webhook",
                    data=body,
                    content_type="application/json",
                    headers={"X-ZEvent-Signature": signature},
                )
        self.assertEqual(response.status_code, 200)

    def test_signed_zalo_webhook_rejects_forged_request(self):
        with patch("app.ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch("app.ZALO_APP_ID", "test-app"), \
             patch("app.ZALO_OA_SECRET_KEY", "test-secret"):
            with app.test_client() as client:
                response = client.post(
                    "/zalo/webhook",
                    json={"app_id": "test-app", "timestamp": "123"},
                    headers={"X-ZEvent-Signature": "forged"},
                )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
