import unittest

from app import ensure_legal_db
from core.planner import plan
from core.retrieval import retrieve


class DomainBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_lost_identity_card_uses_current_identity_source_not_criminal_documents(self):
        question = "Tôi bị mất căn cước"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(units)
        self.assertTrue(all(unit["document_id"] == "CITIZEN_ID_5230_COMMUNE_2026" for unit in units))
        self.assertFalse(any(unit["document_id"] == "BLHS_2025" for unit in units))

    def test_vehicle_transfer_uses_transfer_plus_current_authority_not_first_registration(self):
        question = "Tôi muốn sang tên xe máy"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertTrue(units)
        allowed = {"VEHICLE_TRANSFER_LOCAL_2026", "VEHICLE_CURRENT_2026"}
        self.assertTrue(all(unit["document_id"] in allowed for unit in units))
        self.assertFalse(any(unit["id"] == "VEHICLE_CURRENT_2026:first_domestic_online" for unit in units))
        self.assertFalse(any(unit["document_id"] == "VEHICLE_REGISTRATION_2026" for unit in units))

    def test_theft_of_motorcycle_cannot_use_vehicle_registration_source(self):
        question = "Tôi bị trộm mất xe máy"
        units = retrieve(plan(question, [], dynamic=True), question)
        self.assertFalse(any(unit["document_id"] in {"VEHICLE_REGISTRATION_2026", "VEHICLE_CURRENT_2026"} for unit in units))


if __name__ == "__main__":
    unittest.main()
