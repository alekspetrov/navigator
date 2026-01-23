#!/usr/bin/env python3
"""Tests for exit_gate.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from exit_gate import count_indicators, evaluate_exit


class TestCountIndicators(unittest.TestCase):
    """Tests for indicator counting."""

    def test_empty_dict(self):
        """Empty dict should return 0 met, 5 total."""
        met, total = count_indicators({})
        self.assertEqual(met, 0)
        self.assertEqual(total, 5)

    def test_all_true(self):
        """All true indicators should count correctly."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True
        }
        met, total = count_indicators(indicators)
        self.assertEqual(met, 3)
        self.assertEqual(total, 3)

    def test_mixed_values(self):
        """Mixed true/false should count correctly."""
        indicators = {
            "a": True,
            "b": False,
            "c": True,
            "d": False,
            "e": True
        }
        met, total = count_indicators(indicators)
        self.assertEqual(met, 3)
        self.assertEqual(total, 5)


class TestEvaluateExitDualCondition(unittest.TestCase):
    """Tests for dual-condition exit gate evaluation."""

    def test_both_conditions_met_should_exit(self):
        """Both heuristics met and exit signal should allow exit."""
        indicators = {"code_committed": True, "tests_passing": True}
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=True,
            min_heuristics=2
        )
        self.assertTrue(result["should_exit"])
        self.assertIn("EXIT", result["reason"])
        self.assertIsNone(result["blocked_reason"])

    def test_exit_signal_only_not_enough(self):
        """Exit signal without heuristics should not exit."""
        indicators = {"code_committed": True}  # Only 1 indicator
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=True,
            min_heuristics=2
        )
        self.assertFalse(result["should_exit"])
        self.assertIn("BLOCKED", result["reason"])
        self.assertIsNotNone(result["blocked_reason"])

    def test_heuristics_only_awaiting_signal(self):
        """Heuristics met but no exit signal should continue."""
        indicators = {"code_committed": True, "tests_passing": True}
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=False,
            min_heuristics=2,
            require_explicit=True
        )
        self.assertFalse(result["should_exit"])
        self.assertIn("CONTINUE", result["reason"])
        self.assertIn("explicit", result["blocked_reason"].lower())

    def test_legacy_mode_heuristics_only_exits(self):
        """Legacy mode (no explicit signal required) should exit on heuristics."""
        indicators = {"code_committed": True, "tests_passing": True}
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=False,
            min_heuristics=2,
            require_explicit=False
        )
        self.assertTrue(result["should_exit"])
        self.assertIn("explicit signal not required", result["reason"])

    def test_neither_condition_met(self):
        """Neither condition met should continue."""
        indicators = {"code_committed": False}
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=False,
            min_heuristics=2
        )
        self.assertFalse(result["should_exit"])
        self.assertIn("CONTINUE", result["reason"])
        self.assertEqual(result["blocked_reason"], "More work needed")


class TestEvaluateExitMetadata(unittest.TestCase):
    """Tests for result metadata."""

    def test_result_contains_all_fields(self):
        """Result should contain all expected fields."""
        result = evaluate_exit(
            indicators={"a": True},
            exit_signal=False
        )
        expected_fields = [
            "heuristics_met",
            "heuristics_total",
            "heuristics_satisfied",
            "exit_signal",
            "min_required",
            "require_explicit",
            "should_exit",
            "reason",
            "blocked_reason"
        ]
        for field in expected_fields:
            self.assertIn(field, result)

    def test_heuristics_counts_accurate(self):
        """Heuristic counts should be accurate."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": False,
            "ticket_closed": True
        }
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=False,
            min_heuristics=2
        )
        self.assertEqual(result["heuristics_met"], 3)
        self.assertEqual(result["heuristics_total"], 4)
        self.assertTrue(result["heuristics_satisfied"])


class TestMinHeuristicsThreshold(unittest.TestCase):
    """Tests for variable min_heuristics threshold."""

    def test_higher_threshold_blocks(self):
        """Higher threshold should block exit."""
        indicators = {"code_committed": True, "tests_passing": True}
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=True,
            min_heuristics=3
        )
        self.assertFalse(result["should_exit"])

    def test_lower_threshold_allows(self):
        """Lower threshold should allow exit."""
        indicators = {"code_committed": True}
        result = evaluate_exit(
            indicators=indicators,
            exit_signal=True,
            min_heuristics=1
        )
        self.assertTrue(result["should_exit"])

    def test_threshold_of_zero_always_satisfied(self):
        """Threshold of 0 should always be satisfied."""
        result = evaluate_exit(
            indicators={},
            exit_signal=True,
            min_heuristics=0
        )
        self.assertTrue(result["should_exit"])


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "exit_gate.py"

    def test_cli_exit_allowed(self):
        """CLI should return exit code 0 when exit allowed."""
        indicators = json.dumps({"code_committed": True, "tests_passing": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", indicators,
                "--exit-signal",
                "--min-heuristics", "2"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_cli_exit_blocked(self):
        """CLI should return exit code 1 when exit blocked."""
        indicators = json.dumps({"code_committed": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", indicators,
                "--min-heuristics", "2"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)

    def test_cli_json_output(self):
        """CLI JSON output should be valid."""
        indicators = json.dumps({"code_committed": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", indicators,
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertIn("should_exit", output)

    def test_cli_text_output(self):
        """CLI text output should be human readable."""
        indicators = json.dumps({"code_committed": True, "tests_passing": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", indicators,
                "--exit-signal",
                "--output", "text"
            ],
            capture_output=True,
            text=True
        )
        self.assertIn("Decision:", result.stdout)
        self.assertIn("Reason:", result.stdout)

    def test_cli_invalid_json_error(self):
        """Invalid JSON should cause error."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", "not-valid-json"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid JSON", result.stderr)

    def test_cli_no_require_explicit_flag(self):
        """--no-require-explicit flag should work."""
        indicators = json.dumps({"code_committed": True, "tests_passing": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--indicators", indicators,
                "--no-require-explicit",
                "--min-heuristics", "2"
            ],
            capture_output=True,
            text=True
        )
        # Should exit because we have heuristics and explicit not required
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
