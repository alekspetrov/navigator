#!/usr/bin/env python3
"""Composition suite — the coupled stop_state + prompt_gate pair (TASK-61 Phase 5).

End-to-end through the real dispatcher (subprocess, fresh tmp project per
case — TASK-45 template, plumbing shared with test_parity via corpus.py):

  1. FULL tristate table (mem-037): every value stop_state stamps into
     turn.signals.check_shown (True / False / None), and what prompt_gate
     does with it on the next loop-trigger prompt (warn / BLOCK / warn).
  2. Turn-lifecycle reset barrel: read x5 -> Stop -> read x1 == counter 1,
     driven end-to-end — real PreToolUse(Read) dispatches increment via the
     ops/read_guard.py port; the dispatcher-run stop_state op resets.
  3. mem-034 echo probe (PERMANENT): a gate block's stderr never contains a
     loop-trigger phrase, and re-feeding the block message (plus the
     harness 'Original prompt:' echo) does NOT re-block.
  4. Same-payload composition: gate block short-circuits prompt_brief; a
     non-blocking pass lets both ops inject, gate text first.

Unlike test_parity, payloads here are synthetic by design — they drive the
interesting branches the goldens deliberately do not lock.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import DISPATCH, REPO_ROOT, build_env, build_project  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "hooks"))
from nav_hook_lib import scoring  # noqa: E402

SESSION = "compose-session-0001"
LOOP_PROMPT = "run until done: fix everything"
BLOCK_TAG_OPEN = "<nav-workflow-block>"

CHECK_BLOCK_TEXT = (
    "┌─────────────────────────────────────┐\n"
    "│ WORKFLOW CHECK                      │\n"
    "└─────────────────────────────────────┘"
)


class _ComposeCase(unittest.TestCase):
    """Fresh fixture project + isolated HOME; raw payloads (no rewrites)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.project = build_project(base)
        self.agent_dir = self.project / ".agent"
        home = base / "home"
        home.mkdir()
        self.env = build_env(home, str(REPO_ROOT))

    def dispatch(self, event, payload):
        return subprocess.run(
            [sys.executable, str(DISPATCH), event],
            input=json.dumps(payload), cwd=self.project, env=self.env,
            capture_output=True, text=True, timeout=30,
        )

    def stop_payload(self, **extra):
        payload = {
            "session_id": SESSION,
            "cwd": str(self.project),
            "hook_event_name": "Stop",
            "stop_hook_active": False,
        }
        payload.update(extra)
        return payload

    def prompt_payload(self, prompt):
        return {
            "session_id": SESSION,
            "cwd": str(self.project),
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
        }

    def read_state(self):
        path = self.agent_dir / ".nav-runtime-state.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def check_shown(self):
        return self.read_state()["turn"]["signals"]["check_shown"]

    def stamp_via_stop(self, tristate):
        """Drive a real Stop dispatch that stamps the requested tristate."""
        if tristate is True:
            payload = self.stop_payload(last_assistant_message=CHECK_BLOCK_TEXT)
        elif tristate is False:
            tpath = self.project / "tool-turn.jsonl"
            entry = {"message": {"role": "assistant", "content": [
                {"type": "text", "text": "editing without the check block"},
                {"type": "tool_use", "name": "Edit"},
            ]}}
            tpath.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            payload = self.stop_payload(transcript_path=str(tpath))
        else:
            payload = self.stop_payload(last_assistant_message="Sounds good.")
        proc = self.dispatch("Stop", payload)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "{}\n")  # v6 ack shape survives
        stamped = self.check_shown()
        if tristate is None:
            self.assertIsNone(stamped)
        else:
            self.assertIs(stamped, tristate)


class TristateTableTest(_ComposeCase):
    """The FULL mem-037 table: every stamped value, the gate's exact action."""

    def test_true_stamp_gate_warns_not_blocks(self):
        self.stamp_via_stop(True)
        proc = self.dispatch("UserPromptSubmit", self.prompt_payload(LOOP_PROMPT))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("LOOP MODE TRIGGER DETECTED", proc.stdout)
        self.assertNotIn(BLOCK_TAG_OPEN, proc.stderr)

    def test_false_stamp_gate_blocks(self):
        self.stamp_via_stop(False)
        proc = self.dispatch("UserPromptSubmit", self.prompt_payload(LOOP_PROMPT))
        self.assertEqual(proc.returncode, 2)
        self.assertIn(BLOCK_TAG_OPEN, proc.stderr)
        self.assertEqual(proc.stdout, "")  # warn suppressed when blocking

    def test_none_stamp_gate_warns_not_blocks(self):
        # Conversational turn -> None -> never block (the v6.15.3
        # AskUserQuestion deadlock fix; blocking here was the bug).
        self.stamp_via_stop(None)
        proc = self.dispatch("UserPromptSubmit", self.prompt_payload(LOOP_PROMPT))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("LOOP MODE TRIGGER DETECTED", proc.stdout)
        self.assertNotIn(BLOCK_TAG_OPEN, proc.stderr)


class ReadCounterResetTest(_ComposeCase):
    """read x5 -> Stop -> read x1 == 1 (the reset-barrel acceptance case),
    end-to-end: real read_guard increments, real stop_state reset."""

    def dispatch_read(self):
        """One real PreToolUse(Read) dispatch on a counted .agent/ file."""
        target = self.agent_dir / "tasks" / "TASK-01-sample.md"
        return self.dispatch("PreToolUse", {
            "session_id": SESSION,
            "cwd": str(self.project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": str(target)},
        })

    def turn_count(self):
        return self.read_state()["reads"]["turn_count"]

    def test_five_reads_stop_one_read_counts_one(self):
        for _ in range(5):
            self.dispatch_read()
        self.assertEqual(self.turn_count(), 5)

        proc = self.dispatch(
            "Stop", self.stop_payload(last_assistant_message="DONE"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.turn_count(), 0)  # Stop reset the counter

        one_more = self.dispatch_read()
        self.assertEqual(self.turn_count(), 1)  # no residue from before Stop
        self.assertEqual(one_more.returncode, 0)  # fresh turn: no guard trip
        self.assertEqual(one_more.stderr, "")


class EchoProbeTest(_ComposeCase):
    """mem-034 PERMANENT case — never delete, never weaken."""

    def test_block_stderr_has_no_trigger_and_echo_does_not_reblock(self):
        self.stamp_via_stop(False)

        blocked = self.dispatch("UserPromptSubmit",
                                self.prompt_payload(LOOP_PROMPT))
        self.assertEqual(blocked.returncode, 2)
        self.assertIn(BLOCK_TAG_OPEN, blocked.stderr)
        lowered = blocked.stderr.lower()
        for phrase in scoring.LOOP_TRIGGERS:
            self.assertNotIn(phrase, lowered,
                             f"trigger phrase {phrase!r} leaked into stderr")

        # Claude Code echoes blocked stderr + 'Original prompt: <trigger>'
        # into the next prompt. State still says check_shown=false (the
        # blocked turn never ran) — the echo alone must not re-block.
        echoed = blocked.stderr + "Original prompt: " + LOOP_PROMPT
        refed = self.dispatch("UserPromptSubmit", self.prompt_payload(echoed))
        self.assertEqual(refed.returncode, 0)
        self.assertEqual(refed.stdout, "")
        self.assertNotIn(BLOCK_TAG_OPEN, refed.stderr)


class SamePayloadCompositionTest(_ComposeCase):
    """Gate and brief on ONE payload: block short-circuits; pass composes."""

    PROMPT = "keep going and fix the bugs in the app"  # loop + ambiguous

    def test_gate_block_short_circuits_brief(self):
        self.stamp_via_stop(False)
        proc = self.dispatch("UserPromptSubmit", self.prompt_payload(self.PROMPT))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")  # no NAV-BRIEF: injector skipped

    def test_gate_pass_composes_with_brief_in_registry_order(self):
        self.stamp_via_stop(True)
        proc = self.dispatch("UserPromptSubmit", self.prompt_payload(self.PROMPT))
        self.assertEqual(proc.returncode, 0)
        self.assertIn("LOOP MODE TRIGGER DETECTED", proc.stdout)
        self.assertIn("NAV-BRIEF", proc.stdout)
        self.assertLess(proc.stdout.index("LOOP MODE TRIGGER DETECTED"),
                        proc.stdout.index("NAV-BRIEF"))


if __name__ == "__main__":
    unittest.main()
