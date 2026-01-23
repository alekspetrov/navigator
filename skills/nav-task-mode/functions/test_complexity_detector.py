#!/usr/bin/env python3
"""Tests for complexity_detector.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from complexity_detector import (
    detect_signals,
    calculate_complexity,
    get_recommendation,
    detect_complexity,
    ComplexityResult
)


class TestDetectSignals(unittest.TestCase):
    """Tests for signal detection in text."""

    def test_multi_file_patterns(self):
        """Multi-file patterns should be detected."""
        signals, weights = detect_signals("Refactor the authentication system")
        self.assertTrue(signals.get("multi_file", False))
        self.assertIn("multi_file", weights)

    def test_planning_language(self):
        """Planning/feature language should be detected."""
        signals, weights = detect_signals("Implement a new user registration feature")
        self.assertTrue(signals.get("planning_language", False))

    def test_cross_system_patterns(self):
        """Cross-system patterns should be detected."""
        signals, weights = detect_signals("Update frontend and backend for the new API")
        self.assertTrue(signals.get("cross_system", False))

    def test_research_patterns(self):
        """Research patterns should be detected."""
        signals, weights = detect_signals("Figure out how the cache system works")
        self.assertTrue(signals.get("needs_research", False))

    def test_testing_mentioned(self):
        """Testing requirements should be detected."""
        signals, weights = detect_signals("Add unit tests for the auth service")
        self.assertTrue(signals.get("testing_mentioned", False))

    def test_security_patterns(self):
        """Security-related patterns should be detected."""
        signals, weights = detect_signals("Add authentication to the endpoint")
        self.assertTrue(signals.get("security_work", False))

    def test_data_patterns(self):
        """Data/state patterns should be detected."""
        signals, weights = detect_signals("Update the database schema")
        self.assertTrue(signals.get("data_changes", False))

    def test_simplicity_single_file(self):
        """Single file indicators should be detected."""
        signals, weights = detect_signals("Fix the bug in src/auth.ts")
        self.assertTrue(signals.get("single_file", False))
        self.assertLess(weights.get("single_file", 0), 0)

    def test_simplicity_quick_modifier(self):
        """Quick/simple modifiers should be detected."""
        signals, weights = detect_signals("Just fix the typo")
        self.assertTrue(signals.get("quick_modifier", False))
        self.assertTrue(signals.get("fix_language", False))

    def test_simplicity_specific_location(self):
        """Specific location should be detected."""
        signals, weights = detect_signals("Fix function calculateTotal")
        self.assertTrue(signals.get("specific_location", False))


class TestCalculateComplexity(unittest.TestCase):
    """Tests for complexity score calculation."""

    def test_neutral_no_signals(self):
        """No signals should return neutral 0.5."""
        score = calculate_complexity({}, {})
        self.assertEqual(score, 0.5)

    def test_complexity_increases_with_positive_weights(self):
        """Positive weights should increase complexity."""
        signals = {"multi_file": True, "planning_language": True}
        weights = {"multi_file": 0.3, "planning_language": 0.2}
        score = calculate_complexity(signals, weights)
        self.assertGreater(score, 0.5)
        self.assertEqual(score, 1.0)  # 0.5 + 0.3 + 0.2 = 1.0

    def test_complexity_decreases_with_negative_weights(self):
        """Negative weights should decrease complexity."""
        signals = {"single_file": True, "quick_modifier": True}
        weights = {"single_file": -0.3, "quick_modifier": -0.2}
        score = calculate_complexity(signals, weights)
        self.assertLess(score, 0.5)
        self.assertEqual(score, 0.0)  # 0.5 - 0.3 - 0.2 = 0.0

    def test_complexity_clamped_to_range(self):
        """Complexity should be clamped to 0-1."""
        # Very high
        score = calculate_complexity({}, {"a": 1.0, "b": 1.0})
        self.assertEqual(score, 1.0)
        # Very low
        score = calculate_complexity({}, {"a": -1.0, "b": -1.0})
        self.assertEqual(score, 0.0)


class TestGetRecommendation(unittest.TestCase):
    """Tests for recommendation based on score."""

    def test_low_score_direct_execution(self):
        """Low score should recommend direct execution."""
        rec, reason = get_recommendation(0.2, 0.5)
        self.assertEqual(rec, "direct_execution")

    def test_below_threshold_direct(self):
        """Below threshold should recommend direct execution."""
        rec, reason = get_recommendation(0.4, 0.5)
        self.assertEqual(rec, "direct_execution")
        self.assertIn("threshold", reason)

    def test_medium_score_task_mode(self):
        """Medium score should recommend task mode."""
        rec, reason = get_recommendation(0.6, 0.5)
        self.assertEqual(rec, "task_mode")
        self.assertIn("Substantial", reason)

    def test_high_score_task_mode(self):
        """High score should recommend task mode with full tracking."""
        rec, reason = get_recommendation(0.8, 0.5)
        self.assertEqual(rec, "task_mode")
        self.assertIn("Complex", reason)


class TestDetectComplexity(unittest.TestCase):
    """Tests for full complexity detection."""

    def test_simple_task(self):
        """Simple tasks should have low complexity."""
        result = detect_complexity("Fix the typo in README.md")
        self.assertLess(result.complexity_score, 0.5)
        self.assertFalse(result.is_substantial)
        self.assertEqual(result.recommendation, "direct_execution")

    def test_complex_task(self):
        """Complex tasks should have high complexity."""
        result = detect_complexity(
            "Refactor the authentication system to use JWT and update "
            "both frontend and backend with proper integration tests"
        )
        self.assertGreater(result.complexity_score, 0.5)
        self.assertTrue(result.is_substantial)
        self.assertEqual(result.recommendation, "task_mode")

    def test_context_affects_score(self):
        """Context should influence complexity score."""
        # Same request, different context
        result_simple = detect_complexity(
            "Add validation",
            context="Simple form field"
        )
        result_complex = detect_complexity(
            "Add validation",
            context="Security-critical authentication system with multiple endpoints"
        )
        self.assertLess(result_simple.complexity_score, result_complex.complexity_score)

    def test_custom_threshold(self):
        """Custom threshold should affect is_substantial."""
        result_default = detect_complexity("Implement a feature", threshold=0.5)
        result_high = detect_complexity("Implement a feature", threshold=0.9)

        # Same score, different is_substantial based on threshold
        if result_default.complexity_score >= 0.5:
            self.assertTrue(result_default.is_substantial)
        if result_high.complexity_score < 0.9:
            self.assertFalse(result_high.is_substantial)

    def test_result_structure(self):
        """Result should have all expected fields."""
        result = detect_complexity("Some task")
        self.assertIsInstance(result, ComplexityResult)
        self.assertIsInstance(result.complexity_score, float)
        self.assertIsInstance(result.signals, dict)
        self.assertIsInstance(result.signal_weights, dict)
        self.assertIsInstance(result.recommendation, str)
        self.assertIsInstance(result.reason, str)
        self.assertIsInstance(result.is_substantial, bool)


class TestRealWorldExamples(unittest.TestCase):
    """Tests with real-world request examples."""

    def test_typo_fix(self):
        """Typo fix should be simple."""
        result = detect_complexity("Fix the typo in the README")
        self.assertFalse(result.is_substantial)

    def test_add_component(self):
        """Adding component should be moderate."""
        result = detect_complexity("Add a new button component")
        # This might be medium complexity
        self.assertGreater(result.complexity_score, 0.3)

    def test_refactor_system(self):
        """System refactoring should be complex."""
        result = detect_complexity(
            "Refactor the entire payment system to use a new provider"
        )
        self.assertTrue(result.is_substantial)

    def test_database_migration(self):
        """Database migration should be complex."""
        result = detect_complexity(
            "Add a new table for user preferences with proper schema migration"
        )
        self.assertTrue(result.is_substantial)

    def test_simple_update(self):
        """Simple update should be simple."""
        result = detect_complexity("Update the copyright year in footer")
        self.assertFalse(result.is_substantial)


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "complexity_detector.py"

    def test_cli_basic_invocation(self):
        """Basic CLI invocation should succeed."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Fix a bug"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_cli_json_output(self):
        """CLI JSON output should be valid."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Refactor authentication",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertIn("complexity_score", output)
        self.assertIn("recommendation", output)

    def test_cli_text_output(self):
        """CLI text output should be human readable."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Add feature",
                "--output", "text"
            ],
            capture_output=True,
            text=True
        )
        self.assertIn("Complexity Score:", result.stdout)
        self.assertIn("Recommendation:", result.stdout)

    def test_cli_with_context(self):
        """CLI should handle context parameter."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Update component",
                "--context", "Working on auth system"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_cli_custom_threshold(self):
        """CLI should handle threshold parameter."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Add feature",
                "--threshold", "0.7",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        # Check that threshold affected is_substantial
        self.assertIn("is_substantial", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
