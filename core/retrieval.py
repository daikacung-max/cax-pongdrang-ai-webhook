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
    escaped = []
    for word in words:
        word = word.replace('"', '""')
        escaped.append(f'"{word}"')
    return " OR ".join(escaped)


def detect_document_from_hint(law_hint):
    hint = (law_hint or "").strip().lower()
    for alias, doc_id in DOCUMENT_ALIASES.items():
        if alias in hint:
            return doc_id
    return None


def _candidate_score(unit, query, query_index):
    q = _norm(query)
    title = _norm(unit.get("title") or "")
    text = _norm(unit.get("text") or "")
    q_tokens = {x for x in q.split() if len(x) >= 2}
    title_tokens = set(title.split())
    score = max(0, 12 - query_index * 2)
    if q and q == title:
        score += 400.0
    elif q and q in title:
        score += 120.0
    score += len(q_tokens & title_tokens) * 16.0
    for token in list(q_tokens)[:8]:
        if token in text:
            score += 1.0
    rank = unit.get("_rank")
    if isinstance(rank, (int, float)):
        score += min(8.0, max(-8.0, -float(rank)))
    return score


def retrieve(plan, question):
    candidates = {}

    for ref in plan.get("explicit_references", []):
        article = str(ref.get("article") or "").strip()
        doc_id = detect_document_from_hint(ref.get("law_hint"))
        candidate_docs = [doc_id] if doc_id else ["BLHS_2025"]
        for candidate in candidate_docs:
            if not candidate:
                continue
            for unit in db.get_article(candidate, article):
                entry = dict(unit)
                entry["_why"] = "explicit_article"
                entry["_score"] = 10000.0
                candidates[entry["id"]] = entry

    queries = list(plan.get("search_queries") or []) or [question]
    if question not in queries:
        queries.append(question)

    for query_index, query in enumerate(queries[:4]):
        fts = _fts_query(query)
        if not fts:
            continue
        found = db.search_fts(fts, limit=max(LEGAL_TOP_K * 2, 12))
        if not found:
            found = db.search_like(query, limit=max(LEGAL_TOP_K * 2, 12))
        for unit in found:
            entry = dict(unit)
            score = _candidate_score(entry, query, query_index)
            existing = candidates.get(entry["id"])
            if existing is None or score > existing.get("_score", -1):
                entry["_why"] = f"search:{query}"
                entry["_score"] = score
                candidates[entry["id"]] = entry

    ranked = sorted(candidates.values(), key=lambda x: x.get("_score", 0), reverse=True)
    return ranked[:LEGAL_TOP_K]


def format_context(units):
    blocks = []
    for unit in units:
        source = (
            f"{unit.get('document_title','')}"
            + (f" ({unit.get('document_number')})" if unit.get("document_number") else "")
        ).strip()
        blocks.append(
            "SOURCE_UNIT_ID: " + unit["id"] + "\n"
            "SOURCE: " + source + "\n"
            "ARTICLE: " + str(unit.get("article") or "") + "\n"
            "TITLE: " + str(unit.get("title") or "") + "\n"
            "TEXT:\n" + str(unit.get("text") or "")
        )
    return "\n\n====================\n\n".join(blocks)
