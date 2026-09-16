import unittest
from unittest.mock import patch

from flask import Flask

import adapters.readiness as readiness


class GoLiveGateTests(unittest.TestCase):
    def _client(self):
        app = Flask(__name__)
        app.register_blueprint(readiness.blueprint)
        return app.test_client()

    def test_go_live_is_blocked_when_public_launch_dependencies_are_missing(self):
        client = self._client()
        with patch.object(readiness, "PRODUCTION_MODE", True), \
             patch.object(readiness, "GROQ_API_KEY", "provider"), \
             patch.object(readiness, "OPENAI_API_KEY", ""), \
             patch.object(readiness, "DATABASE_URL", ""), \
             patch.object(readiness, "HISTORY_HMAC_SECRET", ""), \
             patch.object(readiness, "ENABLE_DEMO_CONSOLE", True), \
             patch.object(readiness, "ZALO_WEBHOOK_ENABLED", True), \
             patch.object(readiness, "ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch.object(readiness, "ZALO_APP_ID", "app"), \
             patch.object(readiness, "ZALO_OA_SECRET_KEY", "secret"), \
             patch.object(readiness, "ZALO_DIRECT_REPLY_ENABLED", False), \
             patch.object(readiness, "ZALO_OA_ACCESS_TOKEN", ""), \
             patch.object(readiness, "ZALO_OA_REFRESH_TOKEN", ""), \
             patch.object(readiness, "ZALO_OAUTH_REFRESH_READY", False), \
             patch.object(readiness, "history_persistence_ready", return_value=False), \
             patch.object(readiness, "zalo_token_persistence_ready", return_value=False), \
             patch.object(readiness, "zalo_dispatch_persistence_ready", return_value=False):
            response = client.get("/health/go-live")
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertFalse(body["ready_for_official_operation"])
        self.assertIn("persistent_history", body["blockers"])
        self.assertIn("zalo_direct_reply", body["blockers"])
        self.assertIn("zalo_oauth_refresh", body["blockers"])
        self.assertIn("zalo_refresh_persistence", body["blockers"])
        self.assertIn("zalo_durable_dispatch", body["blockers"])
        self.assertIn("public_demo_disabled", body["blockers"])

    def test_go_live_is_ready_only_when_every_gate_is_green(self):
        client = self._client()
        with patch.object(readiness, "PRODUCTION_MODE", True), \
             patch.object(readiness, "GROQ_API_KEY", "provider"), \
             patch.object(readiness, "OPENAI_API_KEY", ""), \
             patch.object(readiness, "DATABASE_URL", "postgres"), \
             patch.object(readiness, "HISTORY_HMAC_SECRET", "history-secret"), \
             patch.object(readiness, "ENABLE_DEMO_CONSOLE", False), \
             patch.object(readiness, "ZALO_WEBHOOK_ENABLED", True), \
             patch.object(readiness, "ZALO_WEBHOOK_SIGNATURE_REQUIRED", True), \
             patch.object(readiness, "ZALO_APP_ID", "app"), \
             patch.object(readiness, "ZALO_OA_SECRET_KEY", "secret"), \
             patch.object(readiness, "ZALO_DIRECT_REPLY_ENABLED", True), \
             patch.object(readiness, "ZALO_OA_ACCESS_TOKEN", "access"), \
             patch.object(readiness, "ZALO_OA_REFRESH_TOKEN", "refresh"), \
             patch.object(readiness, "ZALO_OAUTH_REFRESH_READY", True), \
             patch.object(readiness, "history_persistence_ready", return_value=True), \
             patch.object(readiness, "zalo_token_persistence_ready", return_value=True), \
             patch.object(readiness, "zalo_dispatch_persistence_ready", return_value=True):
            response = client.get("/health/go-live")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ready_for_official_operation"])
        self.assertEqual(body["blockers"], [])
        self.assertTrue(all(body["checks"].values()))


if __name__ == "__main__":
    unittest.main()
