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


# Stub recall: records argv under <plugin_dir>/recall_argv.txt and emits two
# compact lines. parents[3] of the stub == the plugin dir
# (plugin/skills/nav-graph/functions/memory_recall.py).
STUB_RECALL = (
    "import sys, pathlib\n"
    "pathlib.Path(__file__).resolve().parents[3].joinpath('recall_argv.txt')"
    ".write_text(' '.join(sys.argv))\n"
    "print('- PITFALL: \"Auth breaks session tests\" (90%)')\n"
    "print('- PATTERN: \"Unit before integration\" (85%)')\n"
)

STUB_RECALL_EMPTY = "pass\n"


class SectionRelevantMemoriesTest(unittest.TestCase):
    """v6.17.0: the hook section implementing auto_surface_relevant."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".agent" / "knowledge").mkdir(parents=True)
        (self.root / ".agent" / "knowledge" / "graph.json").write_text("{}")
        self.plugin_dir = self.root / "plugin"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _stub_recall(self, body: str) -> None:
        fn_dir = self.plugin_dir / "skills" / "nav-graph" / "functions"
        fn_dir.mkdir(parents=True, exist_ok=True)
        (fn_dir / "memory_recall.py").write_text(body, encoding="utf-8")

    def test_section_renders_from_recall_output(self):
        self._stub_recall(STUB_RECALL)
        section = self.mod._section_relevant_memories(self.root, self.plugin_dir, 5)
        self.assertIsNotNone(section)
        self.assertIn("## Relevant Memories", section)
        self.assertIn("Auth breaks session tests", section)
        # --auto mode with the configured limit
        argv = (self.plugin_dir / "recall_argv.txt").read_text()
        self.assertIn("--auto", argv)
        self.assertIn("--limit 5", argv)
        self.assertIn("--format compact", argv)

    def test_limit_passthrough(self):
        self._stub_recall(STUB_RECALL)
        self.mod._section_relevant_memories(self.root, self.plugin_dir, 3)
        argv = (self.plugin_dir / "recall_argv.txt").read_text()
        self.assertIn("--limit 3", argv)

    def test_empty_recall_output_returns_none(self):
        self._stub_recall(STUB_RECALL_EMPTY)
        self.assertIsNone(
            self.mod._section_relevant_memories(self.root, self.plugin_dir, 5))

    def test_missing_graph_returns_none(self):
        (self.root / ".agent" / "knowledge" / "graph.json").unlink()
        self._stub_recall(STUB_RECALL)
        self.assertIsNone(
            self.mod._section_relevant_memories(self.root, self.plugin_dir, 5))

    def test_plugin_dir_none_or_missing_recall_returns_none(self):
        self.assertIsNone(
            self.mod._section_relevant_memories(self.root, None, 5))
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.assertIsNone(
            self.mod._section_relevant_memories(self.root, self.plugin_dir, 5))


class HookConfigMemoriesGateTest(unittest.TestCase):
    """knowledge_graph.auto_surface_relevant gates the section; defaults on."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _config(self, tmp: Path, cfg: dict) -> Path:
        (tmp / ".agent").mkdir(parents=True, exist_ok=True)
        (tmp / ".agent" / ".nav-config.json").write_text(json.dumps(cfg))
        return tmp

    def test_defaults_when_block_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._config(Path(tmp), {"version": "1.0.0"})
            cfg = self.mod._read_hook_config(root)
            self.assertTrue(cfg["surface_memories"])
            self.assertEqual(cfg["max_memories"], 5)

    def test_flag_off_disables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._config(Path(tmp), {
                "knowledge_graph": {"auto_surface_relevant": False}})
            cfg = self.mod._read_hook_config(root)
            self.assertFalse(cfg["surface_memories"])

    def test_max_memories_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._config(Path(tmp), {
                "knowledge_graph": {"max_session_memories": 2}})
            self.assertEqual(self.mod._read_hook_config(root)["max_memories"], 2)


class PayloadOrderingTest(unittest.TestCase):
    """Memories section must precede navigator so truncation can't eat it,
    and must not render when the flag is off."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _project(self, tmp: Path, surface: bool) -> Path:
        agent = tmp / ".agent"
        (agent / "knowledge").mkdir(parents=True)
        (agent / "knowledge" / "graph.json").write_text("{}")
        (agent / "DEVELOPMENT-README.md").write_text("# Navigator Index\n")
        (agent / ".nav-config.json").write_text(json.dumps({
            "knowledge_graph": {"auto_surface_relevant": surface}}))
        return tmp

    def _with_stub_plugin(self, tmp: Path):
        import os
        plugin = tmp / "plugin"
        fn_dir = plugin / "skills" / "nav-graph" / "functions"
        fn_dir.mkdir(parents=True)
        (fn_dir / "memory_recall.py").write_text(STUB_RECALL)
        (plugin / "skills" / "nav-start").mkdir(parents=True)
        old = os.environ.get("CLAUDE_PLUGIN_ROOT")
        os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin)
        return old

    def _restore(self, old):
        import os
        if old is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old

    def test_memories_before_navigator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp), surface=True)
            old = self._with_stub_plugin(Path(tmp))
            try:
                body = self.mod._build_payload({"cwd": str(root)})
            finally:
                self._restore(old)
            self.assertIn("## Relevant Memories", body)
            self.assertLess(body.index("## Relevant Memories"),
                            body.index("# Pilot") if "# Pilot" in body
                            else body.index("Navigator Index"))

    def test_flag_off_omits_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp), surface=False)
            old = self._with_stub_plugin(Path(tmp))
            try:
                body = self.mod._build_payload({"cwd": str(root)})
            finally:
                self._restore(old)
            self.assertNotIn("## Relevant Memories", body)
            # Stub was never invoked
            self.assertFalse((Path(tmp) / "plugin" / "recall_argv.txt").exists())


if __name__ == "__main__":
    unittest.main()
