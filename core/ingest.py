from pathlib import Path
import hashlib
import json
import re
import subprocess

from core import db


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pdf_text(pdf_path):
    pdf_path = Path(pdf_path)
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return proc.stdout.decode("utf-8", errors="replace")
    except Exception:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)


ARTICLE_RE = re.compile(r"(?m)^[ \t]*Điều\s+(\d+[a-zA-Z]?)\.\s*(.*)$")


def split_articles(text, max_article=None):
    matches = list(ARTICLE_RE.finditer(text))
    units = []
    for i, match in enumerate(matches):
        article = match.group(1)
        num_match = re.match(r"\d+", article)
        if max_article and num_match and int(num_match.group()) > max_article:
            break
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        title = match.group(2).strip()
        lines = raw.splitlines()
        heading_parts = [title]
        for line in lines[1:5]:
            s = line.strip()
            if not s:
                continue
            if re.match(r"^(?:\d+\.|[a-zđ]\)|Người nào|Pháp nhân|Bộ luật|Luật này|Trong |Khi |Việc |Không |Có )", s):
                break
            if re.fullmatch(r"\d+", s):
                break
            heading_parts.append(s)
        title = re.sub(r"\s+", " ", " ".join(heading_parts)).strip()
        title = re.sub(r"(?<=\D)\d{1,3}$", "", title).strip()
        units.append({"article": article, "title": title, "text": raw})
    return units


def import_article_index(index_path, document_id, title, source_path, number=None,
                         issuer=None, effective_from=None):
    index_path = Path(index_path)
    data = json.loads(index_path.read_text(encoding="utf-8"))
    articles = data.get("articles", [])
    db.upsert_document({
        "id": document_id, "title": title, "number": number, "issuer": issuer,
        "effective_from": effective_from, "source_path": str(source_path),
        "sha256": sha256_file(source_path),
        "metadata": {
            "ingest_method": "verified_article_index",
            "article_count": len(articles),
            "index_path": str(index_path),
        },
    })
    units = [{
        "id": f"{document_id}:article:{item['article']}",
        "unit_type": "article",
        "article": str(item["article"]),
        "title": item.get("title", ""),
        "text": item.get("raw_text", ""),
        "effective_from": effective_from,
    } for item in articles]
    db.replace_document_units(document_id, units)
    return len(units)
