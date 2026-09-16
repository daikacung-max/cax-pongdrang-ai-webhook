"""Durable encrypted queue for Zalo direct replies.

Every acknowledged webhook is represented by one Postgres row keyed by the
provider message id. A lease makes an interrupted worker recoverable without
allowing two workers to claim a live job at the same time. Payloads remain
encrypted at rest; successful rows retain only the idempotency key and audit
state for a bounded period.
"""

from datetime import datetime, timedelta, timezone
import json
import threading
import time

from config import (
    DATABASE_URL,
    ZALO_JOB_LEASE_SECONDS,
    ZALO_JOB_MAX_ATTEMPTS,
    ZALO_JOB_RETENTION_DAYS,
)
from core.history import _postgres_pool
from core.zalo_token_store import persistence_ready as encryption_ready, _fernet


_worker_started = False
_worker_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc)


def persistence_ready():
    """Configuration-level check used before accepting direct-reply webhooks."""
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
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TIMESTAMPTZ NOT NULL,
                    lease_expires_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    last_error_type TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """)
            # Existing P0 rows are migrated in place. IF NOT EXISTS keeps the
            # startup migration safe to execute from every web-process restart.
            cur.execute("ALTER TABLE zalo_reply_jobs ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ")
            cur.execute("ALTER TABLE zalo_reply_jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ")
            cur.execute("ALTER TABLE zalo_reply_jobs ADD COLUMN IF NOT EXISTS last_error_type TEXT")
            cur.execute("UPDATE zalo_reply_jobs SET status='pending' WHERE status IN ('queued', 'retry')")
            cur.execute("UPDATE zalo_reply_jobs SET status='dead' WHERE status='failed'")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_zalo_reply_jobs_ready ON zalo_reply_jobs(status, next_attempt_at, id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_zalo_reply_jobs_lease ON zalo_reply_jobs(status, lease_expires_at)")
            cur.execute(
                "DELETE FROM zalo_reply_jobs WHERE status IN ('completed', 'dead') AND updated_at < %s",
                (_now() - timedelta(days=max(1, ZALO_JOB_RETENTION_DAYS)),),
            )
    return True


def operational_ready():
    """Return true only when encryption and the live durable queue both work."""
    try:
        return bool(_ensure_schema())
    except Exception:
        return False


def enqueue(event_key, user_id, text):
    """Persist a single encrypted job before the webhook is acknowledged."""
    if not _ensure_schema():
        return False
    event_key = str(event_key or "").strip()
    user_id = str(user_id or "").strip()
    text = str(text or "").strip()
    if not event_key or not user_id or not text:
        return False
    payload = json.dumps({"user_id": user_id, "text": text}, ensure_ascii=False).encode("utf-8")
    ciphertext = _fernet().encrypt(payload).decode("ascii")
    now = _now()
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO zalo_reply_jobs(
                    event_key, ciphertext, status, attempts, next_attempt_at,
                    created_at, updated_at
                ) VALUES (%s, %s, 'pending', 0, %s, %s, %s)
                ON CONFLICT(event_key) DO NOTHING
            """, (event_key, ciphertext, now, now, now))
    # A duplicate webhook is already durable; it is safe to acknowledge it.
    return True


def recover_stale_jobs(now=None):
    """Release abandoned leases after a process crash or forced restart."""
    if not _ensure_schema():
        return 0
    now = now or _now()
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='pending', lease_expires_at=NULL,
                    next_attempt_at=%s, updated_at=%s,
                    last_error_type='lease_expired'
                WHERE status='processing' AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= %s
            """, (now, now, now))
            return max(0, cur.rowcount or 0)


def _claim_one():
    if not _ensure_schema():
        return None
    now = _now()
    lease_expires = now + timedelta(seconds=max(10, ZALO_JOB_LEASE_SECONDS))
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='pending', lease_expires_at=NULL,
                    next_attempt_at=%s, updated_at=%s,
                    last_error_type='lease_expired'
                WHERE status='processing' AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= %s
            """, (now, now, now))
            cur.execute("""
                SELECT id, ciphertext, attempts FROM zalo_reply_jobs
                WHERE status='pending' AND next_attempt_at <= %s
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """, (now,))
            row = cur.fetchone()
            if not row:
                return None
            attempts = int(row[2] or 0) + 1
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='processing', attempts=%s, lease_expires_at=%s,
                    updated_at=%s, last_error_type=NULL
                WHERE id=%s
            """, (attempts, lease_expires, now, row[0]))
    try:
        payload = json.loads(_fernet().decrypt(str(row[1]).encode("ascii")).decode("utf-8"))
    except Exception:
        _mark_dead(row[0], "payload_decrypt_failed")
        return None
    return {
        "id": row[0],
        "user_id": payload.get("user_id"),
        "text": payload.get("text"),
        "attempts": attempts,
    }


def _complete(job_id):
    now = _now()
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            # The encrypted message body is no longer needed after delivery.
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='completed', ciphertext='', lease_expires_at=NULL,
                    completed_at=%s, updated_at=%s, last_error_type=NULL
                WHERE id=%s AND status='processing'
            """, (now, now, job_id))


def _mark_dead(job_id, error_type="dispatch_failed"):
    now = _now()
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='dead', lease_expires_at=NULL, updated_at=%s,
                    last_error_type=%s
                WHERE id=%s
            """, (now, str(error_type or "dispatch_failed")[:80], job_id))


def _retry(job_id, attempts, error_type="dispatch_failed"):
    attempts = int(attempts or 0)
    if attempts >= max(1, ZALO_JOB_MAX_ATTEMPTS):
        _mark_dead(job_id, error_type)
        return "dead"
    now = _now()
    next_attempt = now + timedelta(seconds=min(30, 2 ** attempts))
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE zalo_reply_jobs
                SET status='pending', lease_expires_at=NULL, next_attempt_at=%s,
                    updated_at=%s, last_error_type=%s
                WHERE id=%s AND status='processing'
            """, (next_attempt, now, str(error_type or "dispatch_failed")[:80], job_id))
    return "pending"


def job_state(event_key):
    """Internal diagnostic for tests; never returns encrypted payloads."""
    if not _ensure_schema():
        return None
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                SELECT status, attempts, lease_expires_at, completed_at, last_error_type
                FROM zalo_reply_jobs WHERE event_key=%s
            """, (str(event_key or ""),))
            row = cur.fetchone()
    if not row:
        return None
    return {
        "status": row[0], "attempts": int(row[1] or 0),
        "lease_expires_at": row[2].isoformat() if row[2] else None,
        "completed_at": row[3].isoformat() if row[3] else None,
        "last_error_type": row[4],
    }


def delete_for_user(user_id):
    """Remove queued encrypted payloads for a user withdrawal request."""
    if not _ensure_schema():
        return 0
    user_id = str(user_id or "").strip()
    if not user_id:
        return 0
    removed = 0
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT id, ciphertext FROM zalo_reply_jobs WHERE ciphertext <> ''")
            rows = cur.fetchall()
            for job_id, ciphertext in rows:
                try:
                    payload = json.loads(_fernet().decrypt(str(ciphertext).encode("ascii")).decode("utf-8"))
                except Exception:
                    _mark_dead(job_id, "payload_decrypt_failed")
                    continue
                if str(payload.get("user_id") or "") == user_id:
                    cur.execute("DELETE FROM zalo_reply_jobs WHERE id=%s", (job_id,))
                    removed += 1
    return removed


def start_worker(reply_func, logger=None, poll_seconds=0.5):
    """Start one dispatcher per process; row locks and leases protect replicas."""
    global _worker_started
    if not operational_ready():
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
                    error_type = type(exc).__name__
                    error_reason = str(getattr(exc, "reason", "unknown"))[:80]
                    _retry(job["id"], job["attempts"], error_type)
                    if logger:
                        logger.error(
                            "zalo_dispatch failed type=%s reason=%s",
                            error_type,
                            error_reason,
                        )
            except Exception as exc:
                if logger:
                    logger.error("zalo_dispatch loop_error type=%s", type(exc).__name__)
                time.sleep(1.0)

    thread = threading.Thread(target=run, name="zalo-direct-reply-dispatch", daemon=True)
    thread.start()
    return True
