import unittest

from app import ensure_legal_db
from core.planner import quick_plan
from core.retrieval import retrieve


class VNeIDAliasRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_natural_level2_aliases_route_to_vneid_not_identity_card(self):
        questions = [
            "Bạn hãy hướng dẫn cho tôi làm định danh mức 2",
            "Tôi muốn đăng ký định danh mức 2",
            "Làm tài khoản mức 2 ở đâu?",
            "Tôi cần cấp định danh mức độ 02",
            "Hướng dẫn kích hoạt định danh mức 2 cho tôi",
            "Tôi muốn làm VNeID mức 2",
        ]
        for question in questions:
            with self.subTest(question=question):
                units = retrieve(quick_plan(question), question)
                ids = [str(x.get("id") or "") for x in units]
                docs = [str(x.get("document_id") or "") for x in units]
                self.assertTrue(ids, question)
                self.assertEqual(ids[0], "VNEID_2026:level2", question)
                self.assertTrue(all(doc.startswith("VNEID_") for doc in docs), (question, docs))
                self.assertFalse(any(doc.startswith("CITIZEN_ID_") for doc in docs), (question, docs))

    def test_level2_source_contains_current_commune_intake_guidance(self):
        question = "Bạn hãy hướng dẫn cho tôi làm định danh mức 2"
        units = retrieve(quick_plan(question), question)
        level2 = next(x for x in units if x["id"] == "VNEID_2026:level2")
        text = level2["text"].lower()
        self.assertIn("công an xã", text)
        self.assertIn("thẻ căn cước", text)
        self.assertIn("số thuê bao di động chính chủ", text)


if __name__ == "__main__":
    unittest.main()
