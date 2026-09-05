from collections import deque
from threading import Condition, Lock
import time

from config import PENDING_TTL_SECONDS


class PendingZaloMessages:
    """
    Hàng đợi tương thích Zalo Chatbot Dynamic.

    Log thực tế cho thấy GET /zalo/ai đôi khi đến trước POST /zalo/webhook khoảng 40-120ms.
    pop() chờ tối đa 0.28 giây để webhook kịp đưa câu hỏi vào hàng đợi, tránh trả nhầm
    'Anh/chị vui lòng nhập câu hỏi cần hỗ trợ'.

    Nếu Dynamic không truyền user_id thì vẫn phải fallback FIFO. Đây chỉ phù hợp demo/tải thấp.
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

    def push(self, user_id, text, msg_id=""):
        with self._condition:
            self._purge_locked()
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

    def pop(self, user_id=None, wait_seconds=0.28):
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
