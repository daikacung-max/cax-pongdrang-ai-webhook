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
    return any(x in q for x in ["hoac duoi", "nhung thuoc", "tru truong hop", "thuoc mot trong cac truong hop", "ngoai tru"])


def _is_overbroad_negative(text):
    q = norm(text)
    return any(x in q for x in ["khong thuoc pham vi", "khong cau thanh", "chac chan khong", "khong bi xu ly hinh su", "chi khi", "tu 11% tro len moi"])


def _acknowledges_exception(text):
    q = norm(text)
    return any(x in q for x in ["van co the", "neu thuoc", "tru truong hop", "ngoai le", "chua the ket luan", "con phu thuoc", "tuy thuoc", "duoi 11% nhung"])


def _has_residence_source(units):
    return any(str(x.get("document_id") or "").startswith(("RESIDENCE_", "TTHC_TEMP_RESIDENCE_")) for x in units)


def _has_vneid_source(units):
    return any(str(x.get("document_id") or "").startswith("VNEID_") for x in units)


def _has_vehicle_source(units):
    return any(str(x.get("document_id") or "") == "VEHICLE_REGISTRATION_2026" for x in units)


def _unsafe_residence_requirements(answer):
    q = norm(answer)
    risky = [
        "so ho khau", "ho khau gia dinh", "ban sao cmnd", "ban sao cccd", "giay khai sinh", "giay ket hon",
        "thu moi", "giay phep su dung nha", "phong dang ky dan cu", "van phong cong an xa", "cap giay tam tru",
    ]
    return [x for x in risky if x in q]


def _unsafe_vehicle_requirements(answer):
    q = norm(answer)
    risky = ["giay kiem dinh ky thuat", "bao hiem trach nhiem dan su", "phong dang ky xe cua cong an xa", "don dang ky xe", "the dang ky xe", "nhan vien dang ky xe"]
    return [x for x in risky if x in q]


def verify(draft, retrieved_units):
    by_id = {u["id"]: u for u in retrieved_units}
    errors = []
    verified_claims = []

    for claim in draft.get("legal_claims", []):
        unit_id = claim.get("source_unit_id")
        unit = by_id.get(unit_id)
        if not unit:
            errors.append(f"source_unit_id không tồn tại trong nguồn: {unit_id}")
            continue
        claimed_article = claim.get("article")
        if claimed_article is not None and str(claimed_article) != str(unit.get("article") or ""):
            errors.append(f"Điều {claimed_article} không khớp source {unit_id}.")
            continue
        official_title = claim.get("official_title")
        if official_title and norm(official_title) != norm(unit.get("title") or ""):
            errors.append("Tên Điều/tội danh không khớp tiêu đề nguồn.")
            continue
        evidence = str(claim.get("evidence_quote") or "").strip()
        source_text = str(unit.get("text") or "")
        if not evidence or norm(evidence) not in norm(source_text):
            errors.append("evidence_quote không tồn tại nguyên văn trong source.")
            continue
        claim_numbers = _numbers(claim.get("claim", ""))
        evidence_numbers = _numbers(evidence)
        if claim_numbers and not claim_numbers.issubset(evidence_numbers):
            errors.append("Claim nêu số liệu không có trong evidence_quote.")
            continue
        claim_text = str(claim.get("claim") or "")
        if _is_overbroad_negative(claim_text) and _has_exception_structure(source_text) and not _acknowledges_exception(claim_text):
            errors.append("Claim loại trừ quá rộng trong khi nguồn có ngoại lệ.")
            continue
        verified_claims.append(claim)

    allowed_articles = {str(u.get("article")) for u in retrieved_units if u.get("article")}
    cited_articles = set(re.findall(r"(?i)\bĐiều\s+(\d+[a-z]?)\b", draft.get("answer", "")))
    unsupported = sorted(x for x in cited_articles if x not in allowed_articles)
    if unsupported:
        errors.append("Câu trả lời nêu Điều không có trong nguồn: " + ", ".join(unsupported))

    answer_text = str(draft.get("answer") or "")
    source_blob = "\n".join(str(x.get("text") or "") for x in retrieved_units)
    if _is_overbroad_negative(answer_text) and _has_exception_structure(source_blob) and not _acknowledges_exception(answer_text):
        errors.append("Câu trả lời loại trừ tuyệt đối trong khi nguồn có ngoại lệ.")
    if _has_residence_source(retrieved_units):
        risky = _unsafe_residence_requirements(answer_text)
        if risky:
            errors.append("Thành phần/đầu mối cư trú không được nguồn hỗ trợ: " + ", ".join(risky))
    if _has_vehicle_source(retrieved_units):
        risky = _unsafe_vehicle_requirements(answer_text)
        if risky:
            errors.append("Giấy tờ/cách gọi đăng ký xe không được nguồn hỗ trợ: " + ", ".join(risky))

    return {"ok": not errors, "errors": errors, "verified_claims": verified_claims, "allowed_articles": sorted(allowed_articles)}


def verify_dynamic_text(answer, retrieved_units):
    answer = str(answer or "")
    errors = []
    allowed_articles = {str(u.get("article")) for u in retrieved_units if u.get("article")}
    cited_articles = set(re.findall(r"(?i)\bĐiều\s+(\d+[a-z]?)\b", answer))
    unsupported = sorted(x for x in cited_articles if x not in allowed_articles)
    if unsupported:
        errors.append("unsupported_articles:" + ",".join(unsupported))
    source_blob = "\n".join(str(x.get("text") or "") for x in retrieved_units)
    if _is_overbroad_negative(answer) and _has_exception_structure(source_blob) and not _acknowledges_exception(answer):
        errors.append("overbroad_negative")
    if _has_residence_source(retrieved_units):
        risky = _unsafe_residence_requirements(answer)
        if risky:
            errors.append("unsupported_residence_requirements:" + ",".join(risky))
    if _has_vehicle_source(retrieved_units):
        risky = _unsafe_vehicle_requirements(answer)
        if risky:
            errors.append("unsupported_vehicle_requirements:" + ",".join(risky))
    return {"ok": not errors, "errors": errors}


def grounded_dynamic_fallback(question, retrieved_units):
    if not retrieved_units:
        return (
            "Kho dữ liệu hiện chưa có nguồn đã kiểm chứng đủ gần để tôi khẳng định chi tiết nội dung này. "
            "Tôi sẽ không tự đoán giấy tờ, điều luật, mức phạt hoặc thẩm quyền khi chưa có nguồn phù hợp."
        )

    q = norm(question)

    if _has_vneid_source(retrieved_units):
        if any(x in q for x in ["muc 2", "muc do 2", "muc 02", "muc do 02"]):
            return (
                "Đối với tài khoản định danh điện tử VNeID mức độ 02, công dân có thể đến Công an xã, phường, thị trấn hoặc cơ quan quản lý căn cước, không phụ thuộc nơi cư trú. "
                "Công dân xuất trình thẻ căn cước công dân hoặc thẻ căn cước còn hiệu lực, cung cấp thông tin trên Phiếu TK01, số thuê bao di động chính chủ và email nếu có; cán bộ tiếp nhận xác thực khuôn mặt, vân tay. "
                f"Người dân tại địa bàn có thể đến {UNIT_NAME} hoặc gọi số trực ban {HOTLINE} để được hướng dẫn."
            )
        return (
            "VNeID có tài khoản định danh điện tử mức độ 01 và mức độ 02. Mức độ 01 được đăng ký trên ứng dụng VNeID bằng thiết bị số. "
            "Mức độ 02 thực hiện trực tiếp tại Công an xã, phường, thị trấn hoặc cơ quan quản lý căn cước, không phụ thuộc nơi cư trú; công dân xuất trình căn cước còn hiệu lực và thực hiện xác thực khuôn mặt, vân tay. "
            "Nếu anh/chị cho biết cần đăng ký mức độ 01 hay mức độ 02, tôi có thể hướng dẫn đúng từng bước."
        )

    if _has_residence_source(retrieved_units) and "thuong tru" in q:
        return (
            "Đăng ký thường trú được thực hiện tại Công an cấp xã hoặc trực tuyến, thời hạn giải quyết 07 ngày làm việc. "
            "Hồ sơ không có một danh sách cố định cho mọi trường hợp mà phụ thuộc chỗ ở: nhà thuộc sở hữu của anh/chị, nhà của cha mẹ/vợ chồng/con, hoặc nhà thuê/mượn/ở nhờ. "
            "Những thông tin, giấy tờ chứng minh điều kiện cư trú đã có trong cơ sở dữ liệu hoặc VNeID thì cơ quan đăng ký cư trú không được yêu cầu nộp lại. "
            "Anh/chị cho biết mình đăng ký thường trú vào loại chỗ ở nào, tôi sẽ hướng dẫn đúng hồ sơ của trường hợp đó."
        )

    if _has_residence_source(retrieved_units) and "tam tru" in q:
        return (
            "Đăng ký tạm trú thực hiện tại Công an cấp xã hoặc trực tuyến, thời hạn giải quyết 03 ngày làm việc. "
            "Thông tin, giấy tờ đã có trong cơ sở dữ liệu hoặc VNeID không được yêu cầu nộp lại; nếu dữ liệu chưa khai thác được thì có thể cần xuất trình giấy tờ gốc để đối chiếu khi thực sự cần thiết."
        )

    if _has_vehicle_source(retrieved_units) and any(x in q for x in ["dang ky xe", "xe mo to", "xe may", "xe gan may", "bien so"]):
        return (
            "Đối với đăng ký lần đầu xe mô tô, xe gắn máy, hồ sơ cơ bản gồm Giấy khai đăng ký xe theo mẫu ĐKX10, giấy tờ của chủ xe và giấy tờ của xe; "
            "giấy tờ của xe gồm chứng nhận nguồn gốc xe, chứng nhận quyền sở hữu hợp pháp và chứng từ hoàn thành nghĩa vụ tài chính. "
            f"Nếu cần xác nhận điểm tiếp nhận cụ thể tại {UNIT_NAME}, vui lòng gọi số trực ban {HOTLINE}."
        )

    top = retrieved_units[0]
    article = str(top.get("article") or "").strip()
    title = str(top.get("title") or "").strip()
    if article == "134" and any(x in q for x in ["5%", "%", "duoi 11", "dao", "hung khi"]):
        text = (
            "Chưa thể kết luận rằng tỷ lệ thương tích dưới 11% thì không thuộc Điều 134 Bộ luật Hình sự. "
            "Khoản 1 Điều 134 còn quy định trường hợp dưới 11% nhưng thuộc một trong các tình tiết luật định vẫn có thể bị xem xét."
        )
        if "dao" in q or "hung khi" in q:
            text += " Việc dùng dao là dữ kiện quan trọng; cần làm rõ đặc điểm con dao, cách sử dụng và việc có thuộc trường hợp vũ khí hoặc hung khí nguy hiểm hay không."
        return text + " Việc xử lý cụ thể còn phụ thuộc kết quả xác minh và chứng cứ liên quan."
    if article and title:
        return f"Nội dung anh/chị hỏi có liên quan đến Điều {article} Bộ luật Hình sự, {title}. Cần đối chiếu đầy đủ điều kiện của điều luật với diễn biến thực tế trước khi kết luận."
    return "Nguồn phù hợp đã được tìm thấy nhưng dữ kiện hiện có chưa đủ để kết luận chi tiết. Anh/chị có thể bổ sung tình huống cụ thể để tôi phân tích tiếp theo đúng nguồn."


def enforce_phone_policy(text):
    text = str(text or "")
    phone_re = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)")
    def repl(match):
        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("84"):
            digits = "0" + digits[2:]
        return HOTLINE if digits != HOTLINE else HOTLINE
    text = phone_re.sub(repl, text)
    text = re.sub(r"(?i)((?:gọi|liên hệ|điện thoại|hotline|số)\s*[:\-]?\s*)(113|114|115)\b", lambda m: m.group(1) + HOTLINE, text)
    return text


def clean_plain_text(text):
    text = str(text or "").strip()
    for mark in ("```", "**", "__", "`", "*"):
        text = text.replace(mark, "")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?i)đồn\s+công\s+an\s+xã\s+pơng\s+drang(?:,?\s*tỉnh\s+đắk\s+lắk)?", UNIT_NAME, text)
    text = re.sub(r"(?i)cục\s+công\s+an\s+xã\s+pơng\s+drang(?:,?\s*tỉnh\s+đắk\s+lắk)?", UNIT_NAME, text)
    text = re.sub(r"(?i)nhân\s+viên\s+công\s+an", "cán bộ Công an", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def finalize(text, contact_recommended=False):
    text = enforce_phone_policy(clean_plain_text(text))
    if contact_recommended and HOTLINE not in text:
        text += f" Người dân có thể liên hệ trực ban {UNIT_NAME} qua số {HOTLINE}."
    return clean_plain_text(text)


def repair_note(verification):
    return "\n".join("- " + error for error in verification.get("errors", []))
