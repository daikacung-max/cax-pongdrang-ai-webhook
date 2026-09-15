"""Fail-closed Zalo OA customer-service client with durable-capable token refresh."""

import threading
import requests


class ZaloOAReplyError(RuntimeError):
    pass


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
            raise ZaloOAReplyError("OA access token is not configured and refresh is unavailable")
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
                raise ZaloOAReplyError("OA token refresh request was rejected")
            try:
                body = response.json()
            except Exception as exc:
                raise ZaloOAReplyError("OA token refresh returned invalid JSON") from exc
            access_token = str(body.get("access_token") or "").strip()
            if not access_token:
                raise ZaloOAReplyError("OA token refresh did not return an access token")
            self.access_token = access_token
            rotated_refresh = str(body.get("refresh_token") or "").strip()
            if rotated_refresh:
                if self.persist_refresh_token is not None:
                    try:
                        persisted = bool(self.persist_refresh_token(rotated_refresh))
                    except Exception as exc:
                        # Once Zalo has rotated the token, silently losing the new
                        # value can strand production after restart. Fail closed.
                        raise ZaloOAReplyError("OA rotated refresh token could not be persisted") from exc
                    if not persisted:
                        raise ZaloOAReplyError("OA rotated refresh token could not be persisted")
                self.refresh_token = rotated_refresh
            return self.access_token

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
            raise ZaloOAReplyError("OA reply API returned invalid JSON") from exc

    def _send_one(self, user_id, text, timeout=2.0):
        if not self.access_token:
            self._refresh_access_token(timeout=max(timeout, 3.0))

        response = self._post_message(user_id, text, timeout)
        if response.status_code in (401, 403) and self.refresh_ready:
            self._refresh_access_token(timeout=max(timeout, 3.0))
            response = self._post_message(user_id, text, timeout)

        if response.status_code != 200:
            raise ZaloOAReplyError("OA reply request was rejected")

        body = self._json_body(response)
        if body.get("error") in self.INVALID_ACCESS_TOKEN_ERRORS and self.refresh_ready:
            self._refresh_access_token(timeout=max(timeout, 3.0))
            response = self._post_message(user_id, text, timeout)
            if response.status_code != 200:
                raise ZaloOAReplyError("OA reply retry was rejected")
            body = self._json_body(response)

        if body.get("error", 0) not in (0, "0", None):
            raise ZaloOAReplyError("OA reply API returned an error")
        return True

    def send_text(self, user_id, text, timeout=2.0):
        if not self.send_ready:
            raise ZaloOAReplyError("OA reply credentials are not configured")
        chunks = _split_text(text)
        if not chunks:
            raise ZaloOAReplyError("OA reply text is empty")
        for chunk in chunks:
            self._send_one(user_id, chunk, timeout=timeout)
        return True
