import unittest

from app import ensure_legal_db
from core.corpus_audit import audit_corpus
from core.question_corpus_10000 import build_question_corpus_10000


class QuestionCorpus10000Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_10000_questions_are_unique(self):
        cases = build_question_corpus_10000()
        self.assertEqual(len(cases), 10000)
        self.assertEqual(len({case.question for case in cases}), 10000)
        self.assertEqual(len({case.case_id for case in cases}), 10000)

    def test_10000_questions_pass_source_and_semantic_audit(self):
        report = audit_corpus(build_question_corpus_10000(), failure_limit=25)
        if report["failed"]:
            detail = "\n".join(
                f"{item['case_id']} [{item['category']}] {item['question']} :: {item['errors']} :: {item['sources']} :: {item['answer']}"
                for item in report["failures"]
            )
            self.fail(
                f"10k corpus failed={report['failed']}/{report['total']}\n"
                f"error_counts={report['error_counts']}\n{detail}"
            )


if __name__ == "__main__":
    unittest.main()
