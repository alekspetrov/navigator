#!/usr/bin/env python3
"""Tests for memory_recall.py (v6.17.0) — ranking, schema compat, CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import create_empty_graph, add_node
from memory_recall import collect_auto_concepts, rank_memories, \
    render_compact, render_markdown

RECALL = Path(__file__).parent / "memory_recall.py"


def _graph():
    g = create_empty_graph()
    add_node(g, "memories", "mem-001",
             {"type": "pitfall", "summary": "Auth breaks session tests",
              "confidence": 0.9, "concepts": ["authentication", "testing"],
              "path": "memories/pitfalls/mem-001.md"})
    add_node(g, "memories", "mem-002",
             {"type": "pattern", "summary": "Run unit before integration",
              "confidence": 0.8, "concepts": ["testing"]})
    add_node(g, "memories", "mem-003",
             {"type": "decision", "summary": "Superseded decision",
              "confidence": 0.95, "concepts": ["authentication", "testing"],
              "resolved": True})
    add_node(g, "memories", "mem-004",
             {"type": "learning", "summary": "Unrelated deploy note",
              "confidence": 0.99, "concepts": ["deployment"]})
    return g


class TestRanking(unittest.TestCase):
    def test_overlap_then_confidence_ordering(self):
        ranked = rank_memories(_graph(), ["authentication", "testing"])
        # mem-001 overlaps 2 concepts; mem-002 overlaps 1. mem-003 resolved,
        # mem-004 zero overlap — both excluded.
        self.assertEqual([m["id"] for m in ranked], ["mem-001", "mem-002"])
        self.assertEqual(ranked[0]["score"], 2)

    def test_resolved_and_superseded_excluded(self):
        g = _graph()
        g["nodes"]["memories"]["mem-002"]["superseded_by"] = "mem-001"
        ranked = rank_memories(g, ["testing"])
        self.assertEqual([m["id"] for m in ranked], ["mem-001"])

    def test_min_confidence_and_limit(self):
        ranked = rank_memories(_graph(), ["testing"], min_confidence=0.85)
        self.assertEqual([m["id"] for m in ranked], ["mem-001"])
        ranked = rank_memories(_graph(), ["testing"], limit=1)
        self.assertEqual(len(ranked), 1)

    def test_alias_resolution_of_targets(self):
        g = _graph()
        g["nodes"]["concepts"]["authentication"] = {
            "name": "Authentication", "aliases": ["login"], "domain": "sec"}
        ranked = rank_memories(g, ["login"])
        self.assertEqual(ranked[0]["id"], "mem-001")

    def test_empty_targets_return_empty(self):
        self.assertEqual(rank_memories(_graph(), []), [])
        self.assertEqual(rank_memories(_graph(), ["", "  "]), [])


class TestPilotSchemaCompat(unittest.TestCase):
    """Consumer graph fixture: file key, no concept_index, no-path node,
    top-level 'updated'."""

    def _pilot_graph(self):
        return {
            "version": "1.0.0",
            "updated": "2026-07-05",  # not last_updated
            "nodes": {
                "concepts": {},
                "tasks": {"TASK-380": {"title": "t", "status": "open",
                                       "concepts": ["executor"]}},
                "memories": {
                    "mem-010": {"type": "pitfall",
                                "summary": "Executor SHA harvest bug",
                                "confidence": 0.85,
                                "concepts": ["executor", "git-operations"],
                                "file": ".agent/knowledge/memories/pitfalls/bug_x.md"},
                    "mem-011": {"type": "learning",
                                "summary": "Summary-only node",
                                "confidence": 0.7,
                                "concepts": ["executor"]},
                    "mem-012": {"type": "pitfall", "summary": "Archived",
                                "confidence": 0.9,
                                "concepts": ["executor"], "resolved": True},
                },
            },
            "edges": [],
            # NOTE: no concept_index key at all
        }

    def test_ranks_without_concept_index(self):
        ranked = rank_memories(self._pilot_graph(), ["executor"])
        self.assertEqual([m["id"] for m in ranked], ["mem-010", "mem-011"])

    def test_markdown_render_uses_file_key(self):
        ranked = rank_memories(self._pilot_graph(), ["executor"])
        md = render_markdown(ranked)
        self.assertIn("bug_x.md", md)          # file: ref surfaced
        self.assertIn("mem-011", md)           # no-path node still renders

    def test_auto_concepts_from_open_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            concepts = collect_auto_concepts(self._pilot_graph(), Path(tmp))
            self.assertEqual(concepts, ["executor"])


class TestAutoConcepts(unittest.TestCase):
    def test_completed_tasks_excluded_marker_included(self):
        g = create_empty_graph()
        add_node(g, "tasks", "TASK-01",
                 {"status": "completed", "concepts": ["done-topic"]})
        add_node(g, "tasks", "TASK-02",
                 {"status": "in-progress", "concepts": ["live-topic"]})
        add_node(g, "markers", "2026-07-06_auth-work",
                 {"concepts": ["marker-topic"]})

        with tempfile.TemporaryDirectory() as tmp:
            agent = Path(tmp)
            (agent / ".context-markers").mkdir()
            (agent / ".context-markers" / ".active").write_text(
                "2026-07-06_auth-work.md")
            concepts = collect_auto_concepts(g, agent)

        self.assertIn("live-topic", concepts)
        self.assertIn("marker-topic", concepts)
        self.assertNotIn("done-topic", concepts)

    def test_no_marker_file_no_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                collect_auto_concepts(create_empty_graph(), Path(tmp)), [])


class TestRenderers(unittest.TestCase):
    def test_compact_format(self):
        ranked = rank_memories(_graph(), ["authentication"])
        out = render_compact(ranked)
        self.assertIn('- PITFALL: "Auth breaks session tests" (90%)', out)


class TestCli(unittest.TestCase):
    def _run(self, *argv, cwd=None):
        return subprocess.run([sys.executable, str(RECALL), *argv],
                              capture_output=True, text=True, cwd=cwd)

    def test_missing_graph_silent_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run("--concepts", "anything",
                             "--graph-path", f"{tmp}/nope.json")
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout, "")

    def test_no_matches_silent_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            gp = Path(tmp) / "graph.json"
            gp.write_text(json.dumps(_graph()))
            proc = self._run("--concepts", "nonexistent-topic",
                             "--graph-path", str(gp))
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout, "")

    def test_concepts_and_auto_mutually_exclusive(self):
        proc = self._run("--concepts", "a", "--auto")
        self.assertEqual(proc.returncode, 1)
        proc = self._run()
        self.assertEqual(proc.returncode, 1)

    def test_json_format_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            gp = Path(tmp) / "graph.json"
            gp.write_text(json.dumps(_graph()))
            proc = self._run("--concepts", "testing", "--format", "json",
                             "--graph-path", str(gp))
            data = json.loads(proc.stdout)
            self.assertEqual(data[0]["id"], "mem-001")
            self.assertEqual(
                set(data[0]),
                {"id", "type", "summary", "confidence", "score", "file"})

    def test_auto_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = Path(tmp) / ".agent"
            (agent / "knowledge").mkdir(parents=True)
            g = _graph()
            add_node(g, "tasks", "TASK-01",
                     {"status": "open", "concepts": ["authentication"]})
            (agent / "knowledge" / "graph.json").write_text(json.dumps(g))
            proc = self._run("--auto", "--agent-dir", str(agent),
                             "--graph-path", str(agent / "knowledge" / "graph.json"),
                             "--limit", "3")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Auth breaks session tests", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
