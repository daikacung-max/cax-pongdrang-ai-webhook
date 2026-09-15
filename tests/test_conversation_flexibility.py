import unittest

from adapters.demo_ai import _active_notebook_source
from core.form_documents import detect_form_type, handle_form_request
from core.planner import _contextual_question, quick_plan
from core.source_guard import source_grounding_errors


class ConversationFlexibilityTests(unittest.TestCase):
    def _pending_report_history(self):
        return [
            {"role": "user", "content": "Tôi muốn làm đơn trình báo", "meta": {}},
            {
                "role": "assistant",
                "content": "Tôi đang hỗ trợ soạn Đơn trình báo. Vui lòng gửi các dòng sau...",
                "meta": {
                    "path": "citizen_form_assistant",
                    "form_type": "report",
                    "form_ready": False,
                },
            },
        ]

    def test_pending_form_yields_to_new_gambling_topic(self):
        history = self._pending_report_history()
        self.assertEqual(
            detect_form_type("Tôi có biết một người chơi cá độ bóng đá", history=history),
            "",
        )

    def test_pending_form_yields_to_new_vehicle_topic(self):
        history = self._pending_report_history()
        self.assertEqual(
            detect_form_type("Tôi muốn đăng ký xe mô tô cần làm gì", history=history),
            "",
        )

    def test_pending_form_yields_to_conversational_interjection(self):
        history = self._pending_report_history()
        self.assertEqual(detect_form_type("Bạn ơi, tôi nói này", history=history), "")

    def test_pending_form_keeps_export_capability_question(self):
        history = self._pending_report_history()
        self.assertEqual(
            detect_form_type("Bạn có xuất file được không", history=history),
            "report",
        )
        result = handle_form_request(
            "demo-user", "Bạn có xuất file được không", history=history
        )
        self.assertIsNotNone(result)
        self.assertIn("file Word", result["answer"])
        self.assertNotIn("Vui lòng gửi các dòng sau", result["answer"])

    def test_pending_form_keeps_structured_field_reply(self):
        history = self._pending_report_history()
        reply = "Họ tên: Nguyễn Văn A\nCCCD: 012345678901\nĐịa chỉ: xã Pơng Drang"
        self.assertEqual(detect_form_type(reply, history=history), "report")

    def test_temporary_residence_displays_only_source_3(self):
        sources = _active_notebook_source([
            "RESIDENCE_CURRENT_2026:temporary",
            "RESIDENCE_CURRENT_2026:data_reuse",
        ])
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "3. ĐK tạm trú.pdf")

    def test_clear_new_topic_overrides_stale_history(self):
        history = [
            {"role": "user", "content": "Tôi muốn đăng ký tạm trú"},
            {"role": "assistant", "content": "Anh/chị đang ở nhà mình hay ở thuê?"},
        ]
        contextual = _contextual_question("Tôi muốn đăng ký xe mô tô cần làm gì", history)
        self.assertEqual(contextual, "Tôi muốn đăng ký xe mô tô cần làm gì")

    def test_short_elliptical_reply_inherits_history(self):
        history = [{"role": "user", "content": "Tôi muốn đăng ký tạm trú"}]
        contextual = _contextual_question("ở thuê", history)
        self.assertIn("đăng ký tạm trú", contextual)
        self.assertIn("ở thuê", contextual)

    def test_gambling_is_deterministically_legal_topic(self):
        plan = quick_plan("Tôi biết một người cá độ bóng đá")
        self.assertTrue(plan["is_legal"])
        self.assertTrue(any("cá cược" in q or "đánh bạc" in q for q in plan["search_queries"]))

    def test_procedure_code_must_exist_in_source(self):
        units = [{
            "document_title": "Nguồn tạm trú",
            "document_number": "116/2026/TT-BCA",
            "document_issuer": "Bộ Công an",
            "article": "",
            "title": "Đăng ký tạm trú",
            "text": "Đăng ký tạm trú tại Công an cấp xã; thời hạn 03 ngày làm việc.",
        }]
        errors = source_grounding_errors(
            "Nộp trực tuyến theo mã thủ tục 1.004194 và nhận kết quả qua email.",
            units,
        )
        self.assertTrue(any(x.startswith("unsupported_procedure_code:") for x in errors))
        self.assertIn("unsupported_procedural_detail:email", errors)


if __name__ == "__main__":
    unittest.main()
