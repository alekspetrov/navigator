#!/usr/bin/env python3
"""Tests for phase_indicator.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from phase_indicator import (
    get_next_phase,
    calculate_overall_progress,
    format_activation,
    format_transition,
    format_progress,
    format_completion,
    format_skill_defer,
    PHASE_ORDER,
    PHASE_INFO
)


class TestGetNextPhase(unittest.TestCase):
    """Tests for phase sequence navigation."""

    def test_research_to_plan(self):
        """RESEARCH should go to PLAN."""
        self.assertEqual(get_next_phase("RESEARCH"), "PLAN")

    def test_plan_to_impl(self):
        """PLAN should go to IMPL."""
        self.assertEqual(get_next_phase("PLAN"), "IMPL")

    def test_impl_to_verify(self):
        """IMPL should go to VERIFY."""
        self.assertEqual(get_next_phase("IMPL"), "VERIFY")

    def test_verify_to_complete(self):
        """VERIFY should go to COMPLETE."""
        self.assertEqual(get_next_phase("VERIFY"), "COMPLETE")

    def test_complete_has_no_next(self):
        """COMPLETE should have no next phase."""
        self.assertIsNone(get_next_phase("COMPLETE"))

    def test_unknown_phase_returns_none(self):
        """Unknown phase should return None."""
        self.assertIsNone(get_next_phase("UNKNOWN"))

    def test_case_insensitive(self):
        """Phase lookup should be case insensitive."""
        self.assertEqual(get_next_phase("research"), "PLAN")
        self.assertEqual(get_next_phase("Research"), "PLAN")


class TestCalculateOverallProgress(unittest.TestCase):
    """Tests for overall progress calculation."""

    def test_research_start(self):
        """RESEARCH at 0% should be ~0% overall."""
        progress = calculate_overall_progress("RESEARCH", 0)
        self.assertEqual(progress, 0)

    def test_research_complete(self):
        """RESEARCH at 100% should be ~20% overall."""
        progress = calculate_overall_progress("RESEARCH", 100)
        self.assertEqual(progress, 20)

    def test_impl_midway(self):
        """IMPL at 50% should be around 50% overall."""
        progress = calculate_overall_progress("IMPL", 50)
        # IMPL is phase 2 (40%) + 50% of phase weight (10%) = 50%
        self.assertEqual(progress, 50)

    def test_complete_phase(self):
        """COMPLETE at 100% should be 100% overall."""
        progress = calculate_overall_progress("COMPLETE", 100)
        self.assertEqual(progress, 100)

    def test_unknown_phase_returns_phase_progress(self):
        """Unknown phase should return phase progress as fallback."""
        progress = calculate_overall_progress("UNKNOWN", 75)
        self.assertEqual(progress, 75)


class TestFormatActivation(unittest.TestCase):
    """Tests for activation banner formatting."""

    def test_contains_task_summary(self):
        """Activation should show task summary."""
        output = format_activation("Add user auth", 0.7, 0.5)
        self.assertIn("Add user auth", output)

    def test_contains_complexity(self):
        """Activation should show complexity score."""
        output = format_activation("Task", 0.75, 0.5)
        self.assertIn("0.75", output)

    def test_contains_phases(self):
        """Activation should list all phases."""
        output = format_activation("Task", 0.6, 0.5)
        for phase in PHASE_ORDER:
            self.assertIn(phase, output)

    def test_contains_header(self):
        """Activation should have header."""
        output = format_activation("Task", 0.6, 0.5)
        self.assertIn("TASK MODE ACTIVATED", output)


class TestFormatTransition(unittest.TestCase):
    """Tests for phase transition formatting."""

    def test_shows_both_phases(self):
        """Transition should show from and to phases."""
        output = format_transition("RESEARCH", "PLAN", {})
        self.assertIn("RESEARCH", output)
        self.assertIn("PLAN", output)

    def test_shows_completed_details(self):
        """Transition should show completed details."""
        details = {"files_explored": 5, "patterns_found": True}
        output = format_transition("RESEARCH", "PLAN", details)
        self.assertIn("Files Explored", output)
        self.assertIn("5", output)

    def test_boolean_details_format(self):
        """Boolean details should show checkmarks."""
        details = {"tests_written": True, "docs_updated": False}
        output = format_transition("IMPL", "VERIFY", details)
        self.assertIn("✓", output)


class TestFormatProgress(unittest.TestCase):
    """Tests for progress indicator formatting."""

    def test_shows_phase(self):
        """Progress should show current phase."""
        output = format_progress("IMPL", "in_progress", 50, {})
        self.assertIn("IMPL", output)

    def test_shows_progress_bar(self):
        """Progress should show progress bar."""
        output = format_progress("IMPL", "in_progress", 50, {})
        self.assertIn("█", output)
        self.assertIn("░", output)

    def test_shows_percentage(self):
        """Progress should show percentage."""
        output = format_progress("IMPL", "in_progress", 75, {})
        self.assertIn("75%", output)

    def test_shows_details(self):
        """Progress should show activity details."""
        details = {"files_changed": 3, "tests_written": 2}
        output = format_progress("IMPL", "in_progress", 50, details)
        self.assertIn("Files Changed", output)
        self.assertIn("3", output)

    def test_phases_list_shows_current(self):
        """Phases list should mark current phase."""
        output = format_progress("IMPL", "in_progress", 50, {})
        self.assertIn("← current", output)


class TestFormatCompletion(unittest.TestCase):
    """Tests for completion banner formatting."""

    def test_shows_task_summary(self):
        """Completion should show task summary."""
        output = format_completion("Add auth feature", {}, {})
        self.assertIn("Add auth feature", output)

    def test_shows_phases_completed(self):
        """Completion should show phases completed."""
        phases = {
            "RESEARCH": {"duration": "2m"},
            "PLAN": {"duration": "1m"},
            "IMPL": {"duration": "5m"}
        }
        output = format_completion("Task", phases, {})
        self.assertIn("RESEARCH", output)

    def test_shows_summary(self):
        """Completion should show summary metrics."""
        summary = {"files_changed": 5, "tests_added": 3}
        output = format_completion("Task", {}, summary)
        self.assertIn("Files Changed", output)
        self.assertIn("5", output)

    def test_contains_header(self):
        """Completion should have header."""
        output = format_completion("Task", {}, {})
        self.assertIn("TASK MODE COMPLETE", output)


class TestFormatSkillDefer(unittest.TestCase):
    """Tests for skill deferral formatting."""

    def test_shows_skill_name(self):
        """Deferral should show skill name."""
        output = format_skill_defer("frontend-component", 0.9, "Matches component")
        self.assertIn("frontend-component", output)

    def test_shows_confidence(self):
        """Deferral should show confidence."""
        output = format_skill_defer("backend-endpoint", 0.85, "Matches endpoint")
        self.assertIn("85%", output)

    def test_shows_reason(self):
        """Deferral should show reason."""
        output = format_skill_defer("nav-loop", 0.95, "Loop mode trigger detected")
        self.assertIn("Loop mode trigger", output)

    def test_contains_header(self):
        """Deferral should have header."""
        output = format_skill_defer("skill", 0.9, "reason")
        self.assertIn("SKILL DETECTED", output)


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "phase_indicator.py"

    def test_cli_progress_mode(self):
        """CLI progress mode should work."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--status", "in_progress",
                "--progress", "50",
                "--mode", "progress"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("TASK MODE", result.stdout)

    def test_cli_activation_mode(self):
        """CLI activation mode should work."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "RESEARCH",
                "--mode", "activation",
                "--task-summary", "Add new feature",
                "--complexity", "0.7",
                "--threshold", "0.5"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ACTIVATED", result.stdout)

    def test_cli_transition_mode(self):
        """CLI transition mode should work."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "PLAN",
                "--mode", "transition",
                "--from-phase", "RESEARCH"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("→", result.stdout)

    def test_cli_completion_mode(self):
        """CLI completion mode should work."""
        details = json.dumps({
            "phases": {"IMPL": {"duration": "5m"}},
            "summary": {"files_changed": 3}
        })
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "COMPLETE",
                "--mode", "completion",
                "--task-summary", "Feature complete",
                "--details", details
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("COMPLETE", result.stdout)

    def test_cli_defer_mode(self):
        """CLI defer mode should work."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "RESEARCH",
                "--mode", "defer",
                "--skill-name", "frontend-component",
                "--confidence", "0.9"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("SKILL DETECTED", result.stdout)

    def test_cli_with_details_json(self):
        """CLI should handle details JSON."""
        details = json.dumps({"files_changed": 5, "tests_written": True})
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--details", details
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
