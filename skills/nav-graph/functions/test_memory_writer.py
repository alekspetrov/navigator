#!/usr/bin/env python3
"""Tests for memory_writer.py — TRIZ footer fields (TASK-72).

The three optional fields must be emitted only when set, in a fixed order
after **Concepts**, and their absence must leave the file byte-identical to
the pre-TRIZ format.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from memory_writer import create_memory_file

WRITER = Path(__file__).parent / "memory_writer.py"


def _write(tmp: str, **kw) -> str:
    base = dict(memory_id="mem-001", memory_type="decision", title="T",
                summary="S", concepts=["a", "b"], base_dir=tmp)
    base.update(kw)
    return Path(create_memory_file(**base)).read_text()


class TestFooterFields(unittest.TestCase):
    def test_fields_emitted_after_concepts_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = _write(tmp, contradiction="A vs B", separation="time",
                          principle="prior action")
        self.assertTrue(text.endswith(
            "**Concepts**: a, b\n"
            "**Contradiction**: A vs B\n"
            "**Separation**: time\n"
            "**Principle**: prior action\n"), text[-200:])

    def test_partial_fields_emit_only_those_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = _write(tmp, contradiction="A vs B")
        self.assertTrue(text.endswith("**Concepts**: a, b\n**Contradiction**: A vs B\n"))
        self.assertNotIn("**Separation**", text)
        self.assertNotIn("**Principle**", text)

    def test_omitted_fields_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            plain = _write(a)
            explicit_empty = _write(b, contradiction="", separation="", principle="")
        self.assertEqual(plain, explicit_empty)
        self.assertNotIn("**Contradiction**", plain)
        self.assertTrue(plain.endswith("**Concepts**: a, b\n"))

    def test_cli_flags_pass_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(WRITER), "--memory-id", "mem-009",
                 "--memory-type", "decision", "--title", "T", "--summary", "S",
                 "--concepts", "x", "--base-dir", tmp,
                 "--contradiction", "speed vs safety", "--separation", "condition",
                 "--principle", "dynamization"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = (Path(tmp) / "memories" / "decisions" / "mem-009.md").read_text()
        self.assertIn("**Contradiction**: speed vs safety\n", text)
        self.assertIn("**Separation**: condition\n", text)
        self.assertIn("**Principle**: dynamization\n", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
