#!/usr/bin/env python3
"""Tests for ops/subagent_context.py — TASK-62 Phase 4 (SubagentStart, S3 PASS).

Covers: the snapshot assembly (current-task line, marker resolution order,
top-K recall), the hard 2k budget (mem-052) plus the configured budget_chars
under-cut, all-sources-empty silence, and the dispatch-level contract for the
SubagentStart event (default-off config; enabled path ≤2000 chars; env set
AND unset per mem-036).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/ (nav_hook_lib)

import subagent_context
from nav_hook_lib import config

HOOKS_DIR = Path(__file__).resolve().parent.parent
DISPATCH = str(HOOKS_DIR / "nav_dispatch.py")
SESSION_ID = "sess-subagent-context-tests"
NOW = 1_700_000_000.0

RECALL_SUMMARY = (
    '- PITFALL: "Auth changes break session tests" (90%)\n'
    '- DECISION: "JWT over sessions for scaling" (95%)'
)

STUB_RECALL = f"""\
print({RECALL_SUMMARY!r})
"""


class SubagentContextBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name)) / "project"
        self.agent = self.root / ".agent"
        (self.agent / "knowledge").mkdir(parents=True)
        (self.agent / "knowledge" / "graph.json").write_text("{}\n")
        self.markers = self.agent / ".context-markers"
        self.markers.mkdir()

    def payload(self):
        return {"cwd": str(self.root), "session_id": SESSION_ID}

    def ctx(self, cfg=None):
        return types.SimpleNamespace(
            event="SubagentStart",
            payload=self.payload(),
            config=cfg if cfg is not None else config.load(self.root),
            state={},
            pilot_executor=False,
            now=NOW,
        )

    def write_readme(self, current_task="TASK-62 injector ops"):
        (self.agent / "DEVELOPMENT-README.md").write_text(
            f"# Navigator\n\n**Current task**: {current_task}\n\nMore text.\n",
            encoding="utf-8",
        )

    def run_with_recall(self, cfg=None, summary=RECALL_SUMMARY):
        with mock.patch.object(subagent_context.memory, "recall",
                               return_value=summary) as recall:
            result = subagent_context.run(self.ctx(cfg))
        return result, recall


class SnapshotTest(SubagentContextBase):
    def test_snapshot_carries_task_marker_and_memories(self):
        self.write_readme()
        (self.markers / ".active").write_text("2026-07-10-v7-runtime.md\n")
        result, _ = self.run_with_recall()
        text = result["additional_context"]
        self.assertIn("Active task: TASK-62 injector ops.", text)
        self.assertIn("Last context marker: 2026-07-10-v7-runtime.md.", text)
        self.assertIn("Auth changes break session tests", text)

    def test_no_current_task_line_means_no_task_sentence(self):
        (self.agent / "DEVELOPMENT-README.md").write_text(
            "# Navigator\n\nIn-flight tasks listed elsewhere.\n", encoding="utf-8")
        result, _ = self.run_with_recall()
        self.assertNotIn("Active task:", result["additional_context"])

    def test_newest_marker_file_used_when_active_pointer_missing(self):
        old = self.markers / "2025-01-01-old.md"
        old.write_text("old\n")
        new = self.markers / "2026-07-10-new.md"
        new.write_text("new\n")
        past = time.time() - 3600
        os.utime(old, (past, past))
        result, _ = self.run_with_recall()
        self.assertIn("Last context marker: 2026-07-10-new.md.",
                      result["additional_context"])

    def test_all_sources_empty_is_silent(self):
        result, _ = self.run_with_recall(summary="")
        self.assertIsNone(result)

    def test_memories_alone_still_inject(self):
        result, _ = self.run_with_recall()
        self.assertIn("Relevant project memories:", result["additional_context"])

    def test_top_k_comes_from_knowledge_graph_config(self):
        cfg = config.load(self.root)
        cfg["knowledge_graph"]["max_session_memories"] = 2
        _, recall = self.run_with_recall(cfg=cfg)
        self.assertEqual(recall.call_args.kwargs["limit"], 2)
        self.assertTrue(recall.call_args.kwargs["auto"])


class BudgetTest(SubagentContextBase):
    def test_payload_never_exceeds_2000_chars(self):
        self.write_readme()
        huge = "\n".join(f'- PITFALL: "pitfall number {i} with padding" (90%)'
                         for i in range(200))
        result, _ = self.run_with_recall(summary=huge)
        text = result["additional_context"]
        self.assertLessEqual(len(text), 2000)
        self.assertIn("[truncated by nav budget]", text)

    def test_configured_budget_chars_cuts_below_2000(self):
        cfg = config.load(self.root)
        cfg["subagent_context"]["budget_chars"] = 100
        result, _ = self.run_with_recall(cfg=cfg)
        self.assertLessEqual(len(result["additional_context"]), 100)


class DispatchContractTest(SubagentContextBase):
    """TASK-45 subprocess pattern against the live SubagentStart route."""

    def setUp(self):
        super().setUp()
        self.plugin_dir = Path(os.path.realpath(self._tmp.name)) / "plugin"
        functions = self.plugin_dir / "skills" / "nav-graph" / "functions"
        functions.mkdir(parents=True)
        (functions / "memory_recall.py").write_text(STUB_RECALL, encoding="utf-8")
        self.write_readme()

    def enable(self):
        (self.agent / ".nav-config.json").write_text(
            json.dumps({"subagent_context": {"enabled": True}}), encoding="utf-8")

    def dispatch(self, plugin_root=None):
        env = os.environ.copy()
        for key in ("PILOT_EXECUTOR", "CLAUDE_PROJECT_DIR", "CLAUDE_USER_MESSAGE",
                    "CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR"):
            env.pop(key, None)
        if plugin_root is not None:
            env["CLAUDE_PLUGIN_ROOT"] = plugin_root
        return subprocess.run(
            [sys.executable, DISPATCH, "SubagentStart"],
            input=json.dumps(self.payload()),
            capture_output=True,
            text=True,
            cwd=str(self.root),
            env=env,
            timeout=30,
        )

    def test_default_config_keeps_op_off(self):
        proc = self.dispatch(plugin_root=str(self.plugin_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("session snapshot", proc.stdout)

    def test_enabled_injects_under_budget_env_set(self):
        self.enable()
        proc = self.dispatch(plugin_root=str(self.plugin_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        hso = doc["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SubagentStart")
        self.assertIn("Active task: TASK-62 injector ops.", hso["additionalContext"])
        self.assertIn("Auth changes break session tests", hso["additionalContext"])
        self.assertLessEqual(len(hso["additionalContext"]), 2000)

    def test_enabled_env_unset_fails_open(self):
        # mem-036: CLAUDE_PLUGIN_ROOT unset — the file-relative fallback finds
        # the real checkout; recall against the empty tmp graph yields nothing
        # but the snapshot sentence still injects and dispatch exits 0.
        self.enable()
        proc = self.dispatch()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertIn("Active task: TASK-62 injector ops.",
                      doc["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
