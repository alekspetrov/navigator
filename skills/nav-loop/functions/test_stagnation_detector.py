#!/usr/bin/env python3
"""Tests for stagnation_detector.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
from stagnation_detector import (
    calculate_state_hash,
    count_consecutive_same,
    check_stagnation,
    detect_stagnation
)


class TestCalculateStateHash(unittest.TestCase):
    """Tests for state hash calculation."""

    def test_same_state_same_hash(self):
        """Same state should produce same hash."""
        hash1 = calculate_state_hash(
            phase="IMPL",
            indicators={"code_committed": True},
            files_changed=["a.ts", "b.ts"]
        )
        hash2 = calculate_state_hash(
            phase="IMPL",
            indicators={"code_committed": True},
            files_changed=["a.ts", "b.ts"]
        )
        self.assertEqual(hash1, hash2)

    def test_different_phase_different_hash(self):
        """Different phase should produce different hash."""
        hash1 = calculate_state_hash(
            phase="IMPL",
            indicators={},
            files_changed=[]
        )
        hash2 = calculate_state_hash(
            phase="VERIFY",
            indicators={},
            files_changed=[]
        )
        self.assertNotEqual(hash1, hash2)

    def test_different_indicators_different_hash(self):
        """Different indicators should produce different hash."""
        hash1 = calculate_state_hash(
            phase="IMPL",
            indicators={"code_committed": True},
            files_changed=[]
        )
        hash2 = calculate_state_hash(
            phase="IMPL",
            indicators={"code_committed": False},
            files_changed=[]
        )
        self.assertNotEqual(hash1, hash2)

    def test_file_order_doesnt_matter(self):
        """File order should not affect hash (sorted internally)."""
        hash1 = calculate_state_hash(
            phase="IMPL",
            indicators={},
            files_changed=["a.ts", "b.ts"]
        )
        hash2 = calculate_state_hash(
            phase="IMPL",
            indicators={},
            files_changed=["b.ts", "a.ts"]
        )
        self.assertEqual(hash1, hash2)

    def test_error_state_affects_hash(self):
        """Error state should affect hash."""
        hash1 = calculate_state_hash(
            phase="IMPL",
            indicators={},
            files_changed=[],
            error_state="Test failed"
        )
        hash2 = calculate_state_hash(
            phase="IMPL",
            indicators={},
            files_changed=[],
            error_state=None
        )
        self.assertNotEqual(hash1, hash2)

    def test_hash_is_six_chars(self):
        """Hash should be exactly 6 characters."""
        hash1 = calculate_state_hash("INIT", {}, [])
        self.assertEqual(len(hash1), 6)


class TestCountConsecutiveSame(unittest.TestCase):
    """Tests for consecutive same hash counting."""

    def test_empty_history(self):
        """Empty history should return 1 (current counts)."""
        result = count_consecutive_same([], "abc")
        self.assertEqual(result, 1)

    def test_all_same_history(self):
        """All same in history should return correct count."""
        result = count_consecutive_same(["abc", "abc", "abc"], "abc")
        self.assertEqual(result, 4)  # 3 in history + current

    def test_recent_same_old_different(self):
        """Should count only consecutive from end."""
        result = count_consecutive_same(["xyz", "abc", "abc"], "abc")
        self.assertEqual(result, 3)  # 2 recent in history + current

    def test_no_matches(self):
        """No matches in history should return 1."""
        result = count_consecutive_same(["xyz", "def", "ghi"], "abc")
        self.assertEqual(result, 1)


class TestCheckStagnation(unittest.TestCase):
    """Tests for stagnation check."""

    def test_stagnant_at_threshold(self):
        """Should detect stagnation at threshold."""
        history = ["abc", "abc"]  # 2 same
        is_stagnant, count = check_stagnation("abc", history, threshold=3)
        self.assertTrue(is_stagnant)
        self.assertEqual(count, 3)

    def test_not_stagnant_below_threshold(self):
        """Should not detect stagnation below threshold."""
        history = ["abc"]  # 1 same
        is_stagnant, count = check_stagnation("abc", history, threshold=3)
        self.assertFalse(is_stagnant)
        self.assertEqual(count, 2)

    def test_stagnant_above_threshold(self):
        """Should detect stagnation above threshold."""
        history = ["abc", "abc", "abc", "abc"]  # 4 same
        is_stagnant, count = check_stagnation("abc", history, threshold=3)
        self.assertTrue(is_stagnant)
        self.assertEqual(count, 5)


class TestDetectStagnation(unittest.TestCase):
    """Tests for full stagnation detection."""

    def test_no_stagnation_fresh_start(self):
        """Fresh start should not be stagnant."""
        result = detect_stagnation(
            phase="INIT",
            indicators={},
            files_changed=[],
            history=[]
        )
        self.assertFalse(result["is_stagnant"])
        self.assertIn("OK", result["recommendation"])

    def test_stagnation_detected(self):
        """Stagnation should be detected with repeated state."""
        # Calculate what hash would be for this state
        test_hash = calculate_state_hash("IMPL", {}, [])
        result = detect_stagnation(
            phase="IMPL",
            indicators={},
            files_changed=[],
            history=[test_hash, test_hash],
            threshold=3
        )
        self.assertTrue(result["is_stagnant"])
        self.assertIn("PAUSE", result["recommendation"])

    def test_warning_near_threshold(self):
        """Should warn when approaching threshold."""
        test_hash = calculate_state_hash("IMPL", {}, [])
        result = detect_stagnation(
            phase="IMPL",
            indicators={},
            files_changed=[],
            history=[test_hash],
            threshold=3
        )
        self.assertFalse(result["is_stagnant"])
        self.assertIn("WARNING", result["recommendation"])

    def test_result_contains_all_fields(self):
        """Result should contain all expected fields."""
        result = detect_stagnation(
            phase="INIT",
            indicators={},
            files_changed=[],
            history=[]
        )
        expected_fields = [
            "current_hash",
            "previous_hash",
            "is_stagnant",
            "consecutive_count",
            "threshold",
            "recommendation",
            "state_components"
        ]
        for field in expected_fields:
            self.assertIn(field, result)

    def test_state_components_populated(self):
        """State components should be populated."""
        result = detect_stagnation(
            phase="VERIFY",
            indicators={"code_committed": True, "tests_passing": True},
            files_changed=["a.ts", "b.ts"],
            history=[]
        )
        self.assertEqual(result["state_components"]["phase"], "VERIFY")
        self.assertEqual(len(result["state_components"]["met_indicators"]), 2)
        self.assertEqual(result["state_components"]["files_changed_count"], 2)


class TestCLIInterface(unittest.TestCase):
    """Tests for CLI interface."""

    def setUp(self):
        self.script_path = Path(__file__).parent / "stagnation_detector.py"

    def test_cli_basic_invocation(self):
        """Basic CLI invocation should succeed."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--phase", "INIT"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_cli_json_output(self):
        """CLI JSON output should be valid."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        self.assertIn("current_hash", output)
        self.assertIn("is_stagnant", output)

    def test_cli_text_output(self):
        """CLI text output should be human readable."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--output", "text"
            ],
            capture_output=True,
            text=True
        )
        self.assertIn("Hash:", result.stdout)
        self.assertIn("Stagnant:", result.stdout)

    def test_cli_stagnation_exit_code(self):
        """CLI should return 1 when stagnant."""
        # Create history that will cause stagnation
        test_hash = calculate_state_hash("IMPL", {}, [])
        history = json.dumps([test_hash, test_hash])
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--history", history,
                "--threshold", "3"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)

    def test_cli_with_files_changed(self):
        """CLI should handle files-changed parameter."""
        files = json.dumps(["src/auth.ts", "src/login.ts"])
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--files-changed", files
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_cli_invalid_json_error(self):
        """Invalid JSON should cause error."""
        result = subprocess.run(
            [
                sys.executable, str(self.script_path),
                "--phase", "IMPL",
                "--indicators", "not-valid"
            ],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
