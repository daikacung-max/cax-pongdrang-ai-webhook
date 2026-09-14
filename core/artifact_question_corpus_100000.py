"""100,000 distinct citizen questions rooted in the 19-source user artifact.

The corpus has 1,000 semantic seeds distributed across all 19 sources. Each seed
is rendered in 100 natural/colloquial/noisy forms. No numeric suffix is used to
fake uniqueness; source intent remains the oracle.
"""

import re
import unicodedata
from dataclasses import dataclass

from core.notebook_manifest import SOURCES


@dataclass(frozen=True)
class ArtifactQuestionCase:
    case_id: str
    source_index: int
    source_id: str
    source_title: str
    question: str


STEMS = {
    1: (
        "Tôi muốn đăng ký thường trú thì làm thế nào",
        "Đăng ký thường trú cần chuẩn bị những gì",
        "Tôi muốn làm thường trú trực tuyến qua VNeID",
        "Thường trú nộp ở đâu và xử lý ra sao",
        "Nhập thường trú cho người thân cần hướng dẫn",
    ),
    2: (
        "Tôi muốn xóa đăng ký thường trú",
        "Xóa thường trú thực hiện như thế nào",
        "Khi nào cần làm thủ tục xóa đăng ký thường trú",
        "Tôi cần hướng dẫn xóa thường trú của mình",
        "Xóa đăng ký thường trú có làm trực tuyến được không",
    ),
    3: (
        "Tôi muốn đăng ký tạm trú",
        "Đăng ký tạm trú cần chuẩn bị gì",
        "Tạm trú làm trực tuyến thế nào",
        "Tôi đang thuê nhà và muốn làm tạm trú",
        "Đăng ký tạm trú tại Công an xã ra sao",
    ),
    4: (
        "Tôi muốn gia hạn tạm trú",
        "Tạm trú sắp hết hạn thì gia hạn thế nào",
        "Gia hạn tạm trú cần thực hiện ở đâu",
        "Tôi cần hướng dẫn kéo dài thời hạn tạm trú",
        "Gia hạn tạm trú có thể làm trực tuyến không",
    ),
    5: (
        "Tôi muốn làm thủ tục tách hộ",
        "Tách hộ cần điều kiện gì",
        "Tôi muốn tách khỏi hộ hiện tại",
        "Thủ tục tách hộ thực hiện ở đâu",
        "Tách hộ trực tuyến có được không",
    ),
    6: (
        "Tôi cần điều chỉnh thông tin về cư trú",
        "Thông tin cư trú của tôi bị sai thì sửa thế nào",
        "Tôi muốn sửa thông tin trong dữ liệu cư trú",
        "Điều chỉnh thông tin cư trú thực hiện ở đâu",
        "Dữ liệu cư trú có thay đổi thì cập nhật ra sao",
    ),
    7: (
        "Tôi cần khai báo thông tin về cư trú",
        "Khai báo thông tin cư trú thực hiện như thế nào",
        "Tôi chưa đủ điều kiện đăng ký thường trú tạm trú thì khai báo ra sao",
        "Tôi muốn hỏi thủ tục khai báo thông tin về cư trú",
        "Khai báo thông tin cư trú có làm trực tuyến được không",
    ),
    8: (
        "Tôi muốn xin xác nhận thông tin về cư trú",
        "Xác nhận cư trú làm thế nào",
        "Tôi cần giấy xác nhận thông tin cư trú",
        "Xác nhận thông tin cư trú thực hiện ở đâu",
        "Tôi muốn xác nhận cư trú trực tuyến",
    ),
    9: (
        "Tôi muốn xóa đăng ký tạm trú",
        "Xóa tạm trú thực hiện thế nào",
        "Tôi không còn ở nơi tạm trú cũ thì cần làm gì",
        "Tôi cần hướng dẫn thủ tục xóa tạm trú",
        "Xóa đăng ký tạm trú có làm trực tuyến được không",
    ),
    10: (
        "Tôi cần khai báo tạm vắng",
        "Khai báo tạm vắng thực hiện thế nào",
        "Tôi đi khỏi nơi cư trú thì khai báo tạm vắng ra sao",
        "Tạm vắng có thể khai báo trực tuyến không",
        "Tôi muốn hỏi nơi tiếp nhận khai báo tạm vắng",
    ),
    11: (
        "Tôi cần thông báo lưu trú",
        "Thông báo lưu trú cho khách thực hiện thế nào",
        "Có người ở lại qua đêm thì thông báo lưu trú ra sao",
        "Tôi muốn khai báo lưu trú trực tuyến",
        "Cơ sở lưu trú thông báo người ở lại bằng cách nào",
    ),
    12: (
        "Tôi mua xe mới và muốn đăng ký xe",
        "Đăng ký xe máy lần đầu thực hiện thế nào",
        "Tôi muốn sang tên xe máy",
        "Tôi cần làm biển số xe",
        "Thu hồi giấy đăng ký xe trước khi chuyển nhượng làm sao",
    ),
    13: (
        "Tôi muốn làm hộ chiếu phổ thông",
        "Tôi bị mất hộ chiếu thì cần làm gì",
        "Hộ chiếu phổ thông cấp lại thế nào",
        "Tôi muốn hỏi thủ tục xuất nhập cảnh",
        "Làm hộ chiếu trực tuyến thực hiện ra sao",
    ),
    14: (
        "Tôi muốn xin giấy chứng nhận đủ điều kiện về an ninh trật tự",
        "Mở cơ sở cầm đồ cần thủ tục an ninh trật tự gì",
        "Ngành nghề kinh doanh có điều kiện về an ninh trật tự làm thế nào",
        "Tôi muốn hỏi thủ tục quản lý ngành nghề kinh doanh",
        "Giấy chứng nhận an ninh trật tự nộp ở đâu",
    ),
    15: (
        "Tôi muốn làm định danh điện tử mức 2",
        "Đăng ký VNeID mức độ 02 thực hiện thế nào",
        "Tôi cần tài khoản định danh điện tử",
        "VNeID mức 2 làm ở đâu",
        "Tôi muốn hỏi về xác thực điện tử trên VNeID",
    ),
    16: (
        "Tôi muốn làm thẻ căn cước",
        "Tôi bị mất căn cước cần cấp lại",
        "Con tôi dưới 14 tuổi cần làm căn cước",
        "Tôi muốn cấp đổi thẻ căn cước",
        "Thông tin trên căn cước thay đổi thì xử lý thế nào",
    ),
    17: (
        "Tôi muốn hỏi thủ tục về công cụ hỗ trợ",
        "Cơ quan tôi cần giấy phép sử dụng công cụ hỗ trợ",
        "Tôi muốn hỏi quy định quản lý vũ khí",
        "Thủ tục liên quan vật liệu nổ thực hiện thế nào",
        "Tôi cần hỏi quản lý vũ khí vật liệu nổ công cụ hỗ trợ",
    ),
    18: (
        "Tôi muốn xin phiếu lý lịch tư pháp",
        "Phiếu lý lịch tư pháp làm thế nào",
        "Tôi cần cấp lý lịch tư pháp cho bản thân",
        "Xin phiếu lý lịch tư pháp trực tuyến được không",
        "Lý lịch tư pháp nộp ở đâu",
    ),
    19: (
        "Tôi muốn hỏi thủ tục sát hạch giấy phép lái xe",
        "Cấp giấy phép lái xe sau sát hạch thế nào",
        "Tôi cần hỏi về GPLX",
        "Sát hạch lái xe thực hiện ra sao",
        "Tôi muốn hỏi cấp lại giấy phép lái xe",
    ),
}

CONTEXTS = (
    "cho bản thân tôi",
    "cho người thân trong gia đình",
    "khi tôi đang ở xã Pơng Drang",
    "nếu tôi muốn làm trực tiếp",
    "nếu tôi muốn làm trực tuyến",
    "nếu tôi sử dụng VNeID",
    "khi tôi muốn chuẩn bị trước hồ sơ",
    "trong trường hợp thông tin đã có trên hệ thống",
    "khi tôi chưa biết cơ quan tiếp nhận",
    "khi tôi cần biết thời hạn giải quyết",
    "khi tôi cần biết các bước thực hiện",
)

PREFIXES = (
    "",
    "Cho tôi hỏi, ",
    "Nhờ hướng dẫn giúp tôi, ",
    "Tôi chưa rõ việc này: ",
    "Cho hỏi nhanh, ",
    "Xin hướng dẫn, ",
    "Tôi đang cần biết: ",
    "Người dân hỏi rằng: ",
    "Ở xã tôi muốn hỏi: ",
    "Phiền hướng dẫn giúp: ",
)

SUFFIXES = (
    "?",
    " ạ?",
    ", tôi cần làm gì?",
    ", hướng dẫn từng bước giúp tôi?",
    ", tôi nên bắt đầu từ đâu?",
    ", cần chuẩn bị như thế nào?",
    ", có làm online được không?",
    ", cơ quan nào tiếp nhận?",
    ", thời hạn giải quyết ra sao?",
    ", nếu thiếu thông tin thì xử lý thế nào?",
)


def _without_diacritics(text):
    value = unicodedata.normalize("NFD", text)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D")


def _light_typo(text):
    replacements = (
        ("đăng ký", "đăng kí"),
        ("thường trú", "thuong trú"),
        ("tạm trú", "tạm chú"),
        ("căn cước", "căn cuoc"),
        ("VNeID", "VNeid"),
        ("hộ chiếu", "hộ chieu"),
        ("lý lịch", "lí lịch"),
        ("giấy phép", "giay phép"),
    )
    for old, new in replacements:
        if old in text:
            return text.replace(old, new, 1)
    return text


def _style(text, style):
    if style == 1:
        return text.lower()
    if style == 2:
        return _without_diacritics(text)
    if style == 3:
        return _light_typo(text)
    if style == 4:
        return re.sub(r"\s+", " ", text).replace(",", "")
    if style == 5:
        return text.replace("Tôi", "mình", 1).replace("tôi", "mình", 1)
    if style == 6:
        return text.replace("thực hiện", "làm", 1)
    if style == 7:
        return text.replace("như thế nào", "sao", 1)
    if style == 8:
        return text.replace("cần", "cần phải", 1)
    if style == 9:
        return text.replace("muốn", "đang muốn", 1)
    return text


def _semantic_seeds():
    seeds = []
    # Context -> stem -> source is deliberate round-robin distribution so all
    # 19 artifact sources receive nearly the same number of semantic seeds.
    for context in CONTEXTS:
        for stem_index in range(5):
            for source_index in range(1, 20):
                source = SOURCES[source_index - 1]
                question = f"{STEMS[source_index][stem_index]} {context}?"
                seeds.append((source_index, source, question))
                if len(seeds) == 1000:
                    return tuple(seeds)
    raise AssertionError("Không tạo đủ 1.000 semantic seed")


def build_artifact_question_corpus_100000():
    cases = []
    for seed_index, (source_index, source, seed) in enumerate(_semantic_seeds(), start=1):
        stem = seed[:-1] if seed.endswith("?") else seed
        for prefix_index, prefix in enumerate(PREFIXES):
            for suffix_index, suffix in enumerate(SUFFIXES):
                style = (prefix_index + suffix_index) % 10
                question = _style(prefix + stem + suffix, style)
                question = re.sub(r"\s+", " ", question).strip()
                cases.append(ArtifactQuestionCase(
                    case_id=f"AQ{seed_index:04d}-{prefix_index}{suffix_index}",
                    source_index=source_index,
                    source_id=source["id"],
                    source_title=source["title"],
                    question=question,
                ))
    assert len(cases) == 100000
    assert len({case.case_id for case in cases}) == 100000
    assert len({case.question for case in cases}) == 100000
    return tuple(cases)
