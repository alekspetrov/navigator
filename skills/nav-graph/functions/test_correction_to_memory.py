#!/usr/bin/env python3
"""Tests for correction_to_memory.py synced-count accounting.

Covers the wp11/TASK-51 fix: check_for_new_corrections must count only
memories tagged source=='correction' (set at creation), not every memory
node and not a graph-wide edge string match.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from correction_to_memory import (
    sync_corrections_to_graph,
    check_for_new_corrections,
)
from graph_manager import create_empty_graph, save_graph, add_memory


class TestCorrectionSyncedCount(unittest.TestCase):
    """check_for_new_corrections reports the real synced count."""

    def setUp(self):
        # chdir into a temp dir so add_memory's backing-file writes
        # (base_dir='.agent/knowledge') land in the sandbox, not the repo.
        self._cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp()
        os.chdir(self._tmp)
        self.profile_path = "profile.json"
        self.graph_path = ".agent/knowledge/graph.json"

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_profile(self, n: int) -> int:
        corrections = [
            {
                "context": f"context {i}",
                "pattern": f"always do thing {i}",
                "corrected_to": f"do thing {i}",
                "confidence": "high",
            }
            for i in range(n)
        ]
        Path(self.profile_path).write_text(json.dumps({"corrections": corrections}))
        return n

    def test_synced_count_matches_added_memories(self):
        n = self._write_profile(3)
        result = sync_corrections_to_graph(self.profile_path, self.graph_path)
        self.assertEqual(result["synced"], n)

        check = check_for_new_corrections(self.profile_path, self.graph_path)
        self.assertEqual(check["synced_memories"], n)
        self.assertEqual(check["pending"], 0)

    def test_non_correction_memories_not_counted(self):
        # Seed a memory from a different origin (no 'source' field).
        graph = create_empty_graph()
        add_memory(graph, "pattern", "unrelated memory", ["general"],
                   create_file=False)
        save_graph(self.graph_path, graph)

        n = self._write_profile(2)
        sync_corrections_to_graph(self.profile_path, self.graph_path)

        check = check_for_new_corrections(self.profile_path, self.graph_path)
        # The seeded non-correction memory is excluded; only the 2 tagged
        # correction memories count.
        self.assertEqual(check["synced_memories"], n)
        self.assertEqual(check["pending"], 0)

    def test_empty_graph_reports_zero(self):
        self._write_profile(0)
        check = check_for_new_corrections(self.profile_path, self.graph_path)
        self.assertEqual(check["synced_memories"], 0)
        self.assertEqual(check["pending"], 0)


if __name__ == "__main__":
    unittest.main()
