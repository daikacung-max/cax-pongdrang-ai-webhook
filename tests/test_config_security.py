import os
import subprocess
import sys
import unittest


class ConfigSecurityTests(unittest.TestCase):
    def _signature_required(self, production, webhook, requested):
        env = os.environ.copy()
        env.update({
            "PRODUCTION_MODE": "true" if production else "false",
            "ZALO_WEBHOOK_ENABLED": "true" if webhook else "false",
            "ZALO_WEBHOOK_SIGNATURE_REQUIRED": "true" if requested else "false",
        })
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import config; print('1' if config.ZALO_WEBHOOK_SIGNATURE_REQUIRED else '0')",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() == "1"

    def test_production_webhook_cannot_disable_signature_check(self):
        self.assertTrue(self._signature_required(True, True, False))

    def test_local_webhook_can_disable_signature_check_for_tests(self):
        self.assertFalse(self._signature_required(False, True, False))

    def test_explicit_signature_check_remains_enabled(self):
        self.assertTrue(self._signature_required(False, True, True))


if __name__ == "__main__":
    unittest.main()
