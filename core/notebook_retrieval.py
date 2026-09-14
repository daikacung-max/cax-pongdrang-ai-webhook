"""Notebook-style source router layered over the existing legal retriever.

Only categories mirrored from the user's 19-source Gemini Notebook that were not
already explicit in the legacy router are handled here. Everything else falls
through to the existing retriever unchanged.
"""

import re
import unicodedata

from config import LEGAL_TOP_K
from core import db
from core.retrieval import retrieve as legacy_retrieve


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _pack(priority_ids, document_ids, question):
    result = []
    seen = set()
    for unit_id in priority_ids:
        unit = db.get_unit(unit_id)
        if unit and unit["id"] not in seen:
            item = dict(unit)
            item["_why"] = "notebook_priority"
            item["_score"] = 9500 - len(result)
            result.append(item)
            seen.add(item["id"])
    if len(result) < LEGAL_TOP_K:
        # LIKE is intentionally used here because Vietnamese FTS tokenisation can
        # be brittle for short colloquial questions. The document filter keeps
        # the search inside the selected Notebook source pack.
        for unit in db.search_like(question, limit=max(LEGAL_TOP_K * 2, 12), document_ids=document_ids):
            if unit["id"] in seen:
                continue
            item = dict(unit)
            item["_why"] = "notebook_search"
            item["_score"] = 5000 - len(result)
            result.append(item)
            seen.add(item["id"])
            if len(result) >= LEGAL_TOP_K:
                break
    return result[:LEGAL_TOP_K]


def retrieve(plan, question):
    q = _norm(question)

    # Residence sub-notebooks not previously separated by the old router.
    residence_routes = [
        (["xoa dang ky thuong tru", "xoa thuong tru"], "RESIDENCE_NOTEBOOK_2026:delete_permanent"),
        (["gia han tam tru"], "RESIDENCE_NOTEBOOK_2026:extend_temporary"),
        (["tach ho"], "RESIDENCE_NOTEBOOK_2026:split_household"),
        (["dieu chinh thong tin cu tru", "dieu chinh tt ve ct"], "RESIDENCE_NOTEBOOK_2026:adjust"),
        (["khai bao thong tin ve cu tru", "khai bao tt ve ct"], "RESIDENCE_NOTEBOOK_2026:declare"),
        (["xoa dang ky tam tru", "xoa tam tru"], "RESIDENCE_NOTEBOOK_2026:delete_temporary"),
        (["khai bao tam vang", "tam vang"], "RESIDENCE_NOTEBOOK_2026:temporary_absence"),
        (["thong bao luu tru", "luu tru"], "RESIDENCE_NOTEBOOK_2026:stay_notification"),
    ]
    for aliases, unit_id in residence_routes:
        if any(alias in q for alias in aliases):
            return _pack(
                [unit_id, "RESIDENCE_CURRENT_2026:data_reuse"],
                ["RESIDENCE_NOTEBOOK_2026", "RESIDENCE_CURRENT_2026", "RESIDENCE_GUIDANCE_2026"],
                question,
            )

    if any(x in q for x in ["ho chieu", "xuat nhap canh", "passport"]):
        return _pack(
            ["PASSPORT_CURRENT_2026:issue", "PASSPORT_CURRENT_2026:scope"],
            ["PASSPORT_CURRENT_2026"], question,
        )

    if any(x in q for x in ["nganh nghe kinh doanh", "an ninh trat tu", "giay chung nhan du dieu kien ve an ninh"]):
        return _pack(
            ["SECURITY_BUSINESS_CURRENT_2026:new_certificate", "SECURITY_BUSINESS_CURRENT_2026:scope"],
            ["SECURITY_BUSINESS_CURRENT_2026"], question,
        )

    if any(x in q for x in ["vu khi", "vat lieu no", "cong cu ho tro", "ccht"]):
        return _pack(
            ["WEAPONS_CURRENT_2026:support_tool_permit", "WEAPONS_CURRENT_2026:scope"],
            ["WEAPONS_CURRENT_2026"], question,
        )

    if any(x in q for x in ["ly lich tu phap", "phieu ly lich tu phap"]):
        return _pack(
            ["CRIMINAL_RECORD_CURRENT_2026:citizen"],
            ["CRIMINAL_RECORD_CURRENT_2026"], question,
        )

    if any(x in q for x in ["giay phep lai xe", "gplx", "sat hach lai xe", "san tap lai"]):
        return _pack(
            ["DRIVING_LICENCE_CURRENT_2026:scope", "DRIVING_LICENCE_CURRENT_2026:test_center_type3"],
            ["DRIVING_LICENCE_CURRENT_2026"], question,
        )

    return legacy_retrieve(plan, question)
