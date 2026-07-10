#!/usr/bin/env python3
"""Tests for nav_hook_lib/memory.py (TASK-59, Phase 5).

stdlib unittest only. Contract under test (v6 semantics from nav_brief.py /
nav_session_start.py):

  - '' silently on ANY failure: missing graph, missing script, non-zero
    exit, crash, timeout, no targets.
  - --concepts is passed as ONE comma-separated argv entry.
  - A real invocation against this repo's knowledge graph returns compact
    "- TYPE: ..." lines and honors --limit.

Fake recall scripts are injected via CLAUDE_PLUGIN_ROOT, mirroring
hooks/test_nav_brief.py's make_fake_plugin pattern.
"""
import contextlib
import inspect
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import memory

REPO_ROOT = HERE.parent.parent
REPO_AGENT = REPO_ROOT / ".agent"


@contextlib.contextmanager
def plugin_env(root=None):
    """Clear plugin-dir env vars; optionally point CLAUDE_PLUGIN_ROOT at root."""
    saved = {k: os.environ.pop(k, None)
             for k in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR")}
    if root is not None:
        os.environ["CLAUDE_PLUGIN_ROOT"] = str(root)
    try:
        yield
    finally:
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value


def make_fake_plugin(root: Path, recall_body: str) -> Path:
    """Create a fake plugin dir whose memory_recall.py runs recall_body."""
    functions = root / "skills" / "nav-graph" / "functions"
    functions.mkdir(parents=True)
    (functions / "memory_recall.py").write_text(
        "#!/usr/bin/env python3\n" + textwrap.dedent(recall_body))
    return root


class MemoryRecallFakeScriptTest(unittest.TestCase):
    """Failure-path + argv contract via an injected fake recall script."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(os.path.realpath(self._tmp.name))
        self.agent = self.tmp / "project" / ".agent"
        knowledge = self.agent / "knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "graph.json").write_text(json.dumps({"nodes": {}}))
        self.plugin = self.tmp / "plugin"

    def tearDown(self):
        self._tmp.cleanup()

    def recall(self, **kwargs):
        kwargs.setdefault("agent_dir", str(self.agent))
        return memory.recall(**kwargs)

    def test_failing_script_returns_empty(self):
        make_fake_plugin(self.plugin, """
            import sys
            print("should never surface")
            sys.exit(1)
        """)
        with plugin_env(self.plugin):
            self.assertEqual(self.recall(concepts="auth"), "")

    def test_crashing_script_returns_empty(self):
        make_fake_plugin(self.plugin, "raise RuntimeError('recall exploded')\n")
        with plugin_env(self.plugin):
            self.assertEqual(self.recall(concepts="auth"), "")

    def test_timeout_returns_empty(self):
        make_fake_plugin(self.plugin, """
            import time
            time.sleep(10)
            print("too late")
        """)
        with plugin_env(self.plugin):
            self.assertEqual(self.recall(concepts="auth", timeout_s=1), "")

    def test_default_timeout_is_three_seconds(self):
        # FIX 6: v6 parity — nav_brief.py RECALL_TIMEOUT = 3. A per-prompt
        # hook cannot afford a 10s recall stall.
        sig = inspect.signature(memory.recall)
        self.assertEqual(sig.parameters["timeout_s"].default, 3)

    def test_missing_script_returns_empty(self):
        self.plugin.mkdir()  # plugin dir exists, recall script does not
        with plugin_env(self.plugin):
            self.assertEqual(self.recall(concepts="auth"), "")

    def test_missing_graph_returns_empty_without_running_script(self):
        make_fake_plugin(self.plugin, "print('ran anyway')\n")
        bare_agent = self.tmp / "bare" / ".agent"
        bare_agent.mkdir(parents=True)  # no knowledge/graph.json
        with plugin_env(self.plugin):
            self.assertEqual(
                memory.recall(concepts="auth", agent_dir=str(bare_agent)), "")

    def test_no_targets_returns_empty(self):
        make_fake_plugin(self.plugin, "print('ran anyway')\n")
        with plugin_env(self.plugin):
            self.assertEqual(self.recall(), "")
            self.assertEqual(self.recall(concepts=[]), "")

    def test_success_output_stripped(self):
        make_fake_plugin(self.plugin, """
            print('- PITFALL: "watch out" (90%)')
            print()
        """)
        with plugin_env(self.plugin):
            self.assertEqual(self.recall(concepts="auth"),
                             '- PITFALL: "watch out" (90%)')

    def test_concepts_list_joined_into_single_arg(self):
        make_fake_plugin(self.plugin, """
            import sys
            print("|".join(sys.argv[1:]))
        """)
        with plugin_env(self.plugin):
            out = self.recall(concepts=["auth", "jwt tokens", "hooks"], limit=3)
        argv = out.split("|")
        self.assertIn("--concepts", argv)
        self.assertEqual(argv[argv.index("--concepts") + 1],
                         "auth,jwt tokens,hooks")
        self.assertEqual(argv.count("--concepts"), 1)
        self.assertEqual(argv[argv.index("--limit") + 1], "3")
        self.assertEqual(argv[argv.index("--format") + 1], "compact")

    def test_auto_flag_passed(self):
        make_fake_plugin(self.plugin, """
            import sys
            print("|".join(sys.argv[1:]))
        """)
        with plugin_env(self.plugin):
            out = self.recall(auto=True)
        argv = out.split("|")
        self.assertIn("--auto", argv)
        self.assertNotIn("--concepts", argv)


class MemoryRecallRealScriptTest(unittest.TestCase):
    """Real memory_recall.py against this repo's knowledge graph."""

    @classmethod
    def setUpClass(cls):
        graph = REPO_AGENT / "knowledge" / "graph.json"
        if not graph.is_file():
            raise unittest.SkipTest("repo knowledge graph missing")

    def test_real_invocation_compact_lines(self):
        with plugin_env(None):  # force repo-checkout fallback resolution
            out = memory.recall(concepts="hooks", agent_dir=str(REPO_AGENT))
        self.assertTrue(out, "expected 'hooks' memories from the repo graph")
        lines = out.splitlines()
        self.assertLessEqual(len(lines), 5)
        for line in lines:
            self.assertTrue(line.startswith("- "), f"not compact format: {line}")

    def test_real_invocation_honors_limit(self):
        with plugin_env(None):
            out = memory.recall(concepts=["hooks"], agent_dir=str(REPO_AGENT),
                                limit=2)
        self.assertTrue(out)
        self.assertLessEqual(len(out.splitlines()), 2)

    def test_real_script_rejects_concepts_plus_auto(self):
        """Mutual exclusion is delegated: non-zero exit collapses to ''."""
        with plugin_env(None):
            out = memory.recall(concepts="hooks", auto=True,
                                agent_dir=str(REPO_AGENT))
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
