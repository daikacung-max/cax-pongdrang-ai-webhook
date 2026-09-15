import unittest
from unittest.mock import MagicMock, patch


class ZaloDurableDispatchTests(unittest.TestCase):
    def test_direct_reply_webhook_acks_after_durable_enqueue_without_calling_ai_inline(self):
        import app

        handler = app.app.view_functions["zalo_webhook"]
        enqueue = MagicMock(return_value=True)
        with patch.object(app, "ZALO_WEBHOOK_ENABLED", True), \
             patch.object(app, "ZALO_DIRECT_REPLY_ENABLED", True), \
             patch.object(app, "_valid_zalo_webhook_signature", return_value=True), \
             patch.object(app.core, "chat") as chat_mock, \
             patch.dict(handler.__globals__, {
                 "zalo_dispatch_persistence_ready": lambda: True,
                 "enqueue_zalo_reply": enqueue,
             }):
            response = app.app.test_client().post("/zalo/webhook", json={
                "app_id": "app-1",
                "timestamp": "1",
                "event_name": "user_send_text",
                "sender": {"id": "user-1"},
                "message": {"msg_id": "msg-1", "text": "Tôi cần hỗ trợ"},
            }, headers={"X-ZEvent-Signature": "synthetic"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        enqueue.assert_called_once_with("msg-1", "user-1", "Tôi cần hỗ trợ")
        chat_mock.assert_not_called()

    def test_direct_reply_does_not_ack_when_durable_enqueue_fails(self):
        import app

        handler = app.app.view_functions["zalo_webhook"]
        with patch.object(app, "ZALO_WEBHOOK_ENABLED", True), \
             patch.object(app, "ZALO_DIRECT_REPLY_ENABLED", True), \
             patch.object(app, "_valid_zalo_webhook_signature", return_value=True), \
             patch.dict(handler.__globals__, {
                 "zalo_dispatch_persistence_ready": lambda: True,
                 "enqueue_zalo_reply": lambda *args: False,
             }):
            response = app.app.test_client().post("/zalo/webhook", json={
                "app_id": "app-1",
                "timestamp": "1",
                "event_name": "user_send_text",
                "sender": {"id": "user-1"},
                "message": {"msg_id": "msg-1", "text": "Tôi cần hỗ trợ"},
            }, headers={"X-ZEvent-Signature": "synthetic"})

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
