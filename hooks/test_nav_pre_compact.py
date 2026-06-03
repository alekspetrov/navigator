#!/usr/bin/env python3
"""Unit tests for nav_pre_compact._compress_context heuristics.

Focus (wp5 / TASK-46): path detection must be path-SHAPED (a real path token,
not prose that merely mentions an extension), and sampling must cover both the
head and tail of a long transcript — not the tail alone.

stdlib unittest only (pytest is NOT installed). Run with:
  cd hooks && python3 -m unittest test_nav_pre_compact -v
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
PRE_COMPACT = HOOKS_DIR / "nav_pre_compact.py"

FILES_HEADER = "**Files/paths mentioned**:\n"
SECTION_DIVIDER = "\n\n---\n\n"


def _load_module():
    spec = importlib.util.spec_from_file_location("nav_pre_compact", PRE_COMPACT)
    assert spec and spec.loader, "could not load nav_pre_compact spec"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompressContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _files_listed(self, text: str) -> list[str]:
        """Return the lines of the Files/paths section (empty if absent)."""
        out = self.mod._compress_context(text)
        if FILES_HEADER not in out:
            return []
        section = out.split(FILES_HEADER, 1)[1].split(SECTION_DIVIDER, 1)[0]
        return [ln for ln in section.splitlines() if ln.strip()]

    def test_prose_extension_not_captured(self):
        # A bare ".py"/".md" preceded by whitespace is prose, not a path.
        files = self._files_listed("Let's see the .py docs and the .md guide.")
        self.assertEqual(files, [])

    def test_real_path_captured(self):
        files = self._files_listed("I edited hooks/token_monitor.py to fix it.")
        self.assertIn("hooks/token_monitor.py", files)

    def test_captured_token_is_clean(self):
        # Trailing ":140" / ":" must not glue onto the captured path token.
        files = self._files_listed("ran hooks/token_monitor.py:140 just now")
        self.assertIn("hooks/token_monitor.py", files)
        self.assertNotIn("hooks/token_monitor.py:140", files)

    def test_head_and_tail_both_sampled(self):
        # >200 lines: a path near the start AND one near the end must survive.
        head_path = "src/early_module.py"
        tail_path = "src/late_module.py"
        lines = [f"touched {head_path}"] + ["filler"] * 300 + [f"touched {tail_path}"]
        files = self._files_listed("\n".join(lines))
        self.assertIn(head_path, files)
        self.assertIn(tail_path, files)

    def test_empty_transcript(self):
        self.assertEqual(
            self.mod._compress_context(""), "_[transcript unavailable]_"
        )


if __name__ == "__main__":
    unittest.main()
