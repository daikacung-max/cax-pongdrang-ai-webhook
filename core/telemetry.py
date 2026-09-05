import json
import time
import uuid
from contextlib import contextmanager


STAGE_FIELDS = (
    "pending_wait_ms",
    "history_ms",
    "planner_ms",
    "retrieval_ms",
    "llm_ms",
    "verify_ms",
    "finalize_ms",
)

FALLBACK_REASONS = {
    "pending_missing",
    "no_source",
    "llm_timeout",
    "llm_error",
    "verification_failed",
    "weak_answer",
}


def new_trace_id():
    return uuid.uuid4().hex


class StageTimer:
    def __init__(self, trace_id=None):
        self.trace_id = trace_id or new_trace_id()
        self.started = time.perf_counter()
        self.values = {field: 0 for field in STAGE_FIELDS}

    @contextmanager
    def stage(self, field):
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            self.values[field] = round(self.values.get(field, 0) + elapsed, 2)

    def finish(self, **extra):
        result = {
            "trace_id": self.trace_id,
            **self.values,
            "total_ms": round((time.perf_counter() - self.started) * 1000, 2),
            "fallback_reason": None,
            "model_used": None,
            "retrieved_unit_count": 0,
        }
        result.update(extra)
        reason = result.get("fallback_reason")
        if reason is not None and reason not in FALLBACK_REASONS:
            result["fallback_reason"] = "llm_error"
        return result


def log_zalo_latency(logger, payload):
    safe = {
        "event": "zalo_ai_latency",
        "trace_id": str(payload.get("trace_id") or "")[:32],
    }
    for field in STAGE_FIELDS:
        safe[field] = float(payload.get(field) or 0)
    safe.update({
        "total_ms": float(payload.get("total_ms") or 0),
        "fallback_reason": payload.get("fallback_reason"),
        "model_used": str(payload.get("model_used") or "")[:80],
        "retrieved_unit_count": int(payload.get("retrieved_unit_count") or 0),
    })
    logger.info(json.dumps(safe, ensure_ascii=False, separators=(",", ":")))
