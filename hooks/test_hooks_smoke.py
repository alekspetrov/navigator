#!/usr/bin/env python3
"""
Smoke tests for Navigator's non-blocking lifecycle hooks.

Goal: import + no-crash + the empty/malformed-stdin contract. These hooks
are side-effect-only and non-blocking, so exit 0 is the expected contract
for VALID, EMPTY, and MALFORMED stdin alike. When stdout is non-empty it
must be valid JSON.

Each hook is exercised against a throwaway temp project with a minimal
`.agent/`. NEVER touches the real .agent/.

stdlib unittest only (pytest is NOT installed). Run with:
  cd hooks && python3 -m unittest test_hooks_smoke -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent


def _make_project(root: Path) -> Path:
    """Create a minimal Navigator project layout under root."""
    agent = root / ".agent"
    agent.mkdir(parents=True, exist_ok=True)
    (agent / ".nav-config.json").write_text(
        json.dumps({"version": "test"}), encoding="utf-8"
    )
    (agent / "DEVELOPMENT-README.md").write_text(
        "# Navigator Index\n\nMinimal test navigator.\n", encoding="utf-8"
    )
    return root


def _run(hook: str, stdin: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / hook)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _assert_stdout_empty_or_json(test: unittest.TestCase, stdout: str) -> None:
    text = stdout.strip()
    if not text:
        return
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        test.fail(f"stdout is non-empty and not valid JSON: {text!r} ({exc})")


# Minimal VALID per-event stdin payload (cwd is injected per-test).
# SessionStart       → {"cwd": ...}
# PostToolUse (Edit) → {"tool_name": "Edit", "tool_input": {}, "cwd": ...}
# Stop               → {"cwd": ...}
HOOK_PAYLOADS = {
    "nav_session_start.py": {},
    "nav_profile_sync.py": {"tool_name": "Edit", "tool_input": {}},
    "nav_task_graph_sync.py": {"tool_name": "Edit", "tool_input": {}},
    "nav_workflow_state.py": {},
    "token_monitor.py": {"tool_name": "Edit", "tool_input": {}},
}


class HooksSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _make_project(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _valid_stdin(self, hook: str) -> str:
        payload = dict(HOOK_PAYLOADS[hook])
        payload["cwd"] = str(self.root)
        return json.dumps(payload)

    def _check_valid(self, hook: str) -> None:
        proc = _run(hook, self._valid_stdin(hook), self.root)
        self.assertEqual(
            proc.returncode, 0, f"{hook} valid stdin: rc != 0; stderr: {proc.stderr}"
        )
        _assert_stdout_empty_or_json(self, proc.stdout)

    def _check_empty(self, hook: str) -> None:
        proc = _run(hook, "", self.root)
        self.assertEqual(
            proc.returncode, 0, f"{hook} empty stdin: rc != 0; stderr: {proc.stderr}"
        )
        _assert_stdout_empty_or_json(self, proc.stdout)

    def _check_malformed(self, hook: str) -> None:
        proc = _run(hook, "{not json", self.root)
        self.assertEqual(
            proc.returncode, 0, f"{hook} malformed stdin: rc != 0; stderr: {proc.stderr}"
        )
        _assert_stdout_empty_or_json(self, proc.stdout)

    # ── nav_session_start.py (SessionStart) ─────────────────────────────────
    def test_session_start_valid(self) -> None:
        self._check_valid("nav_session_start.py")

    def test_session_start_empty(self) -> None:
        self._check_empty("nav_session_start.py")

    def test_session_start_malformed(self) -> None:
        self._check_malformed("nav_session_start.py")

    # ── nav_profile_sync.py (PostToolUse) ───────────────────────────────────
    def test_profile_sync_valid(self) -> None:
        self._check_valid("nav_profile_sync.py")

    def test_profile_sync_empty(self) -> None:
        self._check_empty("nav_profile_sync.py")

    def test_profile_sync_malformed(self) -> None:
        self._check_malformed("nav_profile_sync.py")

    # ── nav_task_graph_sync.py (PostToolUse) ────────────────────────────────
    def test_task_graph_sync_valid(self) -> None:
        self._check_valid("nav_task_graph_sync.py")

    def test_task_graph_sync_empty(self) -> None:
        self._check_empty("nav_task_graph_sync.py")

    def test_task_graph_sync_malformed(self) -> None:
        self._check_malformed("nav_task_graph_sync.py")

    # ── nav_workflow_state.py (Stop) ────────────────────────────────────────
    def test_workflow_state_valid(self) -> None:
        self._check_valid("nav_workflow_state.py")

    def test_workflow_state_empty(self) -> None:
        self._check_empty("nav_workflow_state.py")

    def test_workflow_state_malformed(self) -> None:
        self._check_malformed("nav_workflow_state.py")

    # ── token_monitor.py (PostToolUse) ──────────────────────────────────────
    def test_token_monitor_valid(self) -> None:
        self._check_valid("token_monitor.py")

    def test_token_monitor_empty(self) -> None:
        self._check_empty("token_monitor.py")

    def test_token_monitor_malformed(self) -> None:
        self._check_malformed("token_monitor.py")


if __name__ == "__main__":
    unittest.main()
