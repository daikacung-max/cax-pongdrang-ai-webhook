import re
import unicodedata

from config import UNIT_NAME, HOTLINE
from core.clarification import clarification_for_unverified_topic


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


def _asserts_guilt(text):
    q = norm(text)
    patterns = [
        r"\b(?:nguoi kia|ho|anh ay|co ay|doi tuong)\s+(?:da\s+)?pham toi\b",
        r"\bchac chan\s+(?:la\s+)?(?:toi pham|pham toi|bi truy cuu)\b",
        r"\bdu can cu ket luan\s+(?:la\s+)?pham toi\b",
    ]
    return any(re.search(pattern, q) for pattern in patterns)


def _premature_fraud_label(answer, question):
    """Không gán Điều 174/tên tội danh chỉ từ lời kể bị lừa chuyển khoản."""
    q = norm(question)
    a = norm(answer)
    is_transfer_report = any(x in q for x in ["bi lua", "lua dao chuyen khoan", "chuyen khoan", "chuyen tien"])
    names_fraud_offence = "dieu 174" in a or "toi lua dao chiem doat tai san" in a
    has_caveat = any(x in a for x in ["chua the ket luan", "chua the xac dinh", "can xac minh", "con phu thuoc"])
    return is_transfer_report and names_fraud_offence and not has_caveat


def _has_residence_source(units):
    return any(str(x.get("document_id") or "").startswith(("RESIDENCE_", "TTHC_TEMP_RESIDENCE_")) for x in units)


def _has_vneid_source(units):
    return any(str(x.get("document_id") or "").startswith("VNEID_") for x in units)


def _has_vehicle_source(units):
    return any(str(x.get("document_id") or "") == "VEHICLE_REGISTRATION_2026" for x in units)


def _has_crime_report_source(units):
    return any(str(x.get("document_id") or "") == "CRIME_REPORT_GUIDANCE_2025" for x in units)


def _has_identity_under14_source(units):
    return any(str(x.get("document_id") or "") == "CITIZEN_ID_UNDER14_2026" for x in units)


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


def _unsupported_procedural_details(answer, source_blob, question=""):
    """Chặn tên biểu mẫu, giấy tờ và cơ quan nhạy cảm không xuất hiện trong nguồn."""
    answer_norm = norm(answer)
    allowed = norm(source_blob + "\n" + str(question or ""))
    candidates = set()

    # Mã biểu mẫu là nơi model dễ bịa nhất, ví dụ TK99 hay ĐKX01.
    for match in re.finditer(
        r"\b(?:mau|phieu|to khai|don)\s+([a-zđ]{0,8}\d+[a-z0-9-]*)\b",
        answer_norm,
    ):
        candidates.add(match.group(0))

    sensitive_phrases = [
        "uy ban nhan dan", "cong an huyen", "cong an tinh",
        "phong canh sat", "phong quan ly hanh chinh", "van phong cong an xa",
        "dich vu buu chinh", "buu chinh cong ich", "hop dong thue nha",
        "giay khai sinh", "giay ket hon", "so ho khau", "so do", "so hong",
        "don khieu nai", "ho so khieu nai", "yeu cau dieu tra",
    ]
    candidates.update(x for x in sensitive_phrases if x in answer_norm)
    return sorted(x for x in candidates if x not in allowed)


def _article_134_dynamic_errors(answer, retrieved_units):
    """Chốt cứng các kết luận Dynamic không được phép suy ra từ thương tích/dùng dao."""
    if not any(str(x.get("article") or "") == "134" for x in retrieved_units):
        return []
    q = norm(answer)
    errors = []
    absolute_no_criminal = [
        "khong bi xu ly hinh su", "khong phai chiu trach nhiem hinh su",
        "khong cau thanh toi pham", "khong the bi truy cuu", "khong bi khoi to",
    ]
    has_low_injury = bool(re.search(r"\b(?:\d+(?:[.,]\d+)?%|duoi\s+11)\b", q))
    if has_low_injury and any(x in q for x in absolute_no_criminal):
        errors.append("article_134_absolute_low_injury_conclusion")

    knife_as_weapon = any(x in q for x in [
        "dao la vu khi", "dao lam vu khi", "su dung dao lam vu khi",
        "dung dao lam vu khi", "dao thuoc diem a", "dung dao thuoc diem a",
        "dao la hung khi nguy hiem", "dao chinh la hung khi nguy hiem",
    ])
    needs_verification = any(x in q for x in [
        "can lam ro", "can xac minh", "co thuoc", "hay khong", "chua the ket luan",
    ])
    if knife_as_weapon and not needs_verification:
        errors.append("article_134_knife_assumed_weapon")
    return errors


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
    # Cả Full Core lẫn Dynamic đều phải giữ cách xưng hô thống nhất khi nói
    # chuyện với người dân. Nếu model dùng "bạn", Full Core sẽ đi qua fallback
    # đã được kiểm chứng thay vì phát nguyên văn câu trả lời đó.
    if re.search(r"(?i)\bbạn\s+(?:có|cần|đã|nên|muốn|hãy|vui lòng)\b", answer_text):
        errors.append("second_person_must_be_anh_chi")
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


def verify_dynamic_text(answer, retrieved_units, question=""):
    answer = str(answer or "")
    errors = []
    allowed_articles = {str(u.get("article")) for u in retrieved_units if u.get("article")}
    cited_articles = set(re.findall(r"(?i)\bĐiều\s+(\d+[a-z]?)\b", answer))
    unsupported = sorted(x for x in cited_articles if x not in allowed_articles)
    if unsupported:
        errors.append("unsupported_articles:" + ",".join(unsupported))
    source_blob = "\n".join(str(x.get("text") or "") for x in retrieved_units)
    allowed_numbers = _numbers(source_blob) | _numbers(question) | _numbers(HOTLINE)
    unsupported_numbers = sorted(_numbers(answer) - allowed_numbers)
    if unsupported_numbers:
        errors.append("unsupported_numbers:" + ",".join(unsupported_numbers))
    if _is_overbroad_negative(answer) and _has_exception_structure(source_blob) and not _acknowledges_exception(answer):
        errors.append("overbroad_negative")
    if _asserts_guilt(answer):
        errors.append("unsupported_guilt_conclusion")
    if _premature_fraud_label(answer, question):
        errors.append("premature_fraud_offence_label")
    # Giữ nhất quán cách xưng hô đã công bố của trợ lý. Nếu model lạc sang
    # "bạn", nhánh Dynamic sẽ dùng câu fallback đã bám nguồn và xưng "anh/chị".
    if re.search(r"(?i)\bbạn\s+(?:có|cần|đã|nên|muốn|hãy|vui lòng)\b", answer):
        errors.append("second_person_must_be_anh_chi")
    answer_norm = norm(answer)
    if any(x in answer_norm for x in ["dao la hung khi nguy hiem", "dao chinh la hung khi nguy hiem"]):
        errors.append("knife_assumed_dangerous_weapon")
    errors.extend(_article_134_dynamic_errors(answer, retrieved_units))
    if _has_residence_source(retrieved_units):
        risky = _unsafe_residence_requirements(answer)
        if risky:
            errors.append("unsupported_residence_requirements:" + ",".join(risky))
    if _has_vehicle_source(retrieved_units):
        risky = _unsafe_vehicle_requirements(answer)
        if risky:
            errors.append("unsupported_vehicle_requirements:" + ",".join(risky))
    unsupported_details = _unsupported_procedural_details(answer, source_blob, question)
    if unsupported_details:
        errors.append("unsupported_procedural_details:" + ",".join(unsupported_details))
    return {"ok": not errors, "errors": errors}


def grounded_dynamic_fallback(question, retrieved_units):
    if not retrieved_units:
        topical_reply = clarification_for_unverified_topic(question)
        if topical_reply:
            return topical_reply
        if "dang ky" in norm(question):
            return (
                "Anh/chị muốn đăng ký tạm trú, thường trú, xe máy mới, sang tên xe hay VNeID? "
                "Mỗi trường hợp có giấy tờ khác nhau; anh/chị cho biết đúng nội dung cần đăng ký để tôi hướng dẫn chính xác."
            )
        return (
            "Kho dữ liệu hiện chưa có nguồn đã kiểm chứng đủ gần để tôi khẳng định chi tiết nội dung này. "
            "Tôi sẽ không tự đoán giấy tờ, điều luật, mức phạt hoặc thẩm quyền khi chưa có nguồn phù hợp."
        )

    q = norm(question)

    if any(unit.get("document_id") == "CITIZEN_ID_REISSUE_PROVINCIAL_2026" for unit in retrieved_units):
        return (
            "Trường hợp mất thẻ Căn cước, thủ tục cấp lại hiện được thực hiện tại cơ quan quản lý căn cước của Công an cấp tỉnh. "
            "Anh/chị có thể đến trực tiếp hoặc đăng ký qua Cổng Dịch vụ công quốc gia, Cổng Dịch vụ công Bộ Công an hoặc ứng dụng VNeID; "
            "thời hạn giải quyết là 07 ngày làm việc. "
            "Khi bị mất thẻ, cơ quan tiếp nhận đối chiếu dữ liệu căn cước đã có để thực hiện thủ tục; anh/chị đang mất thẻ hay thẻ bị hư hỏng không sử dụng được?"
        )

    if any(unit.get("document_id") == "CITIZEN_ID_OVER14_PROVINCIAL_2026" for unit in retrieved_units):
        first_time = any(x in q for x in ["lan dau", "cap moi"])
        states_over14 = any(x in q for x in ["tu du 14", "14 tuoi"])
        opening = (
            "Nếu người cần làm đã từ đủ 14 tuổi, thủ tục cấp thẻ Căn cước hiện được thực hiện tại cơ quan quản lý căn cước của Công an cấp tỉnh "
            if first_time and not states_over14
            else "Với người từ đủ 14 tuổi cần cấp thẻ Căn cước, thủ tục hiện được thực hiện tại cơ quan quản lý căn cước của Công an cấp tỉnh "
        )
        follow_up = " Anh/chị cho biết người cần làm đã đủ 14 tuổi chưa?" if first_time and not states_over14 else ""
        return (
            opening
            + "hoặc Trung tâm phục vụ hành chính công cấp tỉnh nếu địa phương đã triển khai. Anh/chị có thể đến trực tiếp hoặc đăng ký thời gian, "
            + "địa điểm qua Cổng Dịch vụ công quốc gia, Cổng Dịch vụ công Bộ Công an hoặc ứng dụng VNeID; thời hạn giải quyết là 07 ngày làm việc. "
            + follow_up
        )

    if any(unit.get("document_id") == "CITIZEN_ID_RENEWAL_PROVINCIAL_2026" for unit in retrieved_units):
        return "Cấp đổi thẻ Căn cước hiện được thực hiện tại cơ quan quản lý căn cước của Công an cấp tỉnh. Anh/chị có thể đến trực tiếp hoặc đăng ký thời gian, địa điểm qua Cổng Dịch vụ công quốc gia, Cổng Dịch vụ công Bộ Công an hoặc ứng dụng VNeID; thời hạn giải quyết là 07 ngày làm việc. Anh/chị cần đổi do thông tin thay đổi, thẻ sắp hết hạn hay vì lý do khác?"

    if any(unit.get("document_id") == "FRAUD_TRANSFER_GUIDANCE_2026" for unit in retrieved_units):
        return "Tôi đã ghi nhận anh/chị nghi bị lừa qua chuyển khoản. Anh/chị nên liên hệ ngay ngân hàng để đề nghị hỗ trợ tạm dừng hoặc phong tỏa giao dịch nếu còn khả năng; đồng thời lưu tin nhắn, số tài khoản, mã QR, đường dẫn và chứng từ giao dịch liên quan. Tôi chưa thể xác định tội danh từ thông tin ban đầu; anh/chị chuyển khoản vào thời điểm nào?"

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

    if any(unit.get("document_id") == "VEHICLE_TRANSFER_LOCAL_2026" for unit in retrieved_units):
        return (
            "Sang tên xe thực hiện tại Công an cấp xã được phân cấp đăng ký xe, nên cần xác nhận điểm tiếp nhận cụ thể tại địa phương. "
            "Chủ xe đang đứng tên làm thủ tục thu hồi trước, sau đó người nhận chuyển nhượng đăng ký sang tên; hồ sơ gồm giấy khai đăng ký xe, giấy tờ của chủ xe, chứng từ chuyển quyền sở hữu, chứng từ lệ phí trước bạ và chứng nhận thu hồi. "
            "Hai bước cấp chứng nhận không quá 02 ngày làm việc khi hồ sơ hợp lệ. Anh/chị là người đang đứng tên xe hay người nhận chuyển nhượng?"
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
        injury = re.search(r"\b\d+(?:[.,]\d+)?%", str(question or ""))
        acknowledgement = (
            f"Anh/chị cho biết tỷ lệ thương tích là {injury.group(0)}. "
            if injury else ""
        )
        text = (
            acknowledgement
            + "Chưa thể kết luận rằng tỷ lệ thương tích dưới 11% thì không thuộc Điều 134 Bộ luật Hình sự. "
            "Khoản 1 Điều 134 còn quy định trường hợp dưới 11% nhưng thuộc một trong các tình tiết luật định vẫn có thể bị xem xét."
        )
        if "dao" in q or "hung khi" in q:
            text += " Việc dùng dao là dữ kiện quan trọng; cần làm rõ đặc điểm con dao, cách sử dụng và việc có thuộc trường hợp vũ khí hoặc hung khí nguy hiểm hay không."
        return text + " Việc xử lý cụ thể còn phụ thuộc kết quả xác minh và chứng cứ liên quan."

    if _has_identity_under14_source(retrieved_units):
        return (
            "Thủ tục này áp dụng cho người dưới 14 tuổi và thực hiện tại Công an xã. "
            "Nếu làm trực tiếp, người đại diện hợp pháp đưa người dưới 14 tuổi đến địa điểm làm thủ tục. "
            "Anh/chị cho biết người cần làm căn cước hiện dưới 06 tuổi hay từ đủ 06 đến dưới 14 tuổi để tôi hướng dẫn đúng cách thực hiện."
        )

    if _has_crime_report_source(retrieved_units):
        return (
            "Anh/chị có thể tố giác hoặc báo tin trực tiếp, bằng văn bản, qua điện thoại trực ban, qua VNeID hoặc các kênh được hướng dẫn. "
            "Công an cấp xã là một trong các đơn vị tiếp nhận; nếu có nguy cơ bị đe dọa, anh/chị có quyền đề nghị giữ bí mật việc tố giác và bảo vệ theo quy định. "
            f"Anh/chị có thể liên hệ trực ban {UNIT_NAME} qua số {HOTLINE} để được hướng dẫn tiếp nhận."
        )
    if article == "134" and any(x in q for x in ["camera", "video", "clip", "ghi hinh"]):
        return (
            "Đoạn camera là chứng cứ cần bảo toàn. Anh/chị nên giữ nguyên file gốc, không chỉnh sửa, sao lưu thêm một bản và ghi lại thời gian, địa điểm, người biết sự việc; "
            "khi trình báo thì cung cấp bản sao theo hướng dẫn và giữ lại bản gốc để đối chiếu. Việc đánh giá trách nhiệm cụ thể vẫn phải dựa trên toàn bộ diễn biến, thương tích và kết quả xác minh."
        )
    if article == "134" and any(x in q for x in ["bi danh", "nguoi khac danh", "bi hanh hung"]):
        return (
            "Tôi đã ghi nhận anh/chị bị người khác đánh. Nếu có thương tích, anh/chị nên đi khám và giữ lại giấy tờ liên quan; "
            "đồng thời lưu ảnh, video, tin nhắn hoặc thông tin người biết sự việc nếu có. "
            "Anh/chị đã đi khám hoặc có kết quả thương tích chưa?"
        )
    if any(x in q for x in ["bi lua", "lua dao chuyen khoan", "chuyen tien", "chuyen khoan"]):
        return (
            "Tôi đã ghi nhận việc anh/chị nghi bị lừa qua chuyển khoản. Anh/chị nên giữ lại chứng từ giao dịch, tin nhắn, "
            "ảnh chụp và thông tin tài khoản liên quan; tôi chưa thể xác định tội danh chỉ từ thông tin hiện có. "
            "Anh/chị chuyển khoản vào thời điểm nào?"
        )
    if any(x in q for x in ["bi trom", "bi de doa", "mat tai san", "mat xe", "mat dien thoai"]):
        return (
            "Tôi đã ghi nhận sự việc anh/chị phản ánh. Anh/chị nên giữ lại thông tin, hình ảnh, video, tin nhắn "
            "hoặc giấy tờ liên quan nếu có; tôi chưa thể kết luận trách nhiệm hoặc tội danh chỉ từ thông tin ban đầu. "
            "Sự việc xảy ra khi nào và ở đâu?"
        )
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
