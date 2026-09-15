"""Durable encrypted queue for Zalo direct replies.

A signed webhook should be acknowledged promptly, while the AI/provider/OA call
may take longer. Jobs live in managed Postgres and carry an encrypted payload,
so an acknowledged message survives worker/process restarts without storing the
Zalo user id or message text in plaintext.
"""

from datetime import datetime, timedelta, timezone
import json
import threading
import time

from config import DATABASE_URL
from core.history import _postgres_pool
from core.zalo_token_store import persistence_ready as encryption_ready, _fernet


_worker_started = False
_worker_lock = threading.Lock()


def persistence_ready():
    return bool(DATABASE_URL and encryption_ready())


def _ensure_schema():
    if not persistence_ready():
        return False
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS zalo_reply_jobs (
                    id BIGSERIAL PRIMARY KEY,
                    event_key TEXT UNIQUE NOT NULL,
                    ciphertext TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_zalo_reply_jobs_ready ON zalo_reply_jobs(status, next_attempt_at, id)")
    return True


def enqueue(event_key, user_id, text):
    if not _ensure_schema():
        return False
    event_key = str(event_key or "").strip()
    user_id = str(user_id or "").strip()
    text = str(text or "").strip()
    if not event_key or not user_id or not text:
        return False
    payload = json.dumps({"user_id": user_id, "text": text}, ensure_ascii=False).encode("utf-8")
    ciphertext = _fernet().encrypt(payload).decode("ascii")
    now = datetime.now(timezone.utc)
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO zalo_reply_jobs(event_key, ciphertext, status, attempts, next_attempt_at, created_at, updated_at)
                VALUES (%s, %s, 'queued', 0, %s, %s, %s)
                ON CONFLICT(event_key) DO NOTHING
            """, (event_key, ciphertext, now, now, now))
    return True


def _claim_one():
    if not _ensure_schema():
        return None
    now = datetime.now(timezone.utc)
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                SELECT id, ciphertext, attempts FROM zalo_reply_jobs
                WHERE status IN ('queued', 'retry') AND next_attempt_at <= %s
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """, (now,))
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("UPDATE zalo_reply_jobs SET status='processing', updated_at=%s WHERE id=%s", (now, row[0]))
    try:
        payload = json.loads(_fernet().decrypt(str(row[1]).encode("ascii")).decode("utf-8"))
    except Exception:
        _mark_dead(row[0])
        return None
    return {"id": row[0], "user_id": payload.get("user_id"), "text": payload.get("text"), "attempts": int(row[2] or 0)}


def _complete(job_id):
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            # Delete successful payloads immediately. The conversation store has
            # its own retention policy and no duplicate plaintext is retained.
            cur.execute("DELETE FROM zalo_reply_jobs WHERE id=%s", (job_id,))


def _mark_dead(job_id):
    now = datetime.now(timezone.utc)
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("UPDATE zalo_reply_jobs SET status='dead', updated_at=%s WHERE id=%s", (now, job_id))


def _retry(job_id, attempts):
    attempts = int(attempts or 0) + 1
    if attempts >= 3:
        _mark_dead(job_id)
        return
    now = datetime.now(timezone.utc)
    next_attempt = now + timedelta(seconds=min(30, 2 ** attempts))
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='retry', attempts=%s, next_attempt_at=%s, updated_at=%s
                WHERE id=%s
            """, (attempts, next_attempt, now, job_id))


def delete_for_user(user_id):
    """Remove queued encrypted payloads for a user withdrawal request."""
    if not _ensure_schema():
        return 0
    user_id = str(user_id or "").strip()
    if not user_id:
        return 0
    # Payload is encrypted, so scan the small pending set and compare after
    # decrypting. We do not persist a reversible/plain external identifier.
    removed = 0
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT id, ciphertext FROM zalo_reply_jobs WHERE status <> 'dead'")
            rows = cur.fetchall()
            for job_id, ciphertext in rows:
                try:
                    payload = json.loads(_fernet().decrypt(str(ciphertext).encode("ascii")).decode("utf-8"))
                except Exception:
                    continue
                if str(payload.get("user_id") or "") == user_id:
                    cur.execute("DELETE FROM zalo_reply_jobs WHERE id=%s", (job_id,))
                    removed += 1
    return removed


def start_worker(reply_func, logger=None, poll_seconds=0.5):
    """Start one daemon dispatcher per process; DB row locking handles replicas."""
    global _worker_started
    if not persistence_ready():
        return False
    with _worker_lock:
        if _worker_started:
            return True
        _worker_started = True

    def run():
        while True:
            try:
                job = _claim_one()
                if not job:
                    time.sleep(poll_seconds)
                    continue
                try:
                    reply_func(job["user_id"], job["text"])
                    _complete(job["id"])
                except Exception as exc:
                    _retry(job["id"], job["attempts"])
                    if logger:
                        logger.error("zalo_dispatch failed type=%s", type(exc).__name__)
            except Exception as exc:
                if logger:
                    logger.error("zalo_dispatch loop_error type=%s", type(exc).__name__)
                time.sleep(1.0)

    thread = threading.Thread(target=run, name="zalo-direct-reply-dispatch", daemon=True)
    thread.start()
    return True
