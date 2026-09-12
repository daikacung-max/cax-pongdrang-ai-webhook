import time

from flask import Blueprint, jsonify

from config import ENABLE_DEMO_CONSOLE
from core.planner import quick_plan
from core.retrieval import retrieve
from core.current_fallback import grounded_dynamic_fallback


blueprint = Blueprint("ai_core_self_test", __name__)


SELF_TEST_CASES = [
    {
        "name": "Căn cước bị mất",
        "question": "Tôi bị mất căn cước, cấp lại ở đâu?",
        "must_have": ["Công an cấp xã", "07 ngày làm việc"],
        "must_not_have": ["Công an cấp huyện"],
        "source_prefix": "CITIZEN_ID_5230_COMMUNE_2026",
    },
    {
        "name": "Căn cước lần đầu từ đủ 14 tuổi",
        "question": "Tôi 15 tuổi làm căn cước lần đầu ở đâu?",
        "must_have": ["Công an cấp xã", "07 ngày làm việc"],
        "must_not_have": ["Công an cấp huyện"],
        "source_prefix": "CITIZEN_ID_5230_COMMUNE_2026",
    },
    {
        "name": "Đăng ký tạm trú",
        "question": "Tôi muốn đăng ký tạm trú thì làm ở đâu và mất bao lâu?",
        "must_have": ["Công an cấp xã", "03 ngày làm việc"],
        "must_not_have": ["Công an cấp huyện"],
        "source_prefix": "RESIDENCE_CURRENT_2026",
    },
    {
        "name": "Xác nhận thông tin cư trú",
        "question": "Xác nhận thông tin cư trú mất bao lâu?",
        "must_have": ["1/2 ngày làm việc"],
        "must_not_have": ["Công an cấp huyện"],
        "source_prefix": "RESIDENCE_CURRENT_2026",
    },
    {
        "name": "Đăng ký xe máy mới",
        "question": "Tôi đăng ký xe máy mới ở đâu?",
        "must_have": ["cấp tỉnh", "cấp xã", "02 ngày làm việc"],
        "must_not_have": ["Công an cấp huyện"],
        "source_prefix": "VEHICLE_CURRENT_2026",
    },
    {
        "name": "Bị đánh gây thương tích",
        "question": "Tôi bị người khác đánh gây thương tích 5%, người đó dùng dao.",
        "must_have": ["Điều 134"],
        "must_not_have": ["chắc chắn không", "không cấu thành"],
        "source_prefix": "BLHS_2025",
    },
    {
        "name": "Tố giác tội phạm",
        "question": "Tôi muốn tố giác một vụ việc thì làm ở đâu?",
        "must_have": ["Công an cấp xã"],
        "must_not_have": ["Công an cấp huyện"],
        "source_prefix": "CRIME_REPORT_GUIDANCE_2025",
    },
    {
        "name": "Tiếng ồn karaoke",
        "question": "Hàng xóm hát karaoke ồn ào thì xử lý sao?",
        "must_have": ["Nghị định 282/2025/NĐ-CP"],
        "must_not_have": [],
        "source_prefix": "NOISE_KARAOKE_282_2025",
    },
]


def _run_case(case):
    started = time.perf_counter()
    question = case["question"]
    plan = quick_plan(question)
    units = retrieve(plan, question) if plan.get("is_legal") else []
    answer = grounded_dynamic_fallback(question, units) if units else ""
    source_ids = [str(unit.get("id") or "") for unit in units]
    source_ok = any(
        str(unit.get("document_id") or "").startswith(case["source_prefix"])
        for unit in units
    )
    must_have_ok = all(text.casefold() in answer.casefold() for text in case.get("must_have", []))
    must_not_have_ok = all(text.casefold() not in answer.casefold() for text in case.get("must_not_have", []))
    passed = bool(source_ok and must_have_ok and must_not_have_ok)
    return {
        "name": case["name"],
        "question": question,
        "passed": passed,
        "answer": answer,
        "sources": source_ids,
        "checks": {
            "source_ok": source_ok,
            "must_have_ok": must_have_ok,
            "must_not_have_ok": must_not_have_ok,
        },
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


@blueprint.route("/demo/api/self-test", methods=["POST"])
def self_test():
    if not ENABLE_DEMO_CONSOLE:
        return jsonify({"error": "Not found"}), 404
    started = time.perf_counter()
    results = [_run_case(case) for case in SELF_TEST_CASES]
    passed = sum(1 for item in results if item["passed"])
    return jsonify({
        "status": "pass" if passed == len(results) else "fail",
        "passed": passed,
        "total": len(results),
        "failed": len(results) - passed,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "results": results,
        "note": "Tự test chạy cục bộ trên planner/retrieval/fallback; không gửi Zalo và không tạo hồ sơ thật.",
    }), 200
