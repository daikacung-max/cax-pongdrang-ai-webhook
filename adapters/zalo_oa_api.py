"""Fail-closed Zalo OA customer-service client with durable-capable token refresh."""

import threading
import requests


class ZaloOAReplyError(RuntimeError):
    """Fail-closed OA error with a non-sensitive operational category.

    ``reason`` is a fixed code from this module, safe for logs: it never
    contains a token, recipient ID, message body, or provider payload.
    """

    def __init__(self, message, reason="unknown"):
        super().__init__(message)
        self.reason = str(reason or "unknown")[:80]


def _split_text(text, max_chars=1800, max_messages=4):
    """Chia phản hồi dài theo câu/khoảng trắng, không cắt giữa từ khi có thể."""
    text = str(text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts = []
    remaining = text
    while remaining and len(parts) < max_messages:
        if len(remaining) <= max_chars:
            parts.append(remaining.strip())
            break
        window = remaining[:max_chars + 1]
        cut = max(
            window.rfind(". "), window.rfind("? "), window.rfind("! "),
            window.rfind("; "), window.rfind("\n")
        )
        if cut < int(max_chars * 0.55):
            cut = window.rfind(" ")
        if cut < int(max_chars * 0.45):
            cut = max_chars
        piece = remaining[:cut + (1 if remaining[cut:cut + 2] in (". ", "? ", "! ", "; ") else 0)].strip()
        if not piece:
            piece = remaining[:max_chars].strip()
            cut = len(piece)
        parts.append(piece)
        remaining = remaining[max(cut, len(piece)):].strip()

    if remaining:
        tail = remaining[:max_chars].strip()
        if tail:
            if len(parts) >= max_messages:
                parts[-1] = (parts[-1] + " " + tail)[:max_chars].strip()
            else:
                parts.append(tail)
    return parts[:max_messages]


class ZaloOAClient:
    """Gửi tin OA và tự làm mới access token khi có refresh token.

    ``persist_refresh_token`` is optional. Production can inject an encrypted
    durable store so a rotated refresh token survives a process restart; tests
    and local development may keep the default in-memory behaviour.
    """

    endpoint = "https://openapi.zalo.me/v3.0/oa/message/cs"
    token_endpoint = "https://oauth.zaloapp.com/v4/oa/access_token"
    INVALID_ACCESS_TOKEN_ERRORS = {-124, "-124"}

    def __init__(
        self,
        access_token,
        refresh_token="",
        app_id="",
        app_secret="",
        session=requests,
        persist_refresh_token=None,
    ):
        self.access_token = str(access_token or "").strip()
        self.refresh_token = str(refresh_token or "").strip()
        self.app_id = str(app_id or "").strip()
        self.app_secret = str(app_secret or "").strip()
        self.session = session
        self.persist_refresh_token = persist_refresh_token
        self._token_lock = threading.Lock()

    @property
    def refresh_ready(self):
        return bool(self.refresh_token and self.app_id and self.app_secret)

    @property
    def send_ready(self):
        return bool(self.access_token or self.refresh_ready)

    def _refresh_access_token(self, timeout=3.0):
        if not self.refresh_ready:
            raise ZaloOAReplyError(
                "OA access token is not configured and refresh is unavailable",
                "token_refresh_unavailable",
            )
        with self._token_lock:
            response = self.session.post(
                self.token_endpoint,
                headers={
                    "secret_key": self.app_secret,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "refresh_token": self.refresh_token,
                    "app_id": self.app_id,
                    "grant_type": "refresh_token",
                },
                timeout=timeout,
            )
            if response.status_code != 200:
                raise ZaloOAReplyError("OA token refresh request was rejected", "token_refresh_rejected")
            try:
                body = response.json()
            except Exception as exc:
                raise ZaloOAReplyError(
                    "OA token refresh returned invalid JSON", "token_refresh_invalid_json"
                ) from exc
            return self._accept_token_response(body, require_refresh=False)

    def _accept_token_response(self, body, require_refresh):
        """Durably apply an OAuth response without exposing token values."""
        access_token = str((body or {}).get("access_token") or "").strip()
        refresh_token = str((body or {}).get("refresh_token") or "").strip()
        if not access_token:
            raise ZaloOAReplyError(
                "OA token response did not return an access token", "token_response_missing_access"
            )
        if require_refresh and not refresh_token:
            raise ZaloOAReplyError(
                "OA authorization did not return a refresh token", "authorization_missing_refresh"
            )
        if refresh_token and self.persist_refresh_token is not None:
            try:
                persisted = bool(self.persist_refresh_token(refresh_token))
            except Exception as exc:
                raise ZaloOAReplyError(
                    "OA rotated refresh token could not be persisted", "refresh_persistence_failed"
                ) from exc
            if not persisted:
                raise ZaloOAReplyError(
                    "OA rotated refresh token could not be persisted", "refresh_persistence_failed"
                )
        # Treat the OAuth response as one state transition.  If Zalo has
        # rotated the refresh token, it must be durable before either
        # credential becomes active in this process; otherwise a restart
        # could retain only stale credentials.
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        return access_token

    def bootstrap_from_authorization_code(self, code, timeout=5.0):
        """Exchange a one-time OA authorization code for durable OAuth state."""
        code = str(code or "").strip()
        if not code or not self.app_id or not self.app_secret:
            raise ZaloOAReplyError("OA authorization code exchange is not configured", "authorization_unavailable")
        response = self.session.post(
            self.token_endpoint,
            headers={
                "secret_key": self.app_secret,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "code": code,
                "app_id": self.app_id,
                "grant_type": "authorization_code",
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            raise ZaloOAReplyError("OA authorization-code exchange was rejected", "authorization_rejected")
        try:
            body = response.json()
        except Exception as exc:
            raise ZaloOAReplyError(
                "OA authorization-code exchange returned invalid JSON", "authorization_invalid_json"
            ) from exc
        return self._accept_token_response(body, require_refresh=True)

    def _post_message(self, user_id, text, timeout):
        return self.session.post(
            self.endpoint,
            headers={
                "access_token": self.access_token,
                "Content-Type": "application/json",
            },
            json={
                "recipient": {"user_id": str(user_id)},
                "message": {"text": str(text)},
            },
            timeout=timeout,
        )

    @staticmethod
    def _json_body(response):
        try:
            return response.json()
        except Exception as exc:
            raise ZaloOAReplyError("OA reply API returned invalid JSON", "reply_invalid_json") from exc

    def _send_one(self, user_id, text, timeout=2.0):
        if not self.access_token:
            self._refresh_access_token(timeout=max(timeout, 3.0))

        response = self._post_message(user_id, text, timeout)
        if response.status_code in (401, 403) and self.refresh_ready:
            self._refresh_access_token(timeout=max(timeout, 3.0))
            response = self._post_message(user_id, text, timeout)

        if response.status_code != 200:
            raise ZaloOAReplyError("OA reply request was rejected", "reply_rejected")

        body = self._json_body(response)
        if body.get("error") in self.INVALID_ACCESS_TOKEN_ERRORS and self.refresh_ready:
            self._refresh_access_token(timeout=max(timeout, 3.0))
            response = self._post_message(user_id, text, timeout)
            if response.status_code != 200:
                raise ZaloOAReplyError("OA reply retry was rejected", "reply_retry_rejected")
            body = self._json_body(response)

        if body.get("error", 0) not in (0, "0", None):
            raise ZaloOAReplyError("OA reply API returned an error", "reply_api_error")
        return True

    def send_text(self, user_id, text, timeout=2.0):
        if not self.send_ready:
            raise ZaloOAReplyError("OA reply credentials are not configured", "reply_credentials_unavailable")
        chunks = _split_text(text)
        if not chunks:
            raise ZaloOAReplyError("OA reply text is empty", "reply_text_empty")
        for chunk in chunks:
            self._send_one(user_id, chunk, timeout=timeout)
        return True
