"""Encrypted durable storage for rotated Zalo OA refresh tokens.

The token store is intentionally disabled unless both managed Postgres and a
separate Fernet key are configured. SQLite/local files are not used for OA
secrets because Render's filesystem is not a durable secret store.
"""

from datetime import datetime, timezone
import base64
import hashlib
import os

from config import DATABASE_URL
from core.history import _postgres_pool


_NAME = "zalo_oa_refresh_token"


def _key():
    # Read on use so a process receives its configured key at startup without
    # ever writing it to disk or logs. It also makes key validation testable.
    return os.getenv("ZALO_TOKEN_ENCRYPTION_KEY", "").strip()


def _fernet_key():
    """Accept a Fernet key or derive one from a high-entropy Render secret.

    Render's generated secrets are not necessarily Fernet's base64 wire format.
    Deriving a 32-byte Fernet key from a 32+ character secret keeps the secret
    in Render while preserving authenticated encryption at rest.
    """
    key = _key().encode("ascii")
    try:
        from cryptography.fernet import Fernet
        Fernet(key)
        return key
    except Exception:
        if len(key) < 32:
            raise ValueError("ZALO_TOKEN_ENCRYPTION_KEY must be a Fernet key or a 32+ character secret")
        return base64.urlsafe_b64encode(hashlib.sha256(key).digest())


def persistence_ready():
    if not DATABASE_URL or not _key():
        return False
    try:
        from cryptography.fernet import Fernet
        Fernet(_fernet_key())
        return True
    except Exception:
        return False


def _fernet():
    if not persistence_ready():
        raise RuntimeError("Zalo token persistence is not configured")
    from cryptography.fernet import Fernet
    return Fernet(_fernet_key())


def _ensure_schema():
    if not persistence_ready():
        return False
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS integration_secrets (
                    name TEXT PRIMARY KEY,
                    ciphertext TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
            """)
    return True


def operational_ready():
    """Check configuration, encryption and the actual managed-Postgres table."""
    try:
        return bool(_ensure_schema())
    except Exception:
        return False


def load_refresh_token(fallback=""):
    """Return the newest durable token, falling back to the environment seed."""
    fallback = str(fallback or "").strip()
    if not _ensure_schema():
        return fallback
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT ciphertext FROM integration_secrets WHERE name=%s", (_NAME,))
            row = cur.fetchone()
    if not row:
        return fallback
    try:
        return _fernet().decrypt(str(row[0]).encode("ascii")).decode("utf-8").strip() or fallback
    except Exception:
        # Corrupted/wrong-key ciphertext must not leak or crash app startup.
        # The env seed can still recover the integration if it is current.
        return fallback


def refresh_token_available(fallback=""):
    """Report token availability without returning a credential to callers."""
    try:
        return bool(load_refresh_token(fallback))
    except Exception:
        # Health endpoints must fail closed when Postgres or decryption is
        # unavailable, while never exposing the underlying integration secret.
        return False


def save_refresh_token(token):
    token = str(token or "").strip()
    if not token or not _ensure_schema():
        return False
    ciphertext = _fernet().encrypt(token.encode("utf-8")).decode("ascii")
    now = datetime.now(timezone.utc)
    with _postgres_pool().connection() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO integration_secrets(name, ciphertext, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT(name) DO UPDATE SET
                    ciphertext=EXCLUDED.ciphertext,
                    updated_at=EXCLUDED.updated_at
            """, (_NAME, ciphertext, now))
    return True
