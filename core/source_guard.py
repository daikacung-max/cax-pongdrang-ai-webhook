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


def _grounded_detail_aliases(source):
    """Return only citizen-friendly aliases backed by an explicit source term.

    The guard deliberately rejects invented administrative details.  It should
    not, however, reject a common spelling of the *same* item where the source
    already names that item in full (for example ``CCCD`` for a thẻ căn cước
    công dân).  Keeping this mapping small and one-way avoids turning it into
    a general-knowledge bypass for the source boundary.
    """
    aliases = set()
    if "the can cuoc cong dan" in source:
        aliases.add("cccd")
    if "dia chi thu dien tu" in source:
        aliases.add("email")
    return aliases


def source_grounding_errors(answer, units):
    """Bắt chi tiết thủ tục do model tự thêm nhưng không có trong source.

    Lớp này cố ý không khóa cách diễn đạt tự nhiên. Nó chỉ fail-closed với các
    dữ kiện hành chính có vẻ hợp lý nhưng dễ bị model tự bịa: giấy tờ, mã thủ
    tục, cách nhận kết quả, kênh nộp, địa chỉ, giờ làm việc và ví dụ tích hợp.
    """
    if not units:
        return []
    raw = str(answer or "")
    a = _norm(raw)
    source = _source_blob(units)
    grounded_aliases = _grounded_detail_aliases(source)
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

    # Những chi tiết dưới đây thường nghe hợp lý nhưng chỉ được phép xuất hiện
    # khi chính source của lượt hiện tại có chúng.
    high_risk_details = (
        "hop dong thue", "giay chung nhan quyen so huu", "ban sao",
        "anh scan", "file scan", "giay to goc", "cmnd", "cccd", "ho chieu",
        "tin nhan", "email", "tu dong lay du lieu", "ma thu tuc",
        "dich vu buu chinh", "buu chinh cong ich",
    )
    for phrase in high_risk_details:
        if phrase in a and phrase not in source and phrase not in grounded_aliases:
            errors.append("unsupported_procedural_detail:" + phrase)

    # Mã thủ tục dạng 1.012575, 1.004194... phải xuất hiện nguyên vẹn trong
    # source, không cho model đoán từ trí nhớ.
    for code in sorted(set(re.findall(r"\b\d+\.\d{4,8}\b", a))):
        if code not in source:
            errors.append("unsupported_procedure_code:" + code)

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
