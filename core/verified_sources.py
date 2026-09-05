from core import db


# Snapshot đã đối chiếu từ nguồn chính thức ngày 05/09/2026.
# Đây là nguồn sự thật cục bộ cho AI Core, không phải câu trả lời mẫu.


def ensure_verified_sources():
    # 1) CƯ TRÚ HIỆN HÀNH
    db.upsert_document({
        "id": "RESIDENCE_GUIDANCE_2026",
        "title": "Hướng dẫn mới về cư trú từ 01/07/2026 - Bộ Công an",
        "number": "Thông tư 116/2026/TT-BCA và Luật 118/2025/QH15",
        "issuer": "Bộ Công an / Quốc hội",
        "effective_from": "2026-07-01",
        "source_path": "https://www.bocongan.gov.vn/bai-viet/quy-dinh-moi-ve-linh-vuc-cu-tru-gop-phan-nang-cao-chat-luong-phuc-vu-nhan-dan-1783934790",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True, "source_type": "official_guidance_snapshot"},
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
                "để đối chiếu khi thực sự cần thiết."
            ),
            "effective_from": "2026-07-01",
        },
        {
            "id": "RESIDENCE_GUIDANCE_2026:current_law_status",
            "unit_type": "guidance",
            "title": "Văn bản cư trú hiện hành từ 01/07/2026",
            "text": (
                "Thông tư 116/2026/TT-BCA ngày 29/06/2026 có hiệu lực từ 01/07/2026. "
                "Luật 118/2025/QH15 có hiệu lực từ 01/07/2026 và sửa đổi một số quy định liên quan đến Luật Cư trú. "
                "Nếu một trang thủ tục còn hiển thị biểu mẫu hoặc căn cứ cũ, chatbot không được mặc định viện dẫn số mẫu cũ "
                "khi chưa có nguồn hiện hành xác nhận."
            ),
            "effective_from": "2026-07-01",
        },
    ]
    db.replace_document_units("RESIDENCE_GUIDANCE_2026", residence_units)

    db.upsert_document({
        "id": "TTHC_TEMP_RESIDENCE_2026",
        "title": "Đăng ký tạm trú - Cổng Dịch vụ công Bộ Công an",
        "number": "Mã thủ tục 1.004194",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=26356",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True, "source_type": "official_tthc_snapshot"},
    })
    temp_units = [
        {
            "id": "TTHC_TEMP_RESIDENCE_2026:core",
            "unit_type": "procedure",
            "title": "Đăng ký tạm trú: cơ quan, cách thức và thời hạn",
            "text": (
                "Thủ tục đăng ký tạm trú có mã 1.004194. Cơ quan thực hiện: Công an cấp xã. "
                "Cách thức thực hiện: trực tiếp hoặc trực tuyến. Thời hạn giải quyết: 03 ngày làm việc. "
                "Kết quả là cập nhật thông tin trong cơ sở dữ liệu về dân cư/cư trú và thông báo kết quả giải quyết; "
                "không được mô tả mặc định là cấp giấy tạm trú."
            ),
        },
        {
            "id": "TTHC_TEMP_RESIDENCE_2026:documents_policy",
            "unit_type": "procedure",
            "title": "Đăng ký tạm trú: nguyên tắc hồ sơ hiện hành",
            "text": (
                "Công dân cung cấp thông tin cơ bản và thông tin về điều kiện đăng ký cư trú; cơ quan đăng ký cư trú chủ động "
                "khai thác thông tin, giấy tờ đã có trong cơ sở dữ liệu hoặc VNeID và không yêu cầu công dân nộp hoặc xuất trình lại. "
                "Nếu dữ liệu chưa khai thác được thì cơ quan đăng ký cư trú kiểm tra, xác minh và chỉ yêu cầu xuất trình giấy tờ gốc "
                "để đối chiếu khi thực sự cần thiết."
            ),
        },
    ]
    db.replace_document_units("TTHC_TEMP_RESIDENCE_2026", temp_units)

    # 2) ĐĂNG KÝ XE MÔ TÔ, XE GẮN MÁY HIỆN HÀNH
    # Nguồn 1: Thông tư 51/2025/TT-BCA và bài hướng dẫn chính thức Bộ Công an.
    # Nguồn 2: Cổng Dịch vụ công Bộ Công an, thủ tục đăng ký xe mô tô lần đầu.
    db.upsert_document({
        "id": "VEHICLE_REGISTRATION_2026",
        "title": "Đăng ký xe mô tô, xe gắn máy - nguồn chính thức Bộ Công an",
        "number": "Thông tư 79/2024/TT-BCA, Thông tư 51/2025/TT-BCA và TTHC đăng ký xe",
        "issuer": "Bộ Công an",
        "effective_from": "2025-07-01",
        "source_path": "https://bocongan.gov.vn/bai-viet/to-chuc-ca-nhan-trong-nuoc-duoc-lua-chon-dang-ky-xe-tai-phong-canh-sat-giao-thong-hoac-cong-an-cap-xa-d1-t1770",
        "sha256": None,
        "metadata": {
            "checked": "2026-09-05",
            "official": True,
            "source_type": "official_vehicle_registration_snapshot",
            "tthc_source": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=39413",
        },
    })
    vehicle_units = [
        {
            "id": "VEHICLE_REGISTRATION_2026:authority",
            "unit_type": "procedure",
            "title": "Cơ quan đăng ký xe từ 01/07/2025",
            "text": (
                "Từ 01/07/2025, tổ chức, cá nhân trong nước được lựa chọn đăng ký xe tại Phòng Cảnh sát giao thông "
                "hoặc Công an cấp xã trong tỉnh, thành phố theo quy định hiện hành. Việc tổ chức điểm đăng ký cụ thể "
                "được thực hiện theo phân công và tổ chức thực tế của Công an địa phương. Chatbot không được gọi đầu mối "
                "tại Công an cấp xã là 'phòng Đăng ký xe của Công an xã'. Nếu cần xác nhận Công an xã Pơng Drang có tiếp nhận "
                "trực tiếp thủ tục cụ thể tại thời điểm người dân hỏi, hướng dẫn gọi số trực ban 02623509777."
            ),
            "effective_from": "2025-07-01",
        },
        {
            "id": "VEHICLE_REGISTRATION_2026:first_registration_documents",
            "unit_type": "procedure",
            "title": "Đăng ký lần đầu xe mô tô, xe gắn máy: thành phần hồ sơ",
            "text": (
                "Nguồn thủ tục chính thức của Bộ Công an được kiểm tra ngày 05/09/2026 liệt kê hồ sơ đăng ký, cấp biển số xe mô tô, "
                "xe gắn máy lần đầu gồm: Giấy khai đăng ký xe theo mẫu ĐKX10; giấy tờ của chủ xe; giấy tờ của xe gồm chứng nhận nguồn gốc xe, "
                "chứng nhận quyền sở hữu hợp pháp và chứng từ hoàn thành nghĩa vụ tài chính. Danh mục hồ sơ chung này không liệt kê "
                "giấy chứng nhận bảo hiểm trách nhiệm dân sự hoặc giấy kiểm định kỹ thuật xe mô tô như thành phần bắt buộc. "
                "Chatbot không được tự thêm các giấy tờ đó nếu không có tình huống đặc thù và nguồn riêng hỗ trợ."
            ),
        },
        {
            "id": "VEHICLE_REGISTRATION_2026:first_registration_process",
            "unit_type": "procedure",
            "title": "Đăng ký lần đầu xe mô tô, xe gắn máy: trình tự và thời hạn",
            "text": (
                "Chủ xe kê khai Giấy khai đăng ký xe theo quy định. Cán bộ đăng ký xe kiểm tra giấy tờ của chủ xe, giấy tờ của xe, "
                "đối chiếu thông tin dữ liệu và kiểm tra thực tế xe theo quy định. Khi hồ sơ và xe bảo đảm hợp lệ thì cấp biển số theo quy định. "
                "Thời hạn cấp chứng nhận đăng ký xe không quá 02 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ; biển số được cấp theo quy định sau khi hồ sơ hợp lệ. "
                "Chủ xe nhận kết quả tại cơ quan đăng ký xe hoặc qua dịch vụ bưu chính công ích theo lựa chọn."
            ),
        },
        {
            "id": "VEHICLE_REGISTRATION_2026:wording_guard",
            "unit_type": "guidance",
            "title": "Cách diễn đạt đúng khi hướng dẫn đăng ký xe",
            "text": (
                "Khi hướng dẫn người dân, dùng các thuật ngữ: Giấy khai đăng ký xe, giấy tờ của chủ xe, giấy tờ của xe, cơ quan đăng ký xe, "
                "cán bộ đăng ký xe, chứng nhận đăng ký xe và biển số xe. Không dùng các cách gọi không chính xác như 'đơn đăng ký xe', "
                "'phòng Đăng ký xe của Công an xã', 'nhân viên đăng ký xe' hoặc 'thẻ đăng ký xe'."
            ),
        },
    ]
    db.replace_document_units("VEHICLE_REGISTRATION_2026", vehicle_units)
