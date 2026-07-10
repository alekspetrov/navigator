#!/usr/bin/env python3
"""Tests for the claude_updater hook-liveness sequencing guard (TASK-63 Phase 5).

TASK-45 subprocess pattern: each test builds a throwaway project dir and
drives the REAL CLI (`python3 claude_updater.py generate ...`), asserting on
exit code / stderr / on-disk effects. Both branches are covered:

  - refuse: no liveness proof (absent or stale files) -> exit 3, existing
    CLAUDE.md untouched, refusal names the guard, the files checked, and the
    remedy (mem-036 class: never strip prose while hooks are silently dead).
  - proceed: fresh .nav-runtime-state.json (meta.schema == 2, meta.updated
    within 7 days) OR fresh .nav-dispatch-health.json (last_error.ts within
    7 days) -> regeneration happens.

Env discipline (mem-036): the same behavior is asserted with hook-style env
vars set AND unset — the guard reads files, never env.

The --template argument is always a direct FILE path so the CLI takes the
no-network branch (GitHub fetch only fires for directory arguments).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_updater  # noqa: E402

SCRIPT = str(Path(__file__).resolve().parent / "claude_updater.py")

EMPTY_CUSTOMIZATIONS = {
    "project_name": "",
    "description": "",
    "tech_stack": [],
    "code_standards": [],
    "forbidden_actions": [],
    "pm_tool": "none",
    "custom_sections": {},
}

TEMPLATE_BODY = "# [Project Name] - Claude Code Configuration\n\nTemplate body.\n"


def _env_with_hook_vars(project: Path) -> dict:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env["CLAUDE_PLUGIN_ROOT"] = str(project)
    return env


def _env_without_hook_vars() -> dict:
    return {
        k: v for k, v in os.environ.items()
        if not k.startswith("CLAUDE_") and k != "PILOT_EXECUTOR"
    }


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _write_state_file(project: Path, updated: datetime, schema: int = 2) -> None:
    agent = project / ".agent"
    agent.mkdir(parents=True, exist_ok=True)
    doc = {"meta": {"schema": schema, "updated": _iso(updated), "sections": {}}}
    (agent / ".nav-runtime-state.json").write_text(json.dumps(doc))


def _write_health_file(project: Path, ts: datetime) -> None:
    agent = project / ".agent"
    agent.mkdir(parents=True, exist_ok=True)
    doc = {
        "last_error": {
            "ts": _iso(ts), "event": "Stop", "op": "stop_state", "error": "OSError",
        },
        "surfaced": True,
    }
    (agent / ".nav-dispatch-health.json").write_text(json.dumps(doc))


def _run_generate(project: Path, env: dict) -> subprocess.CompletedProcess:
    customizations = project / "customizations.json"
    customizations.write_text(json.dumps(EMPTY_CUSTOMIZATIONS))
    template = project / "template.md"
    template.write_text(TEMPLATE_BODY)
    return subprocess.run(
        [
            sys.executable, SCRIPT, "generate",
            "--customizations", str(customizations),
            "--template", str(template),
            "--output", str(project / "CLAUDE.md"),
        ],
        capture_output=True, text=True, env=env,
    )


class GuardRefusalTests(unittest.TestCase):
    def test_refuses_when_no_liveness_files_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertFalse((project / "CLAUDE.md").exists())
            # Refusal names the guard, both files checked, and the remedy.
            self.assertIn("sequencing guard", result.stderr)
            self.assertIn(".nav-runtime-state.json", result.stderr)
            self.assertIn(".nav-dispatch-health.json", result.stderr)
            self.assertIn("re-run the sync", result.stderr)

    def test_refuses_identically_with_hook_env_unset(self):
        # mem-036 discipline: env state must not change guard behavior.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = _run_generate(project, _env_without_hook_vars())

            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("sequencing guard", result.stderr)
            self.assertFalse((project / "CLAUDE.md").exists())

    def test_refuses_on_stale_state_and_preserves_existing_claude_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            stale = datetime.now(tz=timezone.utc) - timedelta(days=8)
            _write_state_file(project, stale)
            existing = "# Existing prose mandates\n"
            (project / "CLAUDE.md").write_text(existing)

            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual((project / "CLAUDE.md").read_text(), existing)

    def test_refuses_on_fresh_state_with_wrong_schema(self):
        # Schema gate: only meta.schema == 2 documents prove the v7 runtime.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_state_file(project, datetime.now(tz=timezone.utc), schema=1)

            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 3, result.stderr)

    def test_refuses_on_stale_health_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            stale = datetime.now(tz=timezone.utc) - timedelta(days=8)
            _write_health_file(project, stale)

            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 3, result.stderr)


class GuardProceedTests(unittest.TestCase):
    def test_proceeds_with_fresh_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_state_file(project, datetime.now(tz=timezone.utc))

            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Template body.", (project / "CLAUDE.md").read_text())

    def test_proceeds_with_fresh_state_file_env_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_state_file(project, datetime.now(tz=timezone.utc))

            result = _run_generate(project, _env_without_hook_vars())

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((project / "CLAUDE.md").exists())

    def test_proceeds_with_fresh_health_file_only(self):
        # Health is written on error only, but a fresh error record still
        # proves the dispatcher ran — liveness, not health, is the question.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_health_file(project, datetime.now(tz=timezone.utc))

            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((project / "CLAUDE.md").exists())

    def test_proceeds_with_stale_state_but_fresh_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_state_file(project, datetime.now(tz=timezone.utc) - timedelta(days=8))
            _write_health_file(project, datetime.now(tz=timezone.utc))

            result = _run_generate(project, _env_with_hook_vars(project))

            self.assertEqual(result.returncode, 0, result.stderr)


class CheckHookLivenessUnitTests(unittest.TestCase):
    """Direct unit coverage of the boundary math (injectable `now`)."""

    def test_exactly_seven_days_old_is_still_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            now = datetime.now(tz=timezone.utc)
            _write_state_file(project, now - timedelta(days=7))

            alive, message = claude_updater.check_hook_liveness(
                project, now=now.timestamp()
            )
            self.assertTrue(alive, message)

    def test_corrupt_json_counts_as_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            agent = project / ".agent"
            agent.mkdir()
            (agent / ".nav-runtime-state.json").write_text("{not json")
            (agent / ".nav-dispatch-health.json").write_text("[]")

            alive, message = claude_updater.check_hook_liveness(project)
            self.assertFalse(alive)
            self.assertIn("sequencing guard", message)


if __name__ == "__main__":
    unittest.main()
