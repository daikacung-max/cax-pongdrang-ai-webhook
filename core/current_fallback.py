"""Grounded fallback overlay for current (12/09/2026) knowledge.

The legacy verifier remains an audit-safe fallback for older verified domains.
This overlay intercepts domains whose authority/procedure changed in 2026 so a
provider timeout can never resurrect superseded guidance.
"""

import re
import unicodedata

from core.verifier import grounded_dynamic_fallback as legacy_grounded_fallback, norm


def _has(units, document_id):
    return any(str(x.get("document_id") or "") == document_id for x in (units or []))


def _has_unit(units, unit_id):
    return any(str(x.get("id") or "") == unit_id for x in (units or []))


def _citizen_norm(question):
    q = norm(question)
    q = "".join(c for c in unicodedata.normalize("NFD", q) if unicodedata.category(c) != "Mn")
    q = q.replace("dang ki", "dang ky")
    q = q.replace("lam lai can cuoc", "cap lai can cuoc")
    q = q.replace("lam lai cccd", "cap lai cccd")
    return q


def grounded_dynamic_fallback(question, retrieved_units):
    q = _citizen_norm(question)

    if _has(retrieved_units, "RESIDENCE_VNEID_APP_STEPS_2026") and "tam tru" in q:
        return (
            "Anh/chị có thể làm trên VNeID theo các bước sau: mở VNeID và đăng nhập, vào Thủ tục hành chính, chọn Đăng ký tạm trú. "
            "Chọn Tạo mới yêu cầu, rồi chọn đăng ký cho bản thân hoặc khai hộ. Kiểm tra thông tin, chọn lập hộ mới hoặc đăng ký vào hộ đã có; "
            "chọn cách xác nhận của chủ hộ/chủ sở hữu chỗ ở hợp pháp theo lựa chọn VNeID hiển thị. "
            "Tiếp theo chọn và điền địa chỉ tạm trú, quan hệ với chủ hộ, thêm thành viên nếu cùng đăng ký; kiểm tra lại hồ sơ. "
            "Nếu ứng dụng yêu cầu giấy tờ theo trường hợp thì đính kèm bản rõ nét, sau đó nộp lệ phí theo chức năng của ứng dụng và lưu mã hồ sơ để theo dõi. "
            "Cần tài khoản VNeID mức độ 02; nếu dữ liệu cư trú chưa có hoặc không khớp, anh/chị đến Công an cấp xã nơi đăng ký tạm trú để được cập nhật và nộp hồ sơ trực tiếp."
        )

    if _has(retrieved_units, "CITIZEN_ID_5230_COMMUNE_2026"):
        is_reissue = any(x in q for x in [
            "mat can cuoc", "mat cccd", "cap lai can cuoc", "cap lai cccd",
            "cap lai", "hu hong", "khong su dung duoc", "can cuoc bi mat", "cccd bi mat",
        ])
        if is_reissue:
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
        under14_language = any(x in q for x in [
            "duoi 14", "tre em", "con toi", "be nha toi", "nguoi dai dien", "dua con", "dua tre"
        ]) or bool(re.search(r"\b(?:con|be|tre)\s+\d{1,2}\s+tuoi\b", q))
        if under14_language:
            return (
                "Theo Quyết định 5230/QĐ-BCA-C06, người từ đủ 06 đến dưới 14 tuổi làm căn cước trực tiếp tại Công an cấp xã cùng người đại diện hợp pháp. "
                "Người dưới 06 tuổi có thể được người đại diện hợp pháp nộp trực tuyến toàn trình qua Cổng dịch vụ công quốc gia hoặc VNeID; "
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
        rental_followup = any(x in q for x in [
            "o thue", "nha thue", "thue nha", "thue tro", "o tro", "phong tro",
            "o nho", "nha tro", "cho thue",
        ])
        temporary_context = _has_unit(retrieved_units, "RESIDENCE_CURRENT_2026:temporary")
        if "tam tru" in q or (temporary_context and rental_followup):
            if temporary_context and rental_followup:
                return (
                    "Với trường hợp anh/chị ở thuê/ở trọ, thủ tục đang trao đổi vẫn là đăng ký tạm trú. "
                    "Nguồn cư trú hiện hành xác nhận thủ tục thực hiện tại Công an cấp xã hoặc trực tuyến và được giải quyết trong 03 ngày làm việc khi hồ sơ hợp lệ. "
                    "Thành phần hồ sơ phụ thuộc trường hợp chỗ ở cụ thể; thông tin, giấy tờ đã khai thác được từ cơ sở dữ liệu hoặc VNeID thì không yêu cầu nộp lại. "
                    "Nguồn đang dùng chưa liệt kê riêng từng loại giấy tờ cho nhà thuê, nên tôi không tự bổ sung giấy tờ chưa được nguồn xác nhận."
                )
            return (
                "Đăng ký tạm trú thực hiện tại Công an cấp xã hoặc trực tuyến, thời hạn giải quyết 03 ngày làm việc khi hồ sơ hợp lệ. "
                "Thành phần hồ sơ phụ thuộc trường hợp cụ thể; thông tin, giấy tờ đã được khai thác từ cơ sở dữ liệu hoặc VNeID thì không yêu cầu nộp lại."
            )

    if _has(retrieved_units, "VEHICLE_CURRENT_2026"):
        if "sang ten" in q and _has(retrieved_units, "VEHICLE_TRANSFER_LOCAL_2026"):
            return (
                "Sang tên xe thực hiện tại Công an cấp xã được phân cấp đăng ký xe, nên cần xác nhận điểm tiếp nhận cụ thể tại địa phương. "
                "Chủ xe đang đứng tên làm thủ tục thu hồi trước, sau đó người nhận chuyển nhượng đăng ký sang tên; hồ sơ gồm giấy khai đăng ký xe, giấy tờ của chủ xe, chứng từ chuyển quyền sở hữu, chứng từ lệ phí trước bạ và chứng nhận thu hồi. "
                "Hai bước cấp chứng nhận không quá 02 ngày làm việc khi hồ sơ hợp lệ. Anh/chị là người đang đứng tên xe hay người nhận chuyển nhượng?"
            )
        first_registration = any(x in q for x in ["mua xe moi", "lan dau", "xe may moi", "xe moi"])
        # The current first-registration route may be selected from a form or
        # document question (for example, "ĐKX10 dùng khi nào?"). In that
        # case the retrieved first-registration unit is the authoritative
        # intent signal even when the question does not repeat "xe mới".
        first_registration = first_registration or (
            (
                _has_unit(retrieved_units, "VEHICLE_CURRENT_2026:first_domestic_online")
                or _has_unit(retrieved_units, "VEHICLE_REGISTRATION_2026:first_registration_documents")
            )
            and any(x in q for x in ["dkx10", "giay khai dang ky xe"])
        )
        if first_registration:
            form_note = (
                "Giấy khai đăng ký xe mẫu ĐKX10 là thành phần hồ sơ đăng ký lần đầu theo nguồn thủ tục hiện hành. "
                if "dkx10" in q else ""
            )
            return (
                form_note
                + "Nếu anh/chị đang đăng ký lần đầu xe được sản xuất, lắp ráp trong nước, chủ xe kê khai qua Cổng dịch vụ công hoặc VNeID; "
                "cơ quan đăng ký xe được tổ chức ở cấp tỉnh và cấp xã theo phân cấp. Thời hạn cấp chứng nhận đăng ký xe và cấp mới biển số không quá 02 ngày làm việc "
                "kể từ khi nhận đủ hồ sơ hợp lệ."
            )
        if any(x in q for x in ["dang ky xe", "bien so", "xe may", "xe mo to", "xe gan may"]):
            return (
                "Anh/chị có thể làm thủ tục đăng ký xe tại cơ quan đăng ký xe cấp tỉnh hoặc cấp xã theo phân cấp. "
                "Cách thực hiện và hồ sơ phụ thuộc loại thủ tục cụ thể. Anh/chị cho biết đây là xe mới đăng ký lần đầu hay trường hợp sang tên/cấp đổi để tôi hướng dẫn đúng nguồn, "
                "không áp dụng nhầm quy trình của xe đăng ký lần đầu."
            )

    article_134 = any(str(x.get("article") or "") == "134" for x in (retrieved_units or []))
    if article_134 and any(x in q for x in ["camera", "video", "clip", "ghi hinh"]):
        return (
            "Đoạn camera/video là chứng cứ quan trọng đối với việc xác minh sự việc. Anh/chị nên giữ nguyên file gốc, không chỉnh sửa, sao lưu thêm một bản và ghi lại "
            "thời gian, địa điểm, người biết sự việc; khi trình báo thì cung cấp bản sao theo hướng dẫn và giữ bản gốc để đối chiếu. Việc xem xét trách nhiệm theo Điều 134 "
            "Bộ luật Hình sự còn phải dựa trên toàn bộ diễn biến, thương tích và các tình tiết được xác minh, nên chưa thể kết luận chỉ từ video."
        )

    return legacy_grounded_fallback(question, retrieved_units)
