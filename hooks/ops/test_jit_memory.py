#!/usr/bin/env python3
"""Tests for ops/jit_memory.py — TASK-62 Phase 3 (S1-gated PostToolUse injector).

Covers: hooks/**.py path matching (top-level, nested, relative, outside-root),
the once-per-session jit.injected[] dedupe, the declarative-content constraint
(mem-050: no imperatives at the tool-result position), and the dispatch-level
contract (default-off config, enabled config injects, env set AND unset per
mem-036 discipline).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/ (nav_hook_lib)

import jit_memory
from nav_hook_lib import config

HOOKS_DIR = Path(__file__).resolve().parent.parent
DISPATCH = str(HOOKS_DIR / "nav_dispatch.py")
SESSION_ID = "sess-jit-memory-tests"
NOW = 1_700_000_000.0


class JitMemoryBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name)) / "project"
        (self.root / ".agent").mkdir(parents=True)
        (self.root / "hooks" / "ops").mkdir(parents=True)

    def payload(self, file_path, tool_name="Edit"):
        return {
            "cwd": str(self.root),
            "session_id": SESSION_ID,
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
            "tool_response": {},
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

    def touch(self, rel):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# x\n", encoding="utf-8")
        return path


class PathMatchTest(JitMemoryBase):
    def test_top_level_hook_file_injects(self):
        path = self.touch("hooks/nav_dispatch.py")
        result = jit_memory.run(self.ctx(self.payload(str(path))))
        self.assertEqual(result["additional_context"], jit_memory.PITFALL_CONTEXT)

    def test_nested_op_file_injects(self):
        path = self.touch("hooks/ops/whatever.py")
        result = jit_memory.run(self.ctx(self.payload(str(path))))
        self.assertIsNotNone(result)

    def test_relative_path_resolves_against_root(self):
        self.touch("hooks/nav_hook_lib/state.py")
        payload = self.payload("hooks/nav_hook_lib/state.py")
        self.assertIsNotNone(jit_memory.run(self.ctx(payload)))

    def test_non_hook_python_file_is_silent(self):
        path = self.touch("src/app.py")
        self.assertIsNone(jit_memory.run(self.ctx(self.payload(str(path)))))

    def test_non_python_file_under_hooks_is_silent(self):
        path = self.touch("hooks/README.md")
        self.assertIsNone(jit_memory.run(self.ctx(self.payload(str(path)))))

    def test_path_outside_project_root_is_silent(self):
        outside = Path(self._tmp.name) / "elsewhere" / "hooks" / "x.py"
        outside.parent.mkdir(parents=True)
        outside.write_text("# x\n", encoding="utf-8")
        self.assertIsNone(jit_memory.run(self.ctx(self.payload(str(outside)))))

    def test_missing_file_path_key_is_silent(self):
        payload = self.payload("ignored")
        payload["tool_input"] = {}
        self.assertIsNone(jit_memory.run(self.ctx(payload)))

    def test_notebook_path_key_is_considered(self):
        # NotebookEdit payloads carry notebook_path; an .ipynb never matches
        # (*.py only) but the key must not crash the op.
        payload = self.payload("ignored", tool_name="NotebookEdit")
        payload["tool_input"] = {"notebook_path": str(self.root / "hooks" / "n.ipynb")}
        self.assertIsNone(jit_memory.run(self.ctx(payload)))


class DedupeTest(JitMemoryBase):
    def test_second_edit_same_session_injects_nothing(self):
        path = self.touch("hooks/ops/one.py")
        state = {}
        first = jit_memory.run(self.ctx(self.payload(str(path)), state=state))
        self.assertIsNotNone(first)
        self.assertEqual(state["jit"]["injected"], ["mem-034", "mem-035"])
        second = jit_memory.run(self.ctx(self.payload(str(path)), state=state))
        self.assertIsNone(second)
        # dedupe list is not double-appended either
        self.assertEqual(state["jit"]["injected"], ["mem-034", "mem-035"])

    def test_partial_injected_list_completes_and_injects(self):
        path = self.touch("hooks/ops/one.py")
        state = {"jit": {"injected": ["mem-034"]}}
        result = jit_memory.run(self.ctx(self.payload(str(path)), state=state))
        self.assertIsNotNone(result)
        self.assertEqual(state["jit"]["injected"], ["mem-034", "mem-035"])

    def test_corrupt_injected_value_is_replaced(self):
        path = self.touch("hooks/ops/one.py")
        state = {"jit": {"injected": "not-a-list"}}
        result = jit_memory.run(self.ctx(self.payload(str(path)), state=state))
        self.assertIsNotNone(result)
        self.assertEqual(state["jit"]["injected"], ["mem-034", "mem-035"])


class DeclarativeContentTest(unittest.TestCase):
    """mem-050: tool-adjacent context must be declarative — facts, no orders."""

    IMPERATIVE_MARKERS = (
        "you must", "you should", "do not", "don't", "never ", "always ",
        "make sure", "remember to", "be sure",
    )

    def test_context_names_both_memories(self):
        self.assertIn("mem-034", jit_memory.PITFALL_CONTEXT)
        self.assertIn("mem-035", jit_memory.PITFALL_CONTEXT)

    def test_context_contains_no_imperative_phrasing(self):
        lowered = jit_memory.PITFALL_CONTEXT.lower()
        for marker in self.IMPERATIVE_MARKERS:
            self.assertNotIn(marker, lowered, f"imperative phrasing: {marker!r}")

    def test_context_does_not_echo_loop_trigger_phrases(self):
        # mem-034 class: the injected text itself must not carry trigger bait.
        for phrase in ("run until done", "keep going", "do all"):
            self.assertNotIn(phrase, jit_memory.PITFALL_CONTEXT.lower())


class DispatchContractTest(JitMemoryBase):
    """TASK-45 subprocess pattern: the live dispatcher path, env set AND unset."""

    def dispatch(self, payload, env_extra=None, drop=()):
        env = os.environ.copy()
        for key in ("PILOT_EXECUTOR", "CLAUDE_PROJECT_DIR", "CLAUDE_USER_MESSAGE"):
            env.pop(key, None)
        for key in drop:
            env.pop(key, None)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [sys.executable, DISPATCH, "PostToolUse"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(self.root),
            env=env,
            timeout=30,
        )

    def enable(self):
        (self.root / ".agent" / ".nav-config.json").write_text(
            json.dumps({"jit_memory": {"enabled": True}}), encoding="utf-8")

    def test_default_config_keeps_op_off(self):
        # config.DEFAULTS seeds jit_memory.enabled False — pristine projects
        # (no v7 blocks) must not inject.
        path = self.touch("hooks/nav_dispatch.py")
        proc = self.dispatch(self.payload(str(path)))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("mem-034", proc.stdout)

    def _assert_injects_once(self, env_extra=None, drop=()):
        self.enable()
        path = self.touch("hooks/nav_dispatch.py")
        proc = self.dispatch(self.payload(str(path)), env_extra=env_extra, drop=drop)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        context = doc["hookSpecificOutput"]["additionalContext"]
        self.assertIn("mem-034", context)
        self.assertIn("mem-035", context)
        # Second dispatch in the same session: dedupe holds across processes.
        proc2 = self.dispatch(self.payload(str(path)), env_extra=env_extra, drop=drop)
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertNotIn("mem-034", proc2.stdout)

    def test_enabled_injects_once_env_set(self):
        # mem-036 variant: CLAUDE_PLUGIN_ROOT set to the checkout.
        self._assert_injects_once(env_extra={"CLAUDE_PLUGIN_ROOT": str(HOOKS_DIR.parent)})

    def test_enabled_injects_once_env_unset(self):
        # mem-036 variant: CLAUDE_PLUGIN_ROOT absent entirely.
        self._assert_injects_once(drop=("CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR"))


if __name__ == "__main__":
    unittest.main()
