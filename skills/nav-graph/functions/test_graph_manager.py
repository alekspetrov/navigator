#!/usr/bin/env python3
"""Tests for graph_manager.py (stdlib unittest, direct-import style)."""

import sys
import json
import tempfile
import unittest
from pathlib import Path

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
import graph_manager
from graph_manager import (
    load_graph,
    save_graph,
    create_empty_graph,
    add_node,
    remove_node,
    add_edge,
    add_memory,
    query_by_concept,
    format_query_results,
    _clamp_confidence,
)

EMPTY_GRAPH_KEYS = {
    "version",
    "last_updated",
    "stats",
    "nodes",
    "edges",
    "concept_index",
}

EMPTY_NODE_BUCKETS = {
    "tasks",
    "system",
    "sops",
    "markers",
    "concepts",
    "memories",
    "files",
}


class TestLoadGraph(unittest.TestCase):
    """Tests for load_graph resilience."""

    def test_missing_path_returns_empty_graph(self):
        """load_graph on a missing path returns the empty-graph structure."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist.json"
            graph = load_graph(str(missing))

            self.assertEqual(set(graph.keys()), EMPTY_GRAPH_KEYS)
            self.assertEqual(set(graph["nodes"].keys()), EMPTY_NODE_BUCKETS)
            self.assertEqual(graph["edges"], [])
            self.assertEqual(graph["concept_index"], {})

    def test_invalid_json_returns_empty_graph_no_raise(self):
        """load_graph on invalid JSON returns the empty-graph structure, no raise."""
        with tempfile.TemporaryDirectory() as tmp:
            corrupt = Path(tmp) / "corrupt.json"
            corrupt.write_text("{not json")

            # Must NOT raise.
            graph = load_graph(str(corrupt))

            self.assertEqual(set(graph.keys()), EMPTY_GRAPH_KEYS)
            self.assertEqual(set(graph["nodes"].keys()), EMPTY_NODE_BUCKETS)
            self.assertEqual(graph["edges"], [])
            self.assertEqual(graph["concept_index"], {})

    def test_valid_file_returns_contents(self):
        """load_graph on a valid graph file returns its contents."""
        with tempfile.TemporaryDirectory() as tmp:
            valid = Path(tmp) / "graph.json"
            payload = {
                "version": "1.0.0",
                "last_updated": "2026-01-01T00:00:00Z",
                "stats": {"total_nodes": 1, "total_edges": 0, "memory_count": 0},
                "nodes": {
                    "tasks": {"TASK-01": {"title": "Example", "concepts": ["auth"]}},
                    "system": {},
                    "sops": {},
                    "markers": {},
                    "concepts": {},
                    "memories": {},
                    "files": {},
                },
                "edges": [],
                "concept_index": {"auth": ["TASK-01"]},
            }
            valid.write_text(json.dumps(payload))

            graph = load_graph(str(valid))

            self.assertEqual(graph, payload)
            self.assertIn("TASK-01", graph["nodes"]["tasks"])
            self.assertEqual(graph["concept_index"]["auth"], ["TASK-01"])


class TestSaveLoadRoundTrip(unittest.TestCase):
    """Tests for save_graph -> load_graph round-trip."""

    def test_round_trip_preserves_nodes(self):
        """save_graph then load_graph preserves nodes via a tempfile."""
        with tempfile.TemporaryDirectory() as tmp:
            graph_path = Path(tmp) / "nested" / "graph.json"

            graph = create_empty_graph()
            graph = add_node(
                graph, "tasks", "TASK-99",
                {"title": "Round trip", "concepts": ["roundtrip"]},
            )

            self.assertTrue(save_graph(str(graph_path), graph))
            self.assertTrue(graph_path.exists())

            reloaded = load_graph(str(graph_path))

            self.assertIn("TASK-99", reloaded["nodes"]["tasks"])
            self.assertEqual(
                reloaded["nodes"]["tasks"]["TASK-99"]["title"], "Round trip"
            )
            self.assertEqual(reloaded["concept_index"]["roundtrip"], ["TASK-99"])
            # save_graph recomputes stats.
            self.assertEqual(reloaded["stats"]["total_nodes"], 1)


class TestAddNode(unittest.TestCase):
    """Tests for add_node and concept_index consistency."""

    def test_add_node_stores_node_and_indexes_concepts(self):
        """add_node stores the node and updates the concept index."""
        graph = create_empty_graph()
        graph = add_node(
            graph, "tasks", "TASK-01",
            {"title": "Auth work", "concepts": ["authentication", "security"]},
        )

        self.assertIn("TASK-01", graph["nodes"]["tasks"])
        self.assertEqual(graph["concept_index"]["authentication"], ["TASK-01"])
        self.assertEqual(graph["concept_index"]["security"], ["TASK-01"])

    def test_add_node_unknown_type_creates_bucket(self):
        """add_node with a new node_type creates the bucket."""
        graph = create_empty_graph()
        graph = add_node(graph, "custom", "X-1", {"concepts": []})

        self.assertIn("custom", graph["nodes"])
        self.assertIn("X-1", graph["nodes"]["custom"])

    def test_add_node_does_not_duplicate_concept_membership(self):
        """Re-adding the same node id under a concept does not duplicate it."""
        graph = create_empty_graph()
        graph = add_node(graph, "tasks", "TASK-01", {"concepts": ["auth"]})
        # Re-add the same node id (same concept) -> index entry not duplicated.
        graph = add_node(graph, "tasks", "TASK-01", {"concepts": ["auth"]})

        self.assertEqual(graph["concept_index"]["auth"], ["TASK-01"])

    def test_add_node_multiple_nodes_share_concept(self):
        """Two nodes sharing a concept both appear under that concept."""
        graph = create_empty_graph()
        graph = add_node(graph, "tasks", "TASK-01", {"concepts": ["auth"]})
        graph = add_node(graph, "tasks", "TASK-02", {"concepts": ["auth"]})

        self.assertEqual(graph["concept_index"]["auth"], ["TASK-01", "TASK-02"])


class TestRemoveNode(unittest.TestCase):
    """Tests for remove_node and index/edge cleanup."""

    def test_remove_node_cleans_concept_index(self):
        """remove_node deletes the node and prunes the concept index entry."""
        graph = create_empty_graph()
        graph = add_node(graph, "tasks", "TASK-01", {"concepts": ["auth"]})

        graph = remove_node(graph, "tasks", "TASK-01")

        self.assertNotIn("TASK-01", graph["nodes"]["tasks"])
        # Last node for the concept removed -> empty concept entry is deleted.
        self.assertNotIn("auth", graph["concept_index"])

    def test_remove_node_keeps_other_index_members(self):
        """remove_node leaves co-members of a shared concept intact."""
        graph = create_empty_graph()
        graph = add_node(graph, "tasks", "TASK-01", {"concepts": ["auth"]})
        graph = add_node(graph, "tasks", "TASK-02", {"concepts": ["auth"]})

        graph = remove_node(graph, "tasks", "TASK-01")

        self.assertIn("auth", graph["concept_index"])
        self.assertEqual(graph["concept_index"]["auth"], ["TASK-02"])

    def test_remove_node_removes_involving_edges(self):
        """remove_node drops edges that reference the removed node."""
        graph = create_empty_graph()
        graph = add_node(graph, "tasks", "TASK-01", {"concepts": []})
        graph = add_node(graph, "tasks", "TASK-02", {"concepts": []})
        graph = add_edge(graph, "TASK-01", "TASK-02", "relates-to")

        graph = remove_node(graph, "tasks", "TASK-01")

        self.assertEqual(graph["edges"], [])


class TestAddEdge(unittest.TestCase):
    """Tests for add_edge dedup behavior."""

    def test_add_edge_appends(self):
        """add_edge appends a new edge with from/to/type."""
        graph = create_empty_graph()
        graph = add_edge(graph, "A", "B", "relates-to")

        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(
            graph["edges"][0],
            {"from": "A", "to": "B", "type": "relates-to"},
        )

    def test_add_edge_dedup_same_edge_twice(self):
        """Adding the same (from, to, type) edge twice does not duplicate it."""
        graph = create_empty_graph()
        graph = add_edge(graph, "A", "B", "relates-to")
        graph = add_edge(graph, "A", "B", "relates-to")

        self.assertEqual(len(graph["edges"]), 1)

    def test_add_edge_different_type_not_deduped(self):
        """A different edge type between the same nodes is a distinct edge."""
        graph = create_empty_graph()
        graph = add_edge(graph, "A", "B", "relates-to")
        graph = add_edge(graph, "A", "B", "depends-on")

        self.assertEqual(len(graph["edges"]), 2)

    def test_add_edge_weight_stored_only_when_non_default(self):
        """weight is included only when it differs from the default 1.0."""
        graph = create_empty_graph()
        graph = add_edge(graph, "A", "B", "relates-to")
        graph = add_edge(graph, "C", "D", "relates-to", weight=0.5)

        self.assertNotIn("weight", graph["edges"][0])
        self.assertEqual(graph["edges"][1]["weight"], 0.5)


class TestQueryByConcept(unittest.TestCase):
    """query_by_concept must surface markers and concepts, not silently drop them."""

    def test_markers_are_returned(self):
        graph = create_empty_graph()
        graph = add_node(
            graph, "markers", "marker-1",
            {"title": "My Marker", "concepts": ["auth"]},
        )
        results = query_by_concept(graph, "auth")
        ids = [m["id"] for m in results["markers"]]
        self.assertIn("marker-1", ids)

    def test_markers_render_in_output(self):
        graph = create_empty_graph()
        graph = add_node(
            graph, "markers", "marker-1",
            {"title": "Release Marker", "concepts": ["auth"]},
        )
        rendered = format_query_results(query_by_concept(graph, "auth"))
        self.assertIn("MARKERS", rendered)
        self.assertIn("Release Marker", rendered)

    def test_tasks_still_returned(self):
        graph = create_empty_graph()
        graph = add_node(
            graph, "tasks", "TASK-01", {"title": "T", "concepts": ["auth"]},
        )
        results = query_by_concept(graph, "auth")
        self.assertEqual([t["id"] for t in results["tasks"]], ["TASK-01"])


class TestConfidenceClamp(unittest.TestCase):
    """Confidence must be coerced to [0,1] on input (mem-026 was 90.0)."""

    def test_clamp_bounds(self):
        self.assertEqual(_clamp_confidence(90.0), 1.0)
        self.assertEqual(_clamp_confidence(-0.5), 0.0)
        self.assertEqual(_clamp_confidence(0.7), 0.7)

    def test_clamp_non_numeric_falls_back(self):
        self.assertEqual(_clamp_confidence("oops"), 0.8)

    def test_add_memory_clamps_out_of_range(self):
        graph = create_empty_graph()
        mem_id = add_memory(
            graph, "pattern", "summary", ["auth"],
            confidence=5.0, create_file=False,
        )
        self.assertLessEqual(graph["nodes"]["memories"][mem_id]["confidence"], 1.0)


class TestAddMemoryFailLoud(unittest.TestCase):
    """v6.17.0: file is written BEFORE the node; failures propagate."""

    def test_file_written_before_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = create_empty_graph()
            mem_id = add_memory(
                graph, "pattern", "ordering test", ["auth"],
                base_dir=tmp,
            )
            path = Path(tmp) / "memories" / "patterns" / f"{mem_id}.md"
            self.assertTrue(path.exists())
            self.assertIn(mem_id, graph["nodes"]["memories"])

    def test_file_exists_propagates_and_graph_unmutated(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "memories" / "patterns" / "mem-001.md"
            target.parent.mkdir(parents=True)
            target.write_text("pre-existing")

            graph = create_empty_graph()
            with self.assertRaises(FileExistsError):
                add_memory(
                    graph, "pattern", "collision", ["auth"],
                    base_dir=tmp, memory_id="mem-001",
                )
            # No orphan node, no edges, no concept index pollution
            self.assertEqual(graph["nodes"]["memories"], {})
            self.assertEqual(graph["edges"], [])
            self.assertEqual(graph["concept_index"], {})

    def test_oserror_propagates_and_graph_unmutated(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Make the memories root a FILE so mkdir(parents=True) fails
            (Path(tmp) / "memories").write_text("not a dir")
            graph = create_empty_graph()
            with self.assertRaises(OSError):
                add_memory(graph, "pattern", "io failure", ["auth"], base_dir=tmp)
            self.assertEqual(graph["nodes"]["memories"], {})


class TestValidateConcepts(unittest.TestCase):
    """v6.17.0 write-time concept validation."""

    def _graph_with_vocab(self):
        graph = create_empty_graph()
        graph["nodes"]["concepts"]["authentication"] = {
            "name": "Authentication", "aliases": ["login"], "domain": "security",
        }
        graph["nodes"]["concepts"]["database"] = {
            "name": "Database", "aliases": [], "domain": "data",
        }
        return graph

    def test_known_concepts_pass(self):
        graph = self._graph_with_vocab()
        canonical, unknown = graph_manager.validate_concepts(
            graph, ["authentication", "database"])
        self.assertEqual(canonical, ["authentication", "database"])
        self.assertEqual(unknown, [])

    def test_alias_resolves_to_canonical(self):
        graph = self._graph_with_vocab()
        canonical, unknown = graph_manager.validate_concepts(graph, ["login"])
        self.assertEqual(canonical, ["authentication"])
        self.assertEqual(unknown, [])

    def test_builtin_abbreviation_resolves(self):
        # 'auth' maps via the abbreviations table but only counts as known
        # when the canonical target exists in the graph
        graph = self._graph_with_vocab()
        graph["concept_index"]["authentication"] = ["mem-001"]
        canonical, unknown = graph_manager.validate_concepts(graph, ["auth"])
        self.assertEqual(canonical, ["authentication"])
        self.assertEqual(unknown, [])

    def test_unknown_concept_rejected(self):
        graph = self._graph_with_vocab()
        canonical, unknown = graph_manager.validate_concepts(
            graph, ["authentication", "totally-freeform-tag"])
        self.assertEqual(canonical, ["authentication"])
        self.assertEqual(unknown, ["totally-freeform-tag"])

    def test_empty_vocabulary_skips_validation(self):
        graph = create_empty_graph()
        canonical, unknown = graph_manager.validate_concepts(
            graph, ["anything", "goes"])
        self.assertEqual(canonical, ["anything", "goes"])
        self.assertEqual(unknown, [])

    def test_register_concept_creates_fallback_shape(self):
        graph = create_empty_graph()
        graph_manager.register_concept(graph, "New-Domain")
        node = graph["nodes"]["concepts"]["new-domain"]
        self.assertEqual(node["name"], "New-Domain".lower().title())
        self.assertEqual(node["aliases"], [])
        self.assertEqual(node["domain"], "general")


class TestCliAddMemoryRollback(unittest.TestCase):
    """CLI add-memory rolls back the backing file when save_graph fails."""

    def test_save_failure_unlinks_file(self):
        import subprocess
        import os
        with tempfile.TemporaryDirectory() as tmp:
            # graph path inside a directory we then make read-only, so
            # save_graph fails AFTER add_memory wrote the .md under CWD
            ro_dir = Path(tmp) / "ro"
            ro_dir.mkdir()
            graph_path = ro_dir / "graph.json"
            os.chmod(ro_dir, 0o500)
            try:
                proc = subprocess.run(
                    [sys.executable, str(Path(__file__).parent / "graph_manager.py"),
                     "--action", "add-memory",
                     "--graph-path", str(graph_path),
                     "--memory-type", "pattern",
                     "--summary", "rollback test",
                     "--concepts", "rollback-test-concept"],
                    capture_output=True, text=True, cwd=tmp,
                )
            finally:
                os.chmod(ro_dir, 0o700)
            self.assertNotEqual(proc.returncode, 0)
            # The .md written under {cwd}/.agent/knowledge must be gone
            leftovers = list((Path(tmp) / ".agent").rglob("*.md")) \
                if (Path(tmp) / ".agent").exists() else []
            self.assertEqual(leftovers, [])
            self.assertIn("rolled back", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
