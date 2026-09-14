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
    replacements = (
        ("vne id", "vneid"), ("vnied", "vneid"), ("vned", "vneid"),
        ("cccd", "can cuoc"), ("dang ki", "dang ky"),
        ("tam chu", "tam tru"), ("thuong chu", "thuong tru"),
        ("li lich", "ly lich"),
    )
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def _has(q, *parts):
    return any(part in q for part in parts)


def _all(q, *parts):
    return all(part in q for part in parts)


def source_index_for_question(question):
    q = norm(question)
    if not q:
        return None

    # Residence sources 1-11. Specific intents always precede generic mentions.
    if _all(q, "xoa", "thuong tru"):
        return 2
    if (_all(q, "tam tru", "gia han") or _all(q, "tam tru", "het han")
            or _all(q, "tam tru", "keo dai") or _has(q, "keo dai thoi han tam tru")):
        return 4
    if _has(q, "tach ho", "tach khau", "tach khoi ho", "tach ra khoi ho") or (_all(q, "tach", "ho") and not _has(q, "ho chieu")):
        return 5
    if (_all(q, "dieu chinh", "cu tru") or _all(q, "sua", "thong tin", "cu tru")
            or (_all(q, "du lieu", "cu tru") and _has(q, "thay doi", "cap nhat"))
            or (_all(q, "thong tin", "cu tru") and _has(q, "thay doi", "cap nhat"))):
        return 6
    # Tạm vắng and lưu trú are narrower than generic "khai báo ... cư trú".
    if _has(q, "tam vang"):
        return 10
    if (_has(q, "thong bao luu tru", "khai bao luu tru", "luu tru qua dem")
            or (_all(q, "co so luu tru", "thong bao") and _has(q, "nguoi o lai", "khach"))):
        return 11
    if _all(q, "khai bao", "thong tin", "cu tru") or (
        "khai bao" in q
        and _has(q, "chua du dieu kien", "khong du dieu kien")
        and _has(q, "thuong tru", "tam tru", "cu tru")
    ):
        return 7
    if _all(q, "xac nhan", "cu tru"):
        return 8
    if (_all(q, "xoa", "tam tru")
            or (_has(q, "khong con o", "khong con sinh song") and "tam tru" in q)
            or (_has(q, "tam tru cu") and "khong con" in q)):
        return 9
    if _has(q, "dang ky thuong tru", "thuong tru", "nhap khau"):
        return 1
    if _has(q, "dang ky tam tru", "tam tru"):
        return 3

    if _has(q, "dang ky xe", "quan ly phuong tien", "bien so", "sang ten xe", "thu hoi dang ky xe", "xe may", "xe mo to", "xe gan may", "xe o to"):
        return 12
    if _has(q, "ho chieu", "xuat nhap canh", "passport", "thi thuc", "visa"):
        return 13
    if _has(q, "nganh nghe", "an ninh trat tu", "giay chung nhan du dieu kien", "cam do", "kinh doanh co dieu kien"):
        return 14
    if _has(q, "vneid", "dinh danh dien tu", "tai khoan dinh danh", "xac thuc dien tu", "dinh danh muc 1", "dinh danh muc 2", "muc do 01", "muc do 02", "muc 1", "muc 2"):
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
