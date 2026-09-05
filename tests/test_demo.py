import os
import tempfile
import unittest
import uuid

from app import app, ensure_legal_db
from core import db
from core.demo import respond


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_demo_advice_does_not_enter_intake(self):
        result = respond(str(uuid.uuid4()), "Làm VNeID mức 2 cần gì?")
        self.assertEqual(result["mode"], "advice_only")
        self.assertEqual(result["handoff_status"], "not_requested")
        self.assertEqual(result["source_state"], "grounded")

    def test_demo_explicit_intake_is_only_a_simulation(self):
        result = respond(str(uuid.uuid4()), "Tôi muốn nộp hồ sơ đăng ký tạm trú.")
        self.assertEqual(result["mode"], "intake_requested")
        self.assertEqual(result["handoff_status"], "needs_information")
        self.assertIn("chỗ ở", result["answer"])

    def test_lost_identity_card_uses_verified_reissue_guidance_not_criminal_law(self):
        result = respond(str(uuid.uuid4()), "Tôi bị mất căn cước")
        self.assertEqual(result["mode"], "advice_only")
        self.assertEqual(result["source_state"], "grounded")
        self.assertIn("Công an cấp tỉnh", result["answer"])
        self.assertIn("07 ngày làm việc", result["answer"])
        self.assertNotIn("Điều 134", result["answer"])

    def test_assault_starts_with_evidence_and_one_followup(self):
        result = respond(str(uuid.uuid4()), "Tôi bị người khác đánh.")
        self.assertIn("đi khám", result["answer"])
        self.assertIn("kết quả thương tích", result["answer"])
        self.assertNotIn("Điều 134", result["answer"])

    def test_fraud_transfer_does_not_assign_an_offence(self):
        result = respond(str(uuid.uuid4()), "Tôi bị lừa chuyển khoản.")
        self.assertIn("chứng từ giao dịch", result["answer"])
        self.assertIn("chưa thể xác định tội danh", result["answer"])
        self.assertNotIn("Điều 174", result["answer"])

    def test_vehicle_transfer_uses_its_own_verified_procedure(self):
        result = respond(str(uuid.uuid4()), "Tôi muốn sang tên xe máy.")
        self.assertEqual(result["source_state"], "grounded")
        self.assertIn("sang tên", result["answer"])
        self.assertIn("Công an cấp xã được phân cấp", result["answer"])

    def test_theft_of_motorcycle_is_not_vehicle_registration(self):
        result = respond(str(uuid.uuid4()), "Tôi bị trộm mất xe máy.")
        self.assertIn("Sự việc xảy ra khi nào và ở đâu", result["answer"])
        self.assertNotIn("ĐKX10", result["answer"])
        self.assertNotIn("Điều 173", result["answer"])

    def test_threat_report_is_not_a_generic_menu(self):
        result = respond(str(uuid.uuid4()), "Tôi bị người khác đe dọa.")
        self.assertIn("Sự việc xảy ra khi nào và ở đâu", result["answer"])
        self.assertNotIn("Anh/chị cần tôi hỗ trợ nội dung nào", result["answer"])

    def test_demo_console_is_off_by_default(self):
        with app.test_client() as client:
            response = client.get("/demo")
        self.assertEqual(response.status_code, 404)

    def test_demo_console_rejects_invalid_session(self):
        # The route is intentionally disabled by default; test the session validator
        # through its public API only when temporarily enabled.
        import app as application
        old_enabled = application.ENABLE_DEMO_CONSOLE
        application.ENABLE_DEMO_CONSOLE = True
        try:
            with app.test_client() as client:
                response = client.post("/demo/api/chat", json={"session_id": "not-a-uuid", "message": "Xin chào"})
            self.assertEqual(response.status_code, 400)
        finally:
            application.ENABLE_DEMO_CONSOLE = old_enabled

    def test_demo_history_is_isolated_between_sessions(self):
        import app as application
        old_enabled = application.ENABLE_DEMO_CONSOLE
        application.ENABLE_DEMO_CONSOLE = True
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())
        try:
            with app.test_client() as client:
                created = client.post("/demo/api/chat", json={
                    "session_id": session_a,
                    "message": "Làm VNeID mức 2 cần gì?",
                })
                own = client.get("/demo/api/history?session_id=" + session_a)
                other = client.get("/demo/api/history?session_id=" + session_b)
            self.assertEqual(created.status_code, 200)
            self.assertEqual(len(own.get_json()["messages"]), 2)
            self.assertEqual(other.get_json()["messages"], [])
        finally:
            application.ENABLE_DEMO_CONSOLE = old_enabled


if __name__ == "__main__":
    unittest.main()
