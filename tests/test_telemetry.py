import io
import logging
import unittest

from core.telemetry import log_zalo_latency


class TelemetryTests(unittest.TestCase):
    def test_latency_log_whitelists_fields(self):
        stream = io.StringIO()
        logger = logging.getLogger("test-latency")
        logger.handlers = [logging.StreamHandler(stream)]
        logger.setLevel(logging.INFO)
        log_zalo_latency(logger, {
            "trace_id": "abc123",
            "pending_wait_ms": 12,
            "history_ms": 3,
            "total_ms": 20,
            "fallback_reason": None,
            "model_used": "openai/gpt-oss-20b",
            "retrieved_unit_count": 2,
            "question": "Tên tôi là dữ liệu không được log",
            "user_id": "sensitive-zalo-id",
        })
        output = stream.getvalue()
        self.assertIn("zalo_ai_latency", output)
        self.assertNotIn("Tên tôi", output)
        self.assertNotIn("sensitive-zalo-id", output)


if __name__ == "__main__":
    unittest.main()
