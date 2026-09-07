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
        self.assertEqual(session.kwargs["params"]["access_token"], "synthetic-access-token")
        self.assertEqual(session.kwargs["json"]["recipient"]["user_id"], "synthetic-user")
        self.assertEqual(session.kwargs["json"]["message"]["text"], "Xin chào")

    def test_missing_access_token_fails_closed(self):
        with self.assertRaises(ZaloOAReplyError):
            ZaloOAClient("").send_text("synthetic-user", "Xin chào")


if __name__ == "__main__":
    unittest.main()
