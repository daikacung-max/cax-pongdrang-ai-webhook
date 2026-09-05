import unittest

from app import ensure_legal_db
from core.planner import plan
from core.retrieval import retrieve


class DomainBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_lost_identity_card_cannot_fall_through_to_criminal_documents(self):
        question = "Tôi bị mất căn cước"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertEqual(units, [])


if __name__ == "__main__":
    unittest.main()
