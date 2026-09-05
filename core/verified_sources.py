from core import db


# Snapshot nguồn chính thức đã kiểm tra ngày 05/09/2026.
# Các đơn vị dưới đây là dữ liệu nguồn để AI tra cứu, không phải câu trả lời mẫu.


def ensure_verified_sources():
    # ------------------------------------------------------------------
    # 0) CĂN CƯỚC CHO NGƯỜI DƯỚI 14 TUỔI (CẤP XÃ)
    # ------------------------------------------------------------------
    db.upsert_document({
        "id": "CITIZEN_ID_UNDER14_2026",
        "title": "Cấp thẻ căn cước cho người dưới 14 tuổi tại Công an cấp xã",
        "number": "Mã thủ tục 1.014062",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=122156",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("CITIZEN_ID_UNDER14_2026", [
        {
            "id": "CITIZEN_ID_UNDER14_2026:scope",
            "unit_type": "procedure",
            "title": "Cấp thẻ căn cước cho người dưới 14 tuổi tại cấp xã",
            "text": (
                "Thủ tục cấp thẻ căn cước cho người dưới 14 tuổi được thực hiện tại Công an xã. "
                "Người đại diện hợp pháp có thể thực hiện trực tiếp; khi trực tiếp, đưa người dưới 14 tuổi đến địa điểm làm thủ tục. "
                "Đối với người dưới 06 tuổi, người đại diện hợp pháp có thể thực hiện qua Cổng dịch vụ công hoặc ứng dụng định danh quốc gia; "
                "hồ sơ được chuyển đến Công an cấp xã trong cả nước không phụ thuộc nơi cư trú để xem xét, giải quyết theo thông báo của Bộ Công an."
            ),
        },
        {
            "id": "CITIZEN_ID_UNDER14_2026:data_and_representative",
            "unit_type": "procedure",
            "title": "Thông tin dân cư và người đại diện trong thủ tục căn cước dưới 14 tuổi",
            "text": (
                "Cán bộ thu nhận tìm kiếm thông tin trong Cơ sở dữ liệu quốc gia về dân cư để lập hồ sơ. "
                "Nếu thông tin chưa có hoặc có thay đổi thì thực hiện thu thập, cập nhật hoặc điều chỉnh thông tin trước khi làm thủ tục cấp thẻ căn cước. "
                "Người đại diện hợp pháp cần có giấy tờ, tài liệu có giá trị pháp lý chứng minh tư cách đại diện; "
                "Phiếu thu nhận thông tin căn cước được tạo từ dữ liệu để kiểm tra, ký xác nhận."
            ),
        },
        {
            "id": "CITIZEN_ID_UNDER14_2026:time",
            "unit_type": "procedure",
            "title": "Thời hạn giải quyết thủ tục căn cước dưới 14 tuổi tại cấp xã",
            "text": "Thời hạn giải quyết thủ tục là 07 ngày làm việc; kết quả thực hiện là thẻ căn cước.",
        },
    ])

    # ------------------------------------------------------------------
    # 0.1) CẤP LẠI THẺ CĂN CƯỚC BỊ MẤT (CẤP TỈNH)
    # ------------------------------------------------------------------
    # Chỉ dùng cho đúng ý định cấp lại/mất thẻ. Không suy diễn thủ tục này
    # sang cấp mới hoặc cấp đổi, và không nói Công an cấp xã trực tiếp cấp lại.
    db.upsert_document({
        "id": "CITIZEN_ID_REISSUE_PROVINCIAL_2026",
        "title": "Cấp lại thẻ căn cước (thực hiện tại cấp tỉnh)",
        "number": "Mã thủ tục 2.001194",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26093",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("CITIZEN_ID_REISSUE_PROVINCIAL_2026", [
        {
            "id": "CITIZEN_ID_REISSUE_PROVINCIAL_2026:channels",
            "unit_type": "procedure",
            "title": "Cấp lại thẻ căn cước bị mất: nơi và cách thực hiện",
            "text": (
                "Thủ tục cấp lại thẻ căn cước thực hiện tại cơ quan quản lý căn cước của Công an cấp tỉnh. "
                "Công dân có thể đến trực tiếp hoặc sử dụng Cổng dịch vụ công quốc gia, Cổng dịch vụ công Bộ Công an "
                "hoặc ứng dụng định danh quốc gia để chọn thủ tục cấp lại, kiểm tra thông tin và chuyển đề nghị đến cơ quan quản lý căn cước của Công an cấp tỉnh."
            ),
        },
        {
            "id": "CITIZEN_ID_REISSUE_PROVINCIAL_2026:lost_card",
            "unit_type": "procedure",
            "title": "Cấp lại khi bị mất hoặc thẻ hư hỏng không dùng được",
            "text": (
                "Trường hợp cấp lại do mất thẻ căn cước hoặc thẻ hư hỏng không sử dụng được, cán bộ thu nhận sử dụng "
                "thông tin về ảnh khuôn mặt, vân tay, mống mắt đã thu nhận gần nhất cùng các thông tin trong Cơ sở dữ liệu quốc gia về dân cư, "
                "Cơ sở dữ liệu căn cước để thực hiện cấp lại."
            ),
        },
        {
            "id": "CITIZEN_ID_REISSUE_PROVINCIAL_2026:time",
            "unit_type": "procedure",
            "title": "Thời hạn giải quyết cấp lại thẻ căn cước",
            "text": "Thời hạn giải quyết thủ tục cấp lại thẻ căn cước là 07 ngày làm việc, thực hiện trực tiếp hoặc trực tuyến.",
        },
    ])

    # ------------------------------------------------------------------
    # 0.2) CẤP THẺ CĂN CƯỚC TỪ ĐỦ 14 TUỔI (CẤP TỈNH)
    # ------------------------------------------------------------------
    db.upsert_document({
        "id": "CITIZEN_ID_OVER14_PROVINCIAL_2026",
        "title": "Cấp thẻ Căn cước cho người từ đủ 14 tuổi trở lên tại cấp tỉnh",
        "number": "Mã thủ tục 2.000200",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=26052",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("CITIZEN_ID_OVER14_PROVINCIAL_2026", [
        {
            "id": "CITIZEN_ID_OVER14_PROVINCIAL_2026:channels",
            "unit_type": "procedure",
            "title": "Cấp thẻ Căn cước từ đủ 14 tuổi: nơi và cách thực hiện",
            "text": (
                "Thủ tục cấp thẻ Căn cước cho người từ đủ 14 tuổi trở lên thực hiện tại cơ quan quản lý căn cước của Công an cấp tỉnh "
                "hoặc Trung tâm phục vụ hành chính công cấp tỉnh, thành phố nếu đã triển khai. Công dân có thể thực hiện trực tiếp hoặc "
                "qua Cổng dịch vụ công quốc gia, Cổng dịch vụ công Bộ Công an, ứng dụng định danh quốc gia để đăng ký thời gian, địa điểm."
            ),
        },
        {
            "id": "CITIZEN_ID_OVER14_PROVINCIAL_2026:time",
            "unit_type": "procedure",
            "title": "Thời hạn giải quyết cấp thẻ Căn cước từ đủ 14 tuổi",
            "text": "Thời hạn giải quyết thủ tục cấp thẻ Căn cước cho người từ đủ 14 tuổi trở lên là 07 ngày làm việc; lệ phí và phí theo trang thủ tục là không.",
        },
    ])

    # ------------------------------------------------------------------
    # 1) CƯ TRÚ HIỆN HÀNH TỪ 01/07/2026
    # ------------------------------------------------------------------
    db.upsert_document({
        "id": "RESIDENCE_GUIDANCE_2026",
        "title": "Quy định mới về lĩnh vực cư trú từ 01/07/2026 - Bộ Công an",
        "number": "Thông tư 116/2026/TT-BCA và Luật 118/2025/QH15",
        "issuer": "Bộ Công an / Quốc hội",
        "effective_from": "2026-07-01",
        "source_path": "https://www.bocongan.gov.vn/bai-viet/quy-dinh-moi-ve-linh-vuc-cu-tru-gop-phan-nang-cao-chat-luong-phuc-vu-nhan-dan-1783934790",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("RESIDENCE_GUIDANCE_2026", [
        {
            "id": "RESIDENCE_GUIDANCE_2026:data_reuse",
            "unit_type": "guidance",
            "title": "Không yêu cầu nộp lại giấy tờ cư trú đã có dữ liệu",
            "text": (
                "Từ 01/07/2026, trường hợp thông tin, giấy tờ chứng minh điều kiện đăng ký cư trú đã được kết nối, "
                "chia sẻ, khai thác từ cơ sở dữ liệu, hệ thống thông tin hoặc VNeID thì cơ quan đăng ký cư trú không được "
                "yêu cầu công dân nộp hoặc xuất trình lại. Khi công dân nộp hồ sơ trực tiếp, cán bộ tiếp nhận khai thác "
                "thông tin từ Cơ sở dữ liệu quốc gia về dân cư và các cơ sở dữ liệu liên quan để tạo lập hồ sơ. "
                "Khi chưa khai thác được dữ liệu thì cơ quan đăng ký cư trú kiểm tra, xác minh; công dân chỉ xuất trình "
                "giấy tờ gốc để đối chiếu khi thực sự cần thiết."
            ),
            "effective_from": "2026-07-01",
        },
        {
            "id": "RESIDENCE_GUIDANCE_2026:current_law_status",
            "unit_type": "guidance",
            "title": "Văn bản cư trú hiện hành từ 01/07/2026",
            "text": (
                "Thông tư 116/2026/TT-BCA ngày 29/06/2026 có hiệu lực từ 01/07/2026 và đang còn hiệu lực tại thời điểm "
                "kiểm tra 05/09/2026. Luật 118/2025/QH15 có hiệu lực từ 01/07/2026 và sửa đổi một số quy định liên quan "
                "đến Luật Cư trú. Chatbot không được mặc định dùng biểu mẫu hoặc căn cứ cũ chỉ vì một trang thủ tục còn hiển thị dữ liệu cũ."
            ),
            "effective_from": "2026-07-01",
        },
    ])

    # Đăng ký tạm trú.
    db.upsert_document({
        "id": "TTHC_TEMP_RESIDENCE_2026",
        "title": "Đăng ký tạm trú - Cổng Dịch vụ công Bộ Công an",
        "number": "Mã thủ tục 1.004194",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=26356",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("TTHC_TEMP_RESIDENCE_2026", [
        {
            "id": "TTHC_TEMP_RESIDENCE_2026:core",
            "unit_type": "procedure",
            "title": "Đăng ký tạm trú: cơ quan, cách thức và thời hạn",
            "text": (
                "Thủ tục đăng ký tạm trú có cơ quan thực hiện là Công an cấp xã. Cách thức thực hiện: trực tiếp hoặc trực tuyến. "
                "Thời hạn giải quyết: 03 ngày làm việc. Kết quả là cập nhật thông tin trong cơ sở dữ liệu về dân cư, cư trú "
                "và thông báo kết quả giải quyết; không được mô tả mặc định là cấp giấy tạm trú."
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
    ])

    # Đăng ký thường trú.
    db.upsert_document({
        "id": "RESIDENCE_PERMANENT_2026",
        "title": "Đăng ký thường trú - Cổng Dịch vụ công Bộ Công an và quy định cư trú hiện hành",
        "number": "Mã thủ tục 1.004222",
        "issuer": "Bộ Công an",
        "effective_from": "2026-07-01",
        "source_path": "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=26360",
        "sha256": None,
        "metadata": {
            "checked": "2026-09-05",
            "official": True,
            "current_guidance": "Thông tư 116/2026/TT-BCA",
        },
    })
    db.replace_document_units("RESIDENCE_PERMANENT_2026", [
        {
            "id": "RESIDENCE_PERMANENT_2026:core",
            "unit_type": "procedure",
            "title": "Đăng ký thường trú: cơ quan, cách thức và thời hạn",
            "text": (
                "Thủ tục đăng ký thường trú có cơ quan thực hiện là Công an cấp xã. Công dân có thể nộp trực tiếp hoặc trực tuyến. "
                "Thời hạn giải quyết là 07 ngày làm việc. Kết quả giải quyết gồm cập nhật thông tin trong Cơ sở dữ liệu quốc gia về dân cư, "
                "Cơ sở dữ liệu về cư trú và thông báo kết quả giải quyết thủ tục cư trú theo quy định."
            ),
            "effective_from": "2026-07-01",
        },
        {
            "id": "RESIDENCE_PERMANENT_2026:documents_by_case",
            "unit_type": "procedure",
            "title": "Đăng ký thường trú: thành phần hồ sơ phụ thuộc trường hợp",
            "text": (
                "Thành phần hồ sơ đăng ký thường trú phụ thuộc căn cứ và chỗ ở cụ thể của người đăng ký, không có một danh sách giấy tờ chung "
                "áp dụng giống nhau cho mọi trường hợp. Nếu công dân đăng ký thường trú vào chỗ ở hợp pháp thuộc quyền sở hữu của mình, "
                "giấy tờ, tài liệu chứng minh sở hữu chỗ ở hợp pháp chỉ cần cung cấp khi thông tin này chưa có trong cơ sở dữ liệu chuyên ngành, "
                "chưa được kết nối, chia sẻ hoặc chưa có nguồn điện tử để cơ quan đăng ký cư trú tự kiểm tra, xác minh. "
                "Nếu đăng ký vào chỗ ở không thuộc quyền sở hữu của mình như thuê, mượn, ở nhờ hoặc theo quan hệ gia đình thì phải đối chiếu "
                "đúng điều kiện của trường hợp đó, trong đó có thể phát sinh yêu cầu về sự đồng ý của chủ hộ/chủ sở hữu và tài liệu chứng minh điều kiện liên quan. "
                "Chatbot phải hỏi người dân đang đăng ký tại nhà thuộc sở hữu của mình, nhà của cha mẹ/vợ chồng/con hay nhà thuê/mượn/ở nhờ trước khi liệt kê hồ sơ chi tiết."
            ),
            "effective_from": "2026-07-01",
        },
        {
            "id": "RESIDENCE_PERMANENT_2026:no_generic_old_papers",
            "unit_type": "guidance",
            "title": "Không tự tạo bộ hồ sơ thường trú rập khuôn",
            "text": (
                "Không được trả lời rằng mọi trường hợp đăng ký thường trú đều phải nộp một bộ giấy tờ cố định gồm CMND/CCCD, sổ hộ khẩu, "
                "giấy khai sinh, giấy kết hôn, sổ đỏ hoặc hợp đồng thuê nhà. Việc cần tài liệu nào phụ thuộc trường hợp đăng ký và dữ liệu mà cơ quan "
                "đăng ký cư trú đã khai thác được. Những thông tin, giấy tờ chứng minh điều kiện cư trú đã có trong cơ sở dữ liệu hoặc VNeID thì không được yêu cầu nộp hoặc xuất trình lại."
            ),
            "effective_from": "2026-07-01",
        },
    ])

    # ------------------------------------------------------------------
    # 2) VNeID / TÀI KHOẢN ĐỊNH DANH ĐIỆN TỬ
    # ------------------------------------------------------------------
    db.upsert_document({
        "id": "VNEID_2026",
        "title": "Cấp tài khoản định danh điện tử VNeID - Nghị định 69/2024/NĐ-CP",
        "number": "Nghị định 69/2024/NĐ-CP",
        "issuer": "Chính phủ / Bộ Công an",
        "effective_from": "2024-07-01",
        "source_path": "https://bocongan.gov.vn/bai-viet/nghi-dinh-quy-dinh-ve-dinh-danh-va-xac-thuc-dien-tu-d1-t1418",
        "sha256": None,
        "metadata": {
            "checked": "2026-09-05",
            "official": True,
            "future_amendment": "Nghị định 320/2026/NĐ-CP có hiệu lực từ 28/09/2026, chưa có hiệu lực tại snapshot 05/09/2026",
        },
    })
    db.replace_document_units("VNEID_2026", [
        {
            "id": "VNEID_2026:overview",
            "unit_type": "procedure",
            "title": "VNeID: phân biệt tài khoản định danh điện tử mức độ 01 và mức độ 02",
            "text": (
                "Đối với công dân Việt Nam, tài khoản định danh điện tử mức độ 01 được đăng ký trên ứng dụng định danh quốc gia bằng thiết bị số. "
                "Tài khoản định danh điện tử mức độ 02 được thực hiện trực tiếp tại Công an xã, phường, thị trấn hoặc cơ quan quản lý căn cước, "
                "không phụ thuộc vào nơi cư trú. Nếu công dân chưa được cấp thẻ căn cước công dân hoặc thẻ căn cước thì có thể đề nghị cấp tài khoản "
                "định danh điện tử đồng thời với thủ tục cấp thẻ căn cước."
            ),
        },
        {
            "id": "VNEID_2026:level1",
            "unit_type": "procedure",
            "title": "Cấp tài khoản định danh điện tử mức độ 01 cho công dân Việt Nam",
            "text": (
                "Công dân sử dụng thiết bị số tải và cài đặt ứng dụng định danh quốc gia; nhập số định danh cá nhân, số thuê bao di động chính chủ, "
                "địa chỉ thư điện tử nếu có; kê khai thông tin theo hướng dẫn trên ứng dụng, thu nhận ảnh khuôn mặt bằng thiết bị số và gửi yêu cầu. "
                "Cơ quan quản lý định danh và xác thực điện tử kiểm tra, xác thực và thông báo kết quả qua ứng dụng định danh quốc gia hoặc số thuê bao di động chính chủ hoặc địa chỉ thư điện tử."
            ),
        },
        {
            "id": "VNEID_2026:level2",
            "unit_type": "procedure",
            "title": "Cấp tài khoản định danh điện tử mức độ 02 cho công dân Việt Nam",
            "text": (
                "Công dân đến Công an xã, phường, thị trấn hoặc cơ quan quản lý căn cước không phụ thuộc vào nơi cư trú, xuất trình thẻ căn cước công dân "
                "hoặc thẻ căn cước còn hiệu lực và thực hiện thủ tục cấp tài khoản định danh điện tử mức độ 02. Công dân cung cấp đầy đủ, chính xác thông tin "
                "trên Phiếu đề nghị cấp tài khoản định danh điện tử mẫu TK01; trong đó cung cấp số thuê bao di động chính chủ, địa chỉ thư điện tử nếu có và thông tin "
                "khác đề nghị tích hợp nếu có nhu cầu. Cán bộ tiếp nhận xác thực ảnh khuôn mặt, vân tay với Cơ sở dữ liệu căn cước. Kết quả được thông báo qua ứng dụng "
                "định danh quốc gia hoặc số thuê bao di động chính chủ hoặc địa chỉ thư điện tử."
            ),
        },
        {
            "id": "VNEID_2026:under14",
            "unit_type": "procedure",
            "title": "Cấp tài khoản định danh điện tử mức độ 02 cho người dưới 14 tuổi",
            "text": (
                "Người dưới 14 tuổi, người được giám hộ, người được đại diện cùng người đại diện hoặc người giám hộ đến Công an xã, phường, thị trấn hoặc nơi làm thủ tục "
                "cấp thẻ căn cước để làm thủ tục cấp tài khoản định danh điện tử mức độ 02. Người đại diện hoặc người giám hộ sử dụng số thuê bao di động chính chủ của mình để kê khai theo quy định."
            ),
        },
        {
            "id": "VNEID_2026:current_status",
            "unit_type": "guidance",
            "title": "Tình trạng hiệu lực quy định VNeID tại ngày 05/09/2026",
            "text": (
                "Nghị định 69/2024/NĐ-CP có hiệu lực từ 01/07/2024 và là căn cứ đang áp dụng tại thời điểm 05/09/2026. Nghị định 320/2026/NĐ-CP sửa đổi Nghị định 69/2024/NĐ-CP "
                "được ban hành ngày 13/08/2026 nhưng đến 28/09/2026 mới có hiệu lực; chatbot không được áp dụng trước thời điểm có hiệu lực."
            ),
        },
    ])

    db.upsert_document({
        "id": "VNEID_SIM_GUIDANCE_2026",
        "title": "Hỏi đáp Bộ Công an về số điện thoại khi đăng ký tài khoản định danh điện tử",
        "number": "Hỏi đáp ngày 22/04/2026",
        "issuer": "Bộ Công an",
        "effective_from": None,
        "source_path": "https://bocongan.gov.vn/chinh-sach-phap-luat/chi-tiet-cau-hoi/fcbfa61b-a326-4018-af36-dfe4f1b9faa8",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("VNEID_SIM_GUIDANCE_2026", [
        {
            "id": "VNEID_SIM_GUIDANCE_2026:sim",
            "unit_type": "guidance",
            "title": "Số điện thoại khi đăng ký tài khoản định danh điện tử",
            "text": (
                "Theo trả lời của Bộ Công an ngày 22/04/2026, để đăng ký tài khoản định danh điện tử, người dân cần dùng số điện thoại chưa gắn với tài khoản định danh điện tử nào; "
                "phần mềm không kiểm tra chính chủ tại bước đăng ký. Tuy nhiên quy trình cấp vẫn yêu cầu sim đăng ký là sim chính chủ để tránh việc tài khoản bị khóa khi chính chủ của số điện thoại đó đăng ký tài khoản định danh."
            ),
        },
    ])

    # ------------------------------------------------------------------
    # 3) ĐĂNG KÝ XE MÔ TÔ, XE GẮN MÁY
    # ------------------------------------------------------------------
    db.upsert_document({
        "id": "VEHICLE_REGISTRATION_2026",
        "title": "Đăng ký xe mô tô, xe gắn máy - nguồn chính thức Bộ Công an",
        "number": "Thông tư 79/2024/TT-BCA, Thông tư 51/2025/TT-BCA và TTHC đăng ký xe",
        "issuer": "Bộ Công an",
        "effective_from": "2025-07-01",
        "source_path": "https://bocongan.gov.vn/bai-viet/to-chuc-ca-nhan-trong-nuoc-duoc-lua-chon-dang-ky-xe-tai-phong-canh-sat-giao-thong-hoac-cong-an-cap-xa-d1-t1770",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("VEHICLE_REGISTRATION_2026", [
        {
            "id": "VEHICLE_REGISTRATION_2026:authority",
            "unit_type": "procedure",
            "title": "Cơ quan đăng ký xe từ 01/07/2025",
            "text": (
                "Từ 01/07/2025, tổ chức, cá nhân trong nước được lựa chọn đăng ký xe tại Phòng Cảnh sát giao thông hoặc Công an cấp xã trong tỉnh, thành phố theo quy định hiện hành. "
                "Việc tổ chức điểm đăng ký cụ thể thực hiện theo phân công và tổ chức thực tế của Công an địa phương. Nếu cần xác nhận Công an xã Pơng Drang có tiếp nhận trực tiếp thủ tục cụ thể, gọi số trực ban 02623509777."
            ),
            "effective_from": "2025-07-01",
        },
        {
            "id": "VEHICLE_REGISTRATION_2026:first_registration_documents",
            "unit_type": "procedure",
            "title": "Đăng ký lần đầu xe mô tô, xe gắn máy: thành phần hồ sơ",
            "text": (
                "Nguồn thủ tục chính thức Bộ Công an liệt kê hồ sơ đăng ký, cấp biển số xe mô tô, xe gắn máy lần đầu gồm: Giấy khai đăng ký xe theo mẫu ĐKX10; giấy tờ của chủ xe; "
                "giấy tờ của xe gồm chứng nhận nguồn gốc xe, chứng nhận quyền sở hữu hợp pháp và chứng từ hoàn thành nghĩa vụ tài chính. Danh mục hồ sơ chung này không liệt kê giấy chứng nhận "
                "bảo hiểm trách nhiệm dân sự hoặc giấy kiểm định kỹ thuật xe mô tô là thành phần bắt buộc."
            ),
        },
        {
            "id": "VEHICLE_REGISTRATION_2026:first_registration_process",
            "unit_type": "procedure",
            "title": "Đăng ký lần đầu xe mô tô, xe gắn máy: trình tự và thời hạn",
            "text": (
                "Chủ xe kê khai Giấy khai đăng ký xe theo quy định. Cán bộ đăng ký xe kiểm tra giấy tờ của chủ xe, giấy tờ của xe, đối chiếu dữ liệu và kiểm tra thực tế xe theo quy định. "
                "Khi hồ sơ và xe hợp lệ thì cấp biển số theo quy định. Thời hạn cấp chứng nhận đăng ký xe không quá 02 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ."
            ),
        },
    ])

    # ------------------------------------------------------------------
    # 4) TỐ GIÁC, TIN BÁO VỀ TỘI PHẠM
    # ------------------------------------------------------------------
    db.upsert_document({
        "id": "CRIME_REPORT_GUIDANCE_2025",
        "title": "Hướng dẫn tố giác, báo tin về tội phạm, kiến nghị khởi tố",
        "number": "Hướng dẫn Bộ Công an từ 01/03/2025",
        "issuer": "Bộ Công an",
        "effective_from": "2025-03-01",
        "source_path": "https://bocongan.gov.vn/bai-viet/huong-dan-to-giac-bao-tin-ve-toi-pham-kien-nghi-khoi-to-tu-ngay-0132025-d2-t43729",
        "sha256": None,
        "metadata": {"checked": "2026-09-05", "official": True},
    })
    db.replace_document_units("CRIME_REPORT_GUIDANCE_2025", [
        {
            "id": "CRIME_REPORT_GUIDANCE_2025:channels",
            "unit_type": "procedure",
            "title": "Cách tố giác, báo tin về tội phạm",
            "text": (
                "Tổ chức, cá nhân có thể tố giác, báo tin về tội phạm trực tiếp, bằng văn bản, qua điện thoại trực ban của cơ quan có thẩm quyền, "
                "qua phương tiện thông tin đại chúng, hòm thư điện tử, báo nói, báo hình, ứng dụng VNeID, hoặc bằng đơn, thư gửi qua đường bưu điện, giao liên. "
                "Cơ quan điều tra của Công an nhân dân tổ chức trực ban hình sự 24/24 giờ để tiếp nhận đầy đủ tố giác, tin báo về tội phạm, kiến nghị khởi tố."
            ),
        },
        {
            "id": "CRIME_REPORT_GUIDANCE_2025:rights",
            "unit_type": "guidance",
            "title": "Quyền của người tố giác, báo tin về tội phạm",
            "text": (
                "Người tố giác, báo tin có quyền yêu cầu cơ quan có thẩm quyền giữ bí mật việc tố giác, báo tin và bảo vệ tính mạng, sức khỏe, "
                "danh dự, nhân phẩm, uy tín, tài sản, quyền và lợi ích hợp pháp của mình và người thân thích khi bị đe dọa. "
                "Người tố giác, báo tin được thông báo kết quả giải quyết và có trách nhiệm trình bày trung thực những tình tiết mình biết khi cơ quan có thẩm quyền yêu cầu."
            ),
        },
        {
            "id": "CRIME_REPORT_GUIDANCE_2025:local_intake",
            "unit_type": "guidance",
            "title": "Công an cấp xã trong việc tiếp nhận tố giác, tin báo",
            "text": "Công an xã, phường, thị trấn, Đồn Công an nằm trong danh sách đơn vị tiếp nhận tố giác, tin báo về tội phạm theo hướng dẫn của Bộ Công an.",
        },
    ])
