import re
import unicodedata

from config import UNIT_NAME, HOTLINE


def norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _numbers(text):
    return set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", str(text or "")))


def _has_exception_structure(text):
    q = norm(text)
    markers = [
        "hoac duoi",
        "nhung thuoc",
        "tru truong hop",
        "thuoc mot trong cac truong hop",
        "cac truong hop sau day",
        "ngoai tru",
    ]
    return any(marker in q for marker in markers)


def _is_overbroad_negative(text):
    q = norm(text)
    markers = [
        "khong thuoc pham vi",
        "khong cau thanh",
        "chac chan khong",
        "khong bi xu ly hinh su",
        "khong the bi xu ly hinh su",
        "chi khi",
        "chi tu",
    ]
    return any(marker in q for marker in markers)


def _acknowledges_exception(text):
    q = norm(text)
    markers = [
        "van co the",
        "neu thuoc",
        "neu khong thuoc",
        "tru truong hop",
        "ngoai le",
        "chua the ket luan",
        "con phu thuoc",
        "tuy thuoc",
    ]
    return any(marker in q for marker in markers)


def verify(draft, retrieved_units):
    by_id = {unit["id"]: unit for unit in retrieved_units}
    errors = []
    verified_claims = []

    for claim in draft.get("legal_claims", []):
        unit_id = claim.get("source_unit_id")
        unit = by_id.get(unit_id)
        if not unit:
            errors.append(f"legal_claim dùng source_unit_id không có trong nguồn: {unit_id}")
            continue

        claimed_article = claim.get("article")
        if claimed_article is not None:
            if str(claimed_article) != str(unit.get("article") or ""):
                errors.append(
                    f"Điều {claimed_article} không khớp source {unit_id} "
                    f"(source là Điều {unit.get('article')})."
                )
                continue

        official_title = claim.get("official_title")
        if official_title and norm(official_title) != norm(unit.get("title") or ""):
            errors.append(
                f"Tên Điều/tội danh '{official_title}' không khớp "
                f"tiêu đề nguồn '{unit.get('title')}'."
            )
            continue

        evidence_quote = str(claim.get("evidence_quote") or "").strip()
        if not evidence_quote:
            errors.append(
                f"Claim '{claim.get('claim','')}' không có evidence_quote nguyên văn."
            )
            continue

        source_text = str(unit.get("text") or "")
        if norm(evidence_quote) not in norm(source_text):
            errors.append(
                f"evidence_quote của claim không tồn tại nguyên văn trong source {unit_id}."
            )
            continue

        # Nếu claim nêu con số/ngưỡng, con số đó phải xuất hiện trong chính đoạn chứng cứ.
        claim_numbers = _numbers(claim.get("claim", ""))
        evidence_numbers = _numbers(evidence_quote)
        if claim_numbers and not claim_numbers.issubset(evidence_numbers):
            missing = sorted(claim_numbers - evidence_numbers)
            errors.append(
                "Claim nêu số liệu/ngưỡng không có trong evidence_quote: "
                + ", ".join(missing)
            )
            continue

        # Hàng rào chống rút gọn sai quy tắc có ngoại lệ/nhánh thay thế.
        # Ví dụ nguồn có cấu trúc '... hoặc dưới ngưỡng nhưng thuộc trường hợp ...'
        # thì không được kết luận tuyệt đối chỉ dựa vào ngưỡng chính.
        claim_text = str(claim.get("claim") or "")
        if (
            _is_overbroad_negative(claim_text)
            and _has_exception_structure(source_text)
            and not _acknowledges_exception(claim_text)
        ):
            errors.append(
                "Claim kết luận loại trừ quá rộng trong khi nguồn có nhánh/ngoại lệ liên quan; "
                "phải nêu điều kiện/ngoại lệ hoặc dùng cách diễn đạt 'chưa thể kết luận'."
            )
            continue

        verified_claims.append(claim)

    allowed_articles = {
        str(unit.get("article"))
        for unit in retrieved_units
        if unit.get("article")
    }
    cited_articles = set(
        re.findall(r"(?i)\bĐiều\s+(\d+[a-z]?)\b", draft.get("answer", ""))
    )
    unsupported = sorted(
        article for article in cited_articles if article not in allowed_articles
    )
    if unsupported:
        errors.append(
            "Câu trả lời nêu Điều không có trong nguồn truy xuất: "
            + ", ".join(unsupported)
        )

    # Kiểm tra cả câu trả lời cuối: nếu đang kết luận tuyệt đối nhưng nguồn truy xuất
    # có cấu trúc ngoại lệ và câu trả lời không hề nhắc điều kiện/ngoại lệ, từ chối.
    answer_text = str(draft.get("answer") or "")
    source_blob = "\n".join(str(x.get("text") or "") for x in retrieved_units)
    if (
        _is_overbroad_negative(answer_text)
        and _has_exception_structure(source_blob)
        and not _acknowledges_exception(answer_text)
    ):
        errors.append(
            "Câu trả lời có kết luận loại trừ tuyệt đối nhưng nguồn có ngoại lệ/nhánh thay thế; "
            "cần sửa lại để phản ánh đầy đủ quy định."
        )

    return {
        "ok": not errors,
        "errors": errors,
        "verified_claims": verified_claims,
        "allowed_articles": sorted(allowed_articles),
    }


def enforce_phone_policy(text):
    text = str(text or "")
    phone_re = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)")

    def repl(match):
        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("84"):
            digits = "0" + digits[2:]
        if digits == HOTLINE:
            return HOTLINE
        return HOTLINE

    text = phone_re.sub(repl, text)
    text = re.sub(
        r"(?i)((?:gọi|liên hệ|điện thoại|hotline|số)\s*[:\-]?\s*)(113|114|115)\b",
        lambda m: m.group(1) + HOTLINE,
        text,
    )
    return text


def clean_plain_text(text):
    text = str(text or "").strip()
    for mark in ("```", "**", "__", "`", "*"):
        text = text.replace(mark, "")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)

    # Chuẩn hóa cách gọi đơn vị/cán bộ trước khi phát ra Zalo.
    text = re.sub(
        r"(?i)đồn\s+công\s+an\s+xã\s+pơng\s+drang(?:,?\s*tỉnh\s+đắk\s+lắk)?",
        UNIT_NAME,
        text,
    )
    text = re.sub(
        r"(?i)cục\s+công\s+an\s+xã\s+pơng\s+drang(?:,?\s*tỉnh\s+đắk\s+lắk)?",
        UNIT_NAME,
        text,
    )
    text = re.sub(r"(?i)nhân\s+viên\s+công\s+an", "cán bộ Công an", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def finalize(text, contact_recommended=False):
    text = clean_plain_text(text)
    text = enforce_phone_policy(text)
    if contact_recommended and HOTLINE not in text:
        text += f" Người dân có thể liên hệ trực ban {UNIT_NAME} qua số {HOTLINE}."
    return clean_plain_text(text)


def repair_note(verification):
    return "\n".join("- " + error for error in verification.get("errors", []))
