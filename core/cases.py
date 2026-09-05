"""Hồ sơ tiếp nhận tối thiểu cho đường chạy production.

Hồ sơ chỉ lưu khóa HMAC của cuộc trao đổi, mã nhóm việc và trạng thái. Nội dung
hội thoại vẫn nằm trong kho lịch sử có thời hạn lưu/xóa riêng, không được nhân
bản sang bảng hồ sơ hoặc ghi log.
"""

import secrets
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DATABASE_URL, DB_PATH
from core.history import _postgres_pool, conversation_key
import sqlite3


OPEN_STATUSES = ("received", "in_review", "needs_information", "transferred")
ALLOWED_STATUSES = OPEN_STATUSES + ("closed",)


def _now():
    return datetime.now(timezone.utc)


def _case_id():
    return "CAX-" + _now().strftime("%Y%m%d") + "-" + secrets.token_hex(5).upper()


@contextmanager
def _sqlite():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_schema():
    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS intake_cases (
                        case_id TEXT PRIMARY KEY,
                        user_key TEXT NOT NULL,
                        procedure_code TEXT NOT NULL,
                        queue_code TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_intake_cases_queue ON intake_cases(queue_code, status, updated_at DESC)")
        return

    with _sqlite() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS intake_cases (
                case_id TEXT PRIMARY KEY,
                user_key TEXT NOT NULL,
                procedure_code TEXT NOT NULL,
                queue_code TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_intake_cases_queue ON intake_cases(queue_code, status, updated_at DESC)")


def create_or_get_open(user_id, intake):
    """Tạo đúng một hồ sơ đang mở cho cùng người và nhóm việc."""
    if intake.get("handoff_status") != "ready_for_officer":
        return None
    procedure = str(intake.get("procedure_code") or "").strip()
    queue = str(intake.get("handoff_queue") or "").strip()
    if not procedure or not queue:
        return None
    key = conversation_key(user_id)
    now = _now()
    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT case_id, status FROM intake_cases
                    WHERE user_key=%s AND procedure_code=%s AND status <> 'closed'
                    ORDER BY updated_at DESC LIMIT 1
                """, (key, procedure))
                row = cur.fetchone()
                if row:
                    return {"case_id": row[0], "status": row[1], "created": False}
                case_id = _case_id()
                cur.execute("""
                    INSERT INTO intake_cases(case_id, user_key, procedure_code, queue_code, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'received', %s, %s)
                """, (case_id, key, procedure, queue, now, now))
                return {"case_id": case_id, "status": "received", "created": True}

    now_text = now.isoformat()
    with _sqlite() as con:
        row = con.execute("""
            SELECT case_id, status FROM intake_cases
            WHERE user_key=? AND procedure_code=? AND status <> 'closed'
            ORDER BY updated_at DESC LIMIT 1
        """, (key, procedure)).fetchone()
        if row:
            return {"case_id": row[0], "status": row[1], "created": False}
        case_id = _case_id()
        con.execute("""
            INSERT INTO intake_cases(case_id, user_key, procedure_code, queue_code, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'received', ?, ?)
        """, (case_id, key, procedure, queue, now_text, now_text))
        return {"case_id": case_id, "status": "received", "created": True}


def list_cases(queue_code=None, limit=50):
    limit = min(max(1, int(limit)), 100)
    queue_code = str(queue_code or "").strip()
    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                if queue_code:
                    cur.execute("SELECT case_id, procedure_code, queue_code, status, created_at, updated_at FROM intake_cases WHERE queue_code=%s ORDER BY updated_at DESC LIMIT %s", (queue_code, limit))
                else:
                    cur.execute("SELECT case_id, procedure_code, queue_code, status, created_at, updated_at FROM intake_cases ORDER BY updated_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
        return [_serialize(row) for row in rows]
    with _sqlite() as con:
        sql = "SELECT case_id, procedure_code, queue_code, status, created_at, updated_at FROM intake_cases"
        args = []
        if queue_code:
            sql += " WHERE queue_code=?"
            args.append(queue_code)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(limit)
        return [_serialize(row) for row in con.execute(sql, args).fetchall()]


def _serialize(row):
    return {"case_id": row[0], "procedure_code": row[1], "queue_code": row[2], "status": row[3], "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else row[4], "updated_at": row[5].isoformat() if hasattr(row[5], "isoformat") else row[5]}
