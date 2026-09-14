#!/usr/bin/env python3
"""Tests for report_to_graph.py (TASK-74) — bullet → memory mapping, dry-run ingest, CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_to_graph import build_findings, provenance_by_url, run
from research_run import init_run
from source_store import store_note

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


REPORT_WRAPPED = """# Report

## Key findings

- (pattern) All three engines ship WebGPU by default in at least one stable configuration as
  of late 2025, making cross-engine WebGPU a real target rather than a Chromium-only one
  [1][2].
- (pitfall) Short one [2]

## Sources

| n | id | title | url |
|---|---|---|---|
| 1 | 001 | One | https://e.com/1 |
| 2 | 002 | Two | https://e.com/2 |
"""


class TestBuildFindings(unittest.TestCase):
    def test_wrapped_bullet_keeps_cites_and_full_text(self):
        # writers wrap at ~90 cols; the cite lands on a continuation line (TASK-77)
        memories = build_findings(REPORT_WRAPPED, "t", "s")["memories"]
        self.assertEqual(len(memories), 2)
        self.assertEqual(memories[0]["evidence"], "https://e.com/1, https://e.com/2")
        self.assertTrue(memories[0]["summary"].endswith("rather than a Chromium-only one."))
        self.assertIn("as of late 2025", memories[0]["summary"])
        self.assertEqual(memories[1]["evidence"], "https://e.com/2")

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

    def test_provenance_tags_each_cited_url(self):
        prov = {"https://e.com/1": "fetched 2026-09-10, sha256 911574a1f5b0"}
        memories = build_findings(REPORT, "Ion traps", "ion-traps", prov)["memories"]
        self.assertEqual(memories[0]["evidence"],
                         "https://e.com/1 (fetched 2026-09-10, sha256 911574a1f5b0)")
        # untagged URL stays bare; tagged one keeps its tag in the same list
        self.assertEqual(
            memories[1]["evidence"],
            "https://e.com/1 (fetched 2026-09-10, sha256 911574a1f5b0), https://e.com/2")
        self.assertEqual(memories[2]["evidence"], "nav-deep-research run ion-traps")


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

    def test_provenance_read_from_local_source_notes(self):
        import hashlib
        body = "WebGPU is available in Chrome 113 and later."
        store_note(self.slug, "https://e.com/1", body, title="One", agent_dir=self.agent)
        prov = provenance_by_url(self.slug, self.agent)
        expected = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        self.assertIn("https://e.com/1", prov)
        self.assertTrue(prov["https://e.com/1"].startswith("fetched 20"))
        self.assertTrue(prov["https://e.com/1"].endswith(f"sha256 {expected}"))
        (self.dir / "report.md").write_text(REPORT, encoding="utf-8")
        out, code = run(self.slug, self.agent, str(self.graph), dry_run=True)
        self.assertEqual(code, 0)
        evidence = out["memories"][0]["evidence"]
        self.assertTrue(evidence.startswith("https://e.com/1 (fetched "))
        self.assertIn(f"sha256 {expected})", evidence)
        # source 2 has no note on disk → bare URL, no tag
        self.assertTrue(out["memories"][1]["evidence"].endswith(", https://e.com/2"))

    def test_no_notes_keeps_url_only_evidence(self):
        (self.dir / "report.md").write_text(REPORT, encoding="utf-8")
        out, _ = run(self.slug, self.agent, str(self.graph), dry_run=True)
        self.assertEqual(out["memories"][0]["evidence"], "https://e.com/1")

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
