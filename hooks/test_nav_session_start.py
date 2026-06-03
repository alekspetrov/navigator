#!/usr/bin/env python3
"""Unit tests for nav_session_start._section_auto_update (wp5 / TASK-46).

The SessionStart hook must check for updates in READ-ONLY mode: it invokes
auto_updater with `--check-drift` (which only compares versions) and never the
mutating `claude plugin update` path that used to run inside the 10s budget.

These tests stub auto_updater.py with a tiny script so no network / `claude`
CLI is touched. stdlib unittest only. Run with:
  cd hooks && python3 -m unittest test_nav_session_start -v
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
SESSION_START = HOOKS_DIR / "nav_session_start.py"

# Stub updater: records the argv it was called with under <plugin_dir>/argv.txt
# and emits a drift payload. parents[3] of this file == the plugin dir
# (plugin/skills/nav-start/functions/auto_updater.py).
STUB_DRIFT = (
    "import sys, json, pathlib\n"
    "pathlib.Path(__file__).resolve().parents[3].joinpath('argv.txt')"
    ".write_text(' '.join(sys.argv))\n"
    "print(json.dumps({'has_drift': True, 'plugin_version': '9.9.9',\n"
    "  'project_version': '1.0.0',\n"
    "  'message': 'Project config (v1.0.0) behind plugin (v9.9.9). Run nav-upgrade.'}))\n"
)

STUB_NO_DRIFT = "import json; print(json.dumps({'has_drift': False}))\n"


def _load_module():
    spec = importlib.util.spec_from_file_location("nav_session_start", SESSION_START)
    assert spec and spec.loader, "could not load nav_session_start spec"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SectionAutoUpdateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".agent").mkdir(parents=True)
        (self.root / ".agent" / ".nav-config.json").write_text(
            json.dumps({"version": "1.0.0"}), encoding="utf-8"
        )
        self.plugin_dir = self.root / "plugin"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _stub_updater(self, body: str) -> None:
        fn_dir = self.plugin_dir / "skills" / "nav-start" / "functions"
        fn_dir.mkdir(parents=True, exist_ok=True)
        (fn_dir / "auto_updater.py").write_text(body, encoding="utf-8")

    def test_drift_renders_section_in_read_only_mode(self):
        self._stub_updater(STUB_DRIFT)
        section = self.mod._section_auto_update(self.root, self.plugin_dir)
        self.assertIsNotNone(section)
        self.assertIn("Auto-Update", section)
        self.assertIn("9.9.9", section)
        # Proves it ran read-only: --check-drift was passed (mutating mode takes
        # no args), along with the project --config-path.
        argv = (self.plugin_dir / "argv.txt").read_text()
        self.assertIn("--check-drift", argv)
        self.assertIn("--config-path", argv)

    def test_no_drift_returns_none(self):
        self._stub_updater(STUB_NO_DRIFT)
        self.assertIsNone(
            self.mod._section_auto_update(self.root, self.plugin_dir)
        )

    def test_missing_updater_returns_none(self):
        # plugin_dir exists but has no auto_updater.py.
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.assertIsNone(
            self.mod._section_auto_update(self.root, self.plugin_dir)
        )

    def test_plugin_dir_none_returns_none(self):
        self.assertIsNone(self.mod._section_auto_update(self.root, None))

    def test_malformed_updater_output_returns_none(self):
        self._stub_updater("print('not json')\n")
        self.assertIsNone(
            self.mod._section_auto_update(self.root, self.plugin_dir)
        )


if __name__ == "__main__":
    unittest.main()
