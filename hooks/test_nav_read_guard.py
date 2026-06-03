#!/usr/bin/env python3
"""Subprocess tests for hooks/nav_read_guard.py (PreToolUse:Read blocker).

stdlib unittest only (pytest not installed). Each test builds a throwaway
project dir with its own .agent/ and drives the hook via subprocess with a
PreToolUse JSON payload on stdin. Assertions reflect behavior verified
against the source:

  stdin keys: tool_name, tool_input.file_path, cwd, session_id
  counter file: .agent/.nav-read-counter.json (per session, session change resets)
  allowlist (exact .agent-relative path): DEVELOPMENT-README.md, .nav-config.json,
    .user-profile.json, knowledge/graph.json
  warn_threshold default 3, escalate_threshold default 5
  count >= escalate AND strict_block(default true) -> exit 2 + <nav-read-guard-block>
  count >= escalate AND strict_block false -> exit 0 (warn only)
  no .agent/ dir at root -> silent exit 0
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = str(Path(__file__).resolve().parent / "nav_read_guard.py")
SENTINEL_OPEN = "<nav-read-guard-block>"
SENTINEL_CLOSE = "</nav-read-guard-block>"


def run_hook(project_dir, tool_name="Read", file_path=None, session_id="sess-1",
             cwd=None):
    payload = {
        "tool_name": tool_name,
        "session_id": session_id,
        "cwd": cwd if cwd is not None else project_dir,
    }
    if file_path is not None:
        payload["tool_input"] = {"file_path": file_path}
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(
        ["python3", HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
    )


def write_config(agent_dir, **read_guard_overrides):
    cfg = {}
    if read_guard_overrides:
        cfg["read_guard_hook"] = read_guard_overrides
    (agent_dir / ".nav-config.json").write_text(json.dumps(cfg))


class NavReadGuardTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = os.path.realpath(self._tmp.name)
        self.agent = Path(self.project) / ".agent"
        self.agent.mkdir(parents=True)
        # A non-allowlisted target file under .agent/.
        self.target = self.agent / "tasks" / "TASK-99.md"
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text("# task doc\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _read_agent_file(self, n, file_path=None, session_id="sess-1"):
        """Fire n Read invocations of file_path; return list of CompletedProcess."""
        path = file_path if file_path is not None else str(self.target)
        return [
            run_hook(self.project, file_path=path, session_id=session_id)
            for _ in range(n)
        ]

    # (a) non-Read tool_name -> exit 0.
    def test_non_read_tool_exits_zero(self):
        result = run_hook(self.project, tool_name="Edit", file_path=str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.agent / ".nav-read-counter.json").exists())

    # (b) Read of a path OUTSIDE .agent/ -> exit 0, not counted.
    def test_read_outside_agent_not_counted(self):
        outside = Path(self.project) / "src" / "main.py"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("print('hi')\n")
        # Fire well past escalate threshold; must never block or count.
        results = self._read_agent_file(8, file_path=str(outside))
        for r in results:
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.agent / ".nav-read-counter.json").exists())

    # (c) allowlisted .agent/ file never increments the counter.
    def test_allowlisted_file_never_counts(self):
        readme = self.agent / "DEVELOPMENT-README.md"
        readme.write_text("# nav\n")
        results = self._read_agent_file(8, file_path=str(readme))
        for r in results:
            self.assertEqual(r.returncode, 0, r.stderr)
        # Counter file should not exist (allowlisted returns before increment).
        self.assertFalse((self.agent / ".nav-read-counter.json").exists())

    # (c-variant) knowledge/graph.json allowlisted; a different knowledge file counts.
    def test_knowledge_graph_allowlisted_but_memory_counts(self):
        kg_dir = self.agent / "knowledge"
        kg_dir.mkdir(parents=True, exist_ok=True)
        (kg_dir / "graph.json").write_text("{}\n")
        (kg_dir / "mem-001.md").write_text("# memory\n")
        # graph.json: allowlisted, never counts.
        for _ in range(6):
            r = run_hook(self.project, file_path=str(kg_dir / "graph.json"))
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.agent / ".nav-read-counter.json").exists())
        # A non-allowlisted knowledge file DOES count and eventually blocks.
        results = self._read_agent_file(5, file_path=str(kg_dir / "mem-001.md"))
        self.assertEqual(results[-1].returncode, 2, results[-1].stderr)

    # (d) repeated reads of NON-allowlisted file past escalate -> exit 2 + sentinel.
    def test_escalate_blocks_with_default_config(self):
        # No config file -> defaults warn=3, escalate=5, strict_block=true.
        results = self._read_agent_file(5)
        # Reads 1-4 are non-blocking (warn at >=3).
        for r in results[:4]:
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[nav-read-guard]", results[2].stderr)  # warn at count 3
        # 5th read crosses escalate_threshold (5) -> block.
        self.assertEqual(results[4].returncode, 2, results[4].stderr)
        self.assertIn(SENTINEL_OPEN, results[4].stderr)
        self.assertIn(SENTINEL_CLOSE, results[4].stderr)

    # (d-variant) lower thresholds via config block sooner.
    def test_escalate_blocks_with_custom_thresholds(self):
        write_config(self.agent, warn_threshold=1, escalate_threshold=2,
                     strict_block=True)
        results = self._read_agent_file(2)
        self.assertEqual(results[0].returncode, 0, results[0].stderr)  # count 1 warn
        self.assertEqual(results[1].returncode, 2, results[1].stderr)  # count 2 block
        self.assertIn(SENTINEL_OPEN, results[1].stderr)

    # (e) strict_block=false -> exit 0 even past escalate threshold (warn only).
    def test_strict_block_false_warns_not_blocks(self):
        write_config(self.agent, warn_threshold=3, escalate_threshold=5,
                     strict_block=False)
        results = self._read_agent_file(6)
        for r in results:
            self.assertEqual(r.returncode, 0, r.stderr)
        # Past escalate it still emits an advisory, just no sentinel block.
        self.assertIn("[nav-read-guard]", results[5].stderr)
        self.assertNotIn(SENTINEL_OPEN, results[5].stderr)

    # (f) a different session_id resets the counter.
    def test_session_change_resets_counter(self):
        # Build up to 4 in session A (below escalate=5).
        for r in self._read_agent_file(4, session_id="sess-A"):
            self.assertEqual(r.returncode, 0, r.stderr)
        # First read in session B resets to count 1 -> no block.
        r = run_hook(self.project, file_path=str(self.target), session_id="sess-B")
        self.assertEqual(r.returncode, 0, r.stderr)
        counter = json.loads((self.agent / ".nav-read-counter.json").read_text())
        self.assertEqual(counter["turn_count"], 1)
        self.assertEqual(counter["session_id"], "sess-B")

    # (g) cwd with no .agent/ dir -> silent exit 0.
    def test_no_agent_dir_silent(self):
        with tempfile.TemporaryDirectory() as bare:
            bare = os.path.realpath(bare)
            r = run_hook(bare, file_path=str(Path(bare) / "anything.md"), cwd=bare)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "")


if __name__ == "__main__":
    unittest.main()
