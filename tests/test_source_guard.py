import unittest

from core.source_guard import source_grounding_errors


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        self.vneid_units = [{
            "document_id": "VNEID_2026",
            "document_title": "Tài khoản định danh điện tử",
            "document_number": "Nghị định 69/2024/NĐ-CP",
            "title": "Cấp tài khoản định danh điện tử mức độ 02",
            "text": (
                "Công dân đến Công an xã, phường, thị trấn hoặc cơ quan quản lý căn cước không phụ thuộc nơi cư trú; "
                "xuất trình thẻ căn cước còn hiệu lực, cung cấp Phiếu TK01, số thuê bao di động chính chủ và email nếu có."
            ),
        }]

    def test_allows_grounded_natural_answer(self):
        answer = "Anh/chị có thể đến Công an xã để làm định danh điện tử mức độ 02, xuất trình căn cước còn hiệu lực và cung cấp số điện thoại chính chủ."
        self.assertEqual(source_grounding_errors(answer, self.vneid_units), [])

    def test_rejects_invented_physical_address(self):
        answer = "Anh/chị đến Công an xã tại địa chỉ: Số 12, đường A để làm thủ tục."
        self.assertIn("unsupported_physical_address", source_grounding_errors(answer, self.vneid_units))

    def test_rejects_unsourced_office_hours_and_integration_examples(self):
        answer = "Đến trong giờ hành chính; có thể tích hợp tài khoản ngân hàng và mã số thuế."
        errors = source_grounding_errors(answer, self.vneid_units)
        self.assertTrue(any("gio hanh chinh" in x for x in errors))
        self.assertTrue(any("tai khoan ngan hang" in x for x in errors))
        self.assertTrue(any("ma so thue" in x for x in errors))

    def test_rejects_internal_source_id(self):
        answer = "Theo VNEID_2026:level2, anh/chị đến Công an xã."
        self.assertIn("internal_source_id_exposed", source_grounding_errors(answer, self.vneid_units))


if __name__ == "__main__":
    unittest.main()
