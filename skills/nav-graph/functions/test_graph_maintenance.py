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
    find_broken_file_links,
    find_unindexed_memory_files,
    find_invalid_concept_refs,
    reconcile,
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


def _make_memory_tree(root: Path) -> Path:
    """Standard memory tree: {root}/.agent/knowledge/memories/{type}s/."""
    base = root / ".agent" / "knowledge" / "memories"
    (base / "patterns").mkdir(parents=True)
    (base / "pitfalls" / "resolved").mkdir(parents=True)
    return base


class TestFindBrokenFileLinks(unittest.TestCase):
    def test_navigator_and_pilot_styles_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = _make_memory_tree(root)
            (base / "patterns" / "mem-001.md").write_text("x")
            (base / "pitfalls" / "bug_foo.md").write_text("x")

            g = create_empty_graph()
            # Navigator style: path relative to base_dir
            g = add_node(g, "memories", "mem-001",
                         {"path": "memories/patterns/mem-001.md", "concepts": []})
            # Pilot style: 'file' key, root-relative
            g = add_node(g, "memories", "mem-002",
                         {"file": ".agent/knowledge/memories/pitfalls/bug_foo.md",
                          "concepts": []})
            self.assertEqual(find_broken_file_links(g, str(root)), [])

    def test_nonexistent_flagged_no_path_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_memory_tree(root)
            g = create_empty_graph()
            g = add_node(g, "memories", "mem-001",
                         {"path": "memories/patterns/gone.md", "concepts": []})
            # Summary-only node (pilot has 15 of these) — legal, not broken
            g = add_node(g, "memories", "mem-002",
                         {"summary": "no file at all", "concepts": []})
            broken = find_broken_file_links(g, str(root))
            self.assertEqual([b["id"] for b in broken], ["mem-001"])


class TestFindUnindexedMemoryFiles(unittest.TestCase):
    def test_descriptive_slugs_detected_readme_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = _make_memory_tree(root)
            (base / "patterns" / "pattern_squash_merge.md").write_text("x")
            (base / "patterns" / "README.md").write_text("index")
            (base / "patterns" / "mem-001.md").write_text("x")

            g = create_empty_graph()
            g = add_node(g, "memories", "mem-001",
                         {"path": "memories/patterns/mem-001.md", "concepts": []})

            unindexed = find_unindexed_memory_files(g, str(root))
            self.assertEqual(len(unindexed), 1)
            self.assertIn("pattern_squash_merge.md", unindexed[0])

    def test_missing_memories_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(find_unindexed_memory_files(create_empty_graph(), tmp), [])


class TestFindInvalidConceptRefs(unittest.TestCase):
    def _vocab_graph(self):
        g = create_empty_graph()
        g["nodes"]["concepts"]["database"] = {
            "name": "Database", "aliases": ["db-layer"], "domain": "data"}
        return g

    def test_freeform_flagged_alias_not(self):
        g = self._vocab_graph()
        g = add_node(g, "memories", "mem-001",
                     {"concepts": ["database", "db-layer", "totally-freeform"]})
        invalid = find_invalid_concept_refs(g)
        self.assertEqual(invalid, [("mem-001", "totally-freeform")])

    def test_empty_vocabulary_returns_empty(self):
        g = create_empty_graph()
        g = add_node(g, "memories", "mem-001", {"concepts": ["anything"]})
        self.assertEqual(find_invalid_concept_refs(g), [])

    def test_checked_across_all_buckets(self):
        g = self._vocab_graph()
        g = add_node(g, "tasks", "TASK-01", {"concepts": ["ghost-tag"]})
        invalid = find_invalid_concept_refs(g)
        self.assertEqual(invalid, [("TASK-01", "ghost-tag")])


class TestReconcile(unittest.TestCase):
    def _drifted_repo(self, tmp: str):
        """One indexed file, one Navigator-format orphan, one pilot-format
        orphan under resolved/."""
        root = Path(tmp)
        base = _make_memory_tree(root)
        (base / "patterns" / "mem-001.md").write_text("x")
        (base / "patterns" / "pattern_deploy_order.md").write_text(
            "# Pattern: Deploy gateway before adapters\n\nBody.\n\n---\n"
            "**Confidence**: 90%\n**Concepts**: deployment, gateway\n"
        )
        (base / "pitfalls" / "resolved" / "bug_old_issue.md").write_text(
            "---\nname: old-issue\ndescription: Poller stopped silently\n"
            "type: pitfall\n---\n\nBody.\n"
        )
        g = create_empty_graph()
        g = add_node(g, "memories", "mem-001",
                     {"path": "memories/patterns/mem-001.md", "concepts": []})
        return root, g

    def test_dry_run_reports_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, g = self._drifted_repo(tmp)
            before = json.dumps(g, sort_keys=True)
            report = reconcile(g, root=str(root))
            self.assertEqual(len(report["unindexed_files"]), 2)
            self.assertEqual(report["registered"], [])
            self.assertEqual(json.dumps(g, sort_keys=True), before)

    def test_execute_registers_both_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, g = self._drifted_repo(tmp)
            report = reconcile(g, root=str(root), execute=True)
            self.assertEqual(len(report["registered"]), 2)
            self.assertEqual(report["errors"], [])

            mems = g["nodes"]["memories"]
            by_summary = {m.get("summary"): m for m in mems.values()}
            # Navigator-format orphan: heading title, footer confidence/concepts
            nav = by_summary["Deploy gateway before adapters"]
            self.assertEqual(nav["type"], "pattern")
            self.assertEqual(nav["confidence"], 0.9)
            self.assertEqual(nav["concepts"], ["deployment", "gateway"])
            self.assertEqual(nav["source"], "reconcile")
            # Its concepts were registered as vocabulary
            self.assertIn("deployment", g["nodes"]["concepts"])
            # Pilot-format orphan: frontmatter description, resolved/ parent
            pilot = by_summary["Poller stopped silently"]
            self.assertEqual(pilot["type"], "pitfall")
            self.assertTrue(pilot["resolved"])
            self.assertEqual(pilot["confidence"], 0.5)  # conservative default

    def test_execute_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, g = self._drifted_repo(tmp)
            reconcile(g, root=str(root), execute=True)
            second = reconcile(g, root=str(root), execute=True)
            self.assertEqual(second["unindexed_files"], [])
            self.assertEqual(second["registered"], [])


class TestRepairConceptIndex(unittest.TestCase):
    def test_orphaned_index_entries_dropped(self):
        g = _two_task_graph()
        g["concept_index"]["auth"] = ["TASK-01", "GHOST-NODE"]
        g["concept_index"]["dead"] = ["GHOST-ONLY"]
        summary = repair_graph(g)
        self.assertEqual(summary["index_entries_pruned"], 2)
        self.assertEqual(g["concept_index"]["auth"], ["TASK-01"])
        self.assertNotIn("dead", g["concept_index"])


class TestPruneMovesFiles(unittest.TestCase):
    def test_pruned_backing_file_moved_to_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = _make_memory_tree(root)
            f = base / "patterns" / "mem-001.md"
            f.write_text("low value")

            g = create_empty_graph()
            g = add_node(g, "memories", "mem-001",
                         {"path": "memories/patterns/mem-001.md",
                          "confidence": 0.1, "concepts": []})
            result = prune_memories(g, threshold=0.3, dry_run=False, root=str(root))
            self.assertEqual(result["files_moved_to_resolved"], 1)
            self.assertFalse(f.exists())
            self.assertTrue((base / "patterns" / "resolved" / "mem-001.md").exists())
            # reconcile must NOT re-register... unless intentionally: the file
            # now sits under resolved/ and is unindexed. Verify a follow-up
            # reconcile registers it as resolved (not as live knowledge).
            report = reconcile(g, root=str(root), execute=True)
            if report["registered"]:
                new_id = report["registered"][0]["id"]
                self.assertTrue(g["nodes"]["memories"][new_id].get("resolved"))


class TestHealthCheckDrift(unittest.TestCase):
    def test_new_keys_present_and_score_affected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = _make_memory_tree(root)
            (base / "patterns" / "orphan_file.md").write_text("x")

            g = create_empty_graph()
            g = add_node(g, "memories", "mem-001",
                         {"path": "memories/patterns/gone.md", "concepts": []})
            h = health_check(g, str(root))
            self.assertEqual(h["broken_file_links"], 1)
            self.assertEqual(h["unindexed_memory_files"], 1)
            self.assertIn("invalid_concept_refs", h)
            self.assertTrue(any("reconcile" in i for i in h["issues"]))

    def test_backward_compatible_single_arg_call(self):
        # Pre-v6.17.0 signature must keep working
        h = health_check(_two_task_graph())
        self.assertIn("health_score", h)
        self.assertIn("broken_file_links", h)


if __name__ == "__main__":
    unittest.main(verbosity=2)
