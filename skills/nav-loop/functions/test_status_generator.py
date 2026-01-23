#!/usr/bin/env python3
"""Tests for status_generator.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from status_generator import (
    calculate_progress,
    format_indicators,
    count_met_indicators,
    generate_status_block
)


class TestCalculateProgress(unittest.TestCase):
    """Tests for progress calculation based on phase and indicators."""

    def test_init_phase_no_indicators(self):
        """INIT phase with no indicators should return base progress."""
        result = calculate_progress("INIT", {})
        self.assertEqual(result, 10)

    def test_complete_phase_all_indicators(self):
        """COMPLETE phase with all indicators should return 100."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True
        }
        result = calculate_progress("COMPLETE", indicators)
        self.assertEqual(result, 100)

    def test_impl_phase_partial_indicators(self):
        """IMPL phase with partial indicators."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": False,
            "ticket_closed": False
        }
        result = calculate_progress("IMPL", indicators)
        # Base 50 + (2/4 * 25) = 50 + 12.5 = 62
        self.assertEqual(result, 62)

    def test_verify_phase_no_indicators(self):
        """VERIFY phase with no indicators met."""
        result = calculate_progress("VERIFY", {"code_committed": False})
        # Base 75 + 0 = 75
        self.assertEqual(result, 75)

    def test_research_phase_empty_indicators(self):
        """RESEARCH phase with empty indicator dict."""
        result = calculate_progress("RESEARCH", {})
        self.assertEqual(result, 25)

    def test_unknown_phase_defaults_to_zero(self):
        """Unknown phase should use 0 as base."""
        result = calculate_progress("UNKNOWN", {})
        self.assertEqual(result, 0)


class TestFormatIndicators(unittest.TestCase):
    """Tests for indicator formatting."""

    def test_all_false_indicators(self):
        """All false indicators should show empty checkboxes."""
        result = format_indicators({})
        self.assertIn("[ ]", result)
        self.assertIn("Code changes committed", result)
        self.assertIn("Tests passing", result)

    def test_mixed_indicators(self):
        """Mixed indicators should show correct marks."""
        indicators = {
            "code_committed": True,
            "tests_passing": False,
            "docs_updated": True
        }
        result = format_indicators(indicators)
        self.assertIn("[x] Code changes committed", result)
        self.assertIn("[ ] Tests passing", result)
        self.assertIn("[x] Documentation updated", result)

    def test_all_true_indicators(self):
        """All true indicators should show checked boxes."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True,
            "marker_created": True
        }
        result = format_indicators(indicators)
        # Should have 5 [x] marks
        self.assertEqual(result.count("[x]"), 5)


class TestCountMetIndicators(unittest.TestCase):
    """Tests for indicator counting."""

    def test_empty_dict(self):
        """Empty dict should return 0 met, 5 total."""
        met, total = count_met_indicators({})
        self.assertEqual(met, 0)
        self.assertEqual(total, 5)

    def test_all_true(self):
        """All true should return correct count."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True
        }
        met, total = count_met_indicators(indicators)
        self.assertEqual(met, 3)
        self.assertEqual(total, 3)

    def test_mixed_values(self):
        """Mixed values should count correctly."""
        indicators = {
            "code_committed": True,
            "tests_passing": False,
            "docs_updated": True,
            "ticket_closed": False
        }
        met, total = count_met_indicators(indicators)
        self.assertEqual(met, 2)
        self.assertEqual(total, 4)


class TestGenerateStatusBlock(unittest.TestCase):
    """Tests for full status block generation."""

    def test_basic_status_block(self):
        """Basic status block should contain required fields."""
        result = generate_status_block(
            phase="INIT",
            iteration=1,
            max_iterations=5,
            indicators={},
            state_hash="abc123",
            prev_hash="000000",
            stagnation_count=0
        )
        self.assertIn("NAVIGATOR_STATUS", result)
        self.assertIn("Phase: INIT", result)
        self.assertIn("Iteration: 1/5", result)
        self.assertIn("State Hash: abc123", result)

    def test_exit_signal_display(self):
        """Exit signal should be displayed correctly."""
        result = generate_status_block(
            phase="VERIFY",
            iteration=3,
            max_iterations=5,
            indicators={"code_committed": True, "tests_passing": True},
            state_hash="def456",
            prev_hash="abc123",
            stagnation_count=1,
            exit_signal=True
        )
        self.assertIn("EXIT_SIGNAL: true", result)

    def test_stagnation_display(self):
        """Stagnation count should be displayed."""
        result = generate_status_block(
            phase="IMPL",
            iteration=4,
            max_iterations=5,
            indicators={},
            state_hash="same",
            prev_hash="same",
            stagnation_count=2,
            stagnation_threshold=3
        )
        self.assertIn("Stagnation: 2/3", result)

    def test_next_action_display(self):
        """Next action should be displayed."""
        result = generate_status_block(
            phase="RESEARCH",
            iteration=1,
            max_iterations=5,
            indicators={},
            state_hash="abc",
            prev_hash="000",
            stagnation_count=0,
            next_action="Read task documentation"
        )
        self.assertIn("Next Action: Read task documentation", result)

    def test_complete_phase_high_progress(self):
        """COMPLETE phase should show 100% progress."""
        indicators = {
            "code_committed": True,
            "tests_passing": True,
            "docs_updated": True,
            "ticket_closed": True
        }
        result = generate_status_block(
            phase="COMPLETE",
            iteration=5,
            max_iterations=5,
            indicators=indicators,
            state_hash="final",
            prev_hash="prev",
            stagnation_count=0,
            exit_signal=True
        )
        self.assertIn("Progress: 100%", result)


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "status_generator.py"

    def test_cli_basic_invocation(self):
        """Basic CLI invocation should succeed."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--phase", "INIT"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("NAVIGATOR_STATUS", result.stdout)

    def test_cli_with_indicators_json(self):
        """CLI with JSON indicators should parse correctly."""
        indicators = json.dumps({"code_committed": True, "tests_passing": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--indicators", indicators,
                "--iteration", "2",
                "--max-iterations", "5"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("[x] Code changes committed", result.stdout)

    def test_cli_exit_signal_flag(self):
        """CLI --exit-signal flag should work."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "VERIFY",
                "--exit-signal"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("EXIT_SIGNAL: true", result.stdout)

    def test_cli_invalid_json_handles_gracefully(self):
        """Invalid JSON indicators should be handled gracefully."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "INIT",
                "--indicators", "not-valid-json"
            ],
            capture_output=True,
            text=True
        )
        # Should still succeed with empty indicators
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
