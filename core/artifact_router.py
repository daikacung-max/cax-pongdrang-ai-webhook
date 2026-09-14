"""Deterministic router for the 19-source user artifact.

The router answers one question only: which source of the user's Notebook should
own the current citizen message? It does not decide legal truth. Current-law
verification remains a separate layer.
"""

import re
import unicodedata

from core.notebook_manifest import SOURCES


def norm(text):
    value = unicodedata.normalize("NFD", str(text or "").lower())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = value.replace("đ", "d")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return (
        value.replace("vne id", "vneid")
        .replace("vnied", "vneid")
        .replace("vned", "vneid")
        .replace("cccd", "can cuoc")
    )


def _has(q, *parts):
    return any(part in q for part in parts)


def source_index_for_question(question):
    q = norm(question)
    if not q:
        return None

    # Residence sub-procedures must be checked before broad "tạm trú/thường trú".
    if _has(q, "xoa dang ky thuong tru", "xoa thuong tru"):
        return 2
    if _has(q, "gia han tam tru", "keo dai tam tru"):
        return 4
    if _has(q, "tach ho", "tach khau"):
        return 5
    if _has(q, "dieu chinh thong tin cu tru", "dieu chinh tt ve ct", "sua thong tin cu tru"):
        return 6
    if _has(q, "khai bao thong tin ve cu tru", "khai bao tt ve ct", "khai bao cu tru"):
        return 7
    if _has(q, "xac nhan thong tin cu tru", "xac nhan cu tru", "xac nhan tt ve ct"):
        return 8
    if _has(q, "xoa dang ky tam tru", "xoa tam tru"):
        return 9
    if _has(q, "khai bao tam vang", "tam vang"):
        return 10
    if _has(q, "thong bao luu tru", "khai bao luu tru", "luu tru qua dem"):
        return 11
    if _has(q, "dang ky thuong tru", "thuong tru", "nhap khau"):
        return 1
    if _has(q, "dang ky tam tru", "tam tru"):
        return 3

    # Other artifact source groups.
    if _has(q, "dang ky xe", "quan ly phuong tien", "bien so", "sang ten xe", "thu hoi dang ky xe", "xe may", "xe mo to", "xe gan may", "xe o to"):
        return 12
    if _has(q, "ho chieu", "xuat nhap canh", "passport", "thi thuc", "visa"):
        return 13
    if _has(q, "nganh nghe", "an ninh trat tu", "giay chung nhan du dieu kien", "cam do", "kinh doanh co dieu kien"):
        return 14
    if _has(q, "vneid", "dinh danh dien tu", "tai khoan dinh danh", "xac thuc dien tu", "dinh danh muc 1", "dinh danh muc 2", "muc do 01", "muc do 02"):
        return 15
    if _has(q, "can cuoc", "the can cuoc", "can cuoc cong dan", "du lieu can cuoc"):
        return 16
    if _has(q, "vu khi", "vat lieu no", "cong cu ho tro", "ccht", "phao", "giay phep su dung cong cu"):
        return 17
    if _has(q, "ly lich tu phap", "phieu ly lich tu phap", "phieu tu phap"):
        return 18
    if _has(q, "giay phep lai xe", "gplx", "sat hach lai xe", "sat hach", "cap lai bang lai", "doi bang lai"):
        return 19
    return None


def source_for_question(question):
    index = source_index_for_question(question)
    if index is None:
        return None
    return dict(SOURCES[index - 1])


def source_id_for_question(question):
    source = source_for_question(question)
    return source.get("id") if source else None
