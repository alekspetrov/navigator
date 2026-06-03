#!/usr/bin/env python3
"""Subprocess tests for hooks/workflow_enforcer.py (UserPromptSubmit blocker).

stdlib unittest only (pytest not installed). Each test builds a throwaway
project dir with its own .agent/ and drives the hook via subprocess with a
JSON prompt on stdin. Assertions reflect behavior verified against the source:

  - PILOT_EXECUTOR env  -> exit 0 immediately.
  - Empty / non-loop prompt -> exit 0.
  - loop trigger + state.last_turn.check_shown == false + strict_block(default)
    -> exit 2, stderr contains <nav-workflow-block>.
  - same but strict_block == false -> exit 0.
  - sentinel-wrapped prior block text in prompt is stripped before matching
    (mem-034) -> exit 0.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = str(Path(__file__).resolve().parent / "workflow_enforcer.py")
SENTINEL_OPEN = "<nav-workflow-block>"
SENTINEL_CLOSE = "</nav-workflow-block>"


def run_hook(project_dir, prompt=None, raw_stdin=None, env_extra=None):
    """Invoke the hook in a subprocess rooted at project_dir.

    prompt: when given, sent as {"prompt": prompt} JSON on stdin.
    raw_stdin: when given, sent verbatim on stdin (overrides prompt).
    """
    if raw_stdin is None:
        raw_stdin = json.dumps({"prompt": prompt if prompt is not None else ""})
    env = os.environ.copy()
    # Ensure no inherited escape hatch / legacy message bleeds in.
    env.pop("PILOT_EXECUTOR", None)
    env.pop("CLAUDE_USER_MESSAGE", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["python3", HOOK],
        input=raw_stdin,
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
    )


def write_config(agent_dir, strict_block=None, enabled=None):
    cfg = {}
    enforcer = {}
    if enabled is not None:
        enforcer["enabled"] = enabled
    if strict_block is not None:
        enforcer["strict_block"] = strict_block
    if enforcer:
        cfg["workflow_enforcer_hook"] = enforcer
    (agent_dir / ".nav-config.json").write_text(json.dumps(cfg))


def write_state(agent_dir, check_shown):
    (agent_dir / ".nav-workflow-state.json").write_text(
        json.dumps({"last_turn": {"check_shown": check_shown}})
    )


class WorkflowEnforcerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # realpath so macOS /var -> /private/var resolution stays consistent
        self.project = os.path.realpath(self._tmp.name)
        self.agent = Path(self.project) / ".agent"
        self.agent.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    # (a) plain non-loop prompt -> exit 0, no block.
    def test_plain_prompt_exits_zero(self):
        result = run_hook(self.project, prompt="hello, what time is it?")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SENTINEL_OPEN, result.stderr)

    # (a-note) a complex/loop prompt with NO blocking state still prints the
    # WORKFLOW CHECK block to stdout (soft-warn path).
    def test_loop_prompt_soft_warn_prints_workflow_check(self):
        result = run_hook(self.project, prompt="run until done: refactor auth")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WORKFLOW CHECK", result.stdout)

    # (b) loop trigger, NO state file -> fail-open soft warn, exit 0.
    def test_loop_trigger_no_state_file_exits_zero(self):
        self.assertFalse((self.agent / ".nav-workflow-state.json").exists())
        result = run_hook(self.project, prompt="run until done: fix the bug")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SENTINEL_OPEN, result.stderr)

    # (c) loop trigger + check_shown=false + default strict_block -> exit 2 + sentinel.
    def test_loop_trigger_check_shown_false_blocks(self):
        write_state(self.agent, check_shown=False)
        # No config file at all -> strict_block defaults True.
        result = run_hook(self.project, prompt="run until done: ship everything")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(SENTINEL_OPEN, result.stderr)
        self.assertIn(SENTINEL_CLOSE, result.stderr)

    # (c-variant) explicit strict_block=true config also blocks.
    def test_explicit_strict_block_true_blocks(self):
        write_state(self.agent, check_shown=False)
        write_config(self.agent, strict_block=True)
        result = run_hook(self.project, prompt="keep going until complete")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(SENTINEL_OPEN, result.stderr)

    # (d) same trigger + state but strict_block=false -> exit 0.
    def test_strict_block_false_does_not_block(self):
        write_state(self.agent, check_shown=False)
        write_config(self.agent, strict_block=False)
        result = run_hook(self.project, prompt="run until done: ship everything")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SENTINEL_OPEN, result.stderr)

    # (d-variant) check_shown=true -> no block even with strict default.
    def test_check_shown_true_does_not_block(self):
        write_state(self.agent, check_shown=True)
        result = run_hook(self.project, prompt="run until done: ship everything")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SENTINEL_OPEN, result.stderr)

    # (e) PILOT_EXECUTOR=1 -> exit 0 immediately, regardless of prompt/state.
    def test_pilot_executor_bypasses(self):
        # Set up state that WOULD block, to prove the bypass wins.
        write_state(self.agent, check_shown=False)
        result = run_hook(
            self.project,
            prompt="run until done: ship everything",
            env_extra={"PILOT_EXECUTOR": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SENTINEL_OPEN, result.stderr)

    # (f) mem-034 regression: prompt already containing a sentinel-wrapped block
    # notice has that section stripped before trigger matching -> exit 0.
    def test_sentinel_wrapped_block_is_stripped(self):
        # Blocking state present; the ONLY loop-trigger substring lives inside
        # the sentinel-wrapped section, which must be excised before matching.
        write_state(self.agent, check_shown=False)
        echoed = (
            "Original prompt: please summarize the readme\n"
            + SENTINEL_OPEN + "\n"
            "Navigator workflow_enforcer: blocked.\n"
            "  ...your prompt requests autonomous iteration: run until done.\n"
            + SENTINEL_CLOSE + "\n"
        )
        result = run_hook(self.project, prompt=echoed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SENTINEL_OPEN, result.stderr)

    # (f-control) without stripping, the same trigger substring WOULD block.
    # Confirms the substring is genuinely a trigger so test_sentinel above is
    # meaningful.
    def test_unwrapped_trigger_still_blocks(self):
        write_state(self.agent, check_shown=False)
        result = run_hook(
            self.project,
            prompt="please summarize, then run until done on the rest",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(SENTINEL_OPEN, result.stderr)


if __name__ == "__main__":
    unittest.main()
