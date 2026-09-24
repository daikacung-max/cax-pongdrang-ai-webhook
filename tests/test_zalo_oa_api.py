import unittest

from adapters.zalo_oa_api import ZaloOAClient, ZaloOAReplyError


class _Response:
    status_code = 200

    @staticmethod
    def json():
        return {"error": 0}


class _Session:
    def __init__(self):
        self.url = None
        self.kwargs = None

    def post(self, url, **kwargs):
        self.url = url
        self.kwargs = kwargs
        return _Response()


class ZaloOAApiTests(unittest.TestCase):
    def test_text_reply_uses_oa_access_token(self):
        session = _Session()
        client = ZaloOAClient("synthetic-access-token", session=session)

        self.assertTrue(client.send_text("synthetic-user", "Xin chào"))
        self.assertEqual(session.url, "https://openapi.zalo.me/v2.0/oa/message")
        self.assertEqual(session.kwargs["headers"]["access_token"], "synthetic-access-token")
        self.assertEqual(session.kwargs["json"]["recipient"]["user_id"], "synthetic-user")
        self.assertEqual(session.kwargs["json"]["message"]["text"], "Xin chào")

    def test_missing_access_token_fails_closed(self):
        with self.assertRaises(ZaloOAReplyError):
            ZaloOAClient("").send_text("synthetic-user", "Xin chào")

    def test_numeric_provider_error_is_safe_to_classify(self):
        class RejectedResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"error": -201, "message": "provider-only detail"}

        class RejectedSession:
            @staticmethod
            def post(*_args, **_kwargs):
                return RejectedResponse()

        with self.assertRaises(ZaloOAReplyError) as raised:
            ZaloOAClient("synthetic-access-token", session=RejectedSession()).send_text(
                "synthetic-user", "Xin chào"
            )

        self.assertEqual(raised.exception.reason, "reply_api_error_-201")


if __name__ == "__main__":
    unittest.main()
