import unittest

from core import db
from core.notebook_current_sources import ensure_notebook_current_sources
from core.current_knowledge import ensure_current_knowledge
from core.current_fallback import grounded_dynamic_fallback
from core.notebook_manifest import NOTEBOOK_SOURCE_COUNT, SOURCES, used_sources_for_unit_ids
from core.notebook_retrieval import retrieve


class NotebookMirrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_schema()
        ensure_current_knowledge()
        ensure_notebook_current_sources()

    def test_manifest_has_exact_19_source_titles(self):
        expected = [
            "1. Đăng ký thường trú.pdf",
            "2. Xóa ĐK thường trú.pdf",
            "3. ĐK tạm trú.pdf",
            "4. Gia hạn tạm trú.pdf",
            "5. Tách hộ.pdf",
            "6. Điều chỉnh TT về CT.pdf",
            "7. Khai báo TT về CT.pdf",
            "8. Xác nhận TT về CT.pdf",
            "9. Xóa ĐK tạm trú.pdf",
            "10. Khai báo tạm vắng.pdf",
            "11. Thông báo lưu trú.pdf",
            "12. ĐK QL phương tiện Giao thông.pdf",
            "13. Xuất nhập cảnh.pdf",
            "14. Quản lý ngành nghề.pdf",
            "15. Định danh và XTĐT.pdf",
            "16. Cấp quản lý CCCD.pdf",
            "17. Quản lý VK VLN CCHT.pdf",
            "18. Lý lịch tư pháp.pdf",
            "19. Sát hạch cấp giấy phép lái xe.pdf",
        ]
        self.assertEqual(NOTEBOOK_SOURCE_COUNT, 19)
        self.assertEqual([x["title"] for x in SOURCES], expected)

    def test_passport_routes_only_to_passport_pack(self):
        units = retrieve({"search_queries": []}, "Tôi muốn làm hộ chiếu phổ thông")
        self.assertTrue(units)
        self.assertTrue(all(x["document_id"] == "PASSPORT_CURRENT_2026" for x in units))

    def test_criminal_record_routes_to_provincial_pack(self):
        units = retrieve({"search_queries": []}, "Tôi cần xin phiếu lý lịch tư pháp")
        self.assertTrue(units)
        self.assertEqual(units[0]["id"], "CRIMINAL_RECORD_CURRENT_2026:citizen")
        self.assertIn("Công an cấp tỉnh", units[0]["text"])

    def test_residence_subprocedure_keeps_notebook_boundary(self):
        units = retrieve({"search_queries": []}, "Tôi muốn xóa đăng ký tạm trú")
        self.assertTrue(units)
        self.assertEqual(units[0]["id"], "RESIDENCE_NOTEBOOK_2026:delete_temporary")
        self.assertIn("02 ngày làm việc", units[0]["text"])
        labels = used_sources_for_unit_ids([x["id"] for x in units])
        self.assertTrue(labels)
        self.assertEqual(labels[0]["title"], "9. Xóa ĐK tạm trú.pdf")

    def test_short_rental_followup_inherits_temporary_residence_boundary(self):
        plan = {
            "is_legal": True,
            "search_queries": [
                "Tôi muốn đăng ký cư trú tại xã Pơng Drang | tạm trú | ở thuê",
                "Đăng ký tạm trú Công an cấp xã",
            ],
        }
        for followup in ("ở thuê", "nhà thuê", "tôi thuê trọ", "ở trọ", "ở nhờ"):
            with self.subTest(followup=followup):
                units = retrieve(plan, followup)
                self.assertTrue(units)
                self.assertEqual(units[0]["id"], "RESIDENCE_CURRENT_2026:temporary")
                self.assertTrue(all(str(x.get("document_id") or "").startswith("RESIDENCE_") for x in units))
                labels = used_sources_for_unit_ids([x["id"] for x in units])
                self.assertTrue(labels)
                self.assertEqual(labels[0]["title"], "3. ĐK tạm trú.pdf")

    def test_vneid_temporary_residence_returns_actionable_steps_within_source_three(self):
        question = "Tôi muốn hướng dẫn thao tác trên ứng dụng VNeID để đăng ký tạm trú"
        units = retrieve({"search_queries": [question]}, question)

        self.assertEqual(units[0]["id"], "RESIDENCE_VNEID_APP_STEPS_2026:temporary_residence")
        answer = grounded_dynamic_fallback(question, units)
        self.assertIn("Thủ tục hành chính", answer)
        self.assertIn("Tạo mới yêu cầu", answer)
        self.assertIn("mã hồ sơ", answer)
        labels = used_sources_for_unit_ids([x["id"] for x in units])
        self.assertEqual(labels[0]["title"], "3. ĐK tạm trú.pdf")

    def test_user_facing_source_label_hides_internal_unit_id(self):
        labels = used_sources_for_unit_ids(["CRIMINAL_RECORD_CURRENT_2026:citizen"])
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["title"], "18. Lý lịch tư pháp.pdf")
        self.assertNotIn("CRIMINAL_RECORD_CURRENT_2026", labels[0]["title"])


if __name__ == "__main__":
    unittest.main()
