"""Current verified source packs needed to cover the 19-source Notebook catalogue.

These are not canned answers. They are compact source-grounded units derived
from current official Ministry of Public Security public-service pages and are
used only for retrieval. Detailed claims outside these units must fail closed.
"""

from core import db

CHECKED = "2026-09-14"


def _doc(doc_id, title, number, source_path, authority_levels):
    db.upsert_document({
        "id": doc_id,
        "title": title,
        "number": number,
        "issuer": "Bộ Công an",
        "effective_from": None,
        "effective_to": None,
        "source_path": source_path,
        "sha256": None,
        "metadata": {
            "checked": CHECKED,
            "official": True,
            "status": "active",
            "authority_levels": authority_levels,
            "knowledge_mode": "source_grounded",
            "origin": "Gemini Notebook 19-source mirror + current official verification",
        },
    })


def ensure_notebook_current_sources():
    # Residence catalogue mirror. The current DVC-BCA residence catalogue lists
    # all 11 procedure groups mirrored by the user's Notebook.
    _doc(
        "RESIDENCE_NOTEBOOK_2026",
        "Bộ thủ tục đăng ký, quản lý cư trú hiện hành",
        "Danh mục TTHC cư trú - Cổng DVC Bộ Công an; TT 116/2026/TT-BCA",
        "https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/listThuTuc?linh_vuc=QL_CU_TRU",
        ["xa"],
    )
    db.replace_document_units("RESIDENCE_NOTEBOOK_2026", [
        {"id":"RESIDENCE_NOTEBOOK_2026:permanent","unit_type":"procedure","title":"Đăng ký thường trú","text":"Cổng Dịch vụ công Bộ Công an hiện liệt kê thủ tục Đăng ký thường trú trong lĩnh vực đăng ký, quản lý cư trú. Cơ quan đăng ký cư trú trực tiếp phục vụ người dân ở cấp xã; thủ tục có thể được thực hiện theo kênh trực tiếp hoặc trực tuyến khi dịch vụ công hỗ trợ."},
        {"id":"RESIDENCE_NOTEBOOK_2026:delete_permanent","unit_type":"procedure","title":"Xóa đăng ký thường trú","text":"Cổng Dịch vụ công Bộ Công an hiện liệt kê thủ tục Xóa đăng ký thường trú trong lĩnh vực đăng ký, quản lý cư trú; thủ tục hiện được tiếp nhận tại Công an cấp xã và có dịch vụ công trực tuyến."},
        {"id":"RESIDENCE_NOTEBOOK_2026:temporary","unit_type":"procedure","title":"Đăng ký tạm trú","text":"Thủ tục Đăng ký tạm trú thực hiện tại Công an cấp xã hoặc trực tuyến; thời hạn giải quyết 03 ngày làm việc khi hồ sơ hợp lệ."},
        {"id":"RESIDENCE_NOTEBOOK_2026:extend_temporary","unit_type":"procedure","title":"Gia hạn tạm trú","text":"Cổng Dịch vụ công Bộ Công an hiện liệt kê thủ tục Gia hạn tạm trú trong lĩnh vực đăng ký, quản lý cư trú. Khi hướng dẫn chi tiết hồ sơ phải bám đúng trường hợp và dữ liệu hiện có, không mặc định một bộ giấy tờ cho mọi trường hợp."},
        {"id":"RESIDENCE_NOTEBOOK_2026:split_household","unit_type":"procedure","title":"Tách hộ","text":"Cổng Dịch vụ công Bộ Công an hiện liệt kê thủ tục Tách hộ trong lĩnh vực đăng ký, quản lý cư trú. Việc giải quyết thuộc cơ quan đăng ký cư trú; chi tiết điều kiện và hồ sơ phải đối chiếu tình trạng chỗ ở và quan hệ hộ cụ thể."},
        {"id":"RESIDENCE_NOTEBOOK_2026:adjust","unit_type":"procedure","title":"Điều chỉnh thông tin về cư trú","text":"Thủ tục Điều chỉnh thông tin về cư trú trong Cơ sở dữ liệu về cư trú thực hiện tại Công an cấp xã hoặc trực tuyến; thời hạn giải quyết 03 ngày làm việc theo Cổng Dịch vụ công Bộ Công an."},
        {"id":"RESIDENCE_NOTEBOOK_2026:declare","unit_type":"procedure","title":"Khai báo thông tin về cư trú","text":"Cổng Dịch vụ công Bộ Công an hiện liệt kê thủ tục Khai báo thông tin về cư trú đối với người chưa đủ điều kiện đăng ký thường trú, đăng ký tạm trú trong nhóm đăng ký, quản lý cư trú."},
        {"id":"RESIDENCE_NOTEBOOK_2026:confirmation","unit_type":"procedure","title":"Xác nhận thông tin về cư trú","text":"Xác nhận thông tin về cư trú thực hiện tại cơ quan đăng ký cư trú/Công an cấp xã hoặc trực tuyến. Nếu thông tin đã có trong Cơ sở dữ liệu quốc gia về dân cư thì thời hạn giải quyết không quá 1/2 ngày làm việc; nếu cần xác minh thì không quá 03 ngày làm việc."},
        {"id":"RESIDENCE_NOTEBOOK_2026:delete_temporary","unit_type":"procedure","title":"Xóa đăng ký tạm trú","text":"Thủ tục Xóa đăng ký tạm trú thực hiện tại Công an cấp xã hoặc trực tuyến; thời hạn giải quyết 02 ngày làm việc theo Cổng Dịch vụ công Bộ Công an."},
        {"id":"RESIDENCE_NOTEBOOK_2026:temporary_absence","unit_type":"procedure","title":"Khai báo tạm vắng","text":"Cổng Dịch vụ công Bộ Công an hiện liệt kê thủ tục Khai báo tạm vắng trong lĩnh vực đăng ký, quản lý cư trú."},
        {"id":"RESIDENCE_NOTEBOOK_2026:stay_notification","unit_type":"procedure","title":"Thông báo lưu trú","text":"Từ ngày 21/05/2026, Bộ Công an triển khai hệ thống thống nhất để thông báo lưu trú đối với công dân Việt Nam và khai báo tạm trú cho người nước ngoài. Thông báo lưu trú có thể thực hiện qua phần mềm/hệ thống điện tử theo quy định hiện hành."},
    ])

    _doc(
        "PASSPORT_CURRENT_2026",
        "Quản lý xuất nhập cảnh - hộ chiếu phổ thông trong nước",
        "TTHC 1.001456",
        "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=29497",
        ["tinh"],
    )
    db.replace_document_units("PASSPORT_CURRENT_2026", [
        {"id":"PASSPORT_CURRENT_2026:issue","unit_type":"procedure","title":"Cấp hộ chiếu phổ thông ở trong nước tại cấp tỉnh","text":"Thủ tục cấp hộ chiếu phổ thông ở trong nước thực hiện tại Công an cấp tỉnh; có thể thực hiện trực tiếp, trực tuyến hoặc qua dịch vụ bưu chính theo trường hợp. Thời hạn giải quyết thông thường không quá 08 ngày làm việc kể từ khi nhận đủ hồ sơ theo quy định."},
        {"id":"PASSPORT_CURRENT_2026:scope","unit_type":"guidance","title":"Phạm vi nguồn xuất nhập cảnh","text":"Nguồn này dùng cho hướng dẫn về hộ chiếu phổ thông ở trong nước thuộc thẩm quyền Công an cấp tỉnh. Nếu người dân hỏi thủ tục xuất nhập cảnh khác, AI phải xác định đúng thủ tục trước khi nêu hồ sơ, phí hoặc thời hạn."},
    ])

    _doc(
        "SECURITY_BUSINESS_CURRENT_2026",
        "Quản lý ngành, nghề đầu tư kinh doanh có điều kiện về an ninh, trật tự",
        "TTHC 2.001478; QĐ 1523/QĐ-BCA-C06",
        "https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26115",
        ["tinh"],
    )
    db.replace_document_units("SECURITY_BUSINESS_CURRENT_2026", [
        {"id":"SECURITY_BUSINESS_CURRENT_2026:new_certificate","unit_type":"procedure","title":"Cấp mới Giấy chứng nhận đủ điều kiện về an ninh, trật tự tại cấp tỉnh","text":"Tổ chức, cá nhân thuộc nhóm ngành, nghề do Công an cấp tỉnh giải quyết nộp hồ sơ cấp mới Giấy chứng nhận đủ điều kiện về an ninh, trật tự tại Phòng Cảnh sát quản lý hành chính về trật tự xã hội Công an cấp tỉnh. Cổng Dịch vụ công Bộ Công an công bố thời hạn giải quyết 05 ngày làm việc đối với thủ tục này."},
        {"id":"SECURITY_BUSINESS_CURRENT_2026:scope","unit_type":"guidance","title":"Phạm vi nguồn ngành nghề ANTT","text":"Không phải mọi ngành, nghề kinh doanh có điều kiện đều cùng một cơ quan giải quyết. AI phải xác định loại ngành nghề trước khi kết luận thẩm quyền, hồ sơ hoặc phí."},
    ])

    _doc(
        "WEAPONS_CURRENT_2026",
        "Quản lý vũ khí, vật liệu nổ, công cụ hỗ trợ và pháo tại cấp tỉnh",
        "TTHC 1.000468 và nhóm TTHC liên quan",
        "https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26785",
        ["tinh"],
    )
    db.replace_document_units("WEAPONS_CURRENT_2026", [
        {"id":"WEAPONS_CURRENT_2026:support_tool_permit","unit_type":"procedure","title":"Cấp Giấy phép sử dụng công cụ hỗ trợ tại Công an cấp tỉnh","text":"Cơ quan, tổ chức, doanh nghiệp thuộc trường hợp được phép có thể nộp hồ sơ cấp Giấy phép sử dụng công cụ hỗ trợ tại Phòng Cảnh sát quản lý hành chính về trật tự xã hội Công an cấp tỉnh bằng hình thức trực tiếp, trực tuyến hoặc qua dịch vụ bưu chính theo thủ tục công bố."},
        {"id":"WEAPONS_CURRENT_2026:scope","unit_type":"guidance","title":"Phạm vi nguồn vũ khí, vật liệu nổ, công cụ hỗ trợ","text":"Các thủ tục về vũ khí, vật liệu nổ, công cụ hỗ trợ phụ thuộc loại giấy phép, loại phương tiện và tư cách cơ quan/tổ chức. AI không được suy diễn điều kiện trang bị hoặc thành phần hồ sơ nếu chưa retrieve đúng thủ tục."},
    ])

    _doc(
        "CRIMINAL_RECORD_CURRENT_2026",
        "Lý lịch tư pháp thực hiện tại Công an cấp tỉnh",
        "TTHC 3.000333",
        "https://dichvucong.bocongan.gov.vn/public/link-to/chi-tiet-thu-tuc?ma-thu-tuc=61555",
        ["tinh"],
    )
    db.replace_document_units("CRIMINAL_RECORD_CURRENT_2026", [
        {"id":"CRIMINAL_RECORD_CURRENT_2026:citizen","unit_type":"procedure","title":"Cấp Phiếu lý lịch tư pháp cho cá nhân tại Công an cấp tỉnh","text":"Cấp Phiếu lý lịch tư pháp cho công dân Việt Nam, người nước ngoài đang cư trú tại Việt Nam được thực hiện tại Công an cấp tỉnh; có thể thực hiện trực tiếp, trực tuyến hoặc qua dịch vụ bưu chính. Thời hạn thông thường là 10 ngày kể từ khi nhận yêu cầu hợp lệ; một số trường hợp cần xác minh có thể không quá 15 ngày."},
    ])

    _doc(
        "DRIVING_LICENCE_CURRENT_2026",
        "Sát hạch, cấp giấy phép lái xe - nhóm thủ tục tại Công an cấp tỉnh",
        "Lĩnh vực Sát hạch, cấp giấy phép lái xe",
        "https://dichvucong.bocongan.gov.vn/",
        ["tinh"],
    )
    db.replace_document_units("DRIVING_LICENCE_CURRENT_2026", [
        {"id":"DRIVING_LICENCE_CURRENT_2026:scope","unit_type":"guidance","title":"Nhóm thủ tục sát hạch, cấp giấy phép lái xe","text":"Cổng Dịch vụ công Bộ Công an hiện có lĩnh vực Sát hạch, cấp giấy phép lái xe với các thủ tục do Công an cấp tỉnh thực hiện. AI phải xác định đúng nhu cầu của cá nhân hoặc cơ sở sát hạch trước khi nêu hồ sơ, thời hạn hay kết quả."},
        {"id":"DRIVING_LICENCE_CURRENT_2026:test_center_type3","unit_type":"procedure","title":"Cấp giấy phép cho trung tâm sát hạch lái xe loại 3","text":"Thủ tục cấp giấy phép cho trung tâm sát hạch lái xe loại 3 do Công an cấp tỉnh thực hiện; Cổng Dịch vụ công Bộ Công an công bố thời hạn 05 ngày làm việc kể từ ngày nhận đủ hồ sơ theo quy định."},
    ])
