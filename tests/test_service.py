import unittest
import uuid
from unittest.mock import patch

from config import UNIT_ADDRESS, UNIT_NAME
from core.llm import LLMError
import core.form_documents as forms
from core.planner import plan
from core.retrieval import retrieve
from core.service import core


class DynamicServiceTests(unittest.TestCase):
    def test_vneid_followup_answers_identity_card_reissue_instead_of_account_levels(self):
        user_id = "service-test-vneid-reissue-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value="Anh/chị có thể đề nghị cấp lại thẻ căn cước qua VNeID.",
        ):
            first = core.chat(
                user_id,
                "Tôi muốn làm lại căn cước thì làm những thủ tục gì",
                dynamic=True,
            )
            self.assertNotEqual(first["meta"].get("path"), "citizen_form_assistant")
            result = core.chat(user_id, "hướng dẫn tôi nộp hồ sơ vneid", dynamic=True)

        self.assertEqual(result["meta"]["path"], "contextual_citizen_id_vneid_guidance")
        self.assertIn("Cấp lại thẻ căn cước", result["answer"])
        self.assertIn("Thủ tục hành chính", result["answer"])
        self.assertIn("07 ngày làm việc", result["answer"])
        self.assertNotIn("mức độ 01", result["answer"])
        self.assertNotIn("mức độ 02", result["answer"])

    def test_dynamic_report_form_continuation_generates_word_without_general_ai(self):
        user_id = "service-test-form-" + uuid.uuid4().hex
        synthetic_details = (
            "Họ tên: Người Thử Nghiệm\n"
            "Địa chỉ: xã Pơng Drang (giả lập)\n"
            "Nội dung sự việc: Đây là tình huống giả lập chỉ để kiểm thử tạo đơn, không phải vụ việc có thật."
        )
        with patch.object(forms, "HISTORY_HMAC_SECRET", "synthetic-form-test-secret"), patch(
            "core.service.answer_dynamic_text",
            side_effect=AssertionError("form turns must bypass the general answer model"),
        ):
            first = core.chat(user_id, "Tôi muốn làm đơn trình báo", dynamic=True)
            self.assertFalse(first["meta"]["form_ready"])
            self.assertEqual(first["meta"]["path"], "citizen_form_assistant")

            result = core.chat(user_id, synthetic_details, dynamic=True)
            self.assertTrue(result["meta"]["form_ready"])
            token = result["answer"].split("/forms/download/", 1)[1].split("/", 1)[0]
            payload = forms.decode_download_token(token)
            content, filename = forms.render_docx(payload)

        self.assertEqual(filename, "Don-trinh-bao.docx")
        self.assertGreater(len(content), 1000)
        self.assertEqual(payload["fields"]["full_name"], "Người Thử Nghiệm")
        self.assertIn("tình huống giả lập", payload["fields"]["incident_content"])
        self.assertEqual(payload["fields"]["personal_id"], "")
        self.assertEqual(payload["fields"]["phone"], "")

    def test_unsupported_article_fails_closed_after_one_model_call(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch("core.service.answer_dynamic_text", return_value="Người kia chắc chắn phạm Điều 148." ) as model:
            result = core.chat(user_id, "Tôi bị người khác đánh.", dynamic=True)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "verification_failed")
        self.assertNotIn("Điều 148", result["answer"])
        self.assertTrue(any("134" in unit_id for unit_id in result["meta"]["retrieved_unit_ids"]))

    def test_article_134_new_injury_percentage_is_not_ignored(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value="Anh/chị có thể cho biết người đã đánh là ai không?",
        ):
            result = core.chat(user_id, "Kết quả thương tích là 5%.", dynamic=True)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "weak_answer")
        self.assertIn("5%", result["answer"])

    def test_assault_followup_preserves_prior_injury_and_new_stick_detail(self):
        history = [
            {"role": "user", "content": "Tôi bị đánh 7%."},
            {"role": "assistant", "content": "Tôi đã ghi nhận tỷ lệ thương tích."},
        ]
        with patch("core.service.db.get_history", return_value=history), patch(
            "core.service.answer_dynamic_text",
            return_value="Anh/chị có thể trình báo trực tiếp để được hướng dẫn.",
        ):
            result = core.chat("service-test-stick-" + uuid.uuid4().hex, "Dùng gậy đánh", dynamic=True)

        self.assertEqual(result["_telemetry"]["fallback_reason"], "weak_answer")
        self.assertIn("7%", result["answer"])
        self.assertIn("gậy", result["answer"].lower())
        self.assertIn("chưa thể tự khẳng định", result["answer"].lower())

    def test_temporary_residence_current_topic_cannot_fall_back_to_stale_identity_topic(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value=(
                "Chào anh/chị, anh/chị muốn đăng ký thẻ căn cước mới, "
                "đổi thẻ hiện có, hay điều chỉnh thông tin trên thẻ?"
            ),
        ):
            result = core.chat(user_id, "Tôi đăg ký tạm trú", dynamic=True)

        self.assertEqual(result["_telemetry"]["fallback_reason"], "weak_answer")
        self.assertIn("tạm trú", result["answer"].lower())
        self.assertTrue(any(
            unit_id.startswith("RESIDENCE_CURRENT_2026:temporary")
            for unit_id in result["meta"]["retrieved_unit_ids"]
        ))

    def test_vehicle_procedure_always_has_local_office_guidance(self):
        user_id = "service-test-vehicle-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value=(
                "Anh/chị cho biết xe là đăng ký lần đầu, sang tên hay cấp đổi giấy tờ xe "
                "để tôi hướng dẫn đúng trường hợp."
            ),
        ):
            result = core.chat(user_id, "Tôi muốn đăng ký xe máy của tôi thì làm gì, ở đâu?", dynamic=True)

        self.assertIn(UNIT_NAME, result["answer"])
        self.assertIn(UNIT_ADDRESS, result["answer"])
        self.assertIn("theo phân cấp", result["answer"].lower())

    def test_criminal_question_does_not_receive_administrative_procedure_location(self):
        user_id = "service-test-crime-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value="Anh/chị nên giữ lại thông tin, chứng cứ liên quan để trình báo.",
        ):
            result = core.chat(user_id, "Tôi bị người khác đánh", dynamic=True)

        self.assertNotIn(UNIT_ADDRESS, result["answer"])

    def test_noise_fine_followup_keeps_karaoke_context_and_community_team(self):
        history = [
            {"role": "user", "content": "Hàng xóm hát karaoke ồn ào quá."},
            {"role": "assistant", "content": "Anh/chị cho biết nơi và thời điểm gây ồn."},
        ]
        with patch("core.service.db.get_history", return_value=history), patch(
            "core.service.answer_dynamic_text",
            return_value=(
                "Cần xác minh hành vi, địa điểm và mức độ ảnh hưởng thực tế trước khi "
                "xác định căn cứ xử lý."
            ),
        ):
            result = core.chat(
                "service-test-noise-" + uuid.uuid4().hex,
                "Tôi muốn hỏi mức phạt của người ta",
                dynamic=True,
            )

        self.assertTrue(any(
            unit_id.startswith("NOISE_KARAOKE_282_2025:")
            for unit_id in result["meta"]["retrieved_unit_ids"]
        ))
        self.assertIn("Tổ Cảnh sát khu vực", result["answer"])

    def test_playing_cards_for_money_routes_to_gambling_source_and_safe_action(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch(
            "core.service.answer_dynamic_text",
            return_value="Anh/chị cho biết thêm tình huống cụ thể.",
        ):
            result = core.chat(
                user_id,
                "Bạn tôi biết người này đang chơi đánh bài ăn tiền",
                dynamic=True,
            )

        self.assertEqual(result["_telemetry"]["fallback_reason"], "weak_answer")
        self.assertTrue(any(
            unit_id == "BLHS_2025:article:321"
            for unit_id in result["meta"]["retrieved_unit_ids"]
        ))
        self.assertIn("đánh bài ăn tiền", result["answer"].lower())
        self.assertIn("không thể kết luận", result["answer"].lower())

    def test_full_core_provider_error_returns_grounded_fallback(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch("core.service.generate_answer", side_effect=LLMError("provider rejected")):
            result = core.chat(user_id, "Tôi bị mất căn cước, cần làm gì?", dynamic=False)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "llm_error")
        self.assertEqual(result["meta"]["path"], "full_core_grounded_fallback")
        self.assertEqual(
            result["meta"]["verification_errors"],
            ["full_core_fallback:provider_error"],
        )
        self.assertNotIn("AI Core chưa xử lý", result["answer"])

    def test_dynamic_uncovered_legal_question_uses_flexible_model_answer(self):
        user_id = "service-test-" + uuid.uuid4().hex
        no_source_plan = {
            "is_legal": True,
            "search_queries": ["tranh chấp hợp đồng dân sự"],
            "explicit_references": [],
            "needs_clarification": False,
            "clarification_question": None,
            "complexity": "simple",
            "complexity_reasons": [],
        }
        answer_text = (
            "Với tranh chấp hợp đồng, anh/chị nên giữ hợp đồng, tin nhắn và chứng từ liên quan; "
            "trước hết có thể đề nghị bên kia xác nhận phương án giải quyết bằng văn bản."
        )
        with patch("core.service.plan", return_value=no_source_plan), \
             patch("core.service.retrieve", return_value=[]), \
             patch("core.service.answer_dynamic_text", return_value=answer_text) as model:
            result = core.chat(user_id, "Tôi bị tranh chấp hợp đồng dân sự", dynamic=True)

        model.assert_called_once()
        self.assertEqual(result["answer"], answer_text)
        self.assertEqual(result["meta"]["path"], "single_call_or_grounded_fallback")
        self.assertIsNone(result["_telemetry"]["fallback_reason"])

    def test_dynamic_empty_model_reply_never_returns_an_empty_zalo_message(self):
        user_id = "service-test-" + uuid.uuid4().hex
        no_source_plan = {
            "is_legal": True,
            "search_queries": ["tranh chấp hợp đồng dân sự"],
            "explicit_references": [],
            "needs_clarification": False,
            "clarification_question": None,
            "complexity": "simple",
            "complexity_reasons": [],
        }
        with patch("core.service.plan", return_value=no_source_plan), \
             patch("core.service.retrieve", return_value=[]), \
             patch("core.service.answer_dynamic_text", return_value=""):
            result = core.chat(user_id, "Tôi bị tranh chấp hợp đồng dân sự", dynamic=True)

        self.assertTrue(result["answer"].strip())
        self.assertEqual(result["_telemetry"]["fallback_reason"], "empty_answer")
        self.assertNotIn("không có nguồn", result["answer"].lower())

    def test_full_core_provider_status_is_sanitized(self):
        user_id = "service-test-" + uuid.uuid4().hex
        with patch("core.service.generate_answer", side_effect=LLMError("groq HTTP 400: private body")):
            result = core.chat(user_id, "Tôi bị mất căn cước, cần làm gì?", dynamic=False)
        self.assertEqual(
            result["meta"]["verification_errors"],
            ["full_core_fallback:provider_http_400"],
        )

    def test_full_core_repair_error_returns_grounded_fallback(self):
        user_id = "service-test-" + uuid.uuid4().hex
        rejected_draft = {
            "answer": "Người kia chắc chắn phạm Điều 148.",
            "legal_claims": [],
            "needs_followup": False,
            "followup_question": None,
            "contact_recommended": False,
        }
        with patch(
            "core.service.generate_answer",
            side_effect=[rejected_draft, LLMError("repair rejected")],
        ) as model:
            result = core.chat(user_id, "Tôi bị người khác đánh.", dynamic=False)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(result["_telemetry"]["fallback_reason"], "llm_error")
        self.assertEqual(result["meta"]["path"], "full_core_grounded_fallback")

    def test_greeting_is_not_promoted_to_legal_retrieval_by_planner_model(self):
        with patch("core.planner.chat_structured") as planner_model:
            result = plan("Xin chào", [], dynamic=False)
        self.assertFalse(result["is_legal"])
        planner_model.assert_not_called()

    def test_full_core_assault_plan_retrieves_article_134(self):
        question = "Tôi bị người khác đánh"
        result = plan(question, [], dynamic=False)
        units = retrieve(result, question)
        self.assertTrue(any(str(unit.get("article")) == "134" for unit in units))


if __name__ == "__main__":
    unittest.main()

