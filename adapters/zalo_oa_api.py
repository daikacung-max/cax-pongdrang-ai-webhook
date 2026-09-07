"""Minimal, fail-closed client for Zalo OA customer-service replies."""

import requests


class ZaloOAReplyError(RuntimeError):
    pass


class ZaloOAClient:
    """Sends text only; caller owns token storage and retry policy."""

    endpoint = "https://openapi.zalo.me/v3.0/oa/message/cs"

    def __init__(self, access_token, session=requests):
        self.access_token = str(access_token or "").strip()
        self.session = session

    def send_text(self, user_id, text, timeout=2.0):
        if not self.access_token:
            raise ZaloOAReplyError("OA access token is not configured")
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
        body = response.json()
        if body.get("error", 0) not in (0, "0", None):
            raise ZaloOAReplyError("OA reply API returned an error")
        return True

