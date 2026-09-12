"""Minimal, fail-closed client for Zalo OA customer-service replies."""

import re
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
        cut = max(window.rfind(". "), window.rfind("? "), window.rfind("! "), window.rfind("; "), window.rfind("\n"))
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
    """Gửi text qua OA API; caller quản lý token và retry policy."""

    endpoint = "https://openapi.zalo.me/v3.0/oa/message/cs"

    def __init__(self, access_token, session=requests):
        self.access_token = str(access_token or "").strip()
        self.session = session

    def _send_one(self, user_id, text, timeout=2.0):
        response = self.session.post(
            self.endpoint,
            params={"access_token": self.access_token},
            json={
                "recipient": {"user_id": str(user_id)},
                "message": {"text": str(text)},
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            raise ZaloOAReplyError("OA reply request was rejected")
        try:
            body = response.json()
        except Exception as exc:
            raise ZaloOAReplyError("OA reply API returned invalid JSON") from exc
        if body.get("error", 0) not in (0, "0", None):
            raise ZaloOAReplyError("OA reply API returned an error")
        return True

    def send_text(self, user_id, text, timeout=2.0):
        if not self.access_token:
            raise ZaloOAReplyError("OA access token is not configured")
        chunks = _split_text(text)
        if not chunks:
            raise ZaloOAReplyError("OA reply text is empty")
        for chunk in chunks:
            self._send_one(user_id, chunk, timeout=timeout)
        return True
