import re
import unicodedata


def _norm(text):
    value = unicodedata.normalize("NFD", str(text or "").lower())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", value.replace("đ", "d")).strip()


def _source_blob(units):
    return _norm("\n".join(
        "\n".join(str(unit.get(key) or "") for key in (
            "document_title", "document_number", "document_issuer",
            "article", "title", "text",
        ))
        for unit in (units or [])
    ))


def source_grounding_errors(answer, units):
    """Bắt chi tiết thủ tục do model tự thêm nhưng không có trong source.

    Đây là lớp hậu kiểm bổ sung cho verifier. Nó không khóa cách diễn đạt tự
    nhiên, chỉ chặn các loại chi tiết có rủi ro cao như địa chỉ, giờ làm việc,
    ví dụ tích hợp và mã source nội bộ.
    """
    if not units:
        return []
    raw = str(answer or "")
    a = _norm(raw)
    source = _source_blob(units)
    errors = []

    # Không để ID nội bộ kiểu VNEID_2026:level2 lộ vào câu trả lời người dân.
    if re.search(r"\b[A-Z][A-Z0-9_]{3,}:\w+", raw):
        errors.append("internal_source_id_exposed")

    # Địa chỉ vật lý cụ thể chỉ được nói khi source thực sự có địa chỉ đó.
    physical_address_patterns = (
        r"dia chi\s*:\s*(?:so|số|\d)",
        r"so\s+(?:xx|\d+)\s*[,/-].*(?:pong drang|dak lak)",
    )
    if any(re.search(pattern, a) for pattern in physical_address_patterns):
        errors.append("unsupported_physical_address")

    # Thời gian tiếp nhận/địa điểm vận hành không được suy ra từ thói quen hành chính.
    for phrase in ("gio hanh chinh", "co san tai quay", "co san tai noi tiep nhan"):
        if phrase in a and phrase not in source:
            errors.append("unsupported_procedural_detail:" + phrase)

    # Ví dụ loại dữ liệu tích hợp chỉ được nêu khi nguồn đã liệt kê chính ví dụ đó.
    for phrase in ("tai khoan ngan hang", "ma so thue", "ho so y te", "bao hiem y te", "giay phep lai xe"):
        if phrase in a and phrase not in source:
            errors.append("unsupported_integration_example:" + phrase)

    return errors


def merge_verification(result, answer, units):
    merged = dict(result or {})
    errors = list(merged.get("errors") or [])
    for error in source_grounding_errors(answer, units):
        if error not in errors:
            errors.append(error)
    merged["errors"] = errors
    merged["ok"] = not errors
    return merged
