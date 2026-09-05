from pathlib import Path
import json
import re
import unicodedata

BASE_DIR = Path(__file__).resolve().parent
KB = json.loads((BASE_DIR / "knowledge_base.json").read_text(encoding="utf-8"))

UNIT = KB["unit"]["name"]
HOTLINE = KB["unit"]["hotline"]
CARDS = KB.get("cards", [])
SOURCES = {x["id"]: x for x in KB.get("sources", []) if x.get("id")}
EXACT = KB.get("exact_articles", {})

BLHS_INDEX_FILE = BASE_DIR / "source_index" / "Bộ luật Hình sự năm 2025 - chỉ mục điều luật.json"
BLHS_INDEX = json.loads(BLHS_INDEX_FILE.read_text(encoding="utf-8"))
BLHS_ARTICLES = {
    str(item["article"]): item
    for item in BLHS_INDEX.get("articles", [])
    if item.get("article")
}


def norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_plain_text(text):
    text = str(text or "").strip()
    for mark in ("```", "**", "__", "`", "*"):
        text = text.replace(mark, "")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = text.replace("Cục Công an xã Pơng Drang", "Công an xã Pơng Drang")
    text = text.replace("Cục Công an xã", "Công an xã")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


LEGAL_HINTS = [
    "phap luat", "bo luat", "luat ", "dieu ", "nghi dinh", "thong tu",
    "xu phat", "toi pham", "khoi to", "to giac", "tin bao", "tam tru",
    "thuong tru", "dang ky xe", "can cuoc", "vneid", "ma tuy",
    "cong an", "thu tuc", "tham quyen", "thuong tich", "bi danh",
    "bi lua", "trom", "gây rối", "gay roi"
]


def is_legal_question(question):
    q = norm(question)
    return any(x in q for x in LEGAL_HINTS)


def detect_explicit_law(question):
    q = norm(question)

    if any(x in q for x in [
        "bo luat to tung hinh su", "bltths", "to tung hinh su"
    ]):
        return "BLTTHS"

    if any(x in q for x in [
        "luat xu ly vi pham hanh chinh", "xlvphc", "xu ly vi pham hanh chinh"
    ]):
        return "XLVPHC"

    if any(x in q for x in [
        "bo luat hinh su", "blhs"
    ]):
        return "BLHS"

    if "hinh su" in q and "to tung hinh su" not in q:
        return "BLHS"

    return None


# Map này CHỈ dùng để truy xuất nguồn, không phải câu trả lời mẫu.
CRIMINAL_RETRIEVAL_HINTS = [
    (["bi danh", "danh nguoi", "gay thuong tich", "thuong tich", "hung khi"], "134"),
    (["de doa giet", "doa giet", "giet nguoi"], "133"),
    (["trom", "trom cap", "lay trom"], "173"),
    (["lua dao", "gian doi chiem doat"], "174"),
    (["lam dung tin nhiem", "vay khong tra", "muon khong tra"], "175"),
    (["huy hoai", "dap pha", "lam hu hong tai san"], "178"),
    (["gay roi trat tu cong cong", "gay roi"], "318"),
    (["su dung trai phep chat ma tuy", "test ma tuy", "duong tinh ma tuy"], "256a"),
]


def _article_raw(article_no):
    item = BLHS_ARTICLES.get(str(article_no))
    if not item:
        return None
    return {
        "law": "BLHS",
        "article": str(article_no),
        "title": item.get("title", ""),
        "raw_text": item.get("raw_text", ""),
    }


def retrieve_blhs(question, top_k=2):
    """
    Truy xuất Bộ luật Hình sự từ toàn văn PDF.
    Có số Điều cụ thể -> chỉ lấy đúng Điều đó.
    Không có số Điều -> dùng cụm tình huống + tiêu đề Điều để tìm.
    """
    q = norm(question)
    explicit_law = detect_explicit_law(question)
    explicit_article = re.search(r"\bdieu\s+(\d+[a-z]?)\b", q)

    if explicit_article and explicit_law in (None, "BLHS"):
        item = _article_raw(explicit_article.group(1))
        return [item] if item else []

    # Nếu đã nêu rõ luật khác, không được lôi BLHS vào.
    if explicit_law in ("BLTTHS", "XLVPHC"):
        return []

    # Ưu tiên map truy xuất tình huống.
    hinted = []
    for phrases, art in CRIMINAL_RETRIEVAL_HINTS:
        if any(p in q for p in phrases):
            item = _article_raw(art)
            if item and art not in [x["article"] for x in hinted]:
                hinted.append(item)

    if hinted:
        return hinted[:top_k]

    # Tìm theo tên Điều.
    q_tokens = {w for w in q.split() if len(w) >= 3}
    ranked = []

    for art, item in BLHS_ARTICLES.items():
        title_n = norm(item.get("title", ""))
        title_tokens = set(title_n.split())
        score = len(q_tokens & title_tokens) * 8.0

        if score > 0:
            ranked.append((score, item))

    ranked.sort(key=lambda x: x[0], reverse=True)

    result = []
    for _, item in ranked[:top_k]:
        result.append({
            "law": "BLHS",
            "article": str(item.get("article")),
            "title": item.get("title", ""),
            "raw_text": item.get("raw_text", ""),
        })
    return result


def _card_score(question, card):
    q = norm(question)
    q_tokens = set(q.split())
    score = 0.0

    for kw in card.get("keywords", []):
        kn = norm(kw)
        if kn and kn in q:
            score += 10.0
        kt = set(kn.split())
        score += len(q_tokens & kt) * 1.5

    return score


def retrieve_cards(question, top_k=2):
    ranked = [(_card_score(question, card), card) for card in CARDS]
    ranked = [(s, c) for s, c in ranked if s >= 5]
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in ranked[:top_k]]


def retrieve_legal_context(question):
    """
    Trả:
    - context: dữ liệu pháp lý để AI tham khảo.
    - allowed_blhs_articles: Điều BLHS AI được phép nêu số.
    - exact_source_present: có nguồn đủ rõ hay chưa.
    """
    explicit_law = detect_explicit_law(question)
    q = norm(question)

    blhs_items = retrieve_blhs(question, top_k=2)
    cards = retrieve_cards(question, top_k=2)

    blocks = []
    allowed = set()

    for item in blhs_items:
        art = item["article"]
        allowed.add(art)
        raw = item.get("raw_text", "")
        # Đủ nguyên Điều nhưng tránh request quá lớn.
        if len(raw) > 11000:
            raw = raw[:11000]
        blocks.append(
            f"[NGUỒN BLHS - Điều {art}: {item.get('title','')}]\n{raw}"
        )

    for card in cards:
        facts = "\n".join("- " + x for x in card.get("facts", []))
        source_labels = []
        for sid in card.get("sources", []):
            s = SOURCES.get(sid)
            if s:
                source_labels.append(
                    (str(s.get("number", "")) + " " + str(s.get("name", ""))).strip()
                )
        blocks.append(
            f"[THÔNG TIN ĐÃ KIỂM TRA - {card.get('id','')}]\n"
            f"{facts}\n"
            f"Nguồn: {'; '.join(source_labels)}"
        )

    # Một số Điều BLTTHS đã khóa trong KB.
    explicit_article = re.search(r"\bdieu\s+(\d+[a-z]?)\b", q)
    if explicit_article and explicit_law == "BLTTHS":
        art = explicit_article.group(1)
        item = (EXACT.get("BLTTHS") or {}).get(art)
        if item:
            blocks.append(
                f"[NGUỒN BLTTHS - Điều {art}: {item.get('title','')}]\n"
                f"{item.get('summary','')}"
            )

    return {
        "context": "\n\n".join(blocks),
        "allowed_blhs_articles": sorted(allowed),
        "exact_source_present": bool(blocks),
        "top_blhs_article": blhs_items[0]["article"] if blhs_items else None,
        "top_blhs_title": blhs_items[0]["title"] if blhs_items else None,
    }


def exact_article_direct_answer(question):
    """
    Câu hỏi chỉ hỏi tên/nội dung Điều BLHS: trả tên Điều trực tiếp từ PDF.
    Đây không phải câu trả lời mẫu, mà là lookup văn bản gốc.
    """
    q = norm(question)
    m = re.search(r"\bdieu\s+(\d+[a-z]?)\b", q)
    if not m:
        return None

    explicit_law = detect_explicit_law(question)
    art = m.group(1)

    if explicit_law in (None, "BLHS") and art in BLHS_ARTICLES:
        item = BLHS_ARTICLES[art]
        if (
            len(q.split()) <= 4
            or any(x in q for x in [
                "toi gi", "ten toi", "la gi", "quy dinh gi", "noi dung gi"
            ])
        ):
            return (
                f"Điều {art} Bộ luật Hình sự quy định: "
                f"{item.get('title','')}."
            )

    return None


def _replace_hallucinated_criminal_labels(text, allowed_articles, top_article=None):
    """
    Sửa pattern nguy hiểm kiểu:
    "Tội hành hi sinh (Điều 147)" trong câu hỏi bị đánh.
    Nếu chỉ có một Điều BLHS được nguồn truy xuất, dùng tên Điều thật từ PDF.
    """
    allowed = {str(x) for x in allowed_articles}

    pattern = re.compile(
        r"(?i)\bTội\s+[^.;\n()]{2,100}\s*\(\s*Điều\s+(\d+[a-z]?)"
        r"(?:\s+Bộ\s+luật\s+Hình\s+sự)?\s*\)"
    )

    def repl(match):
        cited = match.group(1)
        if cited in allowed and cited in BLHS_ARTICLES:
            item = BLHS_ARTICLES[cited]
            return f"{item.get('title','')} (Điều {cited} Bộ luật Hình sự)"

        if len(allowed) == 1:
            art = next(iter(allowed))
            item = BLHS_ARTICLES.get(art)
            if item:
                return f"{item.get('title','')} (Điều {art} Bộ luật Hình sự)"

        if top_article and top_article in BLHS_ARTICLES:
            item = BLHS_ARTICLES[top_article]
            return f"{item.get('title','')} (Điều {top_article} Bộ luật Hình sự)"

        return "quy định pháp luật hình sự có liên quan"

    return pattern.sub(repl, text)


def _remove_unsupported_blhs_articles(text, allowed_articles):
    """
    Nếu AI nêu số Điều BLHS không có trong nguồn đã truy xuất,
    bỏ số Điều thay vì để thông tin có vẻ chính xác nhưng sai.
    """
    allowed = {str(x) for x in allowed_articles}

    # "Điều 147 Bộ luật Hình sự"
    pattern_full = re.compile(
        r"(?i)\bĐiều\s+(\d+[a-z]?)\s+Bộ\s+luật\s+Hình\s+sự\b"
    )

    def repl_full(match):
        art = match.group(1)
        if art in allowed:
            return match.group(0)
        return "Bộ luật Hình sự"

    text = pattern_full.sub(repl_full, text)

    # Trong câu hỏi hình sự, "Điều 147" đơn lẻ cũng phải thuộc allowed.
    pattern_short = re.compile(r"(?i)\bĐiều\s+(\d+[a-z]?)\b")

    def repl_short(match):
        art = match.group(1)
        if art in allowed:
            return match.group(0)
        # Không đụng các Điều của luật khác nếu câu đã ghi rõ sau đó.
        tail = text[match.end():match.end()+40].lower()
        if "tố tụng hình sự" in tail or "xử lý vi phạm hành chính" in tail:
            return match.group(0)
        return "quy định"

    return pattern_short.sub(repl_short, text)


def _enforce_hotline(text):
    """
    Số liên hệ duy nhất được hiển thị là số trực ban Công an xã Pơng Drang.
    """
    text = str(text or "")

    # Số điện thoại Việt Nam dài.
    phone_pattern = re.compile(
        r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)"
    )

    def phone_repl(match):
        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("84"):
            digits = "0" + digits[2:]
        if digits == HOTLINE:
            return HOTLINE
        return HOTLINE

    text = phone_pattern.sub(phone_repl, text)

    # Các số khẩn cấp nếu xuất hiện trong vai trò số để gọi/liên hệ.
    text = re.sub(
        r"(?i)((?:gọi|số|hotline|điện thoại|liên hệ)\s*[:\-]?\s*)(113|114|115)\b",
        lambda m: m.group(1) + HOTLINE,
        text
    )

    return text



def _dedupe_repeated_legal_lines(text):
    """
    Sau khi sửa một Điều luật sai, hai dòng sai khác nhau có thể cùng được
    chuẩn hóa về một nội dung đúng. Loại dòng/câu trùng để câu trả lời tự nhiên.
    """
    lines = str(text or "").splitlines()
    seen = set()
    out = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue

        # Bỏ số thứ tự đầu dòng trước khi so trùng.
        comparison = re.sub(r"^\s*\d+\.\s*", "", stripped)
        key = norm(comparison)

        if key and key in seen:
            continue

        if key:
            seen.add(key)

        out.append(stripped)

    return "\n".join(out).strip()

def finalize_answer(
    text,
    legal=False,
    allowed_blhs_articles=None,
    top_blhs_article=None,
    contact_relevant=False,
):
    """
    Hàng rào cuối trước khi trả về Zalo.
    Không biến câu trả lời thành khuôn mẫu, chỉ chặn các chi tiết dễ gây hại nếu AI bịa.
    """
    text = clean_plain_text(text)
    allowed = allowed_blhs_articles or []

    if legal:
        text = _replace_hallucinated_criminal_labels(
            text,
            allowed_articles=allowed,
            top_article=top_blhs_article,
        )
        text = _remove_unsupported_blhs_articles(
            text,
            allowed_articles=allowed,
        )

    text = _enforce_hotline(text)
    text = _dedupe_repeated_legal_lines(text)

    q = norm(text)
    if contact_relevant and HOTLINE not in text:
        text += f" Người dân có thể liên hệ trực ban {UNIT} qua số {HOTLINE}."

    return clean_plain_text(text)


def selftest():
    a134 = BLHS_ARTICLES.get("134", {})
    a140 = BLHS_ARTICLES.get("140", {})

    # Mô phỏng đúng câu sai mà người dùng gặp.
    bad = (
        "Nếu bạn bị đánh, người gây ra hành vi đó có thể bị truy tố. "
        "1. Tội hành hi sinh (Điều 147). "
        "2. Tội gây thương tích (Điều 148). "
        "Bạn nên gọi 0123456789."
    )
    ctx = retrieve_legal_context("Tôi bị đánh thì xử lý thế nào?")
    fixed = finalize_answer(
        bad,
        legal=True,
        allowed_blhs_articles=ctx["allowed_blhs_articles"],
        top_blhs_article=ctx["top_blhs_article"],
        contact_relevant=True,
    )

    return {
        "article_134_title": a134.get("title"),
        "article_140_title": a140.get("title"),
        "retrieved_for_assault": ctx["allowed_blhs_articles"],
        "bad_answer_after_guard": fixed,
        "hotline": HOTLINE,
        "passed": (
            a134.get("title")
            == "Tội cố ý gây thương tích hoặc gây tổn hại cho sức khỏe của người khác"
            and ctx["top_blhs_article"] == "134"
            and "Điều 147" not in fixed
            and "Điều 148" not in fixed
            and "0123456789" not in fixed
            and HOTLINE in fixed
        )
    }
