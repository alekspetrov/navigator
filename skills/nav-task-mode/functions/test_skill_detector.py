#!/usr/bin/env python3
"""Tests for skill_detector.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from skill_detector import (
    calculate_match_score,
    detect_skill_match,
    SKILL_TRIGGERS,
    SkillMatch
)


class TestCalculateMatchScore(unittest.TestCase):
    """Tests for match score calculation."""

    def test_pattern_match_increases_score(self):
        """Pattern matches should increase score."""
        score, triggers = calculate_match_score(
            "Create a new component",
            SKILL_TRIGGERS["frontend-component"]["patterns"],
            SKILL_TRIGGERS["frontend-component"]["keywords"]
        )
        self.assertGreater(score, 0)
        self.assertGreater(len(triggers), 0)

    def test_keyword_match_increases_score(self):
        """Keyword matches should increase score."""
        score, triggers = calculate_match_score(
            "Working with react component",
            [],  # No patterns
            ["react", "component"]
        )
        self.assertGreater(score, 0)

    def test_no_match_zero_score(self):
        """No matches should return zero score."""
        score, triggers = calculate_match_score(
            "Something completely unrelated",
            [r'\bxyz123\b'],
            ["xyz", "123"]
        )
        self.assertEqual(score, 0)
        self.assertEqual(len(triggers), 0)

    def test_score_capped_at_one(self):
        """Score should be capped at 1.0."""
        # Many matches
        score, triggers = calculate_match_score(
            "Create a new button component for the react ui interface",
            SKILL_TRIGGERS["frontend-component"]["patterns"],
            SKILL_TRIGGERS["frontend-component"]["keywords"]
        )
        self.assertLessEqual(score, 1.0)


class TestDetectSkillMatch(unittest.TestCase):
    """Tests for skill match detection."""

    def test_frontend_component_detection(self):
        """Should detect frontend-component skill."""
        result = detect_skill_match("Create a new login component")
        self.assertEqual(result.matching_skill, "frontend-component")
        self.assertTrue(result.defer)
        self.assertGreater(result.confidence, 0.5)

    def test_backend_endpoint_detection(self):
        """Should detect backend-endpoint skill."""
        result = detect_skill_match("Add a new REST API endpoint for users")
        self.assertEqual(result.matching_skill, "backend-endpoint")
        self.assertTrue(result.defer)

    def test_database_migration_detection(self):
        """Should detect database-migration skill."""
        result = detect_skill_match("Create a migration to add user preferences table")
        self.assertEqual(result.matching_skill, "database-migration")
        self.assertTrue(result.defer)

    def test_nav_loop_detection(self):
        """Should detect nav-loop skill."""
        result = detect_skill_match("Run until done: implement the feature")
        self.assertEqual(result.matching_skill, "nav-loop")
        self.assertTrue(result.defer)

    def test_nav_marker_detection(self):
        """Should detect nav-marker skill."""
        result = detect_skill_match("Create a checkpoint before we continue")
        self.assertEqual(result.matching_skill, "nav-marker")

    def test_nav_compact_detection(self):
        """Should detect nav-compact skill."""
        result = detect_skill_match("Clear context and start fresh")
        self.assertEqual(result.matching_skill, "nav-compact")

    def test_no_match_returns_none(self):
        """Should return None when no skill matches."""
        result = detect_skill_match("What is the meaning of life?")
        self.assertIsNone(result.matching_skill)
        self.assertFalse(result.defer)
        self.assertEqual(result.confidence, 0)

    def test_low_confidence_no_defer(self):
        """Low confidence matches should not defer."""
        result = detect_skill_match("Maybe update something")
        # Might match weakly but shouldn't defer
        if result.confidence < 0.5:
            self.assertFalse(result.defer)

    def test_available_skills_filter(self):
        """Should only match available skills."""
        result = detect_skill_match(
            "Create a new component",
            available_skills=["backend-endpoint"]  # Exclude frontend-component
        )
        # Should not match frontend-component since it's not available
        self.assertNotEqual(result.matching_skill, "frontend-component")


class TestSkillMatchResult(unittest.TestCase):
    """Tests for SkillMatch result structure."""

    def test_result_structure(self):
        """Result should have all expected fields."""
        result = detect_skill_match("Some request")
        self.assertIsInstance(result, SkillMatch)
        self.assertIn("matching_skill", vars(result) if hasattr(result, '__dict__') else dir(result))

    def test_triggers_limited(self):
        """Triggers should be limited to top 3."""
        result = detect_skill_match(
            "Create new button component for react ui interface widget"
        )
        self.assertLessEqual(len(result.triggers), 3)

    def test_alternatives_limited(self):
        """Alternatives should be limited to top 2."""
        result = detect_skill_match(
            "Create a component and add tests for it"  # Could match multiple
        )
        self.assertLessEqual(len(result.alternative_skills), 2)


class TestRealWorldRequests(unittest.TestCase):
    """Tests with real-world request examples."""

    def test_add_button_component(self):
        """'Add a button component' should match frontend-component."""
        result = detect_skill_match("Add a button component to the header")
        self.assertEqual(result.matching_skill, "frontend-component")

    def test_create_user_endpoint(self):
        """'Create user endpoint' should match backend-endpoint."""
        result = detect_skill_match("Create a POST endpoint for user registration")
        self.assertEqual(result.matching_skill, "backend-endpoint")

    def test_write_tests_for_api(self):
        """'Write tests for API' should match backend-test."""
        result = detect_skill_match("Write unit tests for the authentication API")
        self.assertEqual(result.matching_skill, "backend-test")

    def test_component_tests(self):
        """'Test component' should match frontend-test."""
        result = detect_skill_match("Write unit tests for the LoginForm component")
        # Could match frontend-test or be weak match depending on phrasing
        if result.matching_skill:
            self.assertIn(result.matching_skill, ["frontend-test", "frontend-component"])

    def test_save_progress(self):
        """'Save my progress' should match nav-marker."""
        result = detect_skill_match("Save my progress before I take a break")
        self.assertEqual(result.matching_skill, "nav-marker")

    def test_something_wrong(self):
        """'Something seems off' should match nav-diagnose."""
        result = detect_skill_match("Something seems off with your responses")
        self.assertEqual(result.matching_skill, "nav-diagnose")

    def test_document_solution(self):
        """'Document this solution' should match nav-sop."""
        result = detect_skill_match("Document this solution for future reference")
        self.assertEqual(result.matching_skill, "nav-sop")

    def test_loop_until_done(self):
        """'Run until done' should match nav-loop."""
        result = detect_skill_match("Run until done: implement the feature")
        self.assertEqual(result.matching_skill, "nav-loop")


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "skill_detector.py"

    def test_cli_basic_invocation(self):
        """Basic CLI invocation should succeed."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Create a component"
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
                "--request", "Add new component",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertIn("matching_skill", output)
        self.assertIn("confidence", output)
        self.assertIn("defer", output)

    def test_cli_text_output(self):
        """CLI text output should be human readable."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Add new component",
                "--output", "text"
            ],
            capture_output=True,
            text=True
        )
        self.assertIn("Matching Skill:", result.stdout)

    def test_cli_text_no_match(self):
        """CLI text output for no match."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Random unrelated text xyz123",
                "--output", "text"
            ],
            capture_output=True,
            text=True
        )
        self.assertIn("No skill match", result.stdout)

    def test_cli_available_skills_filter(self):
        """CLI should handle available-skills filter."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Create a component",
                "--available-skills", '["backend-endpoint"]',
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        # Should not match frontend-component
        self.assertNotEqual(output["matching_skill"], "frontend-component")

    def test_cli_invalid_json_error(self):
        """Invalid JSON should cause error."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--request", "Test",
                "--available-skills", "not-valid-json"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
