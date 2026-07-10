#!/usr/bin/env python3
"""Tests for ops/read_guard.py — TASK-61 Phase 4 parity port of nav_read_guard.py.

Covers the v6 threshold ladder (silent < warn < escalate advisory < strict
block with exit 2 + sentinel stderr), allowlist and out-of-tree exemptions,
config overrides, the deny-only channel (no stdout keys, no
permission_decision — mem-035/mem-054), the in-op 300s staleness window over
the schema-2 `reads` state section (missing/invalid timestamps are NOT
stale — the Stop reset barrel writes `{"turn_count": 0}` without one), and
mem-034 hygiene (block stderr never carries the triggering file path).
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

import read_guard
from nav_hook_lib import config, sentinels

SESSION_ID = "sess-read-guard-tests"
NOW = 1_700_000_000.0

BLOCK_OPEN = sentinels.TAGS["nav-read-guard-block"]["open"]
BLOCK_CLOSE = sentinels.TAGS["nav-read-guard-block"]["close"]


class ReadGuardTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve() / "project"
        (self.root / ".agent" / "tasks").mkdir(parents=True)
        self._saved_env = {
            key: os.environ.pop(key, None) for key in ("CLAUDE_PROJECT_DIR",)
        }
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        for key, value in self._saved_env.items():
            if value is not None:
                os.environ[key] = value

    # -- helpers ----------------------------------------------------------

    def write_config(self, hook_cfg):
        path = self.root / ".agent" / ".nav-config.json"
        path.write_text(json.dumps({"read_guard_hook": hook_cfg}), encoding="utf-8")

    def payload(self, file_path, tool_name="Read"):
        return {
            "cwd": str(self.root),
            "session_id": SESSION_ID,
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
        }

    def ctx(self, payload, state=None, now=NOW):
        return types.SimpleNamespace(
            event="PreToolUse",
            payload=payload,
            config=config.load(self.root),
            state=state if state is not None else {},
            pilot_executor=False,
            now=now,
        )

    def agent_file(self, rel="tasks/TASK-01-sample.md"):
        return str(self.root / ".agent" / rel)

    def run_read(self, state, rel="tasks/TASK-01-sample.md", now=NOW):
        ctx = self.ctx(self.payload(self.agent_file(rel)), state=state, now=now)
        return read_guard.run(ctx), ctx


class CountingTest(ReadGuardTestBase):
    def test_first_counted_read_is_silent_and_recorded(self):
        result, ctx = self.run_read(state={})
        self.assertIsNone(result)
        self.assertEqual(ctx.state["reads"]["turn_count"], 1)
        self.assertEqual(ctx.state["reads"]["updated_at"], NOW)

    def test_counter_continues_across_invocations(self):
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 1, "updated_at": NOW - 10}})
        self.assertIsNone(result)
        self.assertEqual(ctx.state["reads"]["turn_count"], 2)

    def test_allowlisted_file_is_not_counted(self):
        result, ctx = self.run_read(state={}, rel="DEVELOPMENT-README.md")
        self.assertIsNone(result)
        self.assertNotIn("reads", ctx.state)

    def test_nested_allowlist_entry_matches_full_relative_path(self):
        result, ctx = self.run_read(state={}, rel="knowledge/graph.json")
        self.assertIsNone(result)
        self.assertNotIn("reads", ctx.state)

    def test_file_outside_agent_dir_is_ignored(self):
        ctx = self.ctx(self.payload(str(self.root / "notes.md")), state={})
        self.assertIsNone(read_guard.run(ctx))
        self.assertNotIn("reads", ctx.state)

    def test_relative_agent_path_is_counted(self):
        ctx = self.ctx(self.payload(".agent/tasks/TASK-01-sample.md"), state={})
        self.assertIsNone(read_guard.run(ctx))
        self.assertEqual(ctx.state["reads"]["turn_count"], 1)

    def test_non_read_tool_is_ignored(self):
        ctx = self.ctx(self.payload(self.agent_file(), tool_name="Grep"), state={})
        self.assertIsNone(read_guard.run(ctx))
        self.assertNotIn("reads", ctx.state)

    def test_missing_file_path_is_ignored(self):
        payload = self.payload("")
        ctx = self.ctx(payload, state={})
        self.assertIsNone(read_guard.run(ctx))
        self.assertNotIn("reads", ctx.state)


class ThresholdLadderTest(ReadGuardTestBase):
    def test_warn_threshold_emits_advisory_without_exit_code(self):
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 2, "updated_at": NOW - 5}})
        self.assertNotIn("exit_code", result)
        self.assertIn("[nav-read-guard] 3 .agent/ files read this turn.",
                      result["stderr"])
        self.assertIn("lazy-loading", result["stderr"])
        self.assertEqual(ctx.state["reads"]["turn_count"], 3)

    def test_escalate_with_strict_block_exits_2_with_sentinel(self):
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 5}})
        self.assertEqual(result["exit_code"], 2)
        self.assertIn(BLOCK_OPEN, result["stderr"])
        self.assertIn(BLOCK_CLOSE, result["stderr"])
        self.assertIn("blocked at 5 .agent/ reads (escalate_threshold=5)",
                      result["stderr"])
        self.assertEqual(ctx.state["reads"]["turn_count"], 5)

    def test_block_stderr_never_carries_the_file_path(self):
        # mem-034: no payload-derived substrings in the block notice (v6 rule).
        result, _ = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 5}})
        self.assertNotIn(self.agent_file(), result["stderr"])
        self.assertNotIn("TASK-01-sample.md", result["stderr"])

    def test_escalate_without_strict_block_is_advisory_only(self):
        self.write_config({"strict_block": False})
        result, _ = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 5}})
        self.assertNotIn("exit_code", result)
        self.assertIn("Bulk-load anti-pattern threshold crossed", result["stderr"])

    def test_deny_only_channel_has_no_stdout_keys(self):
        # mem-035/mem-054: no advisory stdout / additionalContext / permission
        # output from this gate — exit 2 + stderr is the whole channel.
        result, _ = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 5}})
        self.assertEqual(set(result), {"exit_code", "stderr"})

    def test_config_overrides_thresholds(self):
        self.write_config({"warn_threshold": 1, "escalate_threshold": 2})
        result, _ = self.run_read(
            state={"reads": {"turn_count": 1, "updated_at": NOW - 5}})
        self.assertEqual(result["exit_code"], 2)
        self.assertIn("blocked at 2 .agent/ reads (escalate_threshold=2)",
                      result["stderr"])

    def test_config_allowlist_replaces_defaults(self):
        self.write_config({"allowlist": ["custom.md"]})
        result, ctx = self.run_read(state={}, rel="custom.md")
        self.assertIsNone(result)
        self.assertNotIn("reads", ctx.state)
        # Default entries are no longer exempt once overridden (v6 semantics).
        result, ctx = self.run_read(state={}, rel="DEVELOPMENT-README.md")
        self.assertEqual(ctx.state["reads"]["turn_count"], 1)


class StalenessTest(ReadGuardTestBase):
    """The 300s window lives INSIDE the op (v6 semantics); the `reads` section
    TTL (2h, nav_hook_lib.state) is only the coarser lib backstop."""

    def test_stale_counter_resets_before_increment(self):
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 301}})
        self.assertIsNone(result)  # fresh-from-zero: count is 1, no block
        self.assertEqual(ctx.state["reads"]["turn_count"], 1)
        self.assertEqual(ctx.state["reads"]["updated_at"], NOW)

    def test_counter_inside_window_is_kept(self):
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 299}})
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(ctx.state["reads"]["turn_count"], 5)

    def test_missing_timestamp_is_not_stale(self):
        # The Stop reset barrel writes {"turn_count": 0} with no updated_at;
        # v6 treated missing/unparseable timestamps as NOT stale.
        result, ctx = self.run_read(state={"reads": {"turn_count": 4}})
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(ctx.state["reads"]["turn_count"], 5)

    def test_invalid_timestamp_is_not_stale(self):
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": "yesterday"}})
        self.assertEqual(result["exit_code"], 2)

    def test_non_positive_window_disables_staleness(self):
        self.write_config({"stale_after_seconds": 0})
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 999_999}})
        self.assertEqual(result["exit_code"], 2)

    def test_custom_window_from_config(self):
        self.write_config({"stale_after_seconds": 60})
        result, ctx = self.run_read(
            state={"reads": {"turn_count": 4, "updated_at": NOW - 61}})
        self.assertIsNone(result)
        self.assertEqual(ctx.state["reads"]["turn_count"], 1)


if __name__ == "__main__":
    unittest.main()
