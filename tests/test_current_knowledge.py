import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import db
from core.current_knowledge import ensure_current_knowledge
from core.retrieval import retrieve
from core.verifier import verify_dynamic_text


class CurrentKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path_patch = patch.object(db, "DB_PATH", Path(self.tmp.name) / "legal.db")
        self.db_path_patch.start()
        db.init_schema()

    def tearDown(self):
        self.db_path_patch.stop()
        self.tmp.cleanup()

    def test_superseded_identity_snapshot_is_inactive(self):
        db.upsert_document({
            "id": "CITIZEN_ID_REISSUE_PROVINCIAL_2026",
            "title": "old",
            "number": "old",
            "issuer": "BCA",
            "source_path": "https://example.invalid/old",
            "metadata": {},
        })
        db.replace_document_units("CITIZEN_ID_REISSUE_PROVINCIAL_2026", [{
            "id": "CITIZEN_ID_REISSUE_PROVINCIAL_2026:channels",
            "unit_type": "procedure",
            "title": "old provincial procedure",
            "text": "Cấp lại tại cấp tỉnh",
        }])
        ensure_current_knowledge()
        self.assertIsNone(db.get_unit(
            "CITIZEN_ID_REISSUE_PROVINCIAL_2026:channels", as_of="2026-09-12"
        ))
        self.assertIsNotNone(db.get_unit(
            "CITIZEN_ID_REISSUE_PROVINCIAL_2026:channels",
            as_of="2026-08-17", include_inactive=True,
        ))

    def test_future_source_is_not_active_early(self):
        ensure_current_knowledge()
        self.assertIsNone(db.get_unit("ND311_2026_FUTURE:status", as_of="2026-09-12"))
        self.assertIsNotNone(db.get_unit("ND311_2026_FUTURE:status", as_of="2026-09-26"))

    def test_reissue_identity_routes_to_current_commune_source(self):
        ensure_current_knowledge()
        units = retrieve({
            "search_queries": ["mất căn cước cấp lại"],
            "explicit_references": [],
        }, "Tôi bị mất căn cước, cấp lại ở đâu?")
        ids = [x["id"] for x in units]
        self.assertIn("CITIZEN_ID_5230_COMMUNE_2026:reissue", ids)
        blob = " ".join(x.get("text", "") for x in units[:3]).lower()
        self.assertIn("công an cấp xã", blob)
        self.assertNotIn("công an cấp huyện", blob)

    def test_over14_and_renewal_use_commune_source(self):
        ensure_current_knowledge()
        for question, expected in [
            ("Tôi 15 tuổi làm căn cước lần đầu ở đâu?", "CITIZEN_ID_5230_COMMUNE_2026:first_issue_14plus"),
            ("Tôi muốn cấp đổi căn cước thì làm ở đâu?", "CITIZEN_ID_5230_COMMUNE_2026:renewal"),
        ]:
            units = retrieve({"search_queries": [question], "explicit_references": []}, question)
            self.assertIn(expected, [x["id"] for x in units])

    def test_residence_confirmation_uses_current_half_day_rule(self):
        ensure_current_knowledge()
        units = retrieve({
            "search_queries": ["xác nhận thông tin cư trú"],
            "explicit_references": [],
        }, "Xác nhận thông tin cư trú mất bao lâu?")
        self.assertEqual(units[0]["id"], "RESIDENCE_CURRENT_2026:confirmation")
        self.assertIn("1/2 ngày làm việc", units[0]["text"])

    def test_vehicle_current_source_has_2026_amendment_and_two_tiers(self):
        ensure_current_knowledge()
        units = retrieve({
            "search_queries": ["đăng ký xe máy mới"],
            "explicit_references": [],
        }, "Tôi đăng ký xe máy mới ở đâu?")
        ids = [x["id"] for x in units]
        self.assertIn("VEHICLE_CURRENT_2026:first_domestic_online", ids)
        self.assertIn("VEHICLE_CURRENT_2026:legal_chain", ids)
        blob = " ".join(x.get("text", "") for x in units)
        lower_blob = blob.lower()
        self.assertIn("37/2026/TT-BCA", blob)
        self.assertIn("cấp tỉnh", lower_blob)
        self.assertIn("cấp xã", lower_blob)
        self.assertNotIn("công an cấp huyện", lower_blob)

    def test_procedural_huyen_hallucination_is_rejected(self):
        ensure_current_knowledge()
        unit = db.get_unit("CITIZEN_ID_5230_COMMUNE_2026:reissue")
        result = verify_dynamic_text(
            "Anh/chị đến Công an huyện để cấp lại căn cước.",
            [unit],
            question="Tôi mất căn cước làm ở đâu?",
        )
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
