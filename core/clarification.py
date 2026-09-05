"""Làm rõ linh hoạt cho lĩnh vực chưa có nguồn nghiệp vụ được duyệt.

Các câu ở đây không phải là tư vấn pháp luật, không nêu thẩm quyền, biểu mẫu,
thời hạn hay kết luận. Chúng chỉ giúp người dân nói đúng nhu cầu để hệ thống
không trả lời chung chung và không bịa khi chưa có nguồn chính thức.
"""

import re
import unicodedata


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%\s]", " ", text)).strip()


TOPIC_CLARIFICATIONS = (
    # Phải đứng trước nhóm điều kiện kinh doanh karaoke: "hát karaoke ồn ào"
    # là phản ánh tiếng ồn, không phải yêu cầu về ngành nghề kinh doanh.
    (("tieng on", "on ao", "hat karaoke", "karaoke on"),
     "Anh/chị đang phản ánh tiếng ồn sinh hoạt. Kho demo chưa có nguồn đã duyệt để xác định cách xử lý cụ thể; sự việc xảy ra ở đâu và thường vào thời điểm nào?"),
    (("ho chieu", "xuat nhap canh", "thi thuc", "visa"),
     "Nội dung này thuộc nhóm hộ chiếu, thị thực hoặc xuất nhập cảnh. Kho demo chưa có nguồn đã duyệt để nêu thủ tục chi tiết; anh/chị đang cần cấp mới, cấp lại hay gia hạn giấy tờ nào?"),
    (("ly lich tu phap", "phieu tu phap"),
     "Anh/chị đang hỏi về lý lịch tư pháp. Kho demo chưa có nguồn đã duyệt để khẳng định hồ sơ, nơi nộp hoặc thời hạn; anh/chị cần xin phiếu hay đang cần tra cứu thông tin?"),
    (("khieu nai", "to cao", "don thu", "phan anh kien nghi"),
     "Nội dung này thuộc nhóm khiếu nại, tố cáo hoặc phản ánh. Kho demo chưa có nguồn đã duyệt để xác định thẩm quyền hay mẫu đơn; anh/chị muốn phản ánh hành vi của cá nhân, cơ quan hay cán bộ?"),
    (("toa an", "vu an dan su", "khoi kien", "ban an"),
     "Anh/chị đang hỏi về thủ tục tại Tòa án. Kho demo chưa có nguồn đã duyệt để hướng dẫn hồ sơ hoặc thời hạn; việc anh/chị cần giải quyết là tranh chấp dân sự, hôn nhân gia đình hay nội dung khác?"),
    (("thi hanh an", "cuong che thi hanh"),
     "Nội dung này thuộc thi hành án. Kho demo chưa có nguồn đã duyệt để tư vấn chi tiết; anh/chị đang hỏi về bản án dân sự, quyết định xử phạt hay một việc khác?"),
    (("trieu tap", "co quan dieu tra", "bi can", "bi cao", "nguoi lam chung", "luat su"),
     "Anh/chị đang hỏi về tố tụng hoặc hoạt động điều tra. Kho demo chưa có nguồn đã duyệt để hướng dẫn quyền, nghĩa vụ hay thủ tục cụ thể; anh/chị đang được mời làm việc với tư cách nào hoặc chỉ cần hiểu nội dung giấy mời?"),
    (("tranh chap dat", "dat dai", "ranh dat", "so do", "so hong"),
     "Nội dung này thuộc tranh chấp hoặc thủ tục đất đai. Kho demo chưa có nguồn đã duyệt để nêu hồ sơ hay thẩm quyền; anh/chị đang hỏi về ranh giới, giấy tờ đất hay việc chuyển quyền?"),
    (("nha o", "tranh chap nha", "thue nha"),
     "Anh/chị đang hỏi về nhà ở hoặc hợp đồng thuê. Kho demo chưa có nguồn đã duyệt để tư vấn chi tiết; anh/chị đang gặp tranh chấp thuê nhà, quyền sở hữu hay nội dung khác?"),
    (("hon nhan", "ly hon", "nuoi con", "cap duong"),
     "Nội dung này thuộc hôn nhân và gia đình. Kho demo chưa có nguồn đã duyệt để đưa hướng dẫn pháp lý cụ thể; anh/chị cần hỏi về ly hôn, quyền nuôi con hay cấp dưỡng?"),
    (("thua ke", "di chuc", "chia tai san"),
     "Anh/chị đang hỏi về thừa kế hoặc chia tài sản. Kho demo chưa có nguồn đã duyệt để tư vấn chi tiết; anh/chị cần hỏi về di chúc, di sản hay tranh chấp giữa những người thừa kế?"),
    (("no tien", "hop dong", "vay tien", "mua ban"),
     "Nội dung này thuộc nợ, hợp đồng hoặc giao dịch dân sự. Kho demo chưa có nguồn đã duyệt để kết luận trách nhiệm; anh/chị đang cần hỏi về khoản vay, hợp đồng mua bán hay việc bị chiếm giữ tài sản?"),
    (("lao dong", "luong", "bao hiem xa hoi", "bhxh"),
     "Anh/chị đang hỏi về lao động hoặc bảo hiểm xã hội. Kho demo chưa có nguồn đã duyệt để nêu thủ tục chi tiết; anh/chị đang cần hỏi về hợp đồng, tiền lương hay chế độ bảo hiểm?"),
    (("thue", "ma so thue", "hoa don"),
     "Nội dung này thuộc thuế hoặc hóa đơn. Kho demo chưa có nguồn đã duyệt để hướng dẫn chi tiết; anh/chị đang hỏi về mã số thuế, khai thuế hay hóa đơn?"),
    (("khai sinh", "khai tu", "ket hon", "ho tich"),
     "Anh/chị đang hỏi về hộ tịch. Kho demo chưa có nguồn đã duyệt để khẳng định thủ tục; anh/chị cần đăng ký khai sinh, khai tử, kết hôn hay thay đổi thông tin hộ tịch?"),
    (("lo du lieu", "lua dao mang", "tai khoan bi hack", "mat facebook", "mat zalo"),
     "Anh/chị đang phản ánh sự cố dữ liệu hoặc tài khoản trên mạng. Kho demo chưa có nguồn đã duyệt để kết luận hành vi; anh/chị còn giữ tin nhắn, đường dẫn, ảnh chụp hoặc thông tin tài khoản liên quan không?"),
    (("bao ve nguoi tieu dung", "hang gia", "mua hang"),
     "Nội dung này thuộc giao dịch tiêu dùng. Kho demo chưa có nguồn đã duyệt để hướng dẫn chi tiết; anh/chị gặp vấn đề về hàng hóa, hợp đồng mua bán hay thông tin quảng cáo?"),
    (("o nhiem", "moi truong", "tieng on"),
     "Anh/chị đang phản ánh vấn đề môi trường hoặc trật tự sinh hoạt. Kho demo chưa có nguồn đã duyệt để xác định cách xử lý; sự việc xảy ra ở đâu và thuộc tiếng ồn, xả thải hay nội dung khác?"),
    (("xay dung", "giay phep xay dung", "cong trinh"),
     "Anh/chị đang hỏi về xây dựng. Kho demo chưa có nguồn đã duyệt để nêu thủ tục hoặc thẩm quyền; anh/chị cần hỏi về giấy phép, trật tự xây dựng hay tranh chấp công trình?"),
    (("phong chay", "chua chay", "pccc"),
     "Nội dung này thuộc phòng cháy, chữa cháy. Kho demo chưa có nguồn đã duyệt để hướng dẫn chi tiết; anh/chị đang hỏi về cơ sở kinh doanh, nhà ở hay một sự cố cụ thể?"),
    (("co bac", "danh bac"),
     "Anh/chị đang phản ánh hoặc hỏi về cờ bạc. Kho demo chưa có nguồn đã duyệt để kết luận trách nhiệm; đây là việc anh/chị muốn trình báo hay chỉ cần hướng dẫn bảo toàn thông tin?"),
    (("bao luc gia dinh", "bao hanh", "xam hai tre em"),
     "Tôi đã ghi nhận nội dung có dấu hiệu bạo lực hoặc xâm hại. Kho demo chưa có nguồn đã duyệt để hướng dẫn chi tiết; nếu có nguy cơ trước mắt, anh/chị cần tìm hỗ trợ trực tiếp ngay. Anh/chị có đang ở nơi an toàn và cần trình báo sự việc hay chỉ cần thông tin thủ tục?"),
    (("mat nguoi", "that lac nguoi", "nguoi than mat tich"),
     "Anh/chị đang phản ánh việc người thân mất liên lạc. Kho demo chưa có nguồn đã duyệt để hướng dẫn quy trình chi tiết; người đó mất liên lạc từ khi nào và anh/chị có biết khu vực cuối cùng không?"),
    (("mat xe", "that lac xe"),
     "Anh/chị đang phản ánh mất hoặc thất lạc xe. Kho demo chưa có nguồn đã duyệt để xác định thủ tục chi tiết; xe mất ở thời điểm, khu vực nào và anh/chị còn giấy tờ xe hoặc thông tin nhận dạng không?"),
    (("con dau", "an ninh trat tu", "cam do", "karaoke", "luu tru"),
     "Anh/chị đang hỏi về ngành nghề, con dấu hoặc điều kiện an ninh trật tự. Kho demo chưa có nguồn đã duyệt để nêu thủ tục; anh/chị đang chuẩn bị cho loại cơ sở hoặc giấy tờ nào?"),
    (("phao", "vu khi", "cong cu ho tro"),
     "Anh/chị đang hỏi về pháo, vũ khí hoặc công cụ hỗ trợ. Kho demo chưa có nguồn đã duyệt để tư vấn điều kiện cụ thể; anh/chị cần phản ánh sự việc, giao nộp hay hỏi quy định chung?"),
    (("phat nguoi", "phat giao thong", "giay phep lai xe"),
     "Anh/chị đang hỏi về xử phạt giao thông. Kho demo chưa có nguồn đã duyệt để nêu mức phạt, thời hạn hay cách nộp; anh/chị cần hỏi về biên bản, giấy phép lái xe hay tra cứu vi phạm?"),
    (("ma tuy",),
     "Anh/chị đang hỏi hoặc phản ánh nội dung về ma túy. Kho demo chưa có nguồn đã duyệt để kết luận trách nhiệm; anh/chị cần trình báo sự việc cụ thể hay chỉ cần thông tin phòng ngừa?"),
)


def unverified_topic_key(question):
    """Trả về nhãn chủ đề chưa có nguồn đã duyệt, hoặc ``None``.

    Nhãn chỉ dùng để chặn truy xuất lan man vào văn bản không liên quan. Nó
    không phải kết luận về tính chất pháp lý của việc người dân nêu.
    """
    normalized = _norm(question)
    for index, (keywords, _reply) in enumerate(TOPIC_CLARIFICATIONS):
        if any(keyword in normalized for keyword in keywords):
            return index
    return None


def clarification_for_unverified_topic(question):
    topic_key = unverified_topic_key(question)
    if topic_key is None:
        return None
    return TOPIC_CLARIFICATIONS[topic_key][1]
