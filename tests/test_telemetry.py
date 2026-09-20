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
            "provider_error": "http_429",
            "question": "Tên tôi là dữ liệu không được log",
            "user_id": "sensitive-zalo-id",
        })
        output = stream.getvalue()
        self.assertIn("zalo_ai_latency", output)
        self.assertNotIn("Tên tôi", output)
        self.assertNotIn("sensitive-zalo-id", output)
        self.assertIn('\"provider_error\":\"http_429\"', output)

    def test_latency_log_rejects_untrusted_provider_error_text(self):
        stream = io.StringIO()
        logger = logging.getLogger("test-latency-provider-error")
        logger.handlers = [logging.StreamHandler(stream)]
        logger.setLevel(logging.INFO)
        log_zalo_latency(logger, {"provider_error": "HTTP 401: prompt=private"})
        self.assertIn('\"provider_error\":null', stream.getvalue())


if __name__ == "__main__":
    unittest.main()
