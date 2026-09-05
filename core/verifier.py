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
    text = text.replace("Cục Công an xã Pơng Drang", "Công an xã Pơng Drang")
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
