#!/usr/bin/env python3
"""Tests for ops/setup.py — TASK-62 Phase 5 (Setup event).

Covers: the onboarding hint on a missing .agent/ (direct op invocation — the
dispatcher early-outs there, asserted explicitly at the contract level), the
one-line runtime status on an initialized project, and the dispatch-level
contract for the Setup event (validate-or-drop KEPT the registration on CC
2.1.205): status doc emitted, off-switch honored.
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

import setup as setup_op
from nav_hook_lib import config

HOOKS_DIR = Path(__file__).resolve().parent.parent
DISPATCH = str(HOOKS_DIR / "nav_dispatch.py")
SESSION_ID = "sess-setup-tests"
NOW = 1_700_000_000.0


class SetupBase(unittest.TestCase):
    with_agent = True

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name)) / "project"
        self.root.mkdir(parents=True)
        self.agent = self.root / ".agent"
        if self.with_agent:
            self.agent.mkdir()

    def ctx(self):
        return types.SimpleNamespace(
            event="Setup",
            payload={"cwd": str(self.root), "session_id": SESSION_ID},
            config=config.load(self.root),
            state={},
            pilot_executor=False,
            now=NOW,
        )


class OnboardingHintTest(SetupBase):
    with_agent = False

    def test_missing_agent_dir_points_at_nav_init(self):
        result = setup_op.run(self.ctx())
        message = result["system_message"]
        self.assertIn(".agent/ missing", message)
        self.assertIn("nav-init", message)
        self.assertIn("Initialize Navigator in this project", message)


class RuntimeStatusTest(SetupBase):
    def test_status_is_one_line_with_version_and_dispatcher(self):
        (self.agent / ".nav-config.json").write_text(
            '{"version": "6.18.1"}\n', encoding="utf-8")
        message = setup_op.run(self.ctx())["system_message"]
        self.assertNotIn("\n", message)
        self.assertIn("config v6.18.1", message)
        self.assertIn("dispatcher on", message)
        self.assertIn("knowledge graph absent", message)
        self.assertIn("runtime state not yet written", message)

    def test_status_reflects_graph_state_and_kill_switch(self):
        (self.agent / "knowledge").mkdir()
        (self.agent / "knowledge" / "graph.json").write_text("{}\n")
        (self.agent / ".nav-runtime-state.json").write_text("{}\n")
        (self.agent / ".nav-config.json").write_text(
            json.dumps({"dispatcher": {"enabled": False}}), encoding="utf-8")
        message = setup_op.run(self.ctx())["system_message"]
        self.assertIn("dispatcher off", message)
        self.assertIn("knowledge graph present", message)
        self.assertIn("runtime state present", message)
        self.assertIn("config unversioned", message)


class DispatchContractTest(SetupBase):
    """TASK-45 subprocess pattern against the live Setup route."""

    def dispatch(self):
        env = os.environ.copy()
        for key in ("PILOT_EXECUTOR", "CLAUDE_PROJECT_DIR", "CLAUDE_USER_MESSAGE"):
            env.pop(key, None)
        payload = {"cwd": str(self.root), "session_id": SESSION_ID}
        return subprocess.run(
            [sys.executable, DISPATCH, "Setup"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(self.root),
            env=env,
            timeout=30,
        )

    def test_initialized_project_emits_status_doc(self):
        proc = self.dispatch()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertIn("Navigator runtime status:", doc["systemMessage"])

    def test_off_switch_silences_the_status(self):
        (self.agent / ".nav-config.json").write_text(
            json.dumps({"setup_hook": {"enabled": False}}), encoding="utf-8")
        proc = self.dispatch()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("systemMessage", proc.stdout)


class DispatchEarlyOutTest(unittest.TestCase):
    """DELIVERY CAVEAT locked: no .agent/ ⇒ the dispatcher early-outs, so the
    onboarding hint CANNOT ship through the Setup route (TASK-60 contract:
    Navigator must not scaffold — or message — foreign projects)."""

    def test_missing_agent_dir_is_silent_through_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(os.path.realpath(tmp)) / "project"
            project.mkdir()
            env = os.environ.copy()
            for key in ("PILOT_EXECUTOR", "CLAUDE_PROJECT_DIR", "CLAUDE_USER_MESSAGE"):
                env.pop(key, None)
            proc = subprocess.run(
                [sys.executable, DISPATCH, "Setup"],
                input=json.dumps({"cwd": str(project), "session_id": SESSION_ID}),
                capture_output=True,
                text=True,
                cwd=str(project),
                env=env,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
