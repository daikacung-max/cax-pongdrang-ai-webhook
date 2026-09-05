import re
import unicodedata

from config import LEGAL_TOP_K
from core import db

DOCUMENT_ALIASES = {
    "blhs": "BLHS_2025",
    "bộ luật hình sự": "BLHS_2025",
    "bo luat hinh su": "BLHS_2025",
    "hình sự": "BLHS_2025",
}


def _norm(text):
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
        return "permanent_residence", ["RESIDENCE_GUIDANCE_2026", "RESIDENCE_PERMANENT_2026"]
    if any(x in q for x in ["tam tru", "dang ky tam tru"]):
        return "temporary_residence", ["RESIDENCE_GUIDANCE_2026", "TTHC_TEMP_RESIDENCE_2026"]
    if any(x in q for x in ["vneid", "dinh danh dien tu", "tai khoan dinh danh", "muc do 1", "muc do 01", "muc do 2", "muc do 02"]):
        return "vneid", ["VNEID_2026", "VNEID_SIM_GUIDANCE_2026"]
    if any(x in q for x in ["dang ky xe", "xe mo to", "xe may", "xe gan may", "bien so xe", "cap bien so", "mua xe moi"]):
        return "vehicle", ["VEHICLE_REGISTRATION_2026"]
    if any(x in q for x in ["xac nhan cu tru", "xac nhan thong tin cu tru", "cu tru"]):
        return "residence", ["RESIDENCE_GUIDANCE_2026", "RESIDENCE_PERMANENT_2026", "TTHC_TEMP_RESIDENCE_2026"]
    if any(x in q for x in ["toi pham", "bo luat hinh su", "blhs", "bi danh", "danh nguoi", "nguoi khac danh", "thuong tich", "dung dao", "hung khi", "trom", "lua dao", "bi lua chuyen khoan", "lam dung tin nhiem", "gay roi", "huy hoai", "de doa giet"]):
        return "criminal", ["BLHS_2025"]
    return None, None


def _domain(question, queries):
    """
    Ý định của CÂU HIỆN TẠI được ưu tiên tuyệt đối.
    Chỉ dùng lịch sử/planner queries khi câu hiện tại quá ngắn, ví dụ 'thì sao?', 'còn giấy tờ?'.
    Điều này ngăn câu trước về thường trú làm câu mới về VNeID bị route nhầm sang cư trú.
    """
    current_domain = _detect_domain_in_text(question)
    if current_domain[0]:
        return current_domain

    contextual = " ".join(str(x or "") for x in (queries or []))
    return _detect_domain_in_text(contextual)


def _priority_unit_ids(domain, question):
    q = _norm(question)
    if domain == "permanent_residence":
        return [
            "RESIDENCE_PERMANENT_2026:core",
            "RESIDENCE_PERMANENT_2026:documents_by_case",
            "RESIDENCE_GUIDANCE_2026:data_reuse",
        ]
    if domain == "temporary_residence":
        return ["TTHC_TEMP_RESIDENCE_2026:core", "TTHC_TEMP_RESIDENCE_2026:documents_policy"]
    if domain == "vneid":
        if any(x in q for x in ["muc do 2", "muc do 02", "muc 2"]):
            return ["VNEID_2026:level2", "VNEID_2026:overview", "VNEID_SIM_GUIDANCE_2026:sim"]
        if any(x in q for x in ["muc do 1", "muc do 01", "muc 1"]):
            return ["VNEID_2026:level1", "VNEID_2026:overview"]
        if "sim" in q or "so dien thoai" in q:
            return ["VNEID_SIM_GUIDANCE_2026:sim", "VNEID_2026:level2"]
        return ["VNEID_2026:overview", "VNEID_2026:level2", "VNEID_2026:level1"]
    if domain == "vehicle":
        return ["VEHICLE_REGISTRATION_2026:first_registration_documents", "VEHICLE_REGISTRATION_2026:authority"]
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

    for pos, unit_id in enumerate(_priority_unit_ids(domain, question)):
        unit = db.get_unit(unit_id)
        if unit:
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
