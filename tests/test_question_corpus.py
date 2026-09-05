import os
import re
import unittest
import uuid

from app import ensure_legal_db
from core.demo import respond
from core.planner import quick_plan
from core.question_corpus import build_question_corpus
from core.retrieval import retrieve
from core.verifier import grounded_dynamic_fallback


class QuestionCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_one_thousand_questions_have_unique_policy_and_route(self):
        cases = build_question_corpus()
        self.assertEqual(len(cases), 1000)
        self.assertEqual(len({case.question for case in cases}), 1000)

        for case in cases:
            with self.subTest(case_id=case.case_id):
                plan = quick_plan(case.question)
                units = retrieve(plan, case.question) if plan["is_legal"] else []
                if case.policy == "verified_source":
                    self.assertTrue(
                        any(str(unit.get("document_id") or "").startswith(case.source_prefix) for unit in units),
                        case.question,
                    )
                else:
                    # Với nội dung chưa có nguồn được duyệt riêng, chỉ kiểm tra
                    # câu fallback an toàn; không biến corpus thành câu trả lời luật.
                    answer = grounded_dynamic_fallback(case.question, [])
                    self.assertTrue(
                        "chưa có nguồn" in answer.lower()
                        or "không tự đoán" in answer.lower()
                        or "mỗi trường hợp có giấy tờ khác nhau" in answer.lower(),
                        case.question,
                    )
                    self.assertNotRegex(answer, re.compile(r"(?<!\d)(?:113|114|115)(?!\d)"))

    @unittest.skipUnless(
        os.getenv("RUN_DEMO_CORPUS_E2E") == "1",
        "Lượt 1.000 câu end-to-end chỉ chạy khi được yêu cầu để không ghi dữ liệu test vào DB mặc định.",
    )
    def test_one_thousand_questions_return_safe_demo_replies(self):
        """Chạy toàn bộ UI-backend demo bằng dữ liệu giả lập, mỗi câu một phiên."""
        for case in build_question_corpus():
            with self.subTest(case_id=case.case_id):
                result = respond(str(uuid.uuid5(uuid.NAMESPACE_URL, case.case_id)), case.question)
                answer = str(result["answer"] or "")
                self.assertTrue(answer.strip())
                self.assertIn(result["mode"], ("advice_only", "intake_requested"))
                self.assertIn(result["handoff_status"], ("not_requested", "needs_information", "ready_for_officer"))
                self.assertTrue(all(
                    number == "02623509777"
                    for number in re.findall(r"(?<!\d)0\d{9,10}(?!\d)", answer)
                ))
                if case.policy == "verified_source":
                    self.assertEqual(result["source_state"], "grounded", case.question)
                    self.assertNotIn("Nguồn phù hợp đã được tìm thấy nhưng dữ kiện", answer)


if __name__ == "__main__":
    unittest.main()
