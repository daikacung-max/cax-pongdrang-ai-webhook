import unittest

from adapters.zalo_oa_api import ZaloOAClient


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


if __name__ == "__main__":
    unittest.main()
