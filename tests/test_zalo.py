import threading
import time
import unittest
import hashlib
import json
import app_core
from unittest.mock import ANY, patch

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

    def test_dynamic_without_uid_never_consumes_another_users_pending_message(self):
        with patch("app.ZALO_WEBHOOK_ENABLED", True), patch("app.pending.pop") as pop:
            with app.test_client() as client:
                response = client.get("/zalo/ai")

        self.assertEqual(response.status_code, 200)
        self.assertIn("chưa được liên kết", response.get_json()["content"]["messages"][0]["text"])
        pop.assert_not_called()

    def test_dynamic_accepts_uid_from_zalo_sender_envelope(self):
        with patch("app.ZALO_WEBHOOK_ENABLED", True), patch("app.pending.pop", return_value=None) as pop:
            with app.test_client() as client:
                response = client.post("/zalo/ai", json={"sender": {"id": "user-1"}})

        self.assertEqual(response.status_code, 200)
        pop.assert_called_once_with(user_id="user-1")

    def test_dynamic_question_query_uses_ai_without_webhook_pending_message(self):
        with patch("app.ZALO_WEBHOOK_ENABLED", True), \
             patch("app.pending.pop") as pop, \
             patch("app.core.chat", return_value={
                 "answer": "Anh/chị có thể đăng ký tạm trú trên VNeID.",
                 "_telemetry": {},
             }) as chat:
            with app.test_client() as client:
                response = client.get(
                    "/zalo/ai?uid=chatbot-user-1&q=T%C3%B4i%20c%E1%BA%A7n%20%C4%91%C4%83ng%20k%C3%BD%20t%E1%BA%A1m%20tr%C3%BA"
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("đăng ký tạm trú", response.get_json()["content"]["messages"][0]["text"])
        chat.assert_called_once_with(
            "chatbot-user-1", "Tôi cần đăng ký tạm trú", dynamic=True, trace_id=ANY
        )
        pop.assert_not_called()

    def test_dynamic_question_json_input_uses_ai_without_webhook_pending_message(self):
        with patch("app.ZALO_WEBHOOK_ENABLED", True), \
             patch("app.pending.pop") as pop, \
             patch("app.core.chat", return_value={"answer": "Đã tiếp nhận câu hỏi.", "_telemetry": {}}) as chat:
            with app.test_client() as client:
                response = client.post("/zalo/ai", json={
                    "user": {"id": "chatbot-user-2"},
                    "question": {"value": "Tôi muốn làm căn cước"},
                })

        self.assertEqual(response.status_code, 200)
        chat.assert_called_once_with(
            "chatbot-user-2", "Tôi muốn làm căn cước", dynamic=True, trace_id=ANY
        )
        pop.assert_not_called()

    def test_dynamic_ignores_unexpanded_question_placeholder(self):
        with patch("app.ZALO_WEBHOOK_ENABLED", True), patch("app.pending.pop", return_value=None) as pop:
            with app.test_client() as client:
                response = client.get("/zalo/ai?uid=chatbot-user-3&q=((citizen_question))")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Nhập liệu", response.get_json()["content"]["messages"][0]["text"])
        pop.assert_called_once_with(user_id="chatbot-user-3")

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

    def test_dynamic_provider_error_logs_only_sanitized_status(self):
        with patch("app.core.chat", side_effect=LLMError("openai HTTP 429: private body")), \
             patch("app.log_zalo_latency") as log_latency:
            with app.test_client() as client:
                response = client.get("/zalo/ai?uid=synthetic-user&q=Bạn%20có%20khả%20năng%20gì%3F")

        self.assertEqual(response.status_code, 200)
        payload = log_latency.call_args.args[1]
        self.assertEqual(payload["provider_error"], "http_429")

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

    def test_signed_zalo_webhook_accepts_compact_json_signature(self):
        payload = {
            "app_id": "test-app",
            "timestamp": "123",
            "event_name": "user_send_text",
            "sender": {"id": "user-1"},
            "message": {"msg_id": "m-compact", "text": "Xin chào"},
        }
        compact_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        delivered_body = json.dumps(payload, ensure_ascii=False, indent=2)
        signature = hashlib.sha256(
            f"test-app{compact_body}123test-secret".encode("utf-8")
        ).hexdigest()
        with patch("app.ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch("app.ZALO_APP_ID", "test-app"), \
             patch("app.ZALO_OA_SECRET_KEY", "test-secret"):
            with app.test_client() as client:
                response = client.post(
                    "/zalo/webhook",
                    data=delivered_body,
                    content_type="application/json",
                    headers={"X-ZEvent-Signature": signature},
                )
        self.assertEqual(response.status_code, 200)

    def test_empty_webhook_probe_is_acknowledged_without_bypassing_signed_events(self):
        with patch.object(app_core, "ZALO_WEBHOOK_ENABLED", True), \
             patch.object(app_core, "ZALO_WEBHOOK_SIGNATURE_REQUIRED", True):
            with app.test_client() as client:
                response = client.post("/zalo/webhook", data="", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "verification_probe")


if __name__ == "__main__":
    unittest.main()
