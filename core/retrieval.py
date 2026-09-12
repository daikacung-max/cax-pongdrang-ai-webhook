import re
import unicodedata

from config import LEGAL_TOP_K
from core import db
from core.clarification import unverified_topic_key

DOCUMENT_ALIASES = {
    "blhs": "BLHS_2025",
    "bộ luật hình sự": "BLHS_2025",
    "bo luat hinh su": "BLHS_2025",
    "hình sự": "BLHS_2025",
    "bltths": "BLTTHS_104_VBHN_2025",
    "bộ luật tố tụng hình sự": "BLTTHS_104_VBHN_2025",
    "bo luat to tung hinh su": "BLTTHS_104_VBHN_2025",
    "xử lý vi phạm hành chính": "XLVPHC_90_VBHN_2026",
    "xu ly vi pham hanh chinh": "XLVPHC_90_VBHN_2026",
}

_TWO_TIER_TTHC_DOMAINS = {
    "permanent_residence", "temporary_residence", "residence_confirmation", "residence",
    "identity_under14", "identity_reissue", "identity_over14_new", "identity_renewal",
    "identity_data", "identity_general", "vehicle", "vehicle_transfer", "vneid",
}


def _norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("vne id", "vneid").replace("vnied", "vneid").replace("vned", "vneid")


def _fts_query(text):
    words = re.findall(r"[0-9A-Za-zÀ-ỹĐđ]+", str(text or ""))
    words = [w for w in words if len(w) >= 2][:12]
    if not words:
        return ""
    return " OR ".join(f'"{w.replace(chr(34), chr(34)*2)}"' for w in words)


def detect_document_from_hint(law_hint):
    hint = (law_hint or "").strip().lower()
    for alias, doc_id in DOCUMENT_ALIASES.items():
        if alias in hint:
            return doc_id
    return None


def _detect_domain_in_text(text):
    """Nhận diện lĩnh vực trong MỘT đoạn văn bản, ưu tiên ý định hiện tại."""
    q = _norm(text)
    if not q:
        return None, None

    if any(x in q for x in ["thuong tru", "dang ky thuong tru", "ho khau thuong tru", "nhap khau"]):
        return "permanent_residence", ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026", "RESIDENCE_PERMANENT_2026"]
    if any(x in q for x in ["tam tru", "dang ky tam tru"]):
        return "temporary_residence", ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026", "TTHC_TEMP_RESIDENCE_2026"]
    if any(x in q for x in ["xac nhan cu tru", "xac nhan thong tin cu tru"]):
        return "residence_confirmation", ["RESIDENCE_CURRENT_2026"]

    # Người dân thường nói ngắn: "làm định danh mức 2", "đăng ký mức 2",
    # "tài khoản mức 2" thay vì đọc đúng tên "tài khoản định danh điện tử".
    # Ưu tiên nhận diện VNeID trước căn cước để không kéo nhầm notebook căn cước.
    vneid_aliases = [
        "vneid", "dinh danh dien tu", "tai khoan dinh danh", "tai khoan vneid",
        "lam dinh danh", "dang ky dinh danh", "cap dinh danh", "kich hoat dinh danh",
        "dinh danh muc 1", "dinh danh muc 01", "dinh danh muc do 1", "dinh danh muc do 01",
        "dinh danh muc 2", "dinh danh muc 02", "dinh danh muc do 2", "dinh danh muc do 02",
        "tai khoan muc 1", "tai khoan muc 01", "tai khoan muc do 1", "tai khoan muc do 01",
        "tai khoan muc 2", "tai khoan muc 02", "tai khoan muc do 2", "tai khoan muc do 02",
    ]
    if any(x in q for x in vneid_aliases):
        return "vneid", ["VNEID_2026", "VNEID_SIM_GUIDANCE_2026"]
    # Chỉ coi cụm "mức 1/2" đứng một mình là VNeID khi câu có động từ đăng ký/cấp/kích hoạt,
    # tránh bắt nhầm các ngữ cảnh khác cũng có từ "mức".
    if any(x in q for x in ["muc 1", "muc 01", "muc do 1", "muc do 01", "muc 2", "muc 02", "muc do 2", "muc do 02"]) and any(
        x in q for x in ["dang ky", "lam", "cap", "kich hoat", "tai khoan"]
    ):
        return "vneid", ["VNEID_2026", "VNEID_SIM_GUIDANCE_2026"]

    identity_doc = ["CITIZEN_ID_5230_COMMUNE_2026"]
    if "can cuoc" in q and (
        any(x in q for x in ["duoi 14", "tre em", "con toi", "be nha toi", "nguoi dai dien", "nguoi giam ho"])
        or re.search(r"\b(?:con|be)\s+\d{1,2}\s+tuoi\b", q)
    ):
        return "identity_under14", identity_doc
    if any(x in q for x in ["mat can cuoc", "mat cccd", "cap lai can cuoc", "cap lai the can cuoc", "cap lai cccd", "lam lai can cuoc", "lam lai cccd"]) or (
        any(x in q for x in ["can cuoc", "cccd"])
        and any(x in q for x in ["hu hong", "khong su dung duoc"])
    ):
        return "identity_reissue", identity_doc
    if any(x in q for x in ["cap can cuoc lan dau", "cap cccd lan dau", "cap moi can cuoc", "cap moi cccd"]) or (
        any(x in q for x in ["can cuoc", "cccd"])
        and any(x in q for x in ["tu du 14", "14 tuoi"])
        and not any(x in q for x in ["mat", "cap lai", "hu hong", "doi"])
    ):
        return "identity_over14_new", identity_doc
    if any(x in q for x in ["doi can cuoc", "doi cccd", "cap doi can cuoc", "cap doi the can cuoc", "cap doi cccd", "thong tin thay doi", "sap het han"]):
        return "identity_renewal", identity_doc
    if any(x in q for x in ["khai thac thong tin dan cu", "khai thac du lieu dan cu", "du lieu can cuoc", "adn", "giong noi"]) and any(
        x in q for x in ["can cuoc", "dan cu", "adn", "giong noi"]
    ):
        return "identity_data", identity_doc
    if any(x in q for x in ["can cuoc", "cccd", "can cuoc cong dan"]):
        return "identity_general", identity_doc

    if any(x in q for x in ["bi trom", "bi de doa", "mat tai san", "mat xe", "mat dien thoai"]):
        return "incident_report", ["BLHS_2025", "BLTTHS_104_VBHN_2025", "CRIME_REPORT_GUIDANCE_2025"]
    if any(x in q for x in ["lua dao chuyen khoan", "bi lua", "nguoi lua dao", "chuyen khoan", "chuyen tien", "bi scam", "scam chuyen khoan"]):
        return "fraud_transfer", ["FRAUD_TRANSFER_GUIDANCE_2026"]

    if any(x in q for x in ["sang ten", "chuyen nhuong", "thu hoi"]) and any(x in q for x in ["xe", "dang ky xe", "bien so"]):
        return "vehicle_transfer", ["VEHICLE_CURRENT_2026", "VEHICLE_TRANSFER_LOCAL_2026"]
    if any(x in q for x in ["dang ky xe", "xe mo to", "xe may", "xe gan may", "bien so xe", "cap bien so", "mua xe moi", "cap doi dang ky xe", "cap lai dang ky xe"]):
        return "vehicle", ["VEHICLE_CURRENT_2026", "VEHICLE_REGISTRATION_2026"]

    if any(x in q for x in ["cu tru", "tach ho", "xoa tam tru", "xoa thuong tru"]):
        return "residence", ["RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026", "RESIDENCE_PERMANENT_2026", "TTHC_TEMP_RESIDENCE_2026"]
    if any(x in q for x in ["to giac", "tin bao toi pham", "trinh bao toi pham", "bao an"]):
        return "crime_report", ["BLTTHS_104_VBHN_2025", "CRIME_REPORT_GUIDANCE_2025"]
    if any(x in q for x in ["karaoke", "hat karaoke", "loa keo", "tieng on", "on ao", "on nhieu"]):
        return "noise_karaoke", ["NOISE_KARAOKE_282_2025"]
    if any(x in q for x in ["ma tuy", "chat ma tuy", "su dung trai phep chat ma tuy", "cai nghien"]):
        return "drug_law", ["PCTMT_120_2025", "BLHS_2025", "ND282_2025_CURRENT"]
    if any(x in q for x in ["xu phat", "vi pham hanh chinh", "tham quyen xu phat"]):
        return "administrative_sanction", ["XLVPHC_90_VBHN_2026", "SANCTION_AUTHORITY_02_VBHN_2026", "ND282_2025_CURRENT"]

    if unverified_topic_key(q) is not None:
        return "unverified_topic", []
    if any(x in q for x in ["toi pham", "bo luat hinh su", "blhs", "bi danh", "danh nguoi", "nguoi khac danh", "hanh hung", "camera", "thuong tich", "dung dao", "hung khi", "trom", "lua dao", "bi lua chuyen khoan", "lam dung tin nhiem", "gay roi", "huy hoai", "de doa giet"]):
        return "criminal", ["BLHS_2025", "BLTTHS_104_VBHN_2025"]
    return None, None


def _domain(question, queries):
    """Ý định câu hiện tại được ưu tiên; lịch sử chỉ cứu các câu quá ngắn."""
    current_domain = _detect_domain_in_text(question)
    if current_domain[0]:
        return current_domain
    contextual = " ".join(str(x or "") for x in (queries or []))
    return _detect_domain_in_text(contextual)


def _priority_unit_ids(domain, question):
    q = _norm(question)
    if domain == "permanent_residence":
        return ["RESIDENCE_CURRENT_2026:permanent", "RESIDENCE_CURRENT_2026:data_reuse", "RESIDENCE_PERMANENT_2026:documents_by_case"]
    if domain == "temporary_residence":
        return ["RESIDENCE_CURRENT_2026:temporary", "RESIDENCE_CURRENT_2026:data_reuse", "TTHC_TEMP_RESIDENCE_2026:documents_policy"]
    if domain == "residence_confirmation":
        return ["RESIDENCE_CURRENT_2026:confirmation", "RESIDENCE_CURRENT_2026:data_reuse"]
    if domain == "vneid":
        if any(x in q for x in ["muc do 2", "muc do 02", "muc 2", "muc 02", "dinh danh muc 2", "dinh danh muc 02"]):
            return ["VNEID_2026:level2", "VNEID_2026:overview", "VNEID_SIM_GUIDANCE_2026:sim"]
        if any(x in q for x in ["muc do 1", "muc do 01", "muc 1", "muc 01", "dinh danh muc 1", "dinh danh muc 01"]):
            return ["VNEID_2026:level1", "VNEID_2026:overview"]
        if "sim" in q or "so dien thoai" in q:
            return ["VNEID_SIM_GUIDANCE_2026:sim", "VNEID_2026:level2"]
        return ["VNEID_2026:overview", "VNEID_2026:level2", "VNEID_2026:level1"]
    if domain == "identity_under14":
        return ["CITIZEN_ID_5230_COMMUNE_2026:under14", "CITIZEN_ID_5230_COMMUNE_2026:scope"]
    if domain == "identity_reissue":
        return ["CITIZEN_ID_5230_COMMUNE_2026:reissue", "CITIZEN_ID_5230_COMMUNE_2026:fees", "CITIZEN_ID_5230_COMMUNE_2026:scope"]
    if domain == "identity_over14_new":
        return ["CITIZEN_ID_5230_COMMUNE_2026:first_issue_14plus", "CITIZEN_ID_5230_COMMUNE_2026:scope"]
    if domain == "identity_renewal":
        return ["CITIZEN_ID_5230_COMMUNE_2026:renewal", "CITIZEN_ID_5230_COMMUNE_2026:fees", "CITIZEN_ID_5230_COMMUNE_2026:scope"]
    if domain in ("identity_data", "identity_general"):
        return ["CITIZEN_ID_5230_COMMUNE_2026:scope", "CITIZEN_ID_5230_COMMUNE_2026:other_commune_procedures"]
    if domain == "crime_report":
        return ["CRIME_REPORT_GUIDANCE_2025:channels", "CRIME_REPORT_GUIDANCE_2025:rights", "CRIME_REPORT_GUIDANCE_2025:local_intake", "BLTTHS_104_VBHN_2025:article:145", "BLTTHS_104_VBHN_2025:article:146"]
    if domain == "noise_karaoke":
        return ["NOISE_KARAOKE_282_2025:quiet_places", "NOISE_KARAOKE_282_2025:other_noise", "NOISE_KARAOKE_282_2025:public_propaganda"]
    if domain == "fraud_transfer":
        return ["FRAUD_TRANSFER_GUIDANCE_2026:response"]
    if domain == "vehicle":
        return ["VEHICLE_CURRENT_2026:first_domestic_online", "VEHICLE_CURRENT_2026:authority", "VEHICLE_CURRENT_2026:legal_chain", "VEHICLE_REGISTRATION_2026:first_registration_documents"]
    if domain == "vehicle_transfer":
        return ["VEHICLE_CURRENT_2026:authority", "VEHICLE_TRANSFER_LOCAL_2026:scope", "VEHICLE_TRANSFER_LOCAL_2026:documents", "VEHICLE_TRANSFER_LOCAL_2026:time"]
    if domain == "administrative_sanction":
        return ["SANCTION_AUTHORITY_02_VBHN_2026:status"]
    if domain == "drug_law":
        return ["PCTMT_120_2025:status"]
    if domain == "criminal" and any(x in q for x in ["bi danh", "hanh hung", "thuong tich", "dung dao", "camera", "video", "clip"]):
        return ["BLHS_2025:article:134"]
    return []


def _candidate_score(unit, query, query_index):
    q = _norm(query)
    title = _norm(unit.get("title") or "")
    text = _norm(unit.get("text") or "")
    q_tokens = {x for x in q.split() if len(x) >= 2}
    title_tokens = set(title.split())
    score = max(0, 12 - query_index * 2)
    if q and q == title:
        score += 400
    elif q and q in title:
        score += 120
    score += len(q_tokens & title_tokens) * 16
    score += sum(1 for token in list(q_tokens)[:8] if token in text)
    return score


def _unit_allowed_for_domain(domain, unit):
    """Tách notebook theo thủ tục và loại nội dung cấp hành chính đã bỏ.

    Đây là bộ lọc trước khi context được đưa cho model. Audit DB vẫn giữ bản ghi
    gốc nhưng người dân và LLM chỉ nhìn các source-unit hợp phạm vi hiện hành.
    """
    unit_id = str(unit.get("id") or "")
    corpus = _norm((unit.get("title") or "") + " " + (unit.get("text") or ""))
    if domain in _TWO_TIER_TTHC_DOMAINS and "cong an cap huyen" in corpus:
        return False
    if domain == "vehicle_transfer" and unit_id == "VEHICLE_CURRENT_2026:first_domestic_online":
        return False
    if domain == "vehicle" and str(unit.get("document_id") or "") == "VEHICLE_TRANSFER_LOCAL_2026":
        return False
    return True


def retrieve(plan, question):
    candidates = {}
    for ref in plan.get("explicit_references", []):
        article = str(ref.get("article") or "").strip()
        doc_id = detect_document_from_hint(ref.get("law_hint"))
        for candidate in ([doc_id] if doc_id else ["BLHS_2025"]):
            if not candidate:
                continue
            for unit in db.get_article(candidate, article):
                entry = dict(unit)
                entry["_why"] = "explicit_article"
                entry["_score"] = 10000
                candidates[entry["id"]] = entry

    queries = list(plan.get("search_queries") or []) or [question]
    if question not in queries:
        queries.append(question)
    domain, document_filter = _domain(question, queries)
    if domain == "unverified_topic":
        return []

    for pos, unit_id in enumerate(_priority_unit_ids(domain, question)):
        unit = db.get_unit(unit_id)
        if unit and _unit_allowed_for_domain(domain, unit):
            entry = dict(unit)
            entry["_why"] = "domain_priority"
            entry["_score"] = 9000 - pos
            candidates[entry["id"]] = entry

    for query_index, query in enumerate(queries[:4]):
        fts = _fts_query(query)
        if not fts:
            continue
        found = db.search_fts(fts, limit=max(LEGAL_TOP_K * 2, 12), document_ids=document_filter)
        if not found and document_filter is None:
            found = db.search_like(query, limit=max(LEGAL_TOP_K * 2, 12))
        for unit in found:
            if not _unit_allowed_for_domain(domain, unit):
                continue
            entry = dict(unit)
            score = _candidate_score(entry, query, query_index)
            old = candidates.get(entry["id"])
            if old is None or score > old.get("_score", -1):
                entry["_why"] = f"search:{query}"
                entry["_score"] = score
                candidates[entry["id"]] = entry

    ranked = sorted(candidates.values(), key=lambda x: x.get("_score", 0), reverse=True)
    return ranked[:LEGAL_TOP_K]


def format_context(units):
    blocks = []
    for unit in units:
        source = f"{unit.get('document_title','')}" + (f" ({unit.get('document_number')})" if unit.get("document_number") else "")
        blocks.append(
            "SOURCE_UNIT_ID: " + unit["id"] + "\n"
            "SOURCE: " + source.strip() + "\n"
            "ARTICLE: " + str(unit.get("article") or "") + "\n"
            "TITLE: " + str(unit.get("title") or "") + "\n"
            "TEXT:\n" + str(unit.get("text") or "")
        )
    return "\n\n====================\n\n".join(blocks)
