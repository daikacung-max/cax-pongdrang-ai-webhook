from collections import deque
from threading import Lock
import time

from config import PENDING_TTL_SECONDS


class PendingZaloMessages:
    """
    Adapter cho Zalo Chatbot Dynamic hiện tại.
    Nếu Dynamic có thể truyền uid qua query/header thì lấy đúng người dùng.
    Nếu không truyền được uid thì fallback FIFO chỉ phù hợp demo/tải thấp.
    """

    def __init__(self):
        self._queue = deque()
        self._lock = Lock()
        self._seen = {}

    def _purge(self):
        now = time.time()
        while self._queue and now - self._queue[0]["time"] > PENDING_TTL_SECONDS:
            self._queue.popleft()
        for msg_id, ts in list(self._seen.items()):
            if now - ts > 180:
                self._seen.pop(msg_id, None)

    def push(self, user_id, text, msg_id=""):
        with self._lock:
            self._purge()
            if msg_id and msg_id in self._seen:
                return False
            if msg_id:
                self._seen[msg_id] = time.time()
            self._queue.append({
                "user_id": str(user_id),
                "text": str(text),
                "msg_id": str(msg_id or ""),
                "time": time.time(),
            })
            while len(self._queue) > 100:
                self._queue.popleft()
            return True

    def pop(self, user_id=None):
        with self._lock:
            self._purge()
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


pending = PendingZaloMessages()
