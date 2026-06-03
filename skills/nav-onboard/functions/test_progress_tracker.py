#!/usr/bin/env python3
"""Tests for progress_tracker.py corrupt/partial-data resilience.

Covers the wp11/TASK-51 fix: reading a corrupt or partial
.progress-data.json must return an {"error": ...} dict (or None for
get_next_task) instead of raising JSONDecodeError/KeyError.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from progress_tracker import update_progress, get_progress, get_next_task


class TestProgressTrackerResilience(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.onboarding = Path(self.tmp) / ".agent" / "onboarding"
        self.onboarding.mkdir(parents=True)
        self.data_file = self.onboarding / ".progress-data.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, text: str):
        self.data_file.write_text(text)

    # --- corrupt (invalid JSON) ---------------------------------------

    def test_corrupt_get_progress_returns_error(self):
        self._write("{ this is not valid json")
        result = get_progress(self.tmp)
        self.assertIn("error", result)

    def test_corrupt_update_progress_returns_error(self):
        self._write("}{ broken")
        result = update_progress(self.tmp, "nav-start", "completed")
        self.assertIn("error", result)

    def test_corrupt_get_next_task_returns_none(self):
        self._write("not json at all")
        self.assertIsNone(get_next_task(self.tmp))

    # --- partial (valid JSON, missing required keys) ------------------

    def test_partial_data_does_not_crash(self):
        self._write(json.dumps({"flow_type": "quick_start"}))
        # All three must tolerate the missing 'progress'/'total' keys.
        prog = get_progress(self.tmp)
        self.assertIsInstance(prog, dict)
        self.assertEqual(prog.get("percentage"), 0)

        self.assertIsNone(get_next_task(self.tmp))

        upd = update_progress(self.tmp, "nav-start", "completed")
        self.assertIn("error", upd)  # unknown skill, not a KeyError crash


if __name__ == "__main__":
    unittest.main()
