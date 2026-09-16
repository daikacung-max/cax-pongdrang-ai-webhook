import unittest
from unittest.mock import patch

import app as production_app


class _OAuthClient:
    def __init__(self):
        self.codes = []

    def bootstrap_from_authorization_code(self, code):
        self.codes.append(code)
        return "not-exposed"


class ZaloOAuthCallbackTests(unittest.TestCase):
    def setUp(self):
        self.client = production_app.app.test_client()
        self.start = production_app.app.view_functions["zalo_oauth_start"]
        self.callback = production_app.app.view_functions["zalo_oauth_callback"]

    def test_start_fails_closed_without_oauth_configuration(self):
        with patch.dict(self.start.__globals__, {
            "ZALO_APP_ID": "",
            "ZALO_APP_SECRET_KEY": "",
            "ZALO_OAUTH_CALLBACK_URL": "",
        }):
            response = self.client.get("/zalo/oauth/start")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["reason"], "oauth_not_configured")

    def test_callback_rejects_missing_or_invalid_state(self):
        response = self.client.get("/zalo/oauth/callback?code=one-time-code&state=invalid")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["reason"], "oauth_callback_rejected")

    def test_callback_exchanges_valid_code_without_exposing_tokens(self):
        oauth_client = _OAuthClient()
        with patch.dict(self.callback.__globals__, {"ZALO_APP_SECRET_KEY": "test-secret"}):
            state = self.callback.__globals__["_oauth_state"]()
            with patch.object(production_app, "zalo_oa_client", oauth_client):
                response = self.client.get(
                    f"/zalo/oauth/callback?code=one-time-code&state={state}"
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"success": True, "status": "oauth_authorized"})
        self.assertEqual(oauth_client.codes, ["one-time-code"])
        self.assertNotIn("not-exposed", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
