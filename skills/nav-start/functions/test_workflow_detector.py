#!/usr/bin/env python3
"""Tests for workflow_detector.py"""

import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from workflow_detector import (
    detect_loop_trigger,
    calculate_complexity,
    detect_workflow,
    LOOP_TRIGGERS,
    COMPLEXITY_INDICATORS,
)


class TestDetectLoopTrigger(unittest.TestCase):
    """Tests for Loop Mode trigger detection."""

    def test_run_until_done(self):
        """'run until done' should trigger loop mode."""
        triggered, phrase = detect_loop_trigger("run until done: fix the bug")
        self.assertTrue(triggered)
        self.assertEqual(phrase, "run until done")

    def test_keep_going(self):
        """'keep going' should trigger loop mode."""
        triggered, phrase = detect_loop_trigger("Just keep going on this")
        self.assertTrue(triggered)
        self.assertEqual(phrase, "keep going")

    def test_iterate_until(self):
        """'iterate until' should trigger loop mode."""
        triggered, phrase = detect_loop_trigger("iterate until the tests pass")
        self.assertTrue(triggered)
        self.assertEqual(phrase, "iterate until")

    def test_case_insensitive(self):
        """Trigger matching should be case-insensitive."""
        triggered, phrase = detect_loop_trigger("RUN UNTIL DONE please")
        self.assertTrue(triggered)
        self.assertEqual(phrase, "run until done")

    def test_loop_mode_phrase(self):
        """'loop mode' itself should trigger."""
        triggered, phrase = detect_loop_trigger("Use loop mode for this")
        self.assertTrue(triggered)
        self.assertEqual(phrase, "loop mode")

    def test_plain_prompt_no_trigger(self):
        """A plain prompt should not trigger loop mode and returns None phrase."""
        triggered, phrase = detect_loop_trigger("Please review this file")
        self.assertFalse(triggered)
        self.assertIsNone(phrase)

    def test_all_known_triggers_match(self):
        """Each phrase in LOOP_TRIGGERS should be detected."""
        for trigger in LOOP_TRIGGERS:
            triggered, phrase = detect_loop_trigger(f"prefix {trigger} suffix")
            self.assertTrue(triggered, f"Expected trigger for '{trigger}'")
            # First match wins; phrase must be a member of LOOP_TRIGGERS
            self.assertIn(phrase, LOOP_TRIGGERS)


class TestCalculateComplexity(unittest.TestCase):
    """Tests for complexity scoring weights and cap."""

    def test_single_high_indicator(self):
        """A single high indicator contributes 0.3."""
        score, matched = calculate_complexity("Please refactor this")
        self.assertAlmostEqual(score, 0.3, places=2)
        self.assertIn("high:refactor", matched)

    def test_single_medium_indicator(self):
        """A single medium indicator contributes 0.2."""
        # 'enhance' is medium-only (no low/high substring overlap)
        score, matched = calculate_complexity("Please enhance it")
        self.assertAlmostEqual(score, 0.2, places=2)
        self.assertIn("medium:enhance", matched)

    def test_single_low_indicator(self):
        """A single low indicator contributes 0.1."""
        # 'remove' is low-only
        score, matched = calculate_complexity("Please remove it")
        self.assertAlmostEqual(score, 0.1, places=2)
        self.assertIn("low:remove", matched)

    def test_multi_file_adds_once(self):
        """Multi-file indicators add 0.2 and only count once."""
        # 'across' and 'codebase' are both multi-file; only one counts
        score, matched = calculate_complexity("change across the codebase")
        multi_matches = [m for m in matched if m.startswith("multi-file:")]
        self.assertEqual(len(multi_matches), 1)

    def test_trivial_prompt_scores_low(self):
        """A prompt with no indicators scores 0.0."""
        score, matched = calculate_complexity("hello there")
        self.assertEqual(score, 0.0)
        self.assertEqual(matched, [])

    def test_multi_signal_prompt_scores_high(self):
        """A prompt with many indicators scores high (and below/at cap)."""
        score, matched = calculate_complexity(
            "Refactor and implement the new feature across the entire codebase"
        )
        self.assertGreaterEqual(score, 0.5)
        self.assertLessEqual(score, 1.0)

    def test_score_capped_at_one(self):
        """Score is capped at 1.0 even with many strong indicators."""
        # Multiple high (refactor, implement, migrate, architecture, redesign,
        # overhaul) would sum well past 1.0 before the cap.
        score, _ = calculate_complexity(
            "refactor implement migrate architecture redesign overhaul "
            "across the codebase"
        )
        self.assertEqual(score, 1.0)


class TestDetectWorkflow(unittest.TestCase):
    """Tests for full workflow detection dict."""

    EXPECTED_KEYS = {
        "loop_mode",
        "loop_trigger",
        "task_mode",
        "complexity",
        "complexity_indicators",
        "recommended_mode",
    }

    def test_result_has_expected_keys(self):
        """Returned dict exposes the keys the enforcer consumes."""
        result = detect_workflow("Add a button")
        for key in self.EXPECTED_KEYS:
            self.assertIn(key, result)

    def test_loop_trigger_prompt(self):
        """A loop-trigger prompt recommends LOOP mode."""
        result = detect_workflow("run until done: build the dashboard")
        self.assertTrue(result["loop_mode"])
        self.assertEqual(result["loop_trigger"], "run until done")
        self.assertEqual(result["recommended_mode"], "LOOP")

    def test_complex_non_loop_prompt_is_task(self):
        """A complex prompt without loop trigger recommends TASK mode."""
        result = detect_workflow(
            "Refactor the authentication architecture across the codebase"
        )
        self.assertFalse(result["loop_mode"])
        self.assertTrue(result["task_mode"])
        self.assertGreaterEqual(result["complexity"], 0.5)
        self.assertEqual(result["recommended_mode"], "TASK")

    def test_plain_prompt_is_direct(self):
        """A plain low-complexity prompt recommends DIRECT mode."""
        result = detect_workflow("What time is it")
        self.assertFalse(result["loop_mode"])
        self.assertFalse(result["task_mode"])
        self.assertIsNone(result["loop_trigger"])
        self.assertEqual(result["recommended_mode"], "DIRECT")

    def test_task_mode_threshold(self):
        """task_mode flips at complexity >= 0.5."""
        # 'implement' (high, 0.3) alone is below threshold -> not task_mode
        below = detect_workflow("implement it")
        self.assertLess(below["complexity"], 0.5)
        self.assertFalse(below["task_mode"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
