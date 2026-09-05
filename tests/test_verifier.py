import unittest

from core.verifier import verify_dynamic_text


ARTICLE_134 = {
    "id": "BLHS_2025:134",
    "document_id": "BLHS_2025",
    "article": "134",
    "title": "Tội cố ý gây thương tích hoặc gây tổn hại cho sức khỏe của người khác",
    "text": (
        "Người nào cố ý gây thương tích hoặc gây tổn hại cho sức khỏe của người khác "
        "mà tỷ lệ tổn thương cơ thể từ 11% đến 30% hoặc dưới 11% nhưng thuộc một "
        "trong các trường hợp luật định thì bị xử lý theo quy định."
    ),
}


class DynamicVerifierTests(unittest.TestCase):
    def test_rejects_unsupported_article(self):
        result = verify_dynamic_text("Người kia phạm Điều 148.", [ARTICLE_134], question="Tôi bị đánh")
        self.assertFalse(result["ok"])
        self.assertTrue(any("unsupported_articles" in x for x in result["errors"]))

    def test_rejects_invented_legal_number(self):
        result = verify_dynamic_text(
            "Tỷ lệ 45% thì chắc chắn bị xử lý.", [ARTICLE_134], question="Tôi bị thương 5%."
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("unsupported_numbers" in x for x in result["errors"]))

    def test_allows_question_number_and_source_exception(self):
        result = verify_dynamic_text(
            "Mức 5% chưa đủ để kết luận không bị xử lý; dưới 11% vẫn có thể được xem xét nếu thuộc tình tiết luật định.",
            [ARTICLE_134],
            question="Tôi bị thương 5%.",
        )
        self.assertTrue(result["ok"], result["errors"])

    def test_rejects_guilt_conclusion(self):
        result = verify_dynamic_text("Người kia đã phạm tội.", [ARTICLE_134], question="Tôi bị đánh")
        self.assertFalse(result["ok"])
        self.assertIn("unsupported_guilt_conclusion", result["errors"])

    def test_rejects_automatic_knife_classification(self):
        result = verify_dynamic_text(
            "Con dao chính là hung khí nguy hiểm.", [ARTICLE_134], question="Người kia dùng dao."
        )
        self.assertFalse(result["ok"])
        self.assertIn("knife_assumed_dangerous_weapon", result["errors"])

    def test_rejects_invented_form_and_agency(self):
        result = verify_dynamic_text(
            "Anh/chị nộp mẫu TK99 tại Công an huyện.",
            [{
                "article": None,
                "document_id": "RESIDENCE_GUIDANCE_2026",
                "text": "Đăng ký tại Công an cấp xã.",
            }],
            question="Tôi đăng ký tạm trú thế nào?",
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any(
            x.startswith("unsupported_procedural_details:") for x in result["errors"]
        ))

    def test_rejects_production_style_absolute_5_percent_conclusion(self):
        result = verify_dynamic_text(
            "Mức thương tích 5% nằm dưới 11%. Theo Điều 134, hành vi này không bị xử lý hình sự.",
            [ARTICLE_134],
            question="Kết quả thương tích là 5%.",
        )
        self.assertFalse(result["ok"])
        self.assertIn("article_134_absolute_low_injury_conclusion", result["errors"])

    def test_rejects_dao_as_weapon_without_verification(self):
        result = verify_dynamic_text(
            "Việc sử dụng dao làm vũ khí khiến hành vi thuộc điểm a Điều 134.",
            [ARTICLE_134],
            question="Người đó có dùng dao.",
        )
        self.assertFalse(result["ok"])
        self.assertIn("article_134_knife_assumed_weapon", result["errors"])


if __name__ == "__main__":
    unittest.main()
