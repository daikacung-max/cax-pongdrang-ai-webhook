import hashlib
import unittest
from unittest.mock import patch

from app import app


class ZaloSignatureDriftTests(unittest.TestCase):
    def test_valid_signature_uses_signed_payload_app_id_not_stale_local_app_id(self):
        body = (
            '{"app_id":"actual-zalo-app","sender":{"id":"user-1"},'
            '"event_name":"user_send_text","message":{"text":"Xin chào","msg_id":"m-drift"},'
            '"timestamp":"123"}'
        )
        signature = hashlib.sha256(
            f"actual-zalo-app{body}123test-secret".encode("utf-8")
        ).hexdigest()
        with patch("app.ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch("app.ZALO_APP_ID", "stale-local-app"), \
             patch("app.ZALO_OA_SECRET_KEY", "test-secret"), \
             patch("app.ZALO_DIRECT_REPLY_ENABLED", False):
            with app.test_client() as client:
                response = client.post(
                    "/zalo/webhook",
                    data=body,
                    content_type="application/json",
                    headers={"X-ZEvent-Signature": "mac=" + signature},
                )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

    def test_wrong_secret_still_fails_closed(self):
        body = (
            '{"app_id":"actual-zalo-app","timestamp":"123",'
            '"event_name":"user_send_text"}'
        )
        forged = hashlib.sha256(
            f"actual-zalo-app{body}123wrong-secret".encode("utf-8")
        ).hexdigest()
        with patch("app.ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch("app.ZALO_APP_ID", "stale-local-app"), \
             patch("app.ZALO_OA_SECRET_KEY", "real-secret"):
            with app.test_client() as client:
                response = client.post(
                    "/zalo/webhook",
                    data=body,
                    content_type="application/json",
                    headers={"X-ZEvent-Signature": "mac=" + forged},
                )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
