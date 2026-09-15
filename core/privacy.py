"""Data-subject deletion helpers for signed Zalo withdrawal events."""

import sqlite3

from config import DATABASE_URL, DB_PATH
from core.history import _postgres_pool, conversation_key


def delete_user_data(user_id):
    """Delete stored conversation/case linkage for one external user id.

    The external identifier itself is never stored. We derive the same HMAC key
    used by history/cases and delete only rows linked to that key.
    """
    user_id = str(user_id or "").strip()
    if not user_id:
        return {"messages": 0, "conversations": 0, "cases": 0}
    key = conversation_key(user_id)

    if DATABASE_URL:
        with _postgres_pool().connection() as con:
            with con.cursor() as cur:
                cur.execute("DELETE FROM messages WHERE user_key=%s", (key,))
                messages = cur.rowcount or 0
                cur.execute("DELETE FROM conversations WHERE user_key=%s", (key,))
                conversations = cur.rowcount or 0
                cur.execute("DELETE FROM intake_cases WHERE user_key=%s", (key,))
                cases = cur.rowcount or 0
        return {"messages": messages, "conversations": conversations, "cases": cases}

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    try:
        cur = con.execute("DELETE FROM messages WHERE user_id=?", (key,))
        messages = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        cur = con.execute("DELETE FROM conversations WHERE user_id=?", (key,))
        conversations = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        cur = con.execute("DELETE FROM intake_cases WHERE user_key=?", (key,))
        cases = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        con.commit()
    finally:
        con.close()
    return {"messages": messages, "conversations": conversations, "cases": cases}


def delete_zalo_subject_data(data):
    """Delete by every Zalo identifier supplied in a signed withdrawal event."""
    ids = []
    for field in ("user_id", "user_id_by_app"):
        value = str((data or {}).get(field) or "").strip()
        if value and value not in ids:
            ids.append(value)
    totals = {"messages": 0, "conversations": 0, "cases": 0}
    for value in ids:
        result = delete_user_data(value)
        for key in totals:
            totals[key] += int(result.get(key) or 0)
    return totals
