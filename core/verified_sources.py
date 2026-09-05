from core import db


# Các nguồn dưới đây là snapshot đã đối chiếu từ nguồn chính thức ngày 05/09/2026.
# Mục đích: làm nguồn sự thật cục bộ cho AI Core, không phải câu trả lời mẫu.


def ensure_verified_sources():
    # 1) Hướng dẫn cư trú mới của Bộ Công an sau 01/07/2026.
    db.upsert_document({
        "id": "RESIDENCE_GUIDANCE_2026",
        "title": "Hướng dẫn mới về cư trú từ 01/07/2026 - Bộ Công an",
        "number": "Thông tư 116/2026/TT-BCA và Luật 118/2025/QH15",
        "issuer": "Bộ Công an / Quốc hội",
        "effective_from": "2026-07-01",
        "source_path": "https://www.bocongan.gov.vn/bai-viet/quy-dinh-moi-ve-linh-vuc-cu-tru-gop-phan-nang-cao-chat-luong-phuc-vu-nhan-dan-1783934790",
        "sha256": None,
        "metadata": {
            "checked": "2026-09-05",
            "official": True,
            "source_type": "official_guidance_snapshot",
        },
    })

    residence_units = [
        {
            "id": "RESIDENCE_GUIDANCE_2026:data_reuse",
            "unit_type": "guidance",
            "title": "Nguyên tắc tiếp nhận hồ sơ cư trú và tái sử dụng dữ liệu",
            "text": (
                "Từ 01/07/2026, khi công dân nộp hồ sơ cư trú trực tiếp, công dân cung cấp các thông tin cơ bản "
                "và thông tin về điều kiện đăng ký cư trú; cán bộ tiếp nhận có trách nhiệm khai thác thông tin từ "
                "Cơ sở dữ liệu quốc gia về dân cư và các cơ sở dữ liệu liên quan để tạo lập hồ sơ. "
                "Thông tin, giấy tờ chứng minh điều kiện đăng ký cư trú đã được kết nối, chia sẻ, khai thác từ cơ sở dữ liệu, "
                "hệ thống thông tin hoặc VNeID thì cơ quan đăng ký cư trú không được yêu cầu công dân nộp hoặc xuất trình lại. "
                "Khi chưa khai thác được dữ liệu, cơ quan đăng ký cư trú kiểm tra, xác minh; công dân chỉ xuất trình giấy tờ gốc "
                "để đối chiếu khi thực sự cần thiết. Chatbot không được tự bổ sung danh sách giấy tờ ngoài nguồn đã kiểm chứng."
            ),
            "effective_from": "2026-07-01",
        },
        {
            "id": "RESIDENCE_GUIDANCE_2026:current_law_status",
            "unit_type": "guidance",
            "title": "Văn bản cư trú hiện hành từ 01/07/2026",
            "text": (
                "Thông tư 116/2026/TT-BCA ngày 29/06/2026 quy định chi tiết một số điều và biện pháp thi hành Luật Cư trú, "
                "có hiệu lực từ 01/07/2026 và đang còn hiệu lực tại thời điểm kiểm tra 05/09/2026. "
                "Luật 118/2025/QH15 có hiệu lực từ 01/07/2026, sửa đổi một số quy định liên quan đến Luật Cư trú. "
                "Nếu một trang thủ tục còn hiển thị biểu mẫu hoặc căn cứ cũ, chatbot không được mặc định viện dẫn số mẫu cũ "
                "khi chưa có nguồn hiện hành xác nhận."
            ),
            "effective_from": "2026-07-01",
        },
    ]
    db.replace_document_units("RESIDENCE_GUIDANCE_2026", residence_units)

    # 2) Thủ tục đăng ký tạm trú trên Cổng Dịch vụ công Bộ Công an.
    db.upsert_document({
        "id": "TTHC_TEMP_RESIDENCE_2026",
        "title": "Đăng ký tạm trú - Cổng Dịch vụ công Bộ Công an",
        "number": "Mã thủ tục 1.004194",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=26356",
        "sha256": None,
        "metadata": {
            "checked": "2026-09-05",
            "official": True,
            "source_type": "official_tthc_snapshot",
        },
    })

    temp_units = [
        {
            "id": "TTHC_TEMP_RESIDENCE_2026:core",
            "unit_type": "procedure",
            "title": "Đăng ký tạm trú: cơ quan, cách thức và thời hạn",
            "text": (
                "Thủ tục đăng ký tạm trú có mã 1.004194. Cơ quan thực hiện: Công an cấp xã. "
                "Cách thức thực hiện: trực tiếp hoặc trực tuyến. "
                "Thời hạn giải quyết: 03 ngày làm việc đối với hồ sơ nộp trực tiếp tại Công an cấp xã hoặc nộp trực tuyến "
                "qua cổng cung cấp dịch vụ công trực tuyến theo quy định. "
                "Kết quả thủ tục là cập nhật thông tin trong cơ sở dữ liệu về dân cư/cư trú và thông báo kết quả giải quyết; "
                "không được mô tả mặc định là 'cấp giấy tạm trú'."
            ),
        },
        {
            "id": "TTHC_TEMP_RESIDENCE_2026:documents_policy",
            "unit_type": "procedure",
            "title": "Đăng ký tạm trú: nguyên tắc hồ sơ hiện hành",
            "text": (
                "Đối với đăng ký tạm trú, chatbot phải áp dụng nguyên tắc hồ sơ cư trú hiện hành từ 01/07/2026: "
                "công dân cung cấp thông tin cơ bản và thông tin về điều kiện đăng ký cư trú; cơ quan đăng ký cư trú chủ động "
                "khai thác thông tin, giấy tờ đã có trong cơ sở dữ liệu hoặc VNeID và không yêu cầu công dân nộp hoặc xuất trình lại. "
                "Nếu dữ liệu chưa khai thác được thì cơ quan đăng ký cư trú kiểm tra, xác minh và chỉ yêu cầu xuất trình giấy tờ gốc "
                "để đối chiếu khi thực sự cần thiết. Chatbot không được tự mặc định yêu cầu sổ hộ khẩu, bản sao CMND/CCCD, "
                "giấy khai sinh, thư mời, giấy phép sử dụng nhà hoặc giấy chứng minh quan hệ nếu nguồn hiện hành và tình huống cụ thể "
                "không xác định đó là giấy tờ cần thiết."
            ),
        },
    ]
    db.replace_document_units("TTHC_TEMP_RESIDENCE_2026", temp_units)
