"""Kho tri thức hiện hành cho CAX Pơng Drang AI Core.

Nguyên tắc:
- chỉ nguồn chính thức/đã kiểm chứng;
- TTHC phục vụ người dân chỉ dùng cấp xã và cấp tỉnh;
- nguồn bị thay thế được expire, không xóa để còn audit;
- nguồn chưa đến ngày hiệu lực có thể được đăng ký nhưng DB sẽ tự loại khỏi retrieval.

Snapshot kiểm tra: 2026-09-12.
"""

from core import db

CHECKED = "2026-09-12"


def _doc(doc_id, title, number, issuer, source_path, *, effective_from=None,
         effective_to=None, authority_levels=None, status="active", supersedes=None):
    db.upsert_document({
        "id": doc_id,
        "title": title,
        "number": number,
        "issuer": issuer,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "source_path": source_path,
        "sha256": None,
        "metadata": {
            "checked": CHECKED,
            "official": True,
            "status": status,
            "authority_levels": authority_levels or [],
            "supersedes": supersedes or [],
            "knowledge_mode": "source_grounded",
        },
    })


def ensure_current_knowledge():
    # ------------------------------------------------------------------
    # A. CĂN CƯỚC - QĐ 5230/QĐ-BCA-C06 NGÀY 18/08/2026
    # ------------------------------------------------------------------
    # QĐ 5230 công bố thủ tục gộp mới và bãi bỏ các thủ tục tách riêng cũ.
    # Đóng các snapshot cũ trước ngày quyết định có hiệu lực áp dụng.
    for old_id in (
        "CITIZEN_ID_UNDER14_2026",
        "CITIZEN_ID_REISSUE_PROVINCIAL_2026",
        "CITIZEN_ID_OVER14_PROVINCIAL_2026",
        "CITIZEN_ID_RENEWAL_PROVINCIAL_2026",
    ):
        db.expire_document(old_id, "2026-08-17")

    _doc(
        "CITIZEN_ID_5230_COMMUNE_2026",
        "Cấp, cấp đổi, cấp lại thẻ căn cước và TTHC căn cước tại Công an cấp xã",
        "5230/QĐ-BCA-C06",
        "Bộ Công an",
        "https://bocongan.gov.vn/chinh-sach-phap-luat/bai-viet/cong-bo-thu-tuc-hanh-chinh-moi-ban-hanh-thu-tuc-hanh-chinh-duoc-sua-doi-bo-sung-va-bai-bo-thuoc-tham-quyen-giai-quyet-cua-bo-cong-an-1787732411",
        effective_from="2026-08-18",
        authority_levels=["xa"],
        supersedes=[
            "cấp thẻ căn cước dưới 14 tuổi - thủ tục tách riêng",
            "cấp thẻ căn cước từ đủ 14 tuổi - thủ tục tách riêng",
            "cấp đổi thẻ căn cước - thủ tục tách riêng",
            "cấp lại thẻ căn cước - thủ tục tách riêng",
        ],
    )
    db.replace_document_units("CITIZEN_ID_5230_COMMUNE_2026", [
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:scope",
            "unit_type": "procedure",
            "title": "Thủ tục căn cước đang thực hiện tại Công an cấp xã",
            "effective_from": "2026-08-18",
            "text": (
                "Quyết định 5230/QĐ-BCA-C06 ngày 18/08/2026 công bố thủ tục mới 'Cấp, cấp đổi, cấp lại thẻ căn cước' "
                "thực hiện tại cấp xã. Đồng thời công bố tại cấp xã các thủ tục khai thác thông tin trong Cơ sở dữ liệu quốc gia về dân cư, "
                "khai thác thông tin trong Cơ sở dữ liệu căn cước, thu thập/cập nhật thông tin sinh trắc học ADN và giọng nói, và thủ tục đối với "
                "người gốc Việt Nam chưa xác định được quốc tịch. Các thủ tục tách riêng trước đây về cấp thẻ dưới 14 tuổi, từ đủ 14 tuổi, cấp đổi, "
                "cấp lại ở cấp xã được bãi bỏ để thay bằng thủ tục mới gộp."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:first_issue_14plus",
            "unit_type": "procedure",
            "title": "Cấp thẻ căn cước cho người từ đủ 14 tuổi tại Công an cấp xã",
            "effective_from": "2026-08-18",
            "text": (
                "Người từ đủ 14 tuổi có thể thực hiện thủ tục cấp thẻ căn cước trực tiếp tại Công an cấp xã hoặc Bộ phận một cửa cấp xã trong cả nước "
                "không phụ thuộc nơi cư trú (nếu đã triển khai). Có thể đăng ký thời gian, địa điểm qua Cổng dịch vụ công quốc gia hoặc ứng dụng VNeID. "
                "Cán bộ khai thác dữ liệu dân cư để lập hồ sơ; nếu dữ liệu chưa có hoặc cần điều chỉnh thì phải thu thập/cập nhật/điều chỉnh trước khi cấp thẻ. "
                "Thời hạn giải quyết thủ tục cấp, cấp đổi, cấp lại thẻ căn cước không quá 07 ngày làm việc."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:under14",
            "unit_type": "procedure",
            "title": "Cấp thẻ căn cước cho người dưới 14 tuổi tại Công an cấp xã",
            "effective_from": "2026-08-18",
            "text": (
                "Người từ đủ 06 tuổi đến dưới 14 tuổi thực hiện trực tiếp tại Công an cấp xã, người đại diện hợp pháp đưa người dưới 14 tuổi đến làm thủ tục. "
                "Đối với người dưới 06 tuổi, người đại diện hợp pháp có thể nộp trực tuyến toàn trình qua Cổng dịch vụ công quốc gia hoặc VNeID; hồ sơ được chuyển "
                "đến Công an cấp xã nơi người dưới 06 tuổi cư trú để xem xét, giải quyết. Thời hạn chung không quá 07 ngày làm việc."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:renewal",
            "unit_type": "procedure",
            "title": "Cấp đổi thẻ căn cước tại Công an cấp xã",
            "effective_from": "2026-08-18",
            "text": (
                "Công dân có thể đề nghị cấp đổi thẻ căn cước trực tiếp tại Công an cấp xã hoặc Bộ phận một cửa cấp xã trong cả nước không phụ thuộc nơi cư trú "
                "(nếu đã triển khai), hoặc đăng ký thời gian, địa điểm qua Cổng dịch vụ công quốc gia/VNeID. Trường hợp thông tin thay đổi phải thực hiện điều chỉnh "
                "dữ liệu trước khi cấp đổi. Thời hạn giải quyết không quá 07 ngày làm việc."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:reissue",
            "unit_type": "procedure",
            "title": "Cấp lại thẻ căn cước tại Công an cấp xã",
            "effective_from": "2026-08-18",
            "text": (
                "Công dân có thể đề nghị cấp lại thẻ căn cước trực tiếp tại Công an cấp xã hoặc Bộ phận một cửa cấp xã trong cả nước không phụ thuộc nơi cư trú "
                "(nếu đã triển khai). Trường hợp cấp lại do mất thẻ hoặc thẻ hư hỏng không sử dụng được có thể nộp hồ sơ trực tuyến toàn trình qua Cổng dịch vụ công "
                "quốc gia hoặc VNeID; cơ quan tiếp nhận sử dụng thông tin sinh trắc học và dữ liệu căn cước đã thu nhận gần nhất theo quy định. Thời hạn giải quyết "
                "không quá 07 ngày làm việc."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:fees",
            "unit_type": "procedure",
            "title": "Lệ phí cấp, cấp đổi, cấp lại thẻ căn cước theo QĐ 5230",
            "effective_from": "2026-08-18",
            "text": (
                "Cấp thẻ căn cước và cấp đổi do thay đổi địa giới hành chính được miễn phí. Mức lệ phí gốc cấp đổi là 50.000 đồng/thẻ, cấp lại là 70.000 đồng/thẻ. "
                "Từ 01/07/2025 đến hết 31/12/2026, mức thu cấp đổi/cấp lại bằng 50% mức nêu trên. Từ 15/08/2026 đến hết 28/02/2027, công dân đáp ứng điều kiện "
                "tài khoản định danh điện tử mức độ 2 và tích hợp đủ loại thông tin theo chính sách được miễn lệ phí khi đăng ký cấp đổi/cấp lại qua dịch vụ công trực tuyến."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:data_extract",
            "unit_type": "procedure",
            "title": "Khai thác thông tin dân cư tại Công an cấp xã",
            "effective_from": "2026-08-18",
            "text": (
                "Cơ quan, tổ chức, cá nhân thuộc trường hợp luật định có thể đề nghị khai thác thông tin trong Cơ sở dữ liệu quốc gia về dân cư tại Công an cấp xã. "
                "Đối với khai thác thông tin của công dân, hồ sơ trực tuyến có thể thực hiện qua Cổng dịch vụ công quốc gia hoặc VNeID theo điều kiện luật định. "
                "Thời hạn giải quyết là 03 ngày làm việc."
            ),
        },
        {
            "id": "CITIZEN_ID_5230_COMMUNE_2026:other_commune_procedures",
            "unit_type": "procedure",
            "title": "Các thủ tục căn cước khác tại cấp xã theo QĐ 5230",
            "effective_from": "2026-08-18",
            "text": (
                "QĐ 5230 còn công bố ở cấp xã việc khai thác thông tin trong Cơ sở dữ liệu căn cước; thu thập, cập nhật thông tin sinh trắc học ADN, giọng nói; "
                "thu thập, cập nhật, điều chỉnh thông tin của người gốc Việt Nam chưa xác định được quốc tịch vào Cơ sở dữ liệu quốc gia về dân cư, Cơ sở dữ liệu căn cước "
                "và cấp/cấp đổi/cấp lại giấy chứng nhận căn cước. Hai thủ tục được sửa đổi, bổ sung gồm điều chỉnh thông tin trong Cơ sở dữ liệu quốc gia về dân cư "
                "theo đề nghị của công dân và tích hợp, cập nhật, điều chỉnh thông tin trên thẻ căn cước."
            ),
        },
    ])

    # ------------------------------------------------------------------
    # B. CƯ TRÚ HIỆN HÀNH TỪ 01/07/2026
    # ------------------------------------------------------------------
    _doc(
        "RESIDENCE_CURRENT_2026",
        "Luật Cư trú đã sửa đổi và Thông tư 116/2026/TT-BCA",
        "Luật 68/2020/QH14; Luật 118/2025/QH15; 116/2026/TT-BCA",
        "Quốc hội / Bộ Công an",
        "https://vanban.bocongan.gov.vn/co-so-du-lieu-van-ban/thong-tu-quy-dinh-chi-tiet-mot-so-dieu-va-bien-phap-thi-hanh-luat-cu-tru-1784261073",
        effective_from="2026-07-01",
        authority_levels=["xa"],
    )
    db.replace_document_units("RESIDENCE_CURRENT_2026", [
        {
            "id": "RESIDENCE_CURRENT_2026:data_reuse",
            "unit_type": "guidance",
            "title": "Tái sử dụng dữ liệu trong thủ tục cư trú",
            "effective_from": "2026-07-01",
            "text": (
                "Từ 01/07/2026, khi thông tin, giấy tờ chứng minh điều kiện đăng ký cư trú đã được kết nối, chia sẻ hoặc khai thác từ cơ sở dữ liệu, hệ thống thông tin "
                "hoặc VNeID thì cơ quan đăng ký cư trú không yêu cầu công dân nộp hoặc xuất trình lại. Công an cấp xã là cơ quan đăng ký cư trú trực tiếp phục vụ người dân."
            ),
        },
        {
            "id": "RESIDENCE_CURRENT_2026:temporary",
            "unit_type": "procedure",
            "title": "Đăng ký tạm trú tại Công an cấp xã",
            "effective_from": "2026-07-01",
            "text": "Đăng ký tạm trú thực hiện tại Công an cấp xã hoặc trực tuyến; thời hạn giải quyết 03 ngày làm việc khi hồ sơ hợp lệ. Thành phần hồ sơ phải xác định theo trường hợp cụ thể và dữ liệu đã khai thác được.",
        },
        {
            "id": "RESIDENCE_CURRENT_2026:permanent",
            "unit_type": "procedure",
            "title": "Đăng ký thường trú tại Công an cấp xã",
            "effective_from": "2026-07-01",
            "text": "Đăng ký thường trú thực hiện tại Công an cấp xã hoặc trực tuyến; thời hạn giải quyết 07 ngày làm việc. Điều kiện và thành phần hồ sơ phụ thuộc chỗ ở, quan hệ với chủ hộ/chủ sở hữu và dữ liệu đã có, không có một bộ giấy tờ cố định cho mọi trường hợp.",
        },
        {
            "id": "RESIDENCE_CURRENT_2026:confirmation",
            "unit_type": "procedure",
            "title": "Xác nhận thông tin về cư trú",
            "effective_from": "2026-07-01",
            "text": (
                "Xác nhận thông tin về cư trú thực hiện tại cơ quan đăng ký cư trú/Công an cấp xã hoặc trực tuyến. Nếu thông tin đã có trong Cơ sở dữ liệu quốc gia về dân cư thì "
                "thời hạn giải quyết không quá 1/2 ngày làm việc; nếu cần xác minh thì không quá 03 ngày làm việc."
            ),
        },
    ])

    # ------------------------------------------------------------------
    # C. ĐĂNG KÝ XE - CHUỖI VĂN BẢN HIỆN HÀNH, CẤP TỈNH/CẤP XÃ
    # ------------------------------------------------------------------
    _doc(
        "VEHICLE_CURRENT_2026",
        "Đăng ký, quản lý xe - quy định hiện hành đến 12/09/2026",
        "79/2024/TT-BCA; 13/2025/TT-BCA; 51/2025/TT-BCA; 37/2026/TT-BCA",
        "Bộ Công an",
        "https://vanban.bocongan.gov.vn/co-so-du-lieu-van-ban/thong-tu-sua-doi-bo-sung-mot-so-dieu-cua-cac-thong-tu-quy-dinh-ve-dang-ky-kiem-dinh-phuong-tien-1778226403",
        effective_from="2026-06-08",
        authority_levels=["xa", "tinh"],
    )
    db.replace_document_units("VEHICLE_CURRENT_2026", [
        {
            "id": "VEHICLE_CURRENT_2026:authority",
            "unit_type": "procedure",
            "title": "Cơ quan đăng ký xe hiện hành",
            "effective_from": "2026-06-08",
            "text": (
                "Thủ tục đăng ký xe hiện hành được tổ chức tại cơ quan đăng ký xe cấp tỉnh và cấp xã theo phân cấp. Khi hướng dẫn người dân trong mô hình chính quyền hiện tại, "
                "AI Core chỉ sử dụng cấp tỉnh và cấp xã; không hướng dẫn đến Công an cấp huyện theo các trang thủ tục cũ còn lưu trên hệ thống."
            ),
        },
        {
            "id": "VEHICLE_CURRENT_2026:first_domestic_online",
            "unit_type": "procedure",
            "title": "Đăng ký lần đầu trực tuyến toàn trình xe sản xuất, lắp ráp trong nước",
            "effective_from": "2026-06-08",
            "text": (
                "Thủ tục 1.012575 đăng ký xe lần đầu trực tuyến toàn trình đối với xe sản xuất, lắp ráp trong nước do cơ quan đăng ký xe cấp tỉnh, cấp xã thực hiện theo phân cấp. "
                "Chủ xe kê khai trên Cổng dịch vụ công hoặc VNeID; thời hạn cấp chứng nhận đăng ký xe, cấp mới biển số xe không quá 02 ngày làm việc kể từ khi nhận đủ hồ sơ hợp lệ."
            ),
        },
        {
            "id": "VEHICLE_CURRENT_2026:legal_chain",
            "unit_type": "guidance",
            "title": "Văn bản đăng ký xe đang áp dụng",
            "effective_from": "2026-06-08",
            "text": (
                "Thông tư 79/2024/TT-BCA là văn bản nền về đăng ký xe, được sửa đổi/bổ sung bởi các Thông tư 13/2025/TT-BCA, 51/2025/TT-BCA và 37/2026/TT-BCA. "
                "Thông tư 37/2026/TT-BCA có hiệu lực từ 08/06/2026 và còn hiệu lực tại ngày 12/09/2026."
            ),
        },
    ])

    # ------------------------------------------------------------------
    # D. NGUỒN PHÁP LUẬT NỀN ĐANG HIỆU LỰC TRONG PHẠM VI AI CORE
    # ------------------------------------------------------------------
    _doc(
        "BLTTHS_104_VBHN_2025",
        "Bộ luật Tố tụng hình sự - Văn bản hợp nhất",
        "104/VBHN-VPQH",
        "Văn phòng Quốc hội",
        "https://vanban.chinhphu.vn/?docid=215223&pageid=27160",
        authority_levels=["xa", "tinh"],
    )
    db.replace_document_units("BLTTHS_104_VBHN_2025", [
        {
            "id": "BLTTHS_104_VBHN_2025:article:145",
            "unit_type": "article",
            "article": "145",
            "title": "Trách nhiệm tiếp nhận và thẩm quyền giải quyết tố giác, tin báo về tội phạm, kiến nghị khởi tố",
            "text": "Điều 145 quy định mọi tố giác, tin báo về tội phạm, kiến nghị khởi tố phải được tiếp nhận đầy đủ, giải quyết kịp thời; cơ quan, tổ chức có trách nhiệm tiếp nhận không được từ chối tiếp nhận.",
        },
        {
            "id": "BLTTHS_104_VBHN_2025:article:146",
            "unit_type": "article",
            "article": "146",
            "title": "Thủ tục tiếp nhận tố giác, tin báo về tội phạm, kiến nghị khởi tố",
            "text": "Điều 146 quy định về thủ tục tiếp nhận tố giác, tin báo về tội phạm, kiến nghị khởi tố; Công an cấp xã có trách nhiệm tiếp nhận, lập biên bản và thực hiện xử lý ban đầu theo thẩm quyền, chuyển cơ quan có thẩm quyền theo quy định.",
        },
    ])

    _doc(
        "XLVPHC_90_VBHN_2026",
        "Luật Xử lý vi phạm hành chính - Văn bản hợp nhất",
        "90/VBHN-VPQH",
        "Văn phòng Quốc hội",
        "https://vanban.chinhphu.vn/?docid=217377&pageid=27160",
        authority_levels=["xa", "tinh"],
    )
    db.replace_document_units("XLVPHC_90_VBHN_2026", [
        {
            "id": "XLVPHC_90_VBHN_2026:article:134",
            "unit_type": "article",
            "article": "134",
            "title": "Nguyên tắc xử lý người chưa thành niên vi phạm hành chính",
            "text": "Điều 134 Luật Xử lý vi phạm hành chính quy định các nguyên tắc riêng khi xử lý người chưa thành niên, bảo đảm lợi ích tốt nhất, giáo dục, giúp đỡ sửa chữa sai lầm và bảo vệ bí mật riêng tư theo quy định.",
        },
    ])

    _doc(
        "PCTMT_120_2025",
        "Luật Phòng, chống ma túy",
        "120/2025/QH15",
        "Quốc hội",
        "https://vanban.chinhphu.vn/?docid=216502&pageid=27160",
        effective_from="2026-07-01",
        authority_levels=["xa", "tinh"],
    )
    db.replace_document_units("PCTMT_120_2025", [
        {
            "id": "PCTMT_120_2025:status",
            "unit_type": "source_registry",
            "title": "Tình trạng hiệu lực Luật Phòng, chống ma túy 120/2025/QH15",
            "effective_from": "2026-07-01",
            "text": "Luật Phòng, chống ma túy số 120/2025/QH15 có hiệu lực từ 01/07/2026 và là nguồn luật nền đang áp dụng trong AI Core tại ngày kiểm tra 12/09/2026.",
        },
    ])

    _doc(
        "ND282_2025_CURRENT",
        "Nghị định xử phạt vi phạm hành chính trong lĩnh vực an ninh, trật tự, an toàn xã hội và lĩnh vực liên quan",
        "282/2025/NĐ-CP",
        "Chính phủ",
        "https://vanban.chinhphu.vn/?classid=1&docid=215770&pageid=27160",
        effective_from="2025-12-15",
        authority_levels=["xa", "tinh"],
    )
    db.replace_document_units("ND282_2025_CURRENT", [
        {
            "id": "ND282_2025_CURRENT:status",
            "unit_type": "source_registry",
            "title": "Tình trạng hiệu lực Nghị định 282/2025/NĐ-CP",
            "effective_from": "2025-12-15",
            "text": "Nghị định 282/2025/NĐ-CP có hiệu lực từ 15/12/2025 và là nguồn xử phạt hành chính chuyên ngành được AI Core sử dụng khi có điều khoản cụ thể đã được nạp và kiểm chứng.",
        },
    ])

    _doc(
        "SANCTION_AUTHORITY_02_VBHN_2026",
        "Quy định chi tiết Luật Xử lý vi phạm hành chính về thẩm quyền xử phạt vi phạm hành chính - văn bản hợp nhất",
        "02/2026/VBHN-NĐ-BTP",
        "Bộ Tư pháp",
        "https://vanban.chinhphu.vn/?classid=0&docid=219251&pageid=27160",
        effective_from="2026-08-21",
        authority_levels=["xa", "tinh"],
    )
    db.replace_document_units("SANCTION_AUTHORITY_02_VBHN_2026", [
        {
            "id": "SANCTION_AUTHORITY_02_VBHN_2026:status",
            "unit_type": "source_registry",
            "title": "Nguồn hiện hành về thẩm quyền xử phạt vi phạm hành chính",
            "effective_from": "2026-08-21",
            "text": "Văn bản hợp nhất 02/2026/VBHN-NĐ-BTP ngày 21/08/2026 là nguồn hợp nhất hiện hành về thẩm quyền xử phạt vi phạm hành chính. Khi tư vấn phải đối chiếu đúng chức danh, lĩnh vực và mức thẩm quyền cụ thể; không suy diễn chỉ từ cấp hành chính.",
        },
    ])

    # Nguồn tương lai: đăng ký để audit nhưng DB active-date gate không cho retrieval
    # trước 26/09/2026.
    _doc(
        "ND311_2026_FUTURE",
        "Sửa đổi Nghị định 189/2025/NĐ-CP về thẩm quyền xử phạt vi phạm hành chính",
        "311/2026/NĐ-CP",
        "Chính phủ",
        "https://vanban.chinhphu.vn/?docid=218998&pageid=27160",
        effective_from="2026-09-26",
        authority_levels=["xa", "tinh"],
        status="future",
    )
    db.replace_document_units("ND311_2026_FUTURE", [
        {
            "id": "ND311_2026_FUTURE:status",
            "unit_type": "source_registry",
            "title": "Nghị định 311/2026/NĐ-CP - chưa áp dụng trước 26/09/2026",
            "effective_from": "2026-09-26",
            "text": "Nghị định 311/2026/NĐ-CP chỉ có hiệu lực từ 26/09/2026. AI Core không được sử dụng văn bản này làm căn cứ hiện hành trước ngày đó.",
        },
    ])
