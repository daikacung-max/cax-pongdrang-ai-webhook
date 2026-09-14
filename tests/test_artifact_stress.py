import unittest

from app import ensure_legal_db
from core.artifact_planner import enrich_plan
from core.artifact_question_corpus_100000 import build_artifact_question_corpus_100000
from core.artifact_router import source_id_for_question
from core.incident_corpus_10000 import build_incident_corpus_10000
from core.intake import assess
from core.notebook_manifest import used_sources_for_unit_ids
from core.notebook_retrieval import retrieve
from core.planner import quick_plan


class ArtifactStressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_100000_questions_are_unique_and_route_to_exact_artifact_source(self):
        cases = build_artifact_question_corpus_100000()
        self.assertEqual(len(cases), 100000)
        self.assertEqual(len({case.question for case in cases}), 100000)
        failures = []
        for case in cases:
            routed = source_id_for_question(case.question)
            plan = enrich_plan(case.question, quick_plan(case.question))
            if routed != case.source_id or plan.get("artifact_source_id") != case.source_id or not plan.get("is_legal"):
                failures.append((case.case_id, case.source_id, routed, plan.get("artifact_source_id"), case.question))
                if len(failures) >= 30:
                    break
        self.assertFalse(failures, f"100k artifact routing failures: {failures}")

    def test_10000_stratified_questions_retrieve_only_the_selected_artifact_boundary(self):
        # Every tenth question yields a 10,000-case stratified retrieval audit.
        cases = build_artifact_question_corpus_100000()[::10]
        self.assertEqual(len(cases), 10000)
        failures = []
        for case in cases:
            plan = enrich_plan(case.question, quick_plan(case.question))
            units = retrieve(plan, case.question)
            unit_ids = [u.get("id") for u in units]
            tags = {u.get("_artifact_source_id") for u in units if u.get("_artifact_source_id")}
            visible = {x["id"] for x in used_sources_for_unit_ids(unit_ids)}
            if not units or tags != {case.source_id} or case.source_id not in visible:
                failures.append((case.case_id, case.source_id, sorted(tags), sorted(visible), unit_ids, case.question))
                if len(failures) >= 30:
                    break
        self.assertFalse(failures, f"10k source-boundary failures: {failures}")

    def test_10000_citizen_reports_are_unique_and_intake_ready(self):
        cases = build_incident_corpus_10000()
        self.assertEqual(len(cases), 10000)
        self.assertEqual(len({case.question for case in cases}), 10000)
        failures = []
        for case in cases:
            result = assess(case.question, [])
            if (
                result.get("procedure_code") != case.procedure_code
                or result.get("handoff_queue") != case.queue
                or result.get("conversation_mode") != "intake_requested"
                or result.get("handoff_status") != "ready_for_officer"
            ):
                failures.append((case.case_id, case.procedure_code, case.queue, result, case.question))
                if len(failures) >= 30:
                    break
        self.assertFalse(failures, f"10k incident intake failures: {failures}")


if __name__ == "__main__":
    unittest.main()
