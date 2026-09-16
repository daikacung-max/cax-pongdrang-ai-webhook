"""Restart-oriented regression tests for the Postgres persistence boundary.

The CI runner has no managed Postgres service.  These tests use a recording
Postgres protocol double so they exercise the same SQL transitions and Fernet
encryption path that production uses, without adding a SQLite fallback to the
production durable queue.
"""

from contextlib import contextmanager
from cryptography.fernet import Fernet
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core import history, zalo_jobs, zalo_token_store


class _Cursor:
    def __init__(self, pool):
        self.pool = pool
        self.rowcount = pool.rowcount

    def execute(self, sql, params=None):
        self.pool.commands.append((" ".join(sql.split()), params))
        self.rowcount = self.pool.rowcount

    def fetchone(self):
        return self.pool.rows.pop(0) if self.pool.rows else None

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Connection:
    def __init__(self, pool):
        self.pool = pool

    def cursor(self):
        return _Cursor(self.pool)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Pool:
    def __init__(self, rows=None, rowcount=1):
        self.rows = list(rows or [])
        self.rowcount = rowcount
        self.commands = []

    @contextmanager
    def connection(self):
        yield _Connection(self)


class PersistentHistoryRestartTests(unittest.TestCase):
    def test_history_survives_new_store_access_and_stays_user_scoped(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(history, "DATABASE_URL", ""), \
             patch.object(history, "DB_PATH", Path(directory) / "history.db"):
            history.init_schema()
            history.add_message("zalo-a", "user", "turn one", {"path": "test"})
            history.add_message("zalo-a", "assistant", "turn two")
            history.add_message("zalo-b", "user", "other user")

            # Every SQLite call opens a new connection, equivalent to a fresh
            # process reading the same durable local/test store.
            restored = history.get_history("zalo-a", limit=20)

        self.assertEqual([item["content"] for item in restored], ["turn one", "turn two"])
        self.assertEqual(restored[0]["meta"], {"path": "test"})
        self.assertNotIn("other user", [item["content"] for item in restored])


class ZaloQueueRestartTests(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key().decode("ascii")
        self.fernet = Fernet(self.key.encode("ascii"))

    def test_enqueue_encrypts_payload_and_uses_provider_event_id_for_deduplication(self):
        pool = _Pool()
        with patch.object(zalo_jobs, "_ensure_schema", return_value=True), \
             patch.object(zalo_jobs, "_postgres_pool", return_value=pool), \
             patch.object(zalo_jobs, "_fernet", return_value=self.fernet):
            self.assertTrue(zalo_jobs.enqueue("provider-msg-1", "user-1", "Nội dung riêng"))

        insert = next(params for sql, params in pool.commands if "INSERT INTO zalo_reply_jobs" in sql)
        self.assertEqual(insert[0], "provider-msg-1")
        self.assertNotIn("user-1", insert[1])
        self.assertNotIn("Nội dung riêng", insert[1])
        self.assertIn("ON CONFLICT(event_key) DO NOTHING", next(sql for sql, _ in pool.commands if "INSERT INTO zalo_reply_jobs" in sql))

    def test_claim_releases_expired_lease_then_marks_exactly_one_row_processing(self):
        ciphertext = self.fernet.encrypt(b'{"user_id":"user-1","text":"restart-safe"}').decode("ascii")
        pool = _Pool(rows=[(21, ciphertext, 1)])
        with patch.object(zalo_jobs, "_ensure_schema", return_value=True), \
             patch.object(zalo_jobs, "_postgres_pool", return_value=pool), \
             patch.object(zalo_jobs, "_fernet", return_value=self.fernet):
            job = zalo_jobs._claim_one()

        self.assertEqual(job, {"id": 21, "user_id": "user-1", "text": "restart-safe", "attempts": 2})
        sql = "\n".join(statement for statement, _ in pool.commands)
        self.assertIn("WHERE status='processing' AND lease_expires_at IS NOT NULL", sql)
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("status='processing', attempts=%s, lease_expires_at=%s", sql)

    def test_failed_dispatch_retries_with_backoff_then_enters_dead_state(self):
        retry_pool = _Pool()
        with patch.object(zalo_jobs, "_postgres_pool", return_value=retry_pool), \
             patch.object(zalo_jobs, "ZALO_JOB_MAX_ATTEMPTS", 3):
            self.assertEqual(zalo_jobs._retry(7, 1, "TimeoutError"), "pending")
        retry_sql = "\n".join(statement for statement, _ in retry_pool.commands)
        self.assertIn("status='pending'", retry_sql)
        self.assertIn("next_attempt_at=%s", retry_sql)

        dead_pool = _Pool()
        with patch.object(zalo_jobs, "_postgres_pool", return_value=dead_pool), \
             patch.object(zalo_jobs, "ZALO_JOB_MAX_ATTEMPTS", 3):
            self.assertEqual(zalo_jobs._retry(7, 3, "TimeoutError"), "dead")
        dead_sql = "\n".join(statement for statement, _ in dead_pool.commands)
        self.assertIn("status='dead'", dead_sql)

    def test_completed_job_erases_payload_but_keeps_bounded_dedup_audit_state(self):
        pool = _Pool()
        with patch.object(zalo_jobs, "_postgres_pool", return_value=pool):
            zalo_jobs._complete(8)
        sql = "\n".join(statement for statement, _ in pool.commands)
        self.assertIn("status='completed', ciphertext=''", sql)


class ZaloTokenPersistenceRestartTests(unittest.TestCase):
    def test_generated_render_secret_derives_a_valid_fernet_key(self):
        with patch.dict("os.environ", {"ZALO_TOKEN_ENCRYPTION_KEY": "r" * 32}, clear=False), \
             patch.object(zalo_token_store, "DATABASE_URL", "postgres://managed"):
            self.assertTrue(zalo_token_store.persistence_ready())
            ciphertext = zalo_token_store._fernet().encrypt(b"token")
            self.assertEqual(zalo_token_store._fernet().decrypt(ciphertext), b"token")

    def test_rotated_token_is_encrypted_and_reloaded_after_restart(self):
        key = Fernet.generate_key().decode("ascii")
        fernet = Fernet(key.encode("ascii"))
        pool = _Pool(rows=[(fernet.encrypt(b"rotated-refresh-token").decode("ascii"),)])
        with patch.dict("os.environ", {"ZALO_TOKEN_ENCRYPTION_KEY": key}, clear=False), \
             patch.object(zalo_token_store, "DATABASE_URL", "postgres://managed"), \
             patch.object(zalo_token_store, "_ensure_schema", return_value=True), \
             patch.object(zalo_token_store, "_postgres_pool", return_value=pool):
            self.assertEqual(zalo_token_store.load_refresh_token("seed-token"), "rotated-refresh-token")
            self.assertTrue(zalo_token_store.save_refresh_token("new-rotated-token"))

        insert = next(params for sql, params in pool.commands if "INSERT INTO integration_secrets" in sql)
        self.assertNotIn("new-rotated-token", insert[1])
        self.assertNotIn("rotated-refresh-token", "\n".join(sql for sql, _ in pool.commands))

    def test_unreachable_token_store_is_not_operationally_ready(self):
        with patch.object(zalo_token_store, "_ensure_schema", side_effect=RuntimeError("db unavailable")):
            self.assertFalse(zalo_token_store.operational_ready())


if __name__ == "__main__":
    unittest.main()
