import unittest
from unittest.mock import patch

from app import app, ensure_legal_db


class SelfTestConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_legal_db()

    def test_self_test_is_hidden_when_demo_disabled(self):
        import adapters.self_test as self_test_module
        with patch.object(self_test_module, "ENABLE_DEMO_CONSOLE", False):
            with app.test_client() as client:
                response = client.post("/demo/api/self-test")
        self.assertEqual(response.status_code, 404)

    def test_self_test_runs_isolated_current_source_checks(self):
        import adapters.self_test as self_test_module
        with patch.object(self_test_module, "ENABLE_DEMO_CONSOLE", True):
            with app.test_client() as client:
                response = client.post("/demo/api/self-test")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 8)
        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["status"], "pass")
        for result in payload["results"]:
            self.assertTrue(result["passed"], result["name"])
            self.assertNotIn("Công an cấp huyện", result["answer"])


if __name__ == "__main__":
    unittest.main()
