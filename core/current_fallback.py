"""Grounded fallback overlay for current (12/09/2026) knowledge.

The legacy verifier remains an audit-safe fallback for older verified domains.
This overlay intercepts domains whose authority/procedure changed in 2026 so a
provider timeout can never resurrect superseded guidance.
"""

from core.verifier import grounded_dynamic_fallback as legacy_grounded_fallback, norm


def _has(units, document_id):
    return any(str(x.get("document_id") or "") == document_id for x in (units or []))


def grounded_dynamic_fallback(question, retrieved_units):
    q = norm(question)

    if _has(retrieved_units, "CITIZEN_ID_5230_COMMUNE_2026"):
        if any(x in q for x in ["mat can cuoc", "mat cccd", "cap lai", "hu hong", "khong su dung duoc"]):
            return (
                "Theo thủ tục hiện hành được công bố tại Quyết định 5230/QĐ-BCA-C06, anh/chị có thể đề nghị cấp lại thẻ căn cước tại Công an cấp xã "
                "hoặc Bộ phận một cửa cấp xã trong cả nước không phụ thuộc nơi cư trú nếu đã triển khai. Trường hợp mất thẻ hoặc thẻ hư hỏng không sử dụng được "
                "có thể nộp trực tuyến toàn trình qua Cổng dịch vụ công quốc gia hoặc VNeID; thời hạn giải quyết không quá 07 ngày làm việc."
            )
        if any(x in q for x in ["cap doi", "doi can cuoc", "doi cccd", "sap het han", "thong tin thay doi"]):
            return (
                "Theo Quyết định 5230/QĐ-BCA-C06, cấp đổi thẻ căn cước hiện có thể thực hiện tại Công an cấp xã hoặc Bộ phận một cửa cấp xã trong cả nước "
                "không phụ thuộc nơi cư trú nếu đã triển khai. Anh/chị cũng có thể đăng ký thời gian, địa điểm qua Cổng dịch vụ công quốc gia hoặc VNeID; "
                "thời hạn giải quyết không quá 07 ngày làm việc. Nếu thông tin dân cư có thay đổi thì cần điều chỉnh dữ liệu trước khi cấp đổi."
            )
        if any(x in q for x in ["duoi 14", "tre em", "con toi", "be nha toi"]):
            return (
                "Theo Quyết định 5230/QĐ-BCA-C06, người từ đủ 06 đến dưới 14 tuổi làm căn cước trực tiếp tại Công an cấp xã cùng người đại diện hợp pháp. "
                "Người dưới 06 tuổi có thể được người đại diện hợp pháp nộp hồ sơ trực tuyến toàn trình qua Cổng dịch vụ công quốc gia hoặc VNeID; "
                "thời hạn giải quyết chung không quá 07 ngày làm việc."
            )
        if any(x in q for x in ["14 tuoi", "tu du 14"]):
            return (
                "Người từ đủ 14 tuổi có thể làm thủ tục cấp thẻ căn cước tại Công an cấp xã hoặc Bộ phận một cửa cấp xã trong cả nước không phụ thuộc nơi cư trú "
                "nếu đã triển khai, theo Quyết định 5230/QĐ-BCA-C06. Có thể đăng ký thời gian, địa điểm qua Cổng dịch vụ công quốc gia hoặc VNeID; "
                "thời hạn giải quyết không quá 07 ngày làm việc."
            )
        if any(x in q for x in ["cap moi", "lan dau"]):
            return (
                "Thủ tục cấp căn cước hiện được giải quyết tại Công an cấp xã theo Quyết định 5230/QĐ-BCA-C06, nhưng cách thực hiện khác nhau theo độ tuổi. "
                "Anh/chị cho biết người cần làm căn cước đã đủ 14 tuổi chưa để tôi hướng dẫn đúng trường hợp."
            )
        return (
            "Quyết định 5230/QĐ-BCA-C06 đã công bố nhóm thủ tục căn cước mới tại Công an cấp xã, gồm cấp/cấp đổi/cấp lại thẻ căn cước và các thủ tục khai thác, "
            "cập nhật dữ liệu căn cước. Anh/chị cho biết cần cấp mới, cấp đổi, cấp lại hay điều chỉnh dữ liệu để tôi hướng dẫn đúng phần hồ sơ."
        )

    if _has(retrieved_units, "RESIDENCE_CURRENT_2026"):
        if "xac nhan" in q and "cu tru" in q:
            return (
                "Xác nhận thông tin về cư trú thực hiện tại Công an cấp xã/cơ quan đăng ký cư trú hoặc trực tuyến. Nếu thông tin đã có trong Cơ sở dữ liệu quốc gia "
                "về dân cư thì thời hạn giải quyết không quá 1/2 ngày làm việc; nếu cần xác minh thì không quá 03 ngày làm việc."
            )
        if "thuong tru" in q:
            return (
                "Đăng ký thường trú thực hiện tại Công an cấp xã hoặc trực tuyến, thời hạn giải quyết 07 ngày làm việc. Hồ sơ phụ thuộc loại chỗ ở và điều kiện cụ thể; "
                "thông tin, giấy tờ đã khai thác được từ cơ sở dữ liệu hoặc VNeID thì không yêu cầu nộp lại. Anh/chị đăng ký vào nhà của mình, nhà người thân hay nhà thuê/mượn/ở nhờ?"
            )
        if "tam tru" in q:
            return (
                "Đăng ký tạm trú thực hiện tại Công an cấp xã hoặc trực tuyến, thời hạn giải quyết 03 ngày làm việc khi hồ sơ hợp lệ. "
                "Thông tin, giấy tờ đã được khai thác từ cơ sở dữ liệu hoặc VNeID thì không yêu cầu nộp lại."
            )

    if _has(retrieved_units, "VEHICLE_CURRENT_2026"):
        if any(x in q for x in ["mua xe moi", "dang ky xe", "lan dau", "bien so"]):
            return (
                "Theo nguồn đăng ký xe hiện hành, cơ quan đăng ký xe được tổ chức ở cấp tỉnh và cấp xã theo phân cấp. Với thủ tục 1.012575 đối với xe sản xuất, "
                "lắp ráp trong nước, chủ xe kê khai qua Cổng dịch vụ công hoặc VNeID; thời hạn cấp chứng nhận đăng ký xe và cấp mới biển số không quá 02 ngày làm việc "
                "kể từ khi nhận đủ hồ sơ hợp lệ. Không áp dụng hướng dẫn cũ đến Công an cấp huyện."
            )

    return legacy_grounded_fallback(question, retrieved_units)
