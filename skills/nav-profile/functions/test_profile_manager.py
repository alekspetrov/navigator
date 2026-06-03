#!/usr/bin/env python3
"""Tests for profile_manager.py (stdlib unittest, direct-import style)."""

import sys
import json
import tempfile
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
import profile_manager
from profile_manager import (
    load_profile,
    save_profile,
    update_preference,
    add_correction,
    add_goal,
    create_default_profile,
)


class TestLoadProfile(unittest.TestCase):
    """Tests for load_profile resilience."""

    def test_missing_path_returns_empty_dict(self):
        """load_profile on a missing path returns {}."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist.json"
            self.assertEqual(load_profile(str(missing)), {})

    def test_corrupt_json_returns_empty_dict_no_raise(self):
        """load_profile on corrupt JSON returns {} and does NOT raise."""
        with tempfile.TemporaryDirectory() as tmp:
            corrupt = Path(tmp) / "corrupt.json"
            corrupt.write_text("{bad")

            # Must NOT raise.
            self.assertEqual(load_profile(str(corrupt)), {})

    def test_valid_file_returns_contents(self):
        """load_profile on a valid file returns its contents."""
        with tempfile.TemporaryDirectory() as tmp:
            valid = Path(tmp) / "profile.json"
            payload = {"version": "1.0", "preferences": {"communication": {"verbosity": "concise"}}}
            valid.write_text(json.dumps(payload))

            self.assertEqual(load_profile(str(valid)), payload)


class TestSaveLoadRoundTrip(unittest.TestCase):
    """Tests for save_profile -> load_profile round-trip."""

    def test_round_trip_preserves_profile(self):
        """save_profile then load_profile preserves the profile via a tempfile."""
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "nested" / "profile.json"
            profile = create_default_profile()

            self.assertTrue(save_profile(str(profile_path), profile))
            self.assertTrue(profile_path.exists())
            self.assertEqual(load_profile(str(profile_path)), profile)


class TestUpdatePreference(unittest.TestCase):
    """Tests for update_preference."""

    def test_update_existing_nested_key(self):
        """update_preference updates the right nested key and reports old/new."""
        profile = create_default_profile()

        result = update_preference(profile, "communication", "verbosity", "concise")

        self.assertEqual(
            profile["preferences"]["communication"]["verbosity"], "concise"
        )
        self.assertEqual(result["old_value"], "balanced")
        self.assertEqual(result["new_value"], "concise")

    def test_update_creates_missing_category(self):
        """update_preference creates preferences/category when absent."""
        profile = {}

        result = update_preference(profile, "custom", "flag", True)

        self.assertEqual(profile["preferences"]["custom"]["flag"], True)
        self.assertIsNone(result["old_value"])
        self.assertEqual(result["new_value"], True)
        # last_updated stamped.
        self.assertIn("last_updated", profile)


class TestAddCorrection(unittest.TestCase):
    """Tests for add_correction max-20 cap."""

    def test_add_correction_appends_and_stamps_date(self):
        """add_correction appends the correction and stamps a date."""
        profile = create_default_profile()

        add_correction(profile, {"pattern": "first"})

        self.assertEqual(len(profile["corrections"]), 1)
        self.assertEqual(profile["corrections"][0]["pattern"], "first")
        self.assertIn("date", profile["corrections"][0])

    def test_add_correction_caps_at_20_keeps_most_recent(self):
        """add_correction caps at 20, keeping the most recent entries."""
        profile = create_default_profile()

        for i in range(25):
            add_correction(profile, {"pattern": f"c{i}"})

        corrections = profile["corrections"]
        self.assertEqual(len(corrections), 20)
        # Oldest (c0..c4) dropped; most recent 20 kept (c5..c24).
        self.assertEqual(corrections[0]["pattern"], "c5")
        self.assertEqual(corrections[-1]["pattern"], "c24")


class TestAddGoal(unittest.TestCase):
    """Tests for add_goal upsert behavior."""

    def test_add_goal_appends_new(self):
        """add_goal appends a new goal with started/last_mentioned/status."""
        profile = create_default_profile()

        add_goal(profile, {"name": "ship-v1", "context": "release"})

        self.assertEqual(len(profile["goals"]), 1)
        goal = profile["goals"][0]
        self.assertEqual(goal["name"], "ship-v1")
        self.assertIn("started", goal)
        self.assertIn("last_mentioned", goal)
        self.assertEqual(goal["status"], "in-progress")

    def test_add_goal_upserts_existing_by_name(self):
        """add_goal with an existing name updates rather than duplicates."""
        profile = create_default_profile()
        add_goal(profile, {"name": "ship-v1", "context": "release"})

        # Same name again with a new status -> updates existing.
        add_goal(profile, {"name": "ship-v1", "status": "completed"})

        self.assertEqual(len(profile["goals"]), 1)
        self.assertEqual(profile["goals"][0]["status"], "completed")
        # Original context preserved (upsert only touches status/last_mentioned).
        self.assertEqual(profile["goals"][0]["context"], "release")


if __name__ == "__main__":
    unittest.main(verbosity=2)
