#!/usr/bin/env python3
"""Tests for nav_hook_lib/transcript.py (TASK-59, Phase 5).

stdlib unittest only. The load-bearing test is the parity suite: the v6
reader (``hooks/nav_workflow_state.py::_last_assistant_turn``) was run
against ``fixtures/transcript-sample.jsonl`` — a real transcript recorded
during the TASK-57 spike (synthetic scratch-project data, checked for
personal content) — and its derived values (assistant text, tool-name set)
must match ``transcript.last_assistant_turn`` byte for byte. TASK-61
Phase 7 deleted the v6 source: the expected values pinned below (incl. the
fixture text sha256) are the FROZEN v6 truth; the live differential leg
auto-skips when the v6 file is absent (same pattern as
tests/golden/test_parity.py leg 1). Parity is also asserted on synthetic
transcripts covering the tool_use, string-content, and garbage-line paths
the fixture does not hit.
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import transcript

FIXTURE = HERE / "fixtures" / "transcript-sample.jsonl"
V6_READER = HERE.parent / "nav_workflow_state.py"


def load_v6_module():
    """Import the untouched v6 hook directly from its file path."""
    spec = importlib.util.spec_from_file_location("nav_workflow_state_v6", V6_READER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# sha256 of the fixture's last assistant text as derived by the v6 reader —
# recorded before TASK-61 Phase 7 deleted hooks/nav_workflow_state.py.
FIXTURE_TEXT_SHA256 = (
    "1db93158f94bd8293fef4c3843c7ac4175d9b4c4f20e470e9fb0d5aed8864ed6"
)


class TranscriptParityTest(unittest.TestCase):
    """Byte-parity between the lib reader and the (frozen) v6 reader."""

    @classmethod
    def setUpClass(cls):
        cls.v6 = load_v6_module() if V6_READER.is_file() else None

    def assert_parity(self, path):
        lib_text, lib_tools = transcript.last_assistant_turn(path)
        if self.v6 is not None:  # live differential leg (pre-Phase-7 only)
            v6_text, v6_tools = self.v6._last_assistant_turn(
                {"transcript_path": str(path)})
            self.assertEqual(v6_text, lib_text)
            self.assertEqual(v6_tools, lib_tools)
        return lib_text, lib_tools

    def test_fixture_parity(self):
        """Real spike transcript: identical derived values, non-trivial."""
        self.assertTrue(FIXTURE.is_file(), f"missing fixture: {FIXTURE}")
        text, tools = self.assert_parity(FIXTURE)
        # The fixture ends on a text-only assistant turn; parity on empty
        # strings would prove nothing — require real extracted content.
        self.assertTrue(text.strip(), "fixture yielded empty assistant text")
        self.assertEqual(tools, set())
        # Frozen v6 truth: the lib must keep producing the exact bytes the
        # v6 reader produced (recorded before the v6 source was deleted).
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(),
                         FIXTURE_TEXT_SHA256)

    def test_parity_tool_use_only_turn(self):
        """Last assistant turn with tool_use blocks and no text."""
        lines = [
            {"type": "user", "message": {"role": "user", "content": "go"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Edit", "input": {}},
                {"type": "tool_use", "name": "Bash", "input": {}},
            ]}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
            text, tools = self.assert_parity(p)
        self.assertEqual(text, "")
        self.assertEqual(tools, {"Edit", "Bash"})

    def test_parity_string_content_and_garbage_lines(self):
        """String-content assistant message; blank/garbage lines skipped."""
        body = "\n".join([
            "not json at all {{{",
            "",
            json.dumps({"type": "assistant",
                        "message": {"role": "assistant", "content": "plain answer"}}),
            "   ",
            "]{ broken",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.jsonl"
            p.write_text(body + "\n")
            text, tools = self.assert_parity(p)
        self.assertEqual(text, "plain answer")
        self.assertEqual(tools, set())

    def test_parity_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            text, tools = self.assert_parity(Path(tmp) / "nope.jsonl")
        self.assertEqual((text, tools), ("", set()))


class TailEntriesTest(unittest.TestCase):
    def test_fixture_all_lines_parse_as_dicts(self):
        entries = transcript.tail_entries(FIXTURE)
        raw_lines = [ln for ln in FIXTURE.read_text().splitlines() if ln.strip()]
        self.assertEqual(len(entries), len(raw_lines))
        self.assertTrue(all(isinstance(e, dict) for e in entries))
        # File order is preserved: the recorded session starts with a
        # queue-operation entry and ends with a last-prompt entry.
        self.assertEqual(entries[0].get("type"), "queue-operation")
        self.assertEqual(entries[-1].get("type"), "last-prompt")

    def test_small_tail_drops_partial_first_line_only(self):
        """A tail slice cutting mid-record drops just that partial line."""
        full = transcript.tail_entries(FIXTURE)
        size = len(FIXTURE.read_text())
        clipped = transcript.tail_entries(FIXTURE, max_chars=size // 2)
        self.assertLess(len(clipped), len(full))
        self.assertGreater(len(clipped), 0)
        # Whatever survived must be a suffix of the full parse.
        self.assertEqual(clipped, full[len(full) - len(clipped):])

    def test_non_dict_json_lines_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.jsonl"
            p.write_text('[1, 2]\n"str"\n{"type": "assistant"}\n42\n')
            entries = transcript.tail_entries(p)
        self.assertEqual(entries, [{"type": "assistant"}])

    def test_missing_and_unreadable(self):
        self.assertEqual(transcript.tail_entries("/nonexistent/x.jsonl"), [])
        self.assertEqual(transcript.tail_text("/nonexistent/x.jsonl"), "")
        with tempfile.TemporaryDirectory() as tmp:
            # A directory is not a file -> silent empty, no exception.
            self.assertEqual(transcript.tail_entries(tmp), [])


if __name__ == "__main__":
    unittest.main()
