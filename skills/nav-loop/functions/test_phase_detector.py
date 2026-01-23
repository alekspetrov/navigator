#!/usr/bin/env python3
"""Tests for phase_detector.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from phase_detector import detect_phase


class TestDetectPhaseInit(unittest.TestCase):
    """Tests for INIT phase detection."""

    def test_no_activity_is_init(self):
        """No activity should return INIT phase."""
        result = detect_phase(
            files_read=[],
            files_changed=[]
        )
        self.assertEqual(result["phase"], "INIT")
        self.assertGreater(result["confidence"], 0)

    def test_init_with_explicit_flag(self):
        """Using --init should force INIT phase."""
        # This is tested via CLI, but we can test the default behavior
        result = detect_phase([], [])
        self.assertEqual(result["phase"], "INIT")


class TestDetectPhaseResearch(unittest.TestCase):
    """Tests for RESEARCH phase detection."""

    def test_files_read_no_changes(self):
        """Reading files without changes should be RESEARCH."""
        result = detect_phase(
            files_read=["src/auth.ts", "README.md"],
            files_changed=[]
        )
        self.assertEqual(result["phase"], "RESEARCH")
        self.assertIn("Files read", result["reason"])

    def test_single_file_read(self):
        """Single file read should still be RESEARCH."""
        result = detect_phase(
            files_read=["src/config.ts"],
            files_changed=[]
        )
        self.assertEqual(result["phase"], "RESEARCH")


class TestDetectPhaseImpl(unittest.TestCase):
    """Tests for IMPL phase detection."""

    def test_files_changed(self):
        """Changed files should indicate IMPL phase."""
        result = detect_phase(
            files_read=["src/auth.ts"],
            files_changed=["src/login.ts"]
        )
        self.assertEqual(result["phase"], "IMPL")
        self.assertIn("Files modified", result["reason"])

    def test_test_failed_returns_to_impl(self):
        """Failed tests should return to IMPL phase."""
        result = detect_phase(
            files_read=[],
            files_changed=["src/auth.ts"],
            tests_running=False,
            test_exit_code=1
        )
        self.assertEqual(result["phase"], "IMPL")
        self.assertIn("failed", result["reason"])


class TestDetectPhaseVerify(unittest.TestCase):
    """Tests for VERIFY phase detection."""

    def test_tests_running(self):
        """Tests running should indicate VERIFY phase."""
        result = detect_phase(
            files_read=[],
            files_changed=[],
            tests_running=True
        )
        self.assertEqual(result["phase"], "VERIFY")
        self.assertIn("running", result["reason"])

    def test_tests_passed(self):
        """Tests passed should indicate VERIFY phase."""
        result = detect_phase(
            files_read=[],
            files_changed=[],
            tests_running=False,
            test_exit_code=0
        )
        self.assertEqual(result["phase"], "VERIFY")
        self.assertIn("completed", result["reason"])


class TestDetectPhaseComplete(unittest.TestCase):
    """Tests for COMPLETE phase detection."""

    def test_all_indicators_and_exit_signal(self):
        """All indicators + exit signal should be COMPLETE."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True
        }
        result = detect_phase(
            files_read=[],
            files_changed=[],
            indicators=indicators,
            exit_signal=True
        )
        self.assertEqual(result["phase"], "COMPLETE")
        self.assertEqual(result["confidence"], 1.0)

    def test_indicators_without_exit_signal(self):
        """Indicators without exit signal should not be COMPLETE."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True
        }
        result = detect_phase(
            files_read=[],
            files_changed=["something.ts"],  # Still has changes
            indicators=indicators,
            exit_signal=False
        )
        self.assertNotEqual(result["phase"], "COMPLETE")


class TestPhasePriority(unittest.TestCase):
    """Tests for phase detection priority."""

    def test_tests_running_overrides_files_changed(self):
        """Tests running should take priority over files changed."""
        result = detect_phase(
            files_read=["a.ts"],
            files_changed=["b.ts"],
            tests_running=True
        )
        self.assertEqual(result["phase"], "VERIFY")

    def test_complete_overrides_everything(self):
        """COMPLETE phase should override everything."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True
        }
        result = detect_phase(
            files_read=["a.ts"],
            files_changed=["b.ts"],
            tests_running=True,  # Even with tests running
            indicators=indicators,
            exit_signal=True
        )
        self.assertEqual(result["phase"], "COMPLETE")


class TestResultStructure(unittest.TestCase):
    """Tests for result structure."""

    def test_result_contains_all_fields(self):
        """Result should contain all expected fields."""
        result = detect_phase([], [])
        expected_fields = ["phase", "confidence", "reason", "next_expected"]
        for field in expected_fields:
            self.assertIn(field, result)

    def test_confidence_range(self):
        """Confidence should be between 0 and 1."""
        result = detect_phase([], [])
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "phase_detector.py"

    def test_cli_init_flag(self):
        """--init flag should return INIT phase."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--init"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["phase"], "INIT")
        self.assertEqual(output["confidence"], 1.0)

    def test_cli_json_output(self):
        """CLI JSON output should be valid."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--files-read", '["src/auth.ts"]',
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertIn("phase", output)

    def test_cli_text_output(self):
        """CLI text output should be human readable."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--files-read", '["src/auth.ts"]',
                "--output", "text"
            ],
            capture_output=True,
            text=True
        )
        self.assertIn("Phase:", result.stdout)
        self.assertIn("Confidence:", result.stdout)

    def test_cli_tests_running_flag(self):
        """--tests-running flag should work."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--tests-running",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["phase"], "VERIFY")

    def test_cli_test_exit_code(self):
        """--test-exit-code should affect phase detection."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--test-exit-code", "0",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["phase"], "VERIFY")

    def test_cli_with_indicators(self):
        """CLI should handle indicators parameter."""
        indicators = json.dumps({
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True
        })
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", indicators,
                "--exit-signal",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["phase"], "COMPLETE")

    def test_cli_invalid_json_error(self):
        """Invalid JSON should cause error."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--files-read", "not-valid"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
