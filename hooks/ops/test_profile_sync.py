#!/usr/bin/env python3
"""Tests for ops/profile_sync.py — TASK-61 Phase 3 parity port of nav_profile_sync.py.

Covers the v6 branch table (grown corrections → subprocess sync + state
advance; no growth / missing graph / corrupt profile / non-profile edit →
silent ack), success-only counter advance (failed syncs retry), the `{}` ack
contract, and the v6 Edit|Write surface filter under the widened registry
matcher (MultiEdit / NotebookEdit notebook_path payloads skip silently).
Golden byte-parity itself is asserted by tests/golden/test_parity.py.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/ (nav_hook_lib)

import profile_sync
from nav_hook_lib import config

SESSION_ID = "sess-profile-sync-tests"
NOW = 1_700_000_000.0

# Stub syncer: records argv next to itself, exits with the templated code.
STUB_SYNCER = """\
import json, sys
from pathlib import Path
Path(__file__).with_name("calls.json").write_text(json.dumps(sys.argv[1:]))
sys.exit({rc})
"""


class ProfileSyncTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()

        self.root = base / "project"
        (self.root / ".agent" / "knowledge").mkdir(parents=True)
        self.graph_path = self.root / ".agent" / "knowledge" / "graph.json"
        self.graph_path.write_text("{}\n", encoding="utf-8")
        self.profile_path = self.root / ".agent" / ".user-profile.json"

        self.plugin_dir = base / "plugin"
        self.functions_dir = self.plugin_dir / "skills" / "nav-graph" / "functions"
        self.functions_dir.mkdir(parents=True)
        self.write_stub(rc=0)

        self._saved_env = {
            key: os.environ.pop(key, None)
            for key in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR", "CLAUDE_PROJECT_DIR")
        }
        os.environ["CLAUDE_PLUGIN_ROOT"] = str(self.plugin_dir)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        for key, value in self._saved_env.items():
            if value is not None:
                os.environ[key] = value

    # -- helpers ----------------------------------------------------------

    def write_stub(self, rc):
        syncer = self.functions_dir / "correction_to_memory.py"
        syncer.write_text(STUB_SYNCER.format(rc=rc), encoding="utf-8")

    def stub_calls(self):
        path = self.functions_dir / "calls.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_profile(self, corrections_count):
        corrections = [{"note": f"correction {i}"} for i in range(corrections_count)]
        self.profile_path.write_text(json.dumps({"corrections": corrections}),
                                     encoding="utf-8")

    def payload(self, tool_name="Edit", **tool_input):
        if not tool_input:
            tool_input = {"file_path": str(self.profile_path)}
        return {
            "cwd": str(self.root),
            "session_id": SESSION_ID,
            "tool_name": tool_name,
            "tool_input": tool_input,
        }

    def ctx(self, payload, state=None):
        return types.SimpleNamespace(
            event="PostToolUse",
            payload=payload,
            config=config.load(self.root),
            state=state if state is not None else {},
            pilot_executor=False,
            now=NOW,
        )


class CorrectionsSyncTest(ProfileSyncTestBase):
    def test_new_corrections_sync_and_advance_state(self):
        self.write_profile(2)
        ctx = self.ctx(self.payload())
        result = profile_sync.run(ctx)
        self.assertEqual(result["ack"], True)
        self.assertIn("nav_profile_sync: synced 2 new correction(s)", result["stderr"])
        self.assertEqual(ctx.state["profile"]["last_synced_count"], 2)
        calls = self.stub_calls()
        self.assertEqual(calls[:2], ["--action", "sync"])
        self.assertEqual(calls[calls.index("--profile-path") + 1],
                         str(self.profile_path))
        self.assertEqual(calls[calls.index("--graph-path") + 1], str(self.graph_path))
        self.assertEqual(calls[calls.index("--last-synced") + 1], "0")

    def test_delta_sync_passes_prior_last_synced(self):
        self.write_profile(5)
        ctx = self.ctx(self.payload(), state={"profile": {"last_synced_count": 3}})
        result = profile_sync.run(ctx)
        self.assertIn("nav_profile_sync: synced 2 new correction(s)", result["stderr"])
        self.assertEqual(ctx.state["profile"]["last_synced_count"], 5)
        calls = self.stub_calls()
        self.assertEqual(calls[calls.index("--last-synced") + 1], "3")

    def test_failed_sync_does_not_advance_counter(self):
        self.write_stub(rc=1)
        self.write_profile(2)
        ctx = self.ctx(self.payload())
        result = profile_sync.run(ctx)
        self.assertEqual(result["ack"], True)
        self.assertIn("nav_profile_sync: sync failed (rc=1)", result["stderr"])
        self.assertNotIn("profile", ctx.state)  # retries next time (v6 rule)


class SilentAckBranchesTest(ProfileSyncTestBase):
    """v6 printed `{}` on every Edit|Write branch — even when nothing synced."""

    def assert_ack_without_sync(self, ctx):
        result = profile_sync.run(ctx)
        self.assertEqual(result, {"ack": True})
        self.assertIsNone(self.stub_calls())

    def test_no_new_corrections_skips_subprocess(self):
        self.write_profile(2)
        ctx = self.ctx(self.payload(), state={"profile": {"last_synced_count": 2}})
        self.assert_ack_without_sync(ctx)
        self.assertEqual(ctx.state["profile"]["last_synced_count"], 2)

    def test_non_profile_edit_acks_only(self):
        notes = self.root / "notes.md"
        notes.write_text("# Notes\n", encoding="utf-8")
        self.assert_ack_without_sync(self.ctx(self.payload(file_path=str(notes))))

    def test_missing_graph_skips_sync(self):
        self.graph_path.unlink()
        self.write_profile(2)
        self.assert_ack_without_sync(self.ctx(self.payload()))

    def test_corrupt_profile_json_acks_only(self):
        self.profile_path.write_text("{not json", encoding="utf-8")
        self.assert_ack_without_sync(self.ctx(self.payload()))

    def test_missing_file_path_key_acks_only(self):
        payload = self.payload()
        payload["tool_input"] = {}
        self.assert_ack_without_sync(self.ctx(payload))


class WidenedMatcherSkipTest(ProfileSyncTestBase):
    """MultiEdit/NotebookEdit reach the op via the coarse registry matcher.

    v6's manifest fired on Edit|Write only, so the op emits NOTHING for the
    new tool names (no ack, no sync) — locked here per the TASK-61 brief.
    """

    def test_notebook_edit_payload_skips_silently(self):
        self.write_profile(2)
        payload = self.payload(tool_name="NotebookEdit")
        payload["tool_input"] = {"notebook_path": str(self.root / "nb.ipynb")}
        self.assertIsNone(profile_sync.run(self.ctx(payload)))
        self.assertIsNone(self.stub_calls())

    def test_multiedit_payload_skips_silently(self):
        self.write_profile(2)
        payload = self.payload(tool_name="MultiEdit",
                               file_path=str(self.profile_path))
        self.assertIsNone(profile_sync.run(self.ctx(payload)))
        self.assertIsNone(self.stub_calls())


if __name__ == "__main__":
    unittest.main()
