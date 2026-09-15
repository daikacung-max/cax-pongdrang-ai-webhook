import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import core.privacy as privacy
from core.history import conversation_key


class PrivacyDeletionTests(unittest.TestCase):
    def test_delete_user_data_removes_history_and_case_linkage(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "privacy.db"
            con = sqlite3.connect(str(db_path))
            con.executescript("""
                CREATE TABLE conversations (user_id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT);
                CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, role TEXT, content TEXT, meta_json TEXT, created_at TEXT);
                CREATE TABLE intake_cases (case_id TEXT PRIMARY KEY, user_key TEXT, procedure_code TEXT, queue_code TEXT, status TEXT, created_at TEXT, updated_at TEXT);
            """)
            key = conversation_key("zalo-user-1")
            con.execute("INSERT INTO conversations VALUES (?, '', '')", (key,))
            con.execute("INSERT INTO messages(user_id, role, content, meta_json, created_at) VALUES (?, 'user', 'x', '{}', '')", (key,))
            con.execute("INSERT INTO intake_cases VALUES ('case-1', ?, 'p', 'q', 'received', '', '')", (key,))
            con.commit()
            con.close()

            with patch.object(privacy, "DATABASE_URL", ""), patch.object(privacy, "DB_PATH", db_path):
                result = privacy.delete_user_data("zalo-user-1")

            self.assertEqual(result, {"messages": 1, "conversations": 1, "cases": 1})
            con = sqlite3.connect(str(db_path))
            self.assertEqual(con.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM intake_cases").fetchone()[0], 0)
            con.close()

    def test_signed_user_withdraw_event_invokes_deletion_and_pending_purge(self):
        import app

        handler = app.app.view_functions["zalo_webhook"]
        delete_mock = MagicMock(return_value={"messages": 1, "conversations": 1, "cases": 0})
        with patch.object(app, "ZALO_WEBHOOK_ENABLED", True), \
             patch.object(app, "_valid_zalo_webhook_signature", return_value=True), \
             patch.object(app.pending, "purge_user") as purge_mock, \
             patch.dict(handler.__globals__, {"delete_zalo_subject_data": delete_mock}):
            response = app.app.test_client().post("/zalo/webhook", json={
                "app_id": "app-1",
                "timestamp": "1",
                "event_name": "user_withdraw",
                "user_id": "oa-user-1",
                "user_id_by_app": "app-user-1",
            }, headers={"X-ZEvent-Signature": "synthetic"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json().get("success"), True)
        self.assertEqual(purge_mock.call_count, 2)
        delete_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
