"""Corpus 10.000 câu hỏi để kiểm thử AI Core theo cách người dân nói thật.

Không nhân bản bằng số thứ tự. Mỗi câu gốc được biến đổi thành 10 cách diễn đạt
có cùng ý định: nguyên bản, lịch sự, khẩu ngữ, rút gọn, viết thường, không dấu,
dấu câu nhiễu và lỗi chính tả nhẹ. Nhãn policy/source của câu gốc được giữ nguyên
để đánh giá routing và grounded-answer một cách có oracle.
"""

import re
import unicodedata
from dataclasses import replace

from core.question_corpus import QuestionCase, build_question_corpus


def _lower_first(text):
    text = str(text or "").strip()
    if not text:
        return text
    return text[:1].lower() + text[1:]


def _without_diacritics(text):
    value = unicodedata.normalize("NFD", str(text or ""))
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D")


def _light_typo(text):
    """Lỗi thường gặp nhưng vẫn giữ đủ tín hiệu ngữ nghĩa để router phải hiểu."""
    value = str(text or "")
    replacements = (
        ("đăng ký", "đăng kí"),
        ("Đăng ký", "Đăng kí"),
        ("căn cước", "căn cuoc"),
        ("Căn cước", "Căn cuoc"),
        ("VNeID", "VNeid"),
        ("thường trú", "thuong tru"),
        ("tạm trú", "tam tru"),
        ("chuyển khoản", "chuyen khoan"),
        ("thương tích", "thuong tich"),
    )
    for old, new in replacements:
        if old in value:
            return value.replace(old, new, 1)
    # Với nhóm không có typo mục tiêu, bỏ dấu một cụm đầu để vẫn là câu nhiễu.
    words = value.split()
    if len(words) >= 3:
        words[:3] = _without_diacritics(" ".join(words[:3])).split()
        return " ".join(words)
    return _without_diacritics(value)


def _compact(text):
    value = str(text or "").strip()
    value = re.sub(r"^(Tôi|tôi)\s+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def variants(question):
    q = str(question or "").strip()
    stem = q[:-1].strip() if q.endswith("?") else q
    lower = _lower_first(stem)
    generated = (
        q,
        f"Cho tôi hỏi, {lower}?",
        f"Nhờ hướng dẫn giúp tôi: {stem}?",
        f"Tôi chưa rõ, {lower}?",
        f"Ở xã thì {lower}?",
        f"Cho hỏi nhanh: {_compact(stem)}?",
        f"{stem} ạ?",
        f"{stem.lower()}?",
        _without_diacritics(stem) + "?",
        _light_typo(stem) + "?",
    )
    # Bảo đảm 10 biến thể khác nhau. Nếu một câu hiếm gây trùng, thêm biến thể
    # khẩu ngữ có nội dung, không dùng hậu tố số vô nghĩa.
    result = []
    fallbacks = (
        f"Trường hợp của tôi là: {stem}. Hướng dẫn giúp tôi?",
        f"Tôi đang cần xử lý việc này: {stem}. Làm thế nào?",
        f"Xin chỉ giúp tôi việc {lower}?",
    )
    for candidate in generated + fallbacks:
        normalized = re.sub(r"\s+", " ", candidate).strip()
        if normalized not in result:
            result.append(normalized)
        if len(result) == 10:
            break
    if len(result) != 10:
        raise AssertionError(f"Không tạo đủ 10 biến thể cho: {q}")
    return tuple(result)


def build_question_corpus_10000():
    base = build_question_corpus()
    cases = []
    for base_case in base:
        for variant_index, question in enumerate(variants(base_case.question), start=1):
            cases.append(replace(
                base_case,
                case_id=f"{base_case.case_id}-N{variant_index:02d}",
                question=question,
            ))
    assert len(cases) == 10000
    assert len({case.question for case in cases}) == 10000
    return tuple(cases)
