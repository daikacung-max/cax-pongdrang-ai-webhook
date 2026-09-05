import hashlib
import hmac
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from config import (
    DATABASE_URL,
    DB_PATH,
    HISTORY_HMAC_SECRET,
    HISTORY_MAX_MESSAGES,
    HISTORY_POOL_MAX_SIZE,
    HISTORY_RETENTION_DAYS,
    UNIT_NAME,
)

_pool = None


def utc_now():
    return datetime.now(timezone.utc)


def conversation_key(user_id):
    """Khóa ổn định, không thể hiện Zalo user_id trong storage hoặc provider."""
    if DATABASE_URL and not HISTORY_HMAC_SECRET:
        raise RuntimeError("HISTORY_HMAC_SECRET là bắt buộc khi dùng Postgres.")
    secret = (HISTORY_HMAC_SECRET or f"{UNIT_NAME}:local-history").encode("utf-8")
    digest = hmac.new(secret, str(user_id or "").encode("utf-8"), hashlib.sha256).hexdigest()
    return "h1_" + digest[:48]


def backend_name():
    return "postgres" if DATABASE_URL else "sqlite"


def _postgres_pool():
    global _pool
    if _pool is None:
        try:
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL đã có nhưng psycopg_pool chưa được cài đặt.") from exc
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=0,
            max_size=max(1, HISTORY_POOL_MAX_SIZE),
            open=True,
        )
    return _pool


@contextmanager
def _sqlite():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_schema():
    if DATABASE_URL:
        if not HISTORY_HMAC_SECRET:
            raise RuntimeError("HISTORY_HMAC_SECRET là bắt buộc khi dùng Postgres.")
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        user_key TEXT PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id BIGSERIAL PRIMARY KEY,
                        user_key TEXT NOT NULL REFERENCES conversations(user_key),
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        meta_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_key ON messages(user_key, id DESC)")
        return

    with _sqlite() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                user_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                meta_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id DESC)")


def add_message(user_id, role, content, meta=None):
    key = conversation_key(user_id)
    now = utc_now()
    cutoff = now - timedelta(days=max(1, HISTORY_RETENTION_DAYS))
    payload = json.dumps(meta or {}, ensure_ascii=False)

    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations(user_key, created_at, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(user_key) DO UPDATE SET updated_at=EXCLUDED.updated_at
                """, (key, now, now))
                cur.execute("""
                    INSERT INTO messages(user_key, role, content, meta_json, created_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                """, (key, role, content, payload, now))
                cur.execute("DELETE FROM messages WHERE created_at < %s", (cutoff,))
                cur.execute("""
                    DELETE FROM messages WHERE id IN (
                        SELECT id FROM messages WHERE user_key=%s
                        ORDER BY id DESC OFFSET %s
                    )
                """, (key, max(1, HISTORY_MAX_MESSAGES)))
                cur.execute("""
                    DELETE FROM conversations c
                    WHERE c.updated_at < %s
                      AND NOT EXISTS (SELECT 1 FROM messages m WHERE m.user_key=c.user_key)
                """, (cutoff,))
        return

    now_text = now.isoformat()
    with _sqlite() as con:
        con.execute("""
            INSERT INTO conversations(user_id, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at
        """, (key, now_text, now_text))
        con.execute("""
            INSERT INTO messages(user_id, role, content, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key, role, content, payload, now_text))
        con.execute("DELETE FROM messages WHERE created_at < ?", (cutoff.isoformat(),))
        con.execute("""
            DELETE FROM messages WHERE id IN (
                SELECT id FROM messages WHERE user_id=? ORDER BY id DESC LIMIT -1 OFFSET ?
            )
        """, (key, max(1, HISTORY_MAX_MESSAGES)))
        con.execute("""
            DELETE FROM conversations
            WHERE updated_at < ? AND user_id NOT IN (SELECT DISTINCT user_id FROM messages)
        """, (cutoff.isoformat(),))


def get_history(user_id, limit=10):
    key = conversation_key(user_id)
    limit = min(max(1, int(limit)), max(1, HISTORY_MAX_MESSAGES))
    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT role, content, meta_json, created_at FROM messages
                    WHERE user_key=%s ORDER BY id DESC LIMIT %s
                """, (key, limit))
                rows = cur.fetchall()
        return [{
            "role": row[0], "content": row[1], "meta": row[2] or {},
            "created_at": row[3].isoformat() if row[3] else None,
        } for row in reversed(rows)]

    with _sqlite() as con:
        rows = con.execute("""
            SELECT role, content, meta_json, created_at FROM messages
            WHERE user_id=? ORDER BY id DESC LIMIT ?
        """, (key, limit)).fetchall()
    return [{
        "role": row["role"], "content": row["content"],
        "meta": json.loads(row["meta_json"] or "{}"), "created_at": row["created_at"],
    } for row in reversed(rows)]


def message_count():
    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM messages")
                return cur.fetchone()[0]
    with _sqlite() as con:
        return con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
