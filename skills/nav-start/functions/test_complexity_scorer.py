#!/usr/bin/env python3
"""Tests for complexity_scorer.py"""

import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from complexity_scorer import calculate_score, find_matches


class TestFindMatches(unittest.TestCase):
    """Tests for the case-insensitive substring matcher."""

    def test_case_insensitive_match(self):
        matches = find_matches("REFACTOR the code", ["refactor", "rewrite"])
        self.assertEqual(matches, ["refactor"])

    def test_no_match(self):
        matches = find_matches("hello there", ["refactor"])
        self.assertEqual(matches, [])


class TestCalculateScoreStructure(unittest.TestCase):
    """Tests for the returned scoring dict structure."""

    def test_result_top_level_keys(self):
        """Result exposes score, task_mode, category, factors, matched."""
        result = calculate_score("add a button")
        for key in ("score", "task_mode", "category", "factors", "matched"):
            self.assertIn(key, result)

    def test_factor_breakdown_keys(self):
        """factors dict has the four documented factor keys."""
        result = calculate_score("add a button")
        self.assertEqual(
            set(result["factors"].keys()),
            {"action_type", "scope", "files_implied", "planning_needed"},
        )

    def test_types(self):
        """Score is float, task_mode bool, category str, matched list."""
        result = calculate_score("refactor the module")
        self.assertIsInstance(result["score"], float)
        self.assertIsInstance(result["task_mode"], bool)
        self.assertIsInstance(result["category"], str)
        self.assertIsInstance(result["matched"], list)


class TestCategoryBoundaries(unittest.TestCase):
    """Tests for the five category boundaries (verified against source)."""

    def test_trivial(self):
        """score < 0.2 -> trivial. 'typo' scores 0.05."""
        result = calculate_score("typo")
        self.assertEqual(result["score"], 0.05)
        self.assertEqual(result["category"], "trivial")
        self.assertFalse(result["task_mode"])

    def test_simple(self):
        """0.2 <= score < 0.4 -> simple. 'rename this method' scores 0.2."""
        result = calculate_score("rename this method")
        self.assertEqual(result["score"], 0.2)
        self.assertEqual(result["category"], "simple")
        self.assertFalse(result["task_mode"])

    def test_moderate(self):
        """0.4 <= score < 0.6 -> moderate. 'implement a new module' scores 0.4."""
        result = calculate_score("implement a new module")
        self.assertEqual(result["score"], 0.4)
        self.assertEqual(result["category"], "moderate")

    def test_substantial(self):
        """0.6 <= score < 0.8 -> substantial. Scores 0.7."""
        result = calculate_score("refactor module with a design plan")
        self.assertEqual(result["score"], 0.7)
        self.assertEqual(result["category"], "substantial")
        self.assertTrue(result["task_mode"])

    def test_complex(self):
        """score >= 0.8 -> complex; capped at 1.0."""
        result = calculate_score(
            "refactor the entire codebase across all services "
            "with architecture design"
        )
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["category"], "complex")
        self.assertTrue(result["task_mode"])


class TestTaskModeFlag(unittest.TestCase):
    """Tests for the task_mode flag flipping at score >= 0.5."""

    def test_below_threshold_false(self):
        """A 0.4 score is below 0.5 -> task_mode False."""
        result = calculate_score("implement a new module")
        self.assertEqual(result["score"], 0.4)
        self.assertFalse(result["task_mode"])

    def test_at_threshold_true(self):
        """A 0.5 score is at the threshold -> task_mode True."""
        result = calculate_score("refactor the module")
        self.assertEqual(result["score"], 0.5)
        self.assertTrue(result["task_mode"])


class TestScoreCap(unittest.TestCase):
    """Score must never exceed 1.0."""

    def test_capped_at_one(self):
        result = calculate_score(
            "refactor redesign the entire codebase across all services "
            "modules components endpoints with architecture design strategy plan"
        )
        self.assertLessEqual(result["score"], 1.0)
        self.assertEqual(result["score"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
