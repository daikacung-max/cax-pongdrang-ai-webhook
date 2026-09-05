import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH
from core import history


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_schema():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                number TEXT,
                issuer TEXT,
                effective_from TEXT,
                effective_to TEXT,
                source_path TEXT NOT NULL,
                sha256 TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS legal_units (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                article TEXT,
                clause TEXT,
                point TEXT,
                title TEXT,
                text TEXT NOT NULL,
                effective_from TEXT,
                effective_to TEXT,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
        """)
        con.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS legal_units_fts USING fts5(
                unit_id UNINDEXED,
                document_id UNINDEXED,
                article,
                title,
                text,
                tokenize = 'unicode61 remove_diacritics 2'
            )
        """)
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
    history.init_schema()


def upsert_document(doc):
    with connect() as con:
        con.execute("""
            INSERT INTO documents (
                id, title, number, issuer, effective_from, effective_to,
                source_path, sha256, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                number=excluded.number,
                issuer=excluded.issuer,
                effective_from=excluded.effective_from,
                effective_to=excluded.effective_to,
                source_path=excluded.source_path,
                sha256=excluded.sha256,
                metadata_json=excluded.metadata_json
        """, (
            doc["id"], doc["title"], doc.get("number"), doc.get("issuer"),
            doc.get("effective_from"), doc.get("effective_to"), doc["source_path"],
            doc.get("sha256"), json.dumps(doc.get("metadata", {}), ensure_ascii=False),
        ))


def replace_document_units(document_id, units):
    with connect() as con:
        old_ids = [row["id"] for row in con.execute(
            "SELECT id FROM legal_units WHERE document_id=?", (document_id,)
        ).fetchall()]
        if old_ids:
            placeholders = ",".join("?" for _ in old_ids)
            con.execute(f"DELETE FROM legal_units_fts WHERE unit_id IN ({placeholders})", old_ids)
        con.execute("DELETE FROM legal_units WHERE document_id=?", (document_id,))
        for unit in units:
            con.execute("""
                INSERT INTO legal_units (
                    id, document_id, unit_type, article, clause, point,
                    title, text, effective_from, effective_to
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                unit["id"], document_id, unit.get("unit_type", "article"),
                unit.get("article"), unit.get("clause"), unit.get("point"),
                unit.get("title"), unit["text"], unit.get("effective_from"),
                unit.get("effective_to"),
            ))
            con.execute("""
                INSERT INTO legal_units_fts (unit_id, document_id, article, title, text)
                VALUES (?, ?, ?, ?, ?)
            """, (
                unit["id"], document_id, unit.get("article") or "",
                unit.get("title") or "", unit["text"],
            ))


def get_unit(unit_id):
    with connect() as con:
        row = con.execute("""
            SELECT u.*, d.title AS document_title, d.number AS document_number,
                   d.issuer AS document_issuer, d.source_path
            FROM legal_units u JOIN documents d ON d.id=u.document_id
            WHERE u.id=?
        """, (unit_id,)).fetchone()
        return dict(row) if row else None


def get_article(document_id, article):
    with connect() as con:
        rows = con.execute("""
            SELECT u.*, d.title AS document_title, d.number AS document_number,
                   d.issuer AS document_issuer, d.source_path
            FROM legal_units u JOIN documents d ON d.id=u.document_id
            WHERE u.document_id=? AND u.article=? ORDER BY u.id
        """, (document_id, str(article))).fetchall()
        return [dict(x) for x in rows]


def search_fts(query, limit=8, document_ids=None):
    query = (query or "").strip()
    if not query:
        return []
    with connect() as con:
        sql = """
            SELECT f.unit_id, bm25(legal_units_fts, 0.0, 0.0, 3.0, 5.0, 1.0) AS rank
            FROM legal_units_fts f WHERE legal_units_fts MATCH ?
        """
        params = [query]
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            sql += f" AND f.document_id IN ({placeholders})"
            params.extend(document_ids)
        sql += " ORDER BY rank LIMIT ?"
        params.append(int(limit))
        try:
            ids = con.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []
    result = []
    for row in ids:
        unit = get_unit(row["unit_id"])
        if unit:
            unit["_rank"] = row["rank"]
            result.append(unit)
    return result


def search_like(query, limit=8):
    tokens = [x for x in query.split() if len(x) >= 2][:5]
    if not tokens:
        return []
    with connect() as con:
        clauses, params = [], []
        for token in tokens:
            clauses.append("(u.title LIKE ? OR u.text LIKE ?)")
            params.extend([f"%{token}%", f"%{token}%"])
        sql = f"""
            SELECT u.*, d.title AS document_title, d.number AS document_number,
                   d.issuer AS document_issuer, d.source_path
            FROM legal_units u JOIN documents d ON d.id=u.document_id
            WHERE {' OR '.join(clauses)} LIMIT ?
        """
        params.append(int(limit))
        return [dict(x) for x in con.execute(sql, params).fetchall()]


def add_message(user_id, role, content, meta=None):
    history.add_message(user_id, role, content, meta=meta)


def get_history(user_id, limit=10):
    return history.get_history(user_id, limit=limit)


def stats():
    with connect() as con:
        return {
            "documents": con.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "legal_units": con.execute("SELECT COUNT(*) FROM legal_units").fetchone()[0],
            "messages": history.message_count(),
            "history_backend": history.backend_name(),
        }
