"""Tổng hợp p50/p95/max từ các dòng log zalo_ai_latency của Render."""

import argparse
import json
import math
import sys


FIELDS = [
    "pending_wait_ms", "history_ms", "planner_ms", "retrieval_ms",
    "llm_ms", "verify_ms", "finalize_ms", "total_ms",
]


def percentile(values, quantile):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = max(0, math.ceil(quantile * len(ordered)) - 1)
    return round(ordered[rank], 2)


def parse_line(line):
    start = line.find('{"event":"zalo_ai_latency"')
    if start < 0:
        return None
    try:
        payload = json.loads(line[start:])
    except json.JSONDecodeError:
        return None
    return payload if payload.get("event") == "zalo_ai_latency" else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="-", help="File log; bỏ trống để đọc stdin")
    args = parser.parse_args()
    stream = open(args.path, encoding="utf-8") if args.path else sys.stdin
    try:
        rows = [payload for line in stream if (payload := parse_line(line))]
    finally:
        if args.path:
            stream.close()

    stages = {}
    for field in FIELDS:
        values = [float(row.get(field) or 0) for row in rows]
        stages[field] = {
            "p50": percentile(values, 0.50),
            "p95": percentile(values, 0.95),
            "max": round(max(values), 2) if values else 0.0,
        }
    fallbacks = {}
    for row in rows:
        reason = row.get("fallback_reason") or "none"
        fallbacks[reason] = fallbacks.get(reason, 0) + 1
    output = {"sample_count": len(rows), "stages": stages, "fallbacks": fallbacks}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
