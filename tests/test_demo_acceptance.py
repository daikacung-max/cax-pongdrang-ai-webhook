"""Kịch bản nghiệm thu bản demo cục bộ.

Mỗi kịch bản dùng phiên mới để bảo đảm dữ kiện giữa người dân không thể lẫn
vào nhau. Các kiểm tra tập trung vào ranh giới an toàn, không khóa cứng cách
diễn đạt tự nhiên của câu trả lời.
"""

import unittest
import uuid

from app import ensure_legal_db
from core.demo import respond


class DemoAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_thirty_isolated_demo_scenarios(self):
        scenarios = (
            ("Xin chào", "advice_only", "not_requested", "Anh/chị cần tôi hỗ trợ"),
            ("Làm VNeID mức 1 thế nào?", "advice_only", "not_requested", "Mức độ 01"),
            ("Làm VNeID mức 2 cần gì?", "advice_only", "not_requested", "Công an xã"),
            ("Số điện thoại VNeID có cần chính chủ không?", "advice_only", "not_requested", "VNeID"),
            ("Đăng ký tạm trú thế nào?", "advice_only", "not_requested", "03 ngày làm việc"),
            ("Tôi muốn nộp hồ sơ đăng ký tạm trú", "intake_requested", "needs_information", "chỗ ở"),
            ("Đăng ký thường trú cần gì?", "advice_only", "not_requested", "07 ngày làm việc"),
            ("Tôi thuê nhà, muốn đăng ký thường trú", "advice_only", "not_requested", "nhà thuê"),
            ("Đăng ký xe máy mới cần gì?", "advice_only", "not_requested", "ĐKX10"),
            ("Tôi muốn sang tên xe máy", "advice_only", "not_requested", "chưa có nguồn"),
            ("Con tôi 10 tuổi cần làm căn cước", "advice_only", "not_requested", "dưới 14 tuổi"),
            ("Tôi bị mất căn cước", "advice_only", "not_requested", "Công an cấp tỉnh"),
            ("Thẻ căn cước của tôi bị hư hỏng", "advice_only", "not_requested", "Công an cấp tỉnh"),
            ("Tôi bị người khác đánh", "advice_only", "not_requested", "đi khám"),
            ("Tôi bị đánh, thương tích 5%", "advice_only", "not_requested", "Điều 134"),
            ("Người đó dùng dao đánh tôi", "advice_only", "not_requested", "cần làm rõ"),
            ("Tôi có camera ghi lại vụ việc", "advice_only", "not_requested", "file gốc"),
            ("Tôi bị lừa chuyển khoản", "advice_only", "not_requested", "chứng từ giao dịch"),
            ("Tôi muốn tố giác một vụ việc", "intake_requested", "needs_information", "Công an cấp xã"),
            ("Tôi bị trộm mất xe máy", "advice_only", "not_requested", "Sự việc xảy ra khi nào"),
            ("Tôi bị người khác đe dọa", "advice_only", "not_requested", "Sự việc xảy ra khi nào"),
            ("Tôi bị mất điện thoại", "advice_only", "not_requested", "chưa có nguồn"),
            ("Tôi bị mất giấy tờ", "advice_only", "not_requested", "chưa có nguồn"),
            ("Tôi muốn đổi căn cước", "advice_only", "not_requested", "chưa có nguồn"),
            ("Tôi cần cấp căn cước lần đầu", "advice_only", "not_requested", "chưa có nguồn"),
            ("Tôi muốn nộp hồ sơ đăng ký xe máy mới", "intake_requested", "needs_information", "đăng ký lần đầu"),
            ("Tôi muốn trình báo bị đe dọa", "intake_requested", "needs_information", "Sự việc xảy ra khi nào"),
            ("Có được bảo mật người tố giác không?", "advice_only", "not_requested", "giữ bí mật"),
            ("Tôi cần xác nhận cư trú", "advice_only", "not_requested", "nguồn"),
            ("Tôi muốn hỏi về giấy phép xây dựng", "advice_only", "not_requested", "Anh/chị cần tôi hỗ trợ"),
        )
        forbidden_phone = ("113", "114", "115")

        for question, mode, handoff, phrase in scenarios:
            with self.subTest(question=question):
                result = respond(str(uuid.uuid4()), question)
                answer = result["answer"]
                self.assertEqual(result["mode"], mode)
                self.assertEqual(result["handoff_status"], handoff)
                self.assertIn(phrase, answer)
                self.assertFalse(any(number in answer for number in forbidden_phone))

    def test_four_turn_assault_context_keeps_new_facts(self):
        session_id = str(uuid.uuid4())
        first = respond(session_id, "Tôi bị người khác đánh")
        second = respond(session_id, "Thương tích 5%")
        third = respond(session_id, "Có dùng dao")
        fourth = respond(session_id, "Có camera")

        self.assertIn("đi khám", first["answer"])
        self.assertIn("5%", second["answer"])
        self.assertIn("dao", third["answer"].lower())
        self.assertIn("file gốc", fourth["answer"])
        self.assertNotIn("chắc chắn không", second["answer"].lower())


if __name__ == "__main__":
    unittest.main()
