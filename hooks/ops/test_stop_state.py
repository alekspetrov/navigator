#!/usr/bin/env python3
"""Tests for ops/stop_state.py — tristate stamping + the turn-lifecycle reset barrel.

Parity anchors: hooks/nav_workflow_state.py (v6 source) and the recorded
golden (tests/golden/goldens/stop_state.json — asserted by test_parity.py).
Here we pin the op-level contract: the mem-037 tristate rules, the
stop_hook_active early-ack, mem-034 strip-before-scan, and ONE test per
reset-barrel slot (reads.turn_count, completion.tier1_fuse,
completion.held_count).
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/

import stop_state  # noqa: E402
from nav_hook_lib import config as nav_config  # noqa: E402
from nav_hook_lib import sentinels  # noqa: E402


def make_ctx(payload=None, cfg=None, state=None, pilot=False):
    return types.SimpleNamespace(
        event="Stop",
        payload=payload or {},
        config=cfg or copy.deepcopy(nav_config.DEFAULTS),
        state=state if state is not None else {},
        pilot_executor=pilot,
        now=0.0,
    )


def write_transcript(base: Path, blocks) -> Path:
    """One assistant JSONL entry whose content is ``blocks``."""
    path = base / "transcript.jsonl"
    entry = {"message": {"role": "assistant", "content": blocks}}
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return path


class TristateStampingTest(unittest.TestCase):
    """mem-037: True only with the CHECK block; False only on mutating-tool
    turns without it; None otherwise. Never coerced."""

    def _signals(self, ctx):
        return ctx.state["turn"]["signals"]

    def test_true_when_workflow_check_present(self):
        ctx = make_ctx({"last_assistant_message": "│ WORKFLOW CHECK │ Mode: DIRECT"})
        result = stop_state.run(ctx)
        self.assertIs(self._signals(ctx)["check_shown"], True)
        self.assertEqual(result, {"ack": True})

    def test_false_only_when_mutating_tool_used_without_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tpath = write_transcript(Path(tmp), [
                {"type": "text", "text": "editing the file now"},
                {"type": "tool_use", "name": "Edit"},
            ])
            ctx = make_ctx({"transcript_path": str(tpath)})
            stop_state.run(ctx)
        signals = self._signals(ctx)
        self.assertIs(signals["check_shown"], False)
        self.assertEqual(ctx.state["turn"]["tools_used"], ["Edit"])

    def test_none_for_conversational_turn(self):
        ctx = make_ctx({"last_assistant_message": "DONE"})
        stop_state.run(ctx)
        self.assertIsNone(self._signals(ctx)["check_shown"])

    def test_none_for_readonly_tool_turn(self):
        # Read is not a TASK_ACTION_TOOL: a research-only turn must not
        # stamp False (mem-037 deadlock class).
        with tempfile.TemporaryDirectory() as tmp:
            tpath = write_transcript(Path(tmp), [
                {"type": "text", "text": "looking around"},
                {"type": "tool_use", "name": "Read"},
            ])
            ctx = make_ctx({"transcript_path": str(tpath)})
            stop_state.run(ctx)
        self.assertIsNone(self._signals(ctx)["check_shown"])

    def test_inline_message_preferred_over_transcript(self):
        # v6 order: inline last_assistant_message wins (text only, no tools).
        with tempfile.TemporaryDirectory() as tmp:
            tpath = write_transcript(Path(tmp), [
                {"type": "tool_use", "name": "Edit"},
            ])
            ctx = make_ctx({
                "last_assistant_message": "WORKFLOW CHECK shown",
                "transcript_path": str(tpath),
            })
            stop_state.run(ctx)
        self.assertIs(self._signals(ctx)["check_shown"], True)

    def test_echoed_block_notice_cannot_fake_true(self):
        # mem-034: the block notice body mentions "workflow check"; unstripped
        # scanning would stamp True. strip_all() must run first.
        echoed = sentinels.wrap(
            "nav-workflow-block",
            "the prior assistant turn skipped its required workflow check block",
        )
        ctx = make_ctx({"last_assistant_message": echoed})
        stop_state.run(ctx)
        self.assertIsNone(self._signals(ctx)["check_shown"])

    def test_nav_status_and_loop_phase_recorded(self):
        ctx = make_ctx({
            "last_assistant_message": "NAVIGATOR_STATUS\nPhase: VERIFY\nWORKFLOW CHECK",
        })
        stop_state.run(ctx)
        signals = self._signals(ctx)
        self.assertTrue(signals["nav_status_shown"])
        self.assertEqual(signals["loop_phase"], "VERIFY")


class StopHookActiveTest(unittest.TestCase):
    def test_acks_without_touching_state(self):
        ctx = make_ctx({"stop_hook_active": True,
                        "last_assistant_message": "WORKFLOW CHECK"})
        result = stop_state.run(ctx)
        self.assertEqual(result, {"ack": True})
        self.assertEqual(ctx.state, {})  # no stamp, no resets (v6 early exit)


class ResetBarrelTest(unittest.TestCase):
    """Stop is the ONLY writer that resets turn-lifecycle slots — one test
    per slot (TASK-61 acceptance criteria)."""

    def test_read_counter_slot_reset(self):
        ctx = make_ctx({"last_assistant_message": "DONE"},
                       state={"reads": {"turn_count": 5}})
        stop_state.run(ctx)
        self.assertEqual(ctx.state["reads"], {"turn_count": 0})

    def test_tier1_fuse_slot_reset(self):
        ctx = make_ctx({"last_assistant_message": "DONE"},
                       state={"completion": {"tier1_fuse": True}})
        stop_state.run(ctx)
        self.assertIs(ctx.state["completion"]["tier1_fuse"], False)

    def test_continue_counter_slot_reset(self):
        ctx = make_ctx({"last_assistant_message": "DONE"},
                       state={"completion": {"held_count": 2}})
        stop_state.run(ctx)
        self.assertEqual(ctx.state["completion"]["held_count"], 0)

    def test_other_completion_keys_survive_reset(self):
        ctx = make_ctx({"last_assistant_message": "DONE"},
                       state={"completion": {"held_count": 2, "keep": "me"}})
        stop_state.run(ctx)
        self.assertEqual(ctx.state["completion"]["keep"], "me")

    def test_reads_reset_skipped_when_read_guard_disabled(self):
        # v6 _reset_read_counter guard: only an EXPLICIT false skips.
        cfg = copy.deepcopy(nav_config.DEFAULTS)
        cfg["read_guard_hook"]["enabled"] = False
        ctx = make_ctx({"last_assistant_message": "DONE"}, cfg=cfg,
                       state={"reads": {"turn_count": 4}})
        stop_state.run(ctx)
        self.assertEqual(ctx.state["reads"], {"turn_count": 4})


if __name__ == "__main__":
    unittest.main()
