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
        "hoac duoi", "nhung thuoc", "tru truong hop",
        "thuoc mot trong cac truong hop", "cac truong hop sau day", "ngoai tru",
    ]
    return any(marker in q for marker in markers)


def _is_overbroad_negative(text):
    q = norm(text)
    markers = [
        "khong thuoc pham vi", "khong cau thanh", "chac chan khong",
        "khong bi xu ly hinh su", "khong the bi xu ly hinh su",
        "chi khi", "chi tu", "tu 11% tro len moi",
    ]
    return any(marker in q for marker in markers)


def _acknowledges_exception(text):
    q = norm(text)
    markers = [
        "van co the", "neu thuoc", "neu khong thuoc", "tru truong hop",
        "ngoai le", "chua the ket luan", "con phu thuoc", "tuy thuoc",
        "duoi 11% nhung", "hoac duoi 11%",
    ]
    return any(marker in q for marker in markers)


def _has_residence_source(retrieved_units):
    return any(
        str(x.get("document_id") or "").startswith(("RESIDENCE_", "TTHC_TEMP_RESIDENCE_"))
        for x in retrieved_units
    )


def _unsafe_residence_requirements(answer):
    """Các cụm từng bị model tự bịa thành thành phần hồ sơ/đầu mối giải quyết."""
    q = norm(answer)
    risky = [
        "so ho khau",
        "ban sao cmnd",
        "ban sao cccd",
        "giay khai sinh",
        "thu moi",
        "giay phep su dung nha",
        "giay chung minh quan he",
        "phong dang ky dan cu",
        "cap giay tam tru",
    ]
    return [x for x in risky if x in q]


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
        if claimed_article is not None and str(claimed_article) != str(unit.get("article") or ""):
            errors.append(
                f"Điều {claimed_article} không khớp source {unit_id} (source là Điều {unit.get('article')})."
            )
            continue

        official_title = claim.get("official_title")
        if official_title and norm(official_title) != norm(unit.get("title") or ""):
            errors.append(
                f"Tên Điều/tội danh '{official_title}' không khớp tiêu đề nguồn '{unit.get('title')}'."
            )
            continue

        evidence_quote = str(claim.get("evidence_quote") or "").strip()
        if not evidence_quote:
            errors.append(f"Claim '{claim.get('claim','')}' không có evidence_quote nguyên văn.")
            continue

        source_text = str(unit.get("text") or "")
        if norm(evidence_quote) not in norm(source_text):
            errors.append(f"evidence_quote của claim không tồn tại nguyên văn trong source {unit_id}.")
            continue

        claim_numbers = _numbers(claim.get("claim", ""))
        evidence_numbers = _numbers(evidence_quote)
        if claim_numbers and not claim_numbers.issubset(evidence_numbers):
            missing = sorted(claim_numbers - evidence_numbers)
            errors.append("Claim nêu số liệu/ngưỡng không có trong evidence_quote: " + ", ".join(missing))
            continue

        claim_text = str(claim.get("claim") or "")
        if (
            _is_overbroad_negative(claim_text)
            and _has_exception_structure(source_text)
            and not _acknowledges_exception(claim_text)
        ):
            errors.append("Claim kết luận loại trừ quá rộng trong khi nguồn có nhánh/ngoại lệ liên quan.")
            continue

        verified_claims.append(claim)

    allowed_articles = {
        str(unit.get("article")) for unit in retrieved_units if unit.get("article")
    }
    cited_articles = set(
        re.findall(r"(?i)\bĐiều\s+(\d+[a-z]?)\b", draft.get("answer", ""))
    )
    unsupported = sorted(article for article in cited_articles if article not in allowed_articles)
    if unsupported:
        errors.append("Câu trả lời nêu Điều không có trong nguồn truy xuất: " + ", ".join(unsupported))

    answer_text = str(draft.get("answer") or "")
    source_blob = "\n".join(str(x.get("text") or "") for x in retrieved_units)
    if (
        _is_overbroad_negative(answer_text)
        and _has_exception_structure(source_blob)
        and not _acknowledges_exception(answer_text)
    ):
        errors.append("Câu trả lời có kết luận loại trừ tuyệt đối nhưng nguồn có ngoại lệ/nhánh thay thế.")

    if _has_residence_source(retrieved_units):
        risky = _unsafe_residence_requirements(answer_text)
        if risky:
            errors.append("Câu trả lời tự thêm thành phần/đầu mối cư trú không được nguồn hiện hành hỗ trợ: " + ", ".join(risky))

    return {
        "ok": not errors,
        "errors": errors,
        "verified_claims": verified_claims,
        "allowed_articles": sorted(allowed_articles),
    }


def verify_dynamic_text(answer, retrieved_units):
    """Verifier nhẹ cho Zalo Dynamic, không cần gọi model lần hai."""
    answer = str(answer or "")
    allowed_articles = {
        str(unit.get("article")) for unit in retrieved_units if unit.get("article")
    }
    cited_articles = set(re.findall(r"(?i)\bĐiều\s+(\d+[a-z]?)\b", answer))
    unsupported = sorted(x for x in cited_articles if x not in allowed_articles)

    source_blob = "\n".join(str(x.get("text") or "") for x in retrieved_units)
    errors = []
    if unsupported:
        errors.append("unsupported_articles:" + ",".join(unsupported))
    if (
        _is_overbroad_negative(answer)
        and _has_exception_structure(source_blob)
        and not _acknowledges_exception(answer)
    ):
        errors.append("overbroad_negative")

    if _has_residence_source(retrieved_units):
        risky = _unsafe_residence_requirements(answer)
        if risky:
            errors.append("unsupported_residence_requirements:" + ",".join(risky))

    return {"ok": not errors, "errors": errors}


def grounded_dynamic_fallback(question, retrieved_units):
    """Fail-safe có nguồn, dùng khi model Dynamic timeout hoặc bị verifier từ chối."""
    if not retrieved_units:
        return (
            "Kho dữ liệu hiện chưa có nguồn đã kiểm chứng đủ gần để tôi khẳng định chi tiết pháp lý của nội dung này. "
            "Tôi sẽ không tự đoán giấy tờ, điều luật, mức phạt hoặc thẩm quyền khi chưa có nguồn phù hợp."
        )

    q = norm(question)

    # Fallback cư trú hiện hành: dựng hoàn toàn từ snapshot chính thức đã nạp.
    if _has_residence_source(retrieved_units) and "tam tru" in q:
        return (
            "Hiện nay thủ tục đăng ký tạm trú được thực hiện tại Công an cấp xã hoặc trực tuyến; thời hạn giải quyết là 03 ngày làm việc. "
            "Theo quy định cư trú áp dụng từ 01/07/2026, khi nộp trực tiếp, công dân cung cấp thông tin cơ bản và thông tin về điều kiện đăng ký; "
            "cán bộ tiếp nhận chủ động khai thác dữ liệu để tạo lập hồ sơ. Những thông tin, giấy tờ đã có trong cơ sở dữ liệu hoặc VNeID không được yêu cầu nộp lại; "
            "nếu chưa khai thác được dữ liệu thì có thể cần xuất trình giấy tờ gốc để đối chiếu khi thực sự cần thiết."
        )

    top = retrieved_units[0]
    article = str(top.get("article") or "").strip()
    title = str(top.get("title") or "").strip()

    if article == "134":
        if ("5%" in q or "%" in q or "duoi 11" in q or "dao" in q or "hung khi" in q):
            text = (
                "Chưa thể kết luận rằng tỷ lệ thương tích dưới 11% thì không thuộc Điều 134 Bộ luật Hình sự. "
                "Khoản 1 Điều 134 còn quy định trường hợp dưới 11% nhưng thuộc một trong các tình tiết luật định vẫn có thể bị xem xét."
            )
            if "dao" in q or "hung khi" in q:
                text += (
                    " Việc người kia dùng dao là dữ kiện quan trọng; cần làm rõ đặc điểm của con dao, cách sử dụng và "
                    "việc nó có thuộc trường hợp vũ khí hoặc hung khí nguy hiểm theo tình tiết vụ việc hay không."
                )
            text += " Việc xử lý cụ thể còn phụ thuộc kết quả xác minh và các chứng cứ liên quan."
            return text

    if article and title:
        return (
            f"Nội dung anh/chị hỏi có liên quan đến Điều {article} Bộ luật Hình sự, {title}. "
            "Tuy nhiên, cần đối chiếu đầy đủ các điều kiện và tình tiết trong điều luật với diễn biến thực tế trước khi kết luận."
        )

    return (
        "Nguồn đã được tìm thấy nhưng dữ kiện hiện có chưa đủ để kết luận chi tiết. "
        "Tôi sẽ chỉ sử dụng thông tin có trong nguồn đã kiểm chứng và có thể phân tích tiếp khi anh/chị bổ sung tình huống cụ thể."
    )


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
