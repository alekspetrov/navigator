#!/usr/bin/env python3
"""Tests for graph_builder.py memory preservation across rebuilds (v6.17.0).

Before v6.17.0, build_graph initialized memories:{} empty on every rebuild,
silently wiping all memory nodes — a root cause of disk-vs-graph drift.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graph_builder import build_graph


def _make_agent_dir(tmp: str) -> Path:
    """Minimal .agent structure with one open task."""
    agent = Path(tmp) / ".agent"
    (agent / "tasks").mkdir(parents=True)
    (agent / "tasks" / "TASK-01-auth.md").write_text(
        "# TASK-01: Add authentication\n\n**Status**: in-progress\n\n"
        "Implement login and session handling.\n"
    )
    return agent


def _existing_graph_with_memory() -> dict:
    return {
        "version": "1.0.0",
        "nodes": {
            "tasks": {},
            "concepts": {},
            "memories": {
                "mem-001": {
                    "type": "pitfall",
                    "summary": "Auth changes break session tests",
                    "path": "memories/pitfalls/mem-001.md",
                    "confidence": 0.9,
                    "concepts": ["authentication", "graph-preserve-test"],
                    "created": "2026-06-01",
                    "last_validated": "2026-06-01",
                    "source": "execution",
                    "resolved": True,
                },
            },
            "files": {},
        },
        "edges": [
            # memory -> task edge; TASK-01 still exists after rebuild
            {"from": "mem-001", "to": "TASK-01", "type": "learned-from"},
            # memory -> node that will NOT exist after rebuild (dropped)
            {"from": "mem-001", "to": "TASK-99", "type": "learned-from"},
        ],
        "concept_index": {},
    }


class TestBuildGraphPreservesMemories(unittest.TestCase):

    def test_memories_preserved_with_graph_only_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent_dir(tmp)
            graph = build_graph(str(agent), existing_graph=_existing_graph_with_memory())

            self.assertIn("mem-001", graph["nodes"]["memories"])
            mem = graph["nodes"]["memories"]["mem-001"]
            # Graph-only fields survive (unreconstructable from any scan)
            self.assertEqual(mem["source"], "execution")
            self.assertTrue(mem["resolved"])

    def test_memory_concepts_get_nodes_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent_dir(tmp)
            graph = build_graph(str(agent), existing_graph=_existing_graph_with_memory())

            # Concept node exists for a concept only the memory carries
            self.assertIn("graph-preserve-test", graph["nodes"]["concepts"])
            # And the concept_index maps it back to the memory
            self.assertIn("mem-001", graph["concept_index"]["graph-preserve-test"])

    def test_memory_edges_carried_with_referential_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent_dir(tmp)
            graph = build_graph(str(agent), existing_graph=_existing_graph_with_memory())

            pairs = {(e["from"], e["to"]) for e in graph["edges"]}
            self.assertIn(("mem-001", "TASK-01"), pairs)     # endpoint exists
            self.assertNotIn(("mem-001", "TASK-99"), pairs)  # endpoint gone -> dropped

    def test_no_existing_graph_keeps_current_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent_dir(tmp)
            graph = build_graph(str(agent))
            self.assertEqual(graph["nodes"]["memories"], {})

    def test_stats_count_preserved_memories(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = _make_agent_dir(tmp)
            graph = build_graph(str(agent), existing_graph=_existing_graph_with_memory())
            self.assertEqual(graph["stats"]["memory_count"], 1)


class TestBuilderCli(unittest.TestCase):
    """CLI preserves memories from --output by default; flag opts out."""

    def _run(self, tmp: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(Path(__file__).parent / "graph_builder.py"),
             "--agent-dir", str(tmp / ".agent"),
             "--output", str(tmp / ".agent" / "knowledge" / "graph.json"),
             *extra],
            capture_output=True, text=True,
        )

    def _setup(self, tmp: str) -> Path:
        root = Path(tmp)
        _make_agent_dir(tmp)
        out = root / ".agent" / "knowledge" / "graph.json"
        out.parent.mkdir(parents=True)
        out.write_text(json.dumps(_existing_graph_with_memory()))
        return root

    def test_cli_rebuild_preserves_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup(tmp)
            proc = self._run(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            graph = json.loads(
                (root / ".agent" / "knowledge" / "graph.json").read_text())
            self.assertIn("mem-001", graph["nodes"]["memories"])

    def test_cli_no_preserve_flag_wipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup(tmp)
            proc = self._run(root, "--no-preserve-memories")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            graph = json.loads(
                (root / ".agent" / "knowledge" / "graph.json").read_text())
            self.assertEqual(graph["nodes"]["memories"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
