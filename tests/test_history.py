import unittest
import uuid

from config import HISTORY_MAX_MESSAGES
from core import db
from core.history import conversation_key


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_schema()

    def test_conversation_key_does_not_expose_user_id(self):
        raw = "zalo-user-123456"
        key = conversation_key(raw)
        self.assertNotIn(raw, key)
        self.assertTrue(key.startswith("h1_"))

    def test_history_is_bounded_and_ordered(self):
        user_id = "test-" + uuid.uuid4().hex
        for index in range(HISTORY_MAX_MESSAGES + 3):
            db.add_message(user_id, "user", f"message-{index}")
        rows = db.get_history(user_id, limit=HISTORY_MAX_MESSAGES + 10)
        self.assertEqual(len(rows), HISTORY_MAX_MESSAGES)
        self.assertEqual(rows[-1]["content"], f"message-{HISTORY_MAX_MESSAGES + 2}")


if __name__ == "__main__":
    unittest.main()
