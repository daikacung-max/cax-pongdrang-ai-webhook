import unittest

from adapters.zalo_oa_api import ZaloOAClient, ZaloOAReplyError


class _Response:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        return self.responses.pop(0)


class ZaloTokenRefreshTests(unittest.TestCase):
    def test_refreshes_before_send_when_access_token_missing(self):
        session = _Session([
            _Response(200, {
                "access_token": "new-access",
                "refresh_token": "rotated-refresh",
                "expires_in": "3600",
            }),
            _Response(200, {"error": 0, "message": "Success"}),
        ])
        client = ZaloOAClient(
            "",
            refresh_token="refresh-1",
            app_id="app-1",
            app_secret="secret-1",
            session=session,
        )

        self.assertTrue(client.send_text("user-1", "Xin chào"))
        self.assertEqual(client.access_token, "new-access")
        self.assertEqual(client.refresh_token, "rotated-refresh")
        self.assertIn("/v4/oa/access_token", session.calls[0][0])
        self.assertEqual(session.calls[1][1]["headers"]["access_token"], "new-access")

    def test_rotated_refresh_token_is_persisted_before_becoming_runtime_state(self):
        saved = []
        session = _Session([
            _Response(200, {"access_token": "new-access", "refresh_token": "rotated-refresh"}),
            _Response(200, {"error": 0}),
        ])
        client = ZaloOAClient(
            "", refresh_token="old-refresh", app_id="app", app_secret="secret",
            session=session, persist_refresh_token=lambda value: saved.append(value) or True,
        )
        self.assertTrue(client.send_text("u", "x"))
        self.assertEqual(saved, ["rotated-refresh"])
        self.assertEqual(client.refresh_token, "rotated-refresh")

    def test_rotated_refresh_token_persistence_failure_fails_closed(self):
        session = _Session([
            _Response(200, {"access_token": "new-access", "refresh_token": "rotated-refresh"}),
        ])
        client = ZaloOAClient(
            "", refresh_token="old-refresh", app_id="app", app_secret="secret",
            session=session, persist_refresh_token=lambda value: False,
        )
        with self.assertRaises(ZaloOAReplyError):
            client.send_text("u", "x")
        self.assertEqual(client.access_token, "")
        self.assertEqual(client.refresh_token, "old-refresh")

    def test_refresh_without_rotation_updates_only_access_token(self):
        session = _Session([
            _Response(200, {"access_token": "new-access"}),
            _Response(200, {"error": 0}),
        ])
        client = ZaloOAClient(
            "old-access", refresh_token="old-refresh", app_id="app", app_secret="secret",
            session=session,
        )
        client._refresh_access_token()
        self.assertEqual(client.access_token, "new-access")
        self.assertEqual(client.refresh_token, "old-refresh")

    def test_authorization_code_bootstrap_persists_refresh_before_runtime_state(self):
        saved = []
        session = _Session([
            _Response(200, {"access_token": "new-access", "refresh_token": "new-refresh"}),
        ])
        client = ZaloOAClient(
            "old-access", refresh_token="old-refresh", app_id="app", app_secret="secret",
            session=session, persist_refresh_token=lambda value: saved.append(value) or True,
        )
        self.assertEqual(client.bootstrap_from_authorization_code("one-time-code"), "new-access")
        self.assertEqual(saved, ["new-refresh"])
        self.assertEqual(client.access_token, "new-access")
        self.assertEqual(client.refresh_token, "new-refresh")
        self.assertEqual(session.calls[0][1]["data"]["grant_type"], "authorization_code")

    def test_authorization_code_bootstrap_fails_closed_without_refresh_token(self):
        session = _Session([_Response(200, {"access_token": "new-access"})])
        client = ZaloOAClient(
            "old-access", refresh_token="old-refresh", app_id="app", app_secret="secret",
            session=session,
        )
        with self.assertRaises(ZaloOAReplyError):
            client.bootstrap_from_authorization_code("one-time-code")
        self.assertEqual(client.access_token, "old-access")
        self.assertEqual(client.refresh_token, "old-refresh")

    def test_refreshes_and_retries_once_on_expired_access_token(self):
        session = _Session([
            _Response(401, {}),
            _Response(200, {
                "access_token": "fresh-access",
                "refresh_token": "fresh-refresh",
            }),
            _Response(200, {"error": 0, "message": "Success"}),
        ])
        client = ZaloOAClient(
            "expired-access",
            refresh_token="refresh-1",
            app_id="app-1",
            app_secret="secret-1",
            session=session,
        )

        self.assertTrue(client.send_text("user-1", "Nội dung"))
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(session.calls[-1][1]["headers"]["access_token"], "fresh-access")

    def test_refreshes_when_zalo_returns_invalid_token_error_in_json(self):
        session = _Session([
            _Response(200, {"error": -124, "message": "Access token invalid"}),
            _Response(200, {
                "access_token": "fresh-access",
                "refresh_token": "fresh-refresh",
            }),
            _Response(200, {"error": 0, "message": "Success"}),
        ])
        client = ZaloOAClient(
            "expired-access",
            refresh_token="refresh-1",
            app_id="app-1",
            app_secret="secret-1",
            session=session,
        )

        self.assertTrue(client.send_text("user-1", "Nội dung"))
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(session.calls[-1][1]["headers"]["access_token"], "fresh-access")


if __name__ == "__main__":
    unittest.main()
