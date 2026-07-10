#!/usr/bin/env python3
"""Tests for ops/stop_completion.py — the forced-continuation gate (TASK-62).

Layers (TASK-45 pattern):
  - Op-level contract: dual condition (indicators unmet AND no nav-signal v3
    exit), the layered breaker (stop_fuse single-shot, held_count cap,
    stop_hook_active, non-mutating turns per mem-037), both kill switches
    seeded OFF, unconditional Pilot disable, mem-034 strip-before-scan.
  - Vendored-constants sync against skills/nav-loop/functions/exit_gate.py.
  - Subprocess composition via hooks/nav_dispatch.py: fuse consumed exactly
    once (second Stop silent + barrel re-arms), non-mutating turn never
    continues, Pilot/stop_hook_active silent, CLAUDE_PLUGIN_ROOT set AND
    unset (mem-036).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/

import stop_completion  # noqa: E402
from nav_hook_lib import config as nav_config  # noqa: E402
from nav_hook_lib import sentinels, signals  # noqa: E402

HOOKS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = HOOKS_DIR.parent
DISPATCH = str(HOOKS_DIR / "nav_dispatch.py")
EXIT_GATE_PATH = REPO_ROOT / "skills" / "nav-loop" / "functions" / "exit_gate.py"

ENV_VARS = ("PILOT_EXECUTOR", "CLAUDE_USER_MESSAGE", "CLAUDE_PROJECT_DIR",
            "CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR")

EXIT_LINE = signals.emit("exit", success=True, reason="all done")


def enabled_cfg(**overrides):
    cfg = copy.deepcopy(nav_config.DEFAULTS)
    cfg["stop_completion"]["enabled"] = True
    cfg["stop_completion"]["continue_enabled"] = True
    for key, value in overrides.items():
        cfg["stop_completion"][key] = value
    return cfg


def transcript_entries(closing_text, tools=("Edit",), user_prompt="implement it"):
    """A realistic turn: user prompt, tool_use assistant step(s), tool_result
    plumbing, then a text-only closing assistant message (the common shape —
    the tool_use never sits in the FINAL assistant message)."""
    entries = [{"message": {"role": "user", "content": user_prompt}}]
    for tool in tools:
        entries.append({"message": {"role": "assistant", "content": [
            {"type": "text", "text": f"using {tool}"},
            {"type": "tool_use", "name": tool},
        ]}})
        entries.append({"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "ok"},
        ]}})
    entries.append({"message": {"role": "assistant", "content": [
        {"type": "text", "text": closing_text},
    ]}})
    return entries


def write_transcript(base: Path, entries) -> Path:
    path = base / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n",
                    encoding="utf-8")
    return path


class StopCompletionTestBase(unittest.TestCase):
    def setUp(self):
        self._saved = {key: os.environ.pop(key, None) for key in ENV_VARS}
        self.addCleanup(self._restore)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(os.path.realpath(self._tmp.name))

    def _restore(self):
        for key, value in self._saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)

    def make_ctx(self, entries=None, cfg=None, state=None, pilot=False,
                 stop_hook_active=False, payload_extra=None):
        payload = {"stop_hook_active": stop_hook_active}
        if entries is not None:
            payload["transcript_path"] = str(write_transcript(self.tmp, entries))
        if payload_extra:
            payload.update(payload_extra)
        return types.SimpleNamespace(
            event="Stop",
            payload=payload,
            config=cfg if cfg is not None else enabled_cfg(),
            state=state if state is not None else {},
            pilot_executor=pilot,
            now=100.0,
        )


class DualConditionTest(StopCompletionTestBase):
    def test_unfinished_mutating_turn_blocks(self):
        ctx = self.make_ctx(transcript_entries("edited the file; more to do"))
        result = stop_completion.run(ctx)
        self.assertEqual(result["decision"], "block")
        self.assertNotIn("continue_", result)   # mem-051: continue is a no-op
        self.assertNotIn("exit_code", result)
        reason = result["reason"]
        self.assertIn("0/6", reason)
        for name in stop_completion.INDICATOR_VOCABULARY:
            self.assertIn(name, reason)
        self.assertIn('"exit"', reason)  # tells the model how to yield
        completion = ctx.state["completion"]
        self.assertIs(completion["stop_fuse"], True)
        self.assertEqual(completion["held_count"], 1)
        self.assertIs(completion["signal"]["exit_seen"], False)

    def test_exit_signal_yields(self):
        ctx = self.make_ctx(transcript_entries("done\n" + EXIT_LINE))
        self.assertIsNone(stop_completion.run(ctx))

    def test_pilot_signal_v2_exit_yields(self):
        closing = "done\n```pilot-signal\n{\"type\": \"exit\", \"success\": true}\n```"
        ctx = self.make_ctx(transcript_entries(closing))
        self.assertIsNone(stop_completion.run(ctx))

    def test_inline_last_assistant_message_wins_for_signal_scan(self):
        ctx = self.make_ctx(transcript_entries("no signal in transcript"),
                            payload_extra={"last_assistant_message":
                                           "finishing\n" + EXIT_LINE})
        self.assertIsNone(stop_completion.run(ctx))

    def test_indicators_met_yields(self):
        state = {"completion": {"indicators": {
            "code_committed": True, "tests_passing": True}}}
        ctx = self.make_ctx(transcript_entries("committed"), state=state)
        self.assertIsNone(stop_completion.run(ctx))

    def test_one_indicator_is_not_enough(self):
        state = {"completion": {"indicators": {"code_committed": True}}}
        ctx = self.make_ctx(transcript_entries("committed"), state=state)
        result = stop_completion.run(ctx)
        self.assertEqual(result["decision"], "block")
        self.assertIn("1/6", result["reason"])
        self.assertNotIn("code_committed", result["reason"].split("unmet: ")[1])

    def test_non_vocabulary_indicators_are_ignored(self):
        state = {"completion": {"indicators": {"vibes": True, "swagger": True}}}
        ctx = self.make_ctx(transcript_entries("done?"), state=state)
        result = stop_completion.run(ctx)
        self.assertEqual(result["decision"], "block")
        self.assertIn("0/6", result["reason"])

    def test_exit_signal_inside_echoed_sentinel_block_is_ignored(self):
        # mem-034: signals are scanned on strip_all()'d text — an exit line
        # riding inside an echoed block notice must not count as completion.
        closing = sentinels.wrap("nav-workflow-block", EXIT_LINE) + "\nstill going"
        ctx = self.make_ctx(transcript_entries(closing))
        result = stop_completion.run(ctx)
        self.assertEqual(result["decision"], "block")

    def test_reason_never_echoes_transcript_text(self):
        marker = "SECRET-TRANSCRIPT-7f3a"
        ctx = self.make_ctx(transcript_entries(f"work on {marker} continues"))
        result = stop_completion.run(ctx)
        self.assertEqual(result["decision"], "block")
        self.assertNotIn(marker, result["reason"])


class BreakerTest(StopCompletionTestBase):
    def test_consumed_fuse_short_circuits(self):
        state = {"completion": {"stop_fuse": True}}
        ctx = self.make_ctx(transcript_entries("unfinished"), state=state)
        self.assertIsNone(stop_completion.run(ctx))
        self.assertEqual(ctx.state["completion"], {"stop_fuse": True})

    def test_held_count_cap_default_two(self):
        state = {"completion": {"held_count": 2}}
        ctx = self.make_ctx(transcript_entries("unfinished"), state=state)
        self.assertIsNone(stop_completion.run(ctx))

    def test_held_count_below_cap_blocks_and_increments(self):
        state = {"completion": {"held_count": 1}}
        cfg = enabled_cfg(max_continues=3)
        ctx = self.make_ctx(transcript_entries("unfinished"), cfg=cfg, state=state)
        result = stop_completion.run(ctx)
        self.assertEqual(result["decision"], "block")
        self.assertEqual(ctx.state["completion"]["held_count"], 2)

    def test_stop_hook_active_short_circuits(self):
        ctx = self.make_ctx(transcript_entries("unfinished"),
                            stop_hook_active=True)
        self.assertIsNone(stop_completion.run(ctx))

    def test_non_mutating_turn_never_continues(self):
        # mem-037: conversational/research turns must never be forced on.
        entries = [
            {"message": {"role": "user", "content": "what does this do?"}},
            {"message": {"role": "assistant", "content": [
                {"type": "text", "text": "it parses the config"},
            ]}},
        ]
        ctx = self.make_ctx(entries)
        self.assertIsNone(stop_completion.run(ctx))

    def test_readonly_tool_turn_never_continues(self):
        entries = transcript_entries("looked around", tools=("Read",))
        # Read is not in TASK_ACTION_TOOLS — not a mutating turn.
        ctx = self.make_ctx(entries)
        self.assertIsNone(stop_completion.run(ctx))

    def test_inline_only_payload_never_continues(self):
        # The inline field carries no tool information: safe direction.
        ctx = self.make_ctx(payload_extra={
            "last_assistant_message": "edited things, more to do"})
        self.assertIsNone(stop_completion.run(ctx))

    def test_prior_turn_tools_do_not_leak_across_user_prompt_boundary(self):
        entries = transcript_entries("edited", tools=("Edit",))
        entries += [
            {"message": {"role": "user", "content": "thanks, one question"}},
            {"message": {"role": "assistant", "content": [
                {"type": "text", "text": "answering the question only"},
            ]}},
        ]
        ctx = self.make_ctx(entries)
        self.assertIsNone(stop_completion.run(ctx))


class KillSwitchTest(StopCompletionTestBase):
    def test_missing_config_block_is_off(self):
        ctx = self.make_ctx(transcript_entries("unfinished"),
                            cfg=copy.deepcopy(nav_config.DEFAULTS))
        self.assertIsNone(stop_completion.run(ctx))

    def test_enabled_without_continue_enabled_is_off(self):
        cfg = enabled_cfg(continue_enabled=False)
        ctx = self.make_ctx(transcript_entries("unfinished"), cfg=cfg)
        self.assertIsNone(stop_completion.run(ctx))

    def test_continue_enabled_without_enabled_is_off(self):
        cfg = enabled_cfg(enabled=False)
        ctx = self.make_ctx(transcript_entries("unfinished"), cfg=cfg)
        self.assertIsNone(stop_completion.run(ctx))

    def test_pilot_executor_disables_unconditionally(self):
        ctx = self.make_ctx(transcript_entries("unfinished"), pilot=True)
        self.assertIsNone(stop_completion.run(ctx))
        self.assertEqual(ctx.state, {})  # no fuse burn, no counter


class ExitGateSyncTest(StopCompletionTestBase):
    """The vendored constants must track the skill source (no drift)."""

    def _load_skill(self):
        self.assertTrue(EXIT_GATE_PATH.is_file(), EXIT_GATE_PATH)
        spec = importlib.util.spec_from_file_location("exit_gate_src",
                                                      EXIT_GATE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_vendored_constants_match_exit_gate(self):
        gate = self._load_skill()
        self.assertEqual(stop_completion.MIN_HEURISTICS,
                         gate.MIN_HEURISTICS_DEFAULT)
        self.assertEqual(len(stop_completion.INDICATOR_VOCABULARY),
                         gate.TOTAL_INDICATORS)
        source = EXIT_GATE_PATH.read_text(encoding="utf-8")
        for name in stop_completion.INDICATOR_VOCABULARY:
            self.assertIn(name, source,
                          f"indicator {name} not documented in exit_gate.py")

    def test_loader_finds_exit_gate_in_this_checkout(self):
        gate = stop_completion._load_exit_gate()
        self.assertIsNotNone(gate)
        self.assertTrue(callable(gate.evaluate_exit))


class DispatchCompositionTest(StopCompletionTestBase):
    """Subprocess composition via nav_dispatch.py (TASK-45 template)."""

    STOP_ON = json.dumps(
        {"stop_completion": {"enabled": True, "continue_enabled": True}})

    def make_project(self, config_body=None):
        project = self.tmp / "project"
        agent = project / ".agent"
        agent.mkdir(parents=True, exist_ok=True)
        (agent / ".nav-config.json").write_text(
            config_body if config_body is not None else self.STOP_ON)
        return project

    def dispatch(self, project, payload, env_extra=None):
        env = os.environ.copy()
        for var in ENV_VARS:
            env.pop(var, None)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [sys.executable, DISPATCH, "Stop"],
            input=json.dumps(payload), capture_output=True, text=True,
            cwd=project, env=env, timeout=60,
        )

    def payload(self, project, tpath, stop_hook_active=False):
        return {"cwd": str(project), "session_id": "s1",
                "transcript_path": str(tpath),
                "stop_hook_active": stop_hook_active}

    def read_state(self, project):
        path = project / ".agent" / ".nav-runtime-state.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def doc(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def test_fuse_consumed_once_second_stop_silent(self):
        project = self.make_project()
        tpath = write_transcript(self.tmp,
                                 transcript_entries("edited; more to do"))
        payload = self.payload(project, tpath)

        first = self.doc(self.dispatch(project, payload))
        self.assertEqual(first.get("decision"), "block", first)
        state = self.read_state(project)
        self.assertIs(state["completion"]["stop_fuse"], True)
        self.assertEqual(state["completion"]["held_count"], 1)
        # The gate short-circuited the stop_state recorder: same turn, no stamp.
        self.assertNotIn("turn", state)

        second = self.doc(self.dispatch(project, payload))
        self.assertNotIn("decision", second)  # silent: fuse consumed
        state = self.read_state(project)
        # stop_state ran this time: barrel re-armed the breaker for the next
        # turn and stamped the (now ended) turn.
        self.assertIs(state["completion"]["stop_fuse"], False)
        self.assertEqual(state["completion"]["held_count"], 0)
        self.assertIn("turn", state)

    def test_non_mutating_turn_never_continues_composition(self):
        project = self.make_project()
        entries = [
            {"message": {"role": "user", "content": "quick question"}},
            {"message": {"role": "assistant", "content": [
                {"type": "text", "text": "here is the answer"},
            ]}},
        ]
        tpath = write_transcript(self.tmp, entries)
        doc = self.doc(self.dispatch(project, self.payload(project, tpath)))
        self.assertNotIn("decision", doc)

    def test_stop_hook_active_is_silent(self):
        project = self.make_project()
        tpath = write_transcript(self.tmp,
                                 transcript_entries("edited; more to do"))
        doc = self.doc(self.dispatch(
            project, self.payload(project, tpath, stop_hook_active=True)))
        self.assertNotIn("decision", doc)

    def test_pilot_executor_never_blocks(self):
        project = self.make_project()
        tpath = write_transcript(self.tmp,
                                 transcript_entries("edited; more to do"))
        result = self.dispatch(project, self.payload(project, tpath),
                               env_extra={"PILOT_EXECUTOR": "1"})
        doc = self.doc(result)
        self.assertNotIn("decision", doc)
        completion = self.read_state(project).get("completion") or {}
        self.assertNotEqual(completion.get("held_count"), 1)

    def test_seeded_off_pristine_config_is_silent(self):
        project = self.make_project(config_body="{}")
        tpath = write_transcript(self.tmp,
                                 transcript_entries("edited; more to do"))
        doc = self.doc(self.dispatch(project, self.payload(project, tpath)))
        self.assertNotIn("decision", doc)

    def test_block_behavior_identical_env_set_and_unset(self):
        # mem-036: CLAUDE_PLUGIN_ROOT set AND unset must both block.
        for env_extra in (None, {"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)}):
            with self.subTest(env=env_extra):
                project = self.make_project()
                tpath = write_transcript(
                    self.tmp, transcript_entries("edited; more to do"))
                doc = self.doc(self.dispatch(
                    project, self.payload(project, tpath), env_extra=env_extra))
                self.assertEqual(doc.get("decision"), "block", doc)
                # reset for the next subTest iteration
                (project / ".agent" / ".nav-runtime-state.json").unlink()


if __name__ == "__main__":
    unittest.main()
