"""Hướng dẫn an toàn, hữu ích cho nội dung chưa có nguồn chuyên biệt.

Thiếu nguồn chuyên biệt không đồng nghĩa với từ chối hỗ trợ. Module này luôn
trả một hướng dẫn thực dụng, nhưng không tự bịa điều luật, mức phạt, tội danh,
thời hạn, biểu mẫu hay thẩm quyền chưa được kiểm chứng.
"""

import re
import unicodedata

from config import HOTLINE, UNIT_NAME


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%\s]", " ", text)).strip()


def _public_safety_reply(kind, extra=""):
    base = (
        f"Anh/chị có thể báo ngay cho {UNIT_NAME} qua số trực ban {HOTLINE}. "
        "Nếu sự việc đang diễn ra, anh/chị không nên tự đối đầu hoặc can thiệp khi có nguy cơ mất an toàn. "
        "Hãy ghi nhớ hoặc lưu lại những thông tin có thể thu thập an toàn như thời gian, địa điểm, đặc điểm người/phương tiện, hình ảnh hoặc video nếu có. "
    )
    return base + extra


TOPIC_CLARIFICATIONS = (
    (("tieng on", "on ao", "hat karaoke", "karaoke on"),
     _public_safety_reply(
         "noise",
         "Nếu tiếng ồn đang ảnh hưởng sinh hoạt, anh/chị có thể phản ánh ngay; nếu thuận tiện, cho tôi biết địa điểm và thời điểm đang xảy ra để tôi hướng dẫn cách trình bày tin báo ngắn gọn."
     )),
    (("ho chieu", "xuat nhap canh", "thi thuc", "visa"),
     "Tôi có thể hướng dẫn theo đúng nhu cầu của anh/chị. Anh/chị đang cần cấp mới, cấp lại do mất/hỏng, hay hỏi về một thủ tục xuất nhập cảnh cụ thể? Chỉ cần nói rõ trường hợp, tôi sẽ tách thành các bước cần làm."),
    (("ly lich tu phap", "phieu tu phap"),
     "Tôi có thể hỗ trợ xác định đúng việc cần làm. Anh/chị đang muốn xin Phiếu lý lịch tư pháp, tra cứu tình trạng hồ sơ hay hỏi nơi thực hiện?"),
    (("khieu nai", "to cao", "don thu", "phan anh kien nghi"),
     "Anh/chị có thể trình bày ngắn gọn sự việc, người/cơ quan liên quan, thời gian, địa điểm và điều anh/chị đề nghị giải quyết để xác định đây là khiếu nại, tố cáo hoặc phản ánh. Nếu liên quan cá nhân, cơ quan hay cán bộ, tôi có thể giúp sắp xếp nội dung theo thông tin anh/chị cung cấp mà không tự thêm tình tiết."),
    (("toa an", "vu an dan su", "khoi kien", "ban an"),
     "Tôi có thể giúp anh/chị xác định nhóm việc và chuẩn bị câu hỏi/hồ sơ theo tình huống. Anh/chị đang gặp tranh chấp dân sự, hôn nhân gia đình, thi hành bản án hay vấn đề khác?"),
    (("thi hanh an", "cuong che thi hanh"),
     "Anh/chị cho biết đây là thi hành bản án/quyết định dân sự, quyết định xử phạt hay nội dung khác. Tôi sẽ giúp anh/chị xác định bước tiếp theo và những thông tin cần chuẩn bị."),
    (("trieu tap", "co quan dieu tra", "bi can", "bi cao", "nguoi lam chung", "luat su"),
     "Anh/chị nên đọc kỹ cơ quan ban hành, thời gian, địa điểm và tư cách được ghi trên giấy mời/triệu tập. Nếu anh/chị chép lại nội dung chính của giấy, tôi có thể giải thích từng phần và giúp chuẩn bị những thông tin cần mang theo mà không suy đoán tư cách tố tụng."),
    (("tranh chap dat", "dat dai", "ranh dat", "so do", "so hong"),
     "Anh/chị cho biết tranh chấp liên quan ranh giới, quyền sử dụng, giấy chứng nhận hay chuyển nhượng. Tôi sẽ giúp hệ thống hóa sự việc, tài liệu đang có và hướng xử lý phù hợp với đúng loại tranh chấp."),
    (("nha o", "tranh chap nha", "thue nha"),
     "Anh/chị hãy cho biết vấn đề chính là tiền thuê, hợp đồng, trả nhà, tài sản trong nhà hay quyền sở hữu. Tôi có thể giúp anh/chị sắp xếp chứng cứ, mốc thời gian và nội dung cần trao đổi hoặc phản ánh."),
    (("hon nhan", "ly hon", "nuoi con", "cap duong"),
     "Anh/chị cho biết đang cần hỗ trợ về ly hôn, quyền nuôi con, cấp dưỡng hay tài sản chung. Tôi sẽ hướng dẫn theo đúng nhánh đó và chỉ hỏi thêm thông tin thực sự cần thiết."),
    (("thua ke", "di chuc", "chia tai san"),
     "Anh/chị cho biết có di chúc hay không, tài sản nào đang cần giải quyết và hiện có tranh chấp giữa những người liên quan không. Tôi sẽ giúp sắp xếp tình huống và các bước cần kiểm tra tiếp."),
    (("no tien", "hop dong", "vay tien", "mua ban"),
     "Đây là nhóm việc về nợ, hợp đồng hoặc giao dịch dân sự. Anh/chị nên giữ hợp đồng, tin nhắn, chứng từ chuyển tiền và các thỏa thuận liên quan. Cho tôi biết đây là khoản vay, mua bán hay việc giao tài sản, tôi sẽ giúp anh/chị tách rõ nghĩa vụ, chứng cứ và hướng xử lý tiếp theo."),
    (("lao dong", "luong", "bao hiem xa hoi", "bhxh"),
     "Anh/chị cho biết vấn đề nằm ở hợp đồng, tiền lương, nghỉ việc, bảo hiểm xã hội hay chế độ khác. Tôi sẽ giúp xác định thông tin và tài liệu cần kiểm tra trước khi thực hiện bước tiếp theo."),
    (("thue", "ma so thue", "hoa don"),
     "Anh/chị đang cần hỗ trợ về mã số thuế, kê khai, hóa đơn hay nghĩa vụ thuế của một giao dịch cụ thể? Nói rõ trường hợp, tôi sẽ hướng dẫn theo đúng nhánh và không trộn với thủ tục cư trú."),
    (("khai sinh", "khai tu", "ket hon", "ho tich"),
     "Anh/chị cho biết cần khai sinh, khai tử, đăng ký kết hôn hay thay đổi thông tin hộ tịch. Tôi sẽ giúp xác định đúng loại việc và các thông tin cần chuẩn bị."),
    (("lo du lieu", "lua dao mang", "tai khoan bi hack", "mat facebook", "mat zalo"),
     "Anh/chị nên đổi mật khẩu, đăng xuất các phiên lạ, bật xác thực hai bước nếu còn truy cập được và lưu lại tin nhắn, đường dẫn, ảnh chụp, email hoặc thông tin tài khoản liên quan. Nếu có giao dịch tiền hoặc dấu hiệu chiếm đoạt, hãy báo ngay cho cơ quan chức năng và ngân hàng/nền tảng liên quan."),
    (("bao ve nguoi tieu dung", "hang gia", "mua hang"),
     "Anh/chị nên giữ hóa đơn, đơn hàng, nội dung quảng cáo, tin nhắn trao đổi và hình ảnh hàng hóa. Cho tôi biết vấn đề là hàng không đúng mô tả, không giao hàng, bảo hành hay hoàn tiền, tôi sẽ giúp sắp xếp bước xử lý."),
    (("o nhiem", "moi truong", "tieng on"),
     "Anh/chị nên ghi nhận thời gian, địa điểm, hình ảnh/video nếu có và mức độ ảnh hưởng thực tế. Nếu sự việc đang diễn ra và ảnh hưởng đến khu dân cư, anh/chị có thể phản ánh ngay cho cơ quan chức năng tại địa phương."),
    (("xay dung", "giay phep xay dung", "cong trinh"),
     "Anh/chị đang hỏi về xây dựng: cho biết đang hỏi về giấy phép, trật tự xây dựng, lấn chiếm hay tranh chấp công trình. Tôi sẽ giúp xác định đúng nhóm việc và thông tin cần chuẩn bị."),
    (("phong chay", "chua chay", "pccc"),
     "Nếu đang có cháy, khói hoặc nguy cơ trực tiếp, ưu tiên rời khu vực nguy hiểm và gọi lực lượng cứu hỏa/cơ quan chức năng ngay. Nếu anh/chị đang hỏi về điều kiện PCCC của cơ sở hoặc nhà ở, cho tôi biết loại hình để tôi hướng dẫn theo đúng tình huống."),
    (("co bac", "danh bac", "danh bai", "choi bai an tien", "danh bai an tien", "ca do", "ca cuoc"),
     _public_safety_reply(
         "gambling",
         "Với nhóm người đang đánh bạc/cá cược, anh/chị nên báo vị trí đang xảy ra, thời điểm, số người ước tính và đặc điểm nhận biết nếu quan sát được an toàn. Không cần tự tiếp cận để xác minh hay thu giữ đồ vật. Nếu anh/chị muốn, tôi có thể giúp soạn ngay nội dung tin báo thật ngắn để anh/chị gọi hoặc nhắn cho Công an xã."
     )),
    (("bao luc gia dinh", "bao hanh", "xam hai tre em"),
     _public_safety_reply(
         "violence",
         "Nếu có nguy cơ bị tiếp tục hành hung hoặc có trẻ em/người yếu thế đang gặp nguy hiểm, ưu tiên rời khỏi nơi nguy hiểm và tìm người hỗ trợ ngay. Giữ lại ảnh thương tích, tin nhắn, video và thông tin người chứng kiến nếu có."
     )),
    (("de doa", "bi de doa", "de doa toi"),
     _public_safety_reply(
         "threat",
         "Sự việc xảy ra khi nào và ở đâu? Anh/chị không nên tự đối đầu nếu có nguy cơ mất an toàn; hãy giữ lại tin nhắn, cuộc gọi hoặc hình ảnh liên quan nếu có."
     )),
    (("mat nguoi", "that lac nguoi", "nguoi than mat tich"),
     "Anh/chị nên chuẩn bị ảnh gần nhất, thông tin nhận dạng, số điện thoại, phương tiện, quần áo, thời điểm và nơi cuối cùng còn liên lạc. Có thể báo ngay cho Công an nơi gần nhất để được hỗ trợ xác minh; nếu cho tôi các mốc trên, tôi có thể giúp soạn nội dung trình báo ngắn gọn."),
    (("mat xe", "that lac xe"),
     _public_safety_reply(
         "lost_vehicle",
         "Anh/chị nên chuẩn bị biển số, nhãn hiệu/màu xe, đặc điểm riêng, giấy tờ xe nếu còn, cùng thời gian và vị trí phát hiện mất. Nếu có camera gần khu vực, nên đề nghị giữ lại dữ liệu sớm."
     )),
    (("con dau", "an ninh trat tu", "cam do", "karaoke", "luu tru"),
     "Anh/chị cho biết loại cơ sở hoặc loại giấy tờ cụ thể đang cần làm. Tôi sẽ xác định đúng nhóm thủ tục và hướng dẫn từng bước, tránh trộn với nội dung phản ánh tiếng ồn hoặc cư trú."),
    (("phao", "vu khi", "cong cu ho tro"),
     _public_safety_reply(
         "weapons",
         "Nếu anh/chị phát hiện vật nghi là vũ khí, vật liệu nổ hoặc pháo không rõ nguồn gốc, không nên tự tháo lắp, thử sử dụng hoặc di chuyển khi có nguy cơ. Có thể báo vị trí và đặc điểm quan sát được để cơ quan chức năng kiểm tra."
     )),
    (("phat nguoi", "phat giao thong", "giay phep lai xe"),
     "Anh/chị cho biết đang cần tra cứu vi phạm, xử lý biên bản, giấy phép lái xe hay một thủ tục giao thông khác. Tôi sẽ hướng dẫn theo đúng loại việc, không tự đoán mức phạt khi chưa xác định hành vi cụ thể."),
    (("ma tuy",),
     _public_safety_reply(
         "drugs",
         "Nếu anh/chị phát hiện việc sử dụng, tàng trữ, mua bán hoặc tổ chức sử dụng ma túy, hãy báo địa điểm, thời điểm, người/phương tiện liên quan nếu có thể quan sát an toàn. Không tự tiếp cận, tranh cãi hoặc thu giữ chất/vật nghi liên quan."
     )),
)


def unverified_topic_key(question):
    """Trả về nhãn chủ đề chưa có nguồn chuyên biệt, hoặc ``None``."""
    normalized = _norm(question)
    for index, (keywords, _reply) in enumerate(TOPIC_CLARIFICATIONS):
        if any(keyword in normalized for keyword in keywords):
            return index
    return None


def clarification_for_unverified_topic(question):
    """Luôn trả lời hữu ích, kể cả khi chưa có nguồn chuyên biệt.

    Với chủ đề nhận diện được, dùng hướng dẫn theo tình huống. Với chủ đề lạ,
    vẫn hỗ trợ theo hướng an toàn và yêu cầu đúng một dữ kiện để tiếp tục.
    """
    topic_key = unverified_topic_key(question)
    if topic_key is not None:
        return TOPIC_CLARIFICATIONS[topic_key][1]
    return (
        "Tôi có thể hỗ trợ anh/chị tách vấn đề, giải thích hướng xử lý chung và chuẩn bị nội dung cần làm tiếp. "
        "Anh/chị cho biết mục tiêu chính là làm thủ tục, hỏi quy định hay phản ánh/trình báo một sự việc. "
        "Nếu sự việc đang xảy ra và có nguy cơ mất an toàn, hãy ưu tiên bảo đảm an toàn và liên hệ "
        f"{UNIT_NAME} qua số trực ban {HOTLINE}; tôi có thể giúp anh/chị sắp xếp nội dung cần báo ngay sau đó."
    )
