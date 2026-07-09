#!/usr/bin/env python3
"""Tests for task_to_graph.add_task_to_graph referential integrity (wp6 follow-up).

The PostToolUse task-sync hook must not re-introduce dangling 'implements'
edges. Before the fix, keyword_map produced concept 'tom' (no canonical node)
and an unconditional edge, so every task edit poisoned the graph with a
dangling edge that --action repair then had to clean.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import create_empty_graph, save_graph, load_graph, add_node
from graph_maintenance import find_dangling_edges
from task_to_graph import add_task_to_graph, extract_decisions


class TaskSyncIntegrityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.graph_path = self.root / "graph.json"
        graph = create_empty_graph()
        # Only the canonical 'theory of mind' concept exists as a node.
        graph = add_node(
            graph, "concepts", "theory of mind",
            {"name": "Theory of Mind", "aliases": ["tom", "profile"]},
        )
        save_graph(str(self.graph_path), graph)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_task(self, name: str, body: str) -> Path:
        path = self.root / name
        path.write_text(body)
        return path

    def test_sync_creates_no_dangling_edges(self):
        # 'profile' -> 'theory of mind' (node exists -> edge ok);
        # 'deploy' -> 'deployment' (no node -> edge filtered, not dangling).
        task = self._write_task(
            "TASK-77.md",
            "# TASK-77: x\n\nWork on the user profile and deployment pipeline.\n",
        )
        add_task_to_graph(str(task), str(self.graph_path))
        graph = load_graph(str(self.graph_path))
        self.assertEqual(find_dangling_edges(graph), [])

    def test_canonical_concept_edge_is_added(self):
        # 'profile'/'tom' both normalize to the canonical 'theory of mind' node.
        task = self._write_task(
            "TASK-78.md",
            "# TASK-78: x\n\nImprove the profile / tom modeling.\n",
        )
        add_task_to_graph(str(task), str(self.graph_path))
        graph = load_graph(str(self.graph_path))
        edges = [(e["from"], e["to"]) for e in graph["edges"]]
        self.assertIn(("TASK-78", "theory of mind"), edges)


COMPLETED_TASK_WITH_DECISIONS = """# TASK-99: Demo

**Status**: ✅ Completed

## Technical Decisions

| Decision | Options | Chosen | Reasoning |
|----------|---------|--------|-----------|
| Issue interface | gh, API | `gh` | GitHub-only access |
"""


class DecisionExtractionTest(unittest.TestCase):
    """Separator rows must never be ingested as decisions (mem-038/mem-044)."""

    def test_wide_separator_row_not_ingested(self):
        decisions = extract_decisions(COMPLETED_TASK_WITH_DECISIONS)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision"], "Issue interface")

    def test_narrow_separator_row_still_skipped(self):
        content = (
            "## Technical Decisions\n\n"
            "| Decision | Options | Chosen | Reasoning |\n"
            "|---|---|---|---|\n"
            "| X | a, b | a | short reason here |\n"
        )
        decisions = extract_decisions(content)
        self.assertEqual([d["decision"] for d in decisions], ["X"])

    def test_colon_aligned_separator_skipped(self):
        content = (
            "## Technical Decisions\n\n"
            "| Decision | Options | Chosen | Reasoning |\n"
            "|:---------|:-------:|-------:|-----------|\n"
            "| Y | a, b | b | another reason here |\n"
        )
        decisions = extract_decisions(content)
        self.assertEqual([d["decision"] for d in decisions], ["Y"])


class DecisionDedupeTest(unittest.TestCase):
    """Re-syncing a completed task must not duplicate its decision memories
    (the TASK-54 double-sync produced mem-044..049 as copies of mem-038..043).
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.graph_path = self.root / "graph.json"
        save_graph(str(self.graph_path), create_empty_graph())
        # add_memory writes backing files under CWD-relative .agent/knowledge;
        # run inside the tmp root so tests never touch the real project graph.
        self._old_cwd = Path.cwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def test_resync_does_not_duplicate_decision_memories(self):
        task = self.root / "TASK-99.md"
        task.write_text(COMPLETED_TASK_WITH_DECISIONS)

        first = add_task_to_graph(str(task), str(self.graph_path))
        self.assertEqual(len(first["memories_created"]), 1)

        second = add_task_to_graph(str(task), str(self.graph_path))
        self.assertEqual(second["memories_created"], [])

        graph = load_graph(str(self.graph_path))
        summaries = [m["summary"] for m in graph["nodes"]["memories"].values()]
        self.assertEqual(len(summaries), len(set(summaries)))
        self.assertEqual(len(summaries), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
