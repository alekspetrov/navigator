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


if __name__ == "__main__":
    unittest.main(verbosity=2)
