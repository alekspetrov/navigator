#!/usr/bin/env python3
"""Tests for graph_maintenance.py integrity + decay logic (wp6 / TASK-47).

stdlib unittest, direct-import style. First Python coverage for nav-graph
maintenance: repair (dedup / dangling / confidence), health-check defect
counts, prune empty-key cleanup, and idempotent decay.
"""

import sys
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import create_empty_graph, add_node
from graph_maintenance import (
    find_duplicate_edges,
    find_dangling_edges,
    find_out_of_range_confidence,
    repair_graph,
    health_check,
    prune_memories,
    apply_decay,
    _read_decay_rate,
    DEFAULT_DECAY_RATE,
)


def _mem(graph, mem_id, confidence=0.8, concepts=None, last_validated="2026-01-01",
         last_decayed=None):
    data = {
        "type": "pattern",
        "summary": "x",
        "confidence": confidence,
        "concepts": concepts or [],
        "last_validated": last_validated,
    }
    if last_decayed:
        data["last_decayed"] = last_decayed
    return add_node(graph, "memories", mem_id, data)


def _two_task_graph():
    g = create_empty_graph()
    g = add_node(g, "tasks", "TASK-01", {"concepts": []})
    g = add_node(g, "tasks", "TASK-02", {"concepts": []})
    return g


class TestDetectors(unittest.TestCase):
    def test_find_duplicate_edges(self):
        g = _two_task_graph()
        g["edges"] = [
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},  # dup
            {"from": "TASK-02", "to": "TASK-01", "type": "relates-to"},  # distinct
        ]
        self.assertEqual(find_duplicate_edges(g), 1)

    def test_find_dangling_edges(self):
        g = _two_task_graph()
        g["edges"] = [
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},
            {"from": "TASK-01", "to": "GHOST", "type": "relates-to"},  # dangling
        ]
        dangling = find_dangling_edges(g)
        self.assertEqual(len(dangling), 1)
        self.assertEqual(dangling[0]["to"], "GHOST")

    def test_find_out_of_range_confidence(self):
        g = create_empty_graph()
        g = _mem(g, "mem-001", confidence=90.0)
        g = _mem(g, "mem-002", confidence=0.5)
        oor = find_out_of_range_confidence(g)
        self.assertEqual([m[0] for m in oor], ["mem-001"])


class TestRepair(unittest.TestCase):
    def _defective_graph(self):
        g = _two_task_graph()
        g["edges"] = [
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},  # dup
            {"from": "TASK-01", "to": "GHOST", "type": "relates-to"},    # dangling
        ]
        g = _mem(g, "mem-001", confidence=90.0)
        return g

    def test_repair_fixes_all_defects(self):
        g = self._defective_graph()
        summary = repair_graph(g)
        self.assertEqual(summary["duplicates_removed"], 1)
        self.assertEqual(summary["dangling_removed"], 1)
        self.assertEqual(summary["confidences_normalized"], 1)
        self.assertEqual(len(g["edges"]), 1)
        self.assertEqual(g["nodes"]["memories"]["mem-001"]["confidence"], 0.9)
        # No edge references an absent node id.
        node_ids = {nid for bucket in g["nodes"].values() for nid in bucket}
        for e in g["edges"]:
            self.assertIn(e["from"], node_ids)
            self.assertIn(e["to"], node_ids)

    def test_repair_is_idempotent(self):
        g = self._defective_graph()
        repair_graph(g)
        second = repair_graph(g)
        self.assertEqual(
            (second["duplicates_removed"], second["dangling_removed"],
             second["confidences_normalized"]),
            (0, 0, 0),
        )


class TestHealthCheck(unittest.TestCase):
    def test_health_reports_integrity_metrics(self):
        g = _two_task_graph()
        g["edges"] = [
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},
            {"from": "TASK-01", "to": "TASK-02", "type": "relates-to"},  # dup
            {"from": "TASK-01", "to": "GHOST", "type": "relates-to"},    # dangling
        ]
        g = _mem(g, "mem-001", confidence=90.0)
        h = health_check(g)
        self.assertEqual(h["duplicate_edges"], 1)
        self.assertEqual(h["dangling_edges"], 1)
        self.assertEqual(h["confidence_out_of_range"], 1)
        # Conflicts/staleness are advisory, not score-affecting issues.
        self.assertIn("advisory", h)

    def test_clean_graph_has_zero_defects(self):
        g = _two_task_graph()
        g["edges"] = [{"from": "TASK-01", "to": "TASK-02", "type": "relates-to"}]
        h = health_check(g)
        self.assertEqual(
            (h["duplicate_edges"], h["dangling_edges"], h["confidence_out_of_range"]),
            (0, 0, 0),
        )


class TestPrune(unittest.TestCase):
    def test_prune_removes_empty_concept_keys(self):
        g = create_empty_graph()
        g = _mem(g, "mem-001", confidence=0.1, concepts=["lonely"])
        result = prune_memories(g, threshold=0.3, dry_run=False)
        self.assertEqual(result["removed"], 1)
        self.assertNotIn("mem-001", g["nodes"]["memories"])
        # The sole member left -> the concept key must be gone, not left empty.
        self.assertNotIn("lonely", g["concept_index"])

    def test_prune_keeps_shared_concept(self):
        g = create_empty_graph()
        g = _mem(g, "mem-001", confidence=0.1, concepts=["shared"])
        g = _mem(g, "mem-002", confidence=0.9, concepts=["shared"])
        prune_memories(g, threshold=0.3, dry_run=False)
        self.assertIn("shared", g["concept_index"])
        self.assertEqual(g["concept_index"]["shared"], ["mem-002"])


class TestDecay(unittest.TestCase):
    def test_decay_is_idempotent_same_day(self):
        g = create_empty_graph()
        g = _mem(g, "mem-001", confidence=0.8, last_validated="2026-01-01")
        apply_decay(g, decay_rate=0.01, today=date(2026, 3, 1))
        first = g["nodes"]["memories"]["mem-001"]["confidence"]
        self.assertLess(first, 0.8)
        self.assertEqual(g["nodes"]["memories"]["mem-001"]["last_decayed"], "2026-03-01")
        # Second run on the SAME day must not decay further.
        apply_decay(g, decay_rate=0.01, today=date(2026, 3, 1))
        self.assertEqual(g["nodes"]["memories"]["mem-001"]["confidence"], first)

    def test_decay_accrues_on_a_later_day(self):
        g = create_empty_graph()
        g = _mem(g, "mem-001", confidence=0.8, last_validated="2026-01-01")
        apply_decay(g, decay_rate=0.01, today=date(2026, 3, 1))
        first = g["nodes"]["memories"]["mem-001"]["confidence"]
        apply_decay(g, decay_rate=0.01, today=date(2026, 4, 1))
        self.assertLess(g["nodes"]["memories"]["mem-001"]["confidence"], first)

    def test_decay_reads_rate_from_config_when_none(self):
        g = create_empty_graph()
        g = _mem(g, "mem-001", confidence=0.8, last_validated="2026-01-01")
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "cfg.json"
            cfg.write_text(json.dumps({"knowledge_graph": {"confidence_decay_rate": 0.5}}))
            apply_decay(g, decay_rate=None, config_path=str(cfg), today=date(2026, 3, 1))
        # High rate -> large drop (much lower than a 0.01 rate would give).
        self.assertLess(g["nodes"]["memories"]["mem-001"]["confidence"], 0.5)


class TestReadDecayRate(unittest.TestCase):
    def test_reads_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "cfg.json"
            cfg.write_text(json.dumps({"knowledge_graph": {"confidence_decay_rate": 0.05}}))
            self.assertEqual(_read_decay_rate(str(cfg)), 0.05)

    def test_missing_file_returns_default(self):
        self.assertEqual(_read_decay_rate("/no/such/file.json"), DEFAULT_DECAY_RATE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
