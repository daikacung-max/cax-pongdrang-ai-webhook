import unittest
from unittest.mock import patch

from adapters.zalo import PendingZaloMessages
from adapters.zalo_oa_api import ZaloOAClient, _split_text


class FakeResponse:
    status_code = 200

    @staticmethod
    def json():
        return {"error": 0}


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, params=None, json=None, timeout=None):
        self.calls.append({"url": url, "params": params, "json": json, "timeout": timeout})
        return FakeResponse()


class ZaloReplyHardeningTests(unittest.TestCase):
    def test_direct_reply_dedupes_without_leaving_pending_message(self):
        queue = PendingZaloMessages()
        with patch("adapters.zalo.ZALO_DIRECT_REPLY_ENABLED", True):
            self.assertTrue(queue.push("u1", "xin chao", msg_id="m1"))
            self.assertFalse(queue.push("u1", "xin chao", msg_id="m1"))
            self.assertIsNone(queue.pop(user_id="u1", wait_seconds=0))

    def test_dynamic_mode_still_queues_message(self):
        queue = PendingZaloMessages()
        with patch("adapters.zalo.ZALO_DIRECT_REPLY_ENABLED", False):
            self.assertTrue(queue.push("u1", "xin chao", msg_id="m2"))
            item = queue.pop(user_id="u1", wait_seconds=0)
        self.assertEqual(item["text"], "xin chao")

    def test_long_oa_reply_is_split_and_sent_in_order(self):
        session = FakeSession()
        client = ZaloOAClient("token", session=session)
        long_text = ("Đây là một câu trả lời có căn cứ nguồn. " * 120).strip()
        chunks = _split_text(long_text)
        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(len(chunks), 4)
        self.assertTrue(all(len(x) <= 1800 for x in chunks))

        self.assertTrue(client.send_text("user-1", long_text))
        self.assertEqual(len(session.calls), len(chunks))
        self.assertTrue(all(call["json"]["recipient"]["user_id"] == "user-1" for call in session.calls))


if __name__ == "__main__":
    unittest.main()
