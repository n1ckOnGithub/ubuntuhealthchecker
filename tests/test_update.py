from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcheck import update_system, CheckResult

class TestUpdateSystem(unittest.TestCase):

    @patch("healthcheck.subprocess.run")
    def test_update_success(self, mock_run):
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            ),
        ]

        result = update_system()

        self.assertEqual(result.status, "OK")
        self.assertEqual(
            result.summary,
            "System packages updated successfully"
        )
        self.assertEqual(mock_run.call_count, 2)

    @patch("healthcheck.subprocess.run")
    def test_sudo_authentication_failure(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1
        )

        result = update_system()

        self.assertEqual(result.status, "WARN")
        self.assertEqual(mock_run.call_count, 1)

    @patch("healthcheck.subprocess.run")
    def test_upgrade_failure(self, mock_run):
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="Could not get lock",
            ),
        ]

        result = update_system()

        self.assertEqual(result.status, "WARN")
        self.assertIn("Could not get lock", result.summary)


if __name__ == "__main__":
    unittest.main()