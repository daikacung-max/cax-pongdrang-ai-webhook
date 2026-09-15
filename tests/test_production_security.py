import unittest
from unittest.mock import patch

from flask import Flask

import core.production_security as security


class ProductionSecurityTests(unittest.TestCase):
    def _app(self):
        app = Flask(__name__)

        @app.post("/api/chat")
        def api_chat():
            return {"ok": True}

        @app.get("/debug/article/134")
        def debug_article():
            return {"found": True}

        @app.post("/demo/api/ai-chat")
        def demo_chat():
            return {"ok": True}

        return app

    def test_production_hides_debug_and_unauthenticated_chat_api(self):
        app = self._app()
        with patch.object(security, "PRODUCTION_MODE", True), \
             patch.object(security, "_API_CHAT_TOKEN", ""), \
             patch.object(security, "_ENABLE_DEBUG_ENDPOINTS", False):
            security.register_production_security(app)
            client = app.test_client()
            self.assertEqual(client.get("/debug/article/134").status_code, 404)
            self.assertEqual(client.post("/api/chat", json={"x": 1}).status_code, 404)

    def test_production_chat_requires_matching_bearer_token(self):
        app = self._app()
        with patch.object(security, "PRODUCTION_MODE", True), \
             patch.object(security, "_API_CHAT_TOKEN", "secret-token"):
            security.register_production_security(app)
            client = app.test_client()
            self.assertEqual(client.post("/api/chat", json={"x": 1}).status_code, 401)
            response = client.post(
                "/api/chat",
                json={"x": 1},
                headers={"Authorization": "Bearer secret-token"},
            )
            self.assertEqual(response.status_code, 200)

    def test_security_headers_are_added(self):
        app = self._app()
        with patch.object(security, "PRODUCTION_MODE", True):
            security.register_production_security(app)
            response = app.test_client().post("/demo/api/ai-chat", json={"x": 1})
            self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
            self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
            self.assertIn("max-age=31536000", response.headers.get("Strict-Transport-Security", ""))

    def test_request_body_limit_is_enforced(self):
        app = self._app()
        with patch.object(security, "_MAX_REQUEST_BYTES", 4096):
            security.register_production_security(app)
            response = app.test_client().post(
                "/demo/api/ai-chat",
                data=b"x" * 5000,
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
