from collections import deque
from threading import Condition, Lock
import time

from config import PENDING_TTL_SECONDS, ZALO_DIRECT_REPLY_ENABLED


class PendingZaloMessages:
    """
    Hàng đợi tương thích Zalo Chatbot Dynamic, đồng thời giữ bộ nhớ chống lặp
    webhook theo msg_id. Khi Direct Reply hoạt động, push() chỉ claim msg_id và
    không xếp nội dung vào pending queue để tránh phản hồi trùng lần hai.
    """

    def __init__(self):
        self._lock = Lock()
        self._condition = Condition(self._lock)
        self._queue = deque()
        self._seen = {}

    def _purge_locked(self):
        now = time.time()
        while self._queue and now - self._queue[0]["time"] > PENDING_TTL_SECONDS:
            self._queue.popleft()
        for msg_id, ts in list(self._seen.items()):
            if now - ts > 180:
                self._seen.pop(msg_id, None)

    def _claim_locked(self, msg_id=""):
        msg_id = str(msg_id or "").strip()
        if msg_id and msg_id in self._seen:
            return False
        if msg_id:
            self._seen[msg_id] = time.time()
        return True

    def claim(self, msg_id=""):
        """Đánh dấu một webhook đã nhận mà không đưa nội dung vào pending queue."""
        with self._condition:
            self._purge_locked()
            return self._claim_locked(msg_id)

    def push(self, user_id, text, msg_id=""):
        with self._condition:
            self._purge_locked()
            if not self._claim_locked(msg_id):
                return False
            if ZALO_DIRECT_REPLY_ENABLED:
                return True
            self._queue.append({
                "user_id": str(user_id),
                "text": str(text),
                "msg_id": str(msg_id or ""),
                "time": time.time(),
            })
            while len(self._queue) > 100:
                self._queue.popleft()
            self._condition.notify_all()
            return True

    def _take_locked(self, user_id=None):
        self._purge_locked()
        if not self._queue:
            return None
        if user_id:
            user_id = str(user_id)
            for i, item in enumerate(self._queue):
                if item["user_id"] == user_id:
                    del self._queue[i]
                    return item
            return None
        return self._queue.popleft()

    def pop(self, user_id=None, wait_seconds=0.65):
        deadline = time.monotonic() + max(0.0, float(wait_seconds or 0))
        with self._condition:
            while True:
                item = self._take_locked(user_id=user_id)
                if item:
                    return item
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(timeout=remaining)


pending = PendingZaloMessages()
