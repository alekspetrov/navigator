#!/usr/bin/env python3
"""Tests for report_to_graph.py (TASK-74) — bullet → memory mapping, dry-run ingest, CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_to_graph import build_findings, run
from research_run import init_run

SCRIPT = Path(__file__).parent / "report_to_graph.py"

REPORT = """# Report

## Summary

Text [1] and [2].

## Key findings

- (pattern) Ion traps use laser cooling [1]
- (pitfall) Heating limits depth [1][2]
- (learning) Unsourced claim
- plain bullet is ignored

## Sources

| n | id | title | url |
|---|---|---|---|
| 1 | 001 | One | https://e.com/1 |
| 2 | 002 | Two | https://e.com/2 |
"""


class TestBuildFindings(unittest.TestCase):
    def test_maps_cites_to_urls_and_defaults(self):
        findings = build_findings(REPORT, "Ion traps", "ion-traps")
        self.assertEqual(findings["topic"], "Ion traps")
        self.assertEqual(findings["files_sampled"], 2)
        memories = findings["memories"]
        self.assertEqual(len(memories), 3)
        self.assertEqual(memories[0]["type"], "pattern")
        self.assertEqual(memories[0]["summary"], "Ion traps use laser cooling")
        self.assertEqual(memories[0]["evidence"], "https://e.com/1")
        self.assertEqual(memories[1]["evidence"], "https://e.com/1, https://e.com/2")
        self.assertEqual(memories[2]["evidence"], "nav-deep-research run ion-traps")
        self.assertTrue(all(m["confidence"] == 0.7 for m in memories))


class TestRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agent = str(self.root / ".agent")
        out = init_run("Ion trap gate fidelity", self.agent, str(self.root))
        self.slug, self.dir = out["slug"], Path(out["dir"])
        self.graph = self.root / "graph.json"
        self.graph.write_text(json.dumps({
            "version": "1.0.0", "nodes": [], "edges": [],
            "metadata": {"last_updated": "2026-01-01T00:00:00Z"}}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_report_exit_1(self):
        out, code = run(self.slug, self.agent, str(self.graph), dry_run=True)
        self.assertEqual(code, 1)
        self.assertIn("error", out)

    def test_dry_run_reports_memories_without_writing(self):
        (self.dir / "report.md").write_text(REPORT)
        before = self.graph.read_text()
        out, code = run(self.slug, self.agent, str(self.graph), dry_run=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["topic"], "Ion trap gate fidelity")
        self.assertEqual(len(out["memories"]), 3)
        self.assertEqual(out["ingest"].get("errors"), [])
        self.assertEqual(self.graph.read_text(), before)
        self.assertFalse((self.dir / "findings" / "graph-ingest.json").exists())

    def test_cli_dry_run(self):
        (self.dir / "report.md").write_text(REPORT)
        proc = subprocess.run([sys.executable, str(SCRIPT), "--run", self.slug, "--agent-dir",
                               self.agent, "--graph-path", str(self.graph), "--dry-run"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(json.loads(proc.stdout)["memories"]), 3)


if __name__ == "__main__":
    unittest.main()
