"""Semantic audit cho corpus 10.000 câu.

Mục tiêu không khóa câu chữ. Audit chỉ kiểm tra ý nghĩa bắt buộc, nguồn, phạm vi
thẩm quyền và các điều cấm. Câu trả lời của model vẫn được phép diễn đạt tự nhiên.
"""

from collections import Counter, defaultdict

from core.current_fallback import grounded_dynamic_fallback
from core.planner import quick_plan
from core.retrieval import retrieve
from core.verifier import norm, verify_dynamic_text


CURRENT_SOURCE_PREFIX = {
    "vneid_level2": "VNEID_",
    "temporary_residence": "RESIDENCE_CURRENT_2026",
    "permanent_residence": "RESIDENCE_CURRENT_2026",
    "vehicle_first_registration": "VEHICLE_CURRENT_2026",
    "vehicle_transfer": "VEHICLE_TRANSFER_LOCAL_2026",
    "identity_reissue": "CITIZEN_ID_5230_COMMUNE_2026",
    "identity_renewal": "CITIZEN_ID_5230_COMMUNE_2026",
    "identity_under14": "CITIZEN_ID_5230_COMMUNE_2026",
    "assault_article134": "BLHS_2025",
    "fraud_transfer": "FRAUD_TRANSFER_GUIDANCE_2026",
}

# Các mốc này là semantic anchors, không phải nguyên văn bắt buộc.
SEMANTIC_ANCHORS = {
    "vneid_level2": (("cong an xa", "cong an cap xa"), ("muc do 02", "muc 2", "muc do 2")),
    "temporary_residence": (("03 ngay lam viec",), ("cong an cap xa", "cong an xa")),
    "permanent_residence": (("07 ngay lam viec",), ("cong an cap xa", "cong an xa")),
    "vehicle_first_registration": (("02 ngay lam viec",), ("cap xa",), ("cap tinh",)),
    "vehicle_transfer": (("sang ten", "chuyen quyen so huu"), ("cap xa",)),
    "identity_reissue": (("07 ngay lam viec",), ("cong an cap xa", "bo phan mot cua cap xa")),
    "identity_renewal": (("07 ngay lam viec",), ("cong an cap xa", "bo phan mot cua cap xa")),
    "identity_under14": (("duoi 14", "06 tuoi", "6 tuoi"), ("cong an cap xa", "cong an xa")),
    "assault_article134": (("dieu 134",),),
    "fraud_transfer": (("chung tu giao dich", "sao ke", "giao dich"), ("chua the", "can xac minh", "chua du")),
}

FORBIDDEN_GLOBAL = (
    "cong an cap huyen",
    "cuc cong an xa",
    "don cong an xa",
    "nhan vien cong an",
)

UNSUPPORTED_FAIL_CLOSED_MARKERS = (
    "chua co nguon",
    "khong tu doan",
    "chua co nguon da duoc kiem chung",
    "can lam ro",
    "can xac minh",
    "cho biet",
    "noi dung nao",
)


def _has_any(text, alternatives):
    return any(part in text for part in alternatives)


def _active_source_ok(case, units):
    prefix = CURRENT_SOURCE_PREFIX.get(case.category, case.source_prefix)
    return bool(prefix) and any(str(u.get("document_id") or "").startswith(prefix) for u in units)


def audit_case(case):
    plan = quick_plan(case.question)
    units = retrieve(plan, case.question) if plan.get("is_legal") else []
    answer = grounded_dynamic_fallback(case.question, units)
    answer_n = norm(answer)
    source_blob_n = norm(" ".join(str(u.get("text") or "") for u in units))
    errors = []

    for forbidden in FORBIDDEN_GLOBAL:
        if forbidden in answer_n:
            errors.append("forbidden_answer:" + forbidden)
        # Với TTHC hai cấp, ngay cả context đưa cho model cũng phải sạch.
        if case.category in CURRENT_SOURCE_PREFIX and forbidden in source_blob_n:
            errors.append("forbidden_source:" + forbidden)

    check = verify_dynamic_text(answer, units, question=case.question)
    if not check.get("ok"):
        errors.extend("verifier:" + item for item in check.get("errors", []))

    if case.policy == "verified_source":
        if not _active_source_ok(case, units):
            errors.append("wrong_or_missing_source")
        for alternatives in SEMANTIC_ANCHORS.get(case.category, ()):  # AND giữa các nhóm, OR trong nhóm
            normalized_alts = tuple(norm(x) for x in alternatives)
            if not _has_any(answer_n, normalized_alts):
                errors.append("missing_semantic:" + "|".join(alternatives))
        if case.category == "assault_article134" and any(x in answer_n for x in (
            "chac chan khong", "khong cau thanh", "khong bi xu ly hinh su"
        )):
            errors.append("absolute_criminal_exclusion")
        if case.category == "fraud_transfer" and any(x in answer_n for x in (
            "da pham toi", "chac chan la toi lua dao", "dieu 174"
        )) and not any(x in answer_n for x in ("chua the", "can xac minh")):
            errors.append("premature_fraud_label")
    else:
        # Với miền chưa có notebook đủ sâu, pass nghĩa là hệ thống không bịa.
        # Nếu retrieval vô tình có một nguồn nền, verifier vẫn phải pass; nếu
        # không có nguồn thì fallback phải thể hiện giới hạn/đòi dữ kiện thêm.
        if not units and not any(marker in answer_n for marker in UNSUPPORTED_FAIL_CLOSED_MARKERS):
            errors.append("unsupported_not_fail_closed")

    return {
        "case_id": case.case_id,
        "category": case.category,
        "question": case.question,
        "policy": case.policy,
        "passed": not errors,
        "errors": errors,
        "answer": answer,
        "sources": [str(u.get("id") or "") for u in units],
    }


def audit_corpus(cases, failure_limit=100):
    total = 0
    passed = 0
    failures = []
    categories = defaultdict(lambda: {"total": 0, "passed": 0})
    error_counts = Counter()
    for case in cases:
        total += 1
        result = audit_case(case)
        bucket = categories[case.category]
        bucket["total"] += 1
        if result["passed"]:
            passed += 1
            bucket["passed"] += 1
        else:
            for error in result["errors"]:
                error_counts[error] += 1
            if len(failures) < max(1, int(failure_limit)):
                failures.append(result)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "status": "pass" if passed == total else "fail",
        "categories": dict(sorted(categories.items())),
        "error_counts": dict(error_counts.most_common()),
        "failures": failures,
    }
