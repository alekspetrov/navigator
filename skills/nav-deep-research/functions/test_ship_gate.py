#!/usr/bin/env python3
"""Tests for ship_gate.py + report_parse.py (TASK-74) — every failure mode has a fixture."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_parse import body_citations, citation_ranges, key_findings, sources_table
from research_run import init_run, set_meta
from ship_gate import evaluate
from source_store import store_note

SCRIPT = Path(__file__).parent / "ship_gate.py"


def _report(n_sources=3, extra_body="", findings=None, tail=""):
    findings = findings if findings is not None else [
        "- (pattern) Trapped ions use laser cooling [1]",
        "- (pitfall) Heating rates limit gate depth [2][3]",
    ]
    rows = "\n".join(f"| {i} | {i:03d} | Source {i} | https://e.com/{i} |"
                     for i in range(1, n_sources + 1))
    cites = " ".join(f"[{i}]" for i in range(1, n_sources + 1))
    return (
        "# Report\n\n## Summary\n\nIntro citing {cites}. {extra}\n\n"
        "```\ncode [99] is ignored\n```\n\n"
        "A markdown link [text](https://x) is not a cite.\n\n"
        "## Key findings\n\n{findings}\n\n"
        "## Sources\n\n| n | id | title | url |\n|---|---|---|---|\n{rows}\n{tail}"
    ).format(cites=cites, extra=extra_body, findings="\n".join(findings), rows=rows, tail=tail)


class TestReportParse(unittest.TestCase):
    def test_citations_ignore_code_and_links_and_keep_first_use_order(self):
        text = "see [3] then [1] and [3] again\n```\n[7]\n```\n[link](u) [2]\n## Sources\n[9]"
        self.assertEqual(body_citations(text), [3, 1, 2])

    def test_ranges_detected(self):
        self.assertEqual(citation_ranges("a [3-5] b [1–2]"), ["[3-5]", "[1–2]"])

    def test_sources_table_and_findings(self):
        text = _report()
        rows = sources_table(text)
        self.assertEqual([r["n"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[1]["id"], "002")
        found = key_findings(text)
        self.assertEqual(found[0]["type"], "pattern")
        self.assertEqual(found[0]["text"], "Trapped ions use laser cooling")
        self.assertEqual(found[1]["cites"], [2, 3])


class TestGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agent = str(self.root / ".agent")
        out = init_run("gate tests", self.agent, str(self.root))
        self.slug = out["slug"]
        self.dir = Path(out["dir"])
        for i in range(1, 4):
            store_note(self.slug, f"https://e.com/{i}", f"body {i}", title=f"Source {i}",
                       agent_dir=self.agent)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        (self.dir / "report.md").write_text(text)

    def _failed(self, result):
        return {c["name"] for c in result["checks"] if not c["ok"]}

    def test_passing_report(self):
        self._write(_report())
        result = evaluate(self.dir, min_sources=3)
        self.assertTrue(result["ok"], result)

    def test_missing_report(self):
        result = evaluate(self.dir, min_sources=3)
        self.assertEqual(self._failed(result), {"report-exists"})

    def test_missing_section_and_sources_not_last(self):
        self._write(_report().replace("## Summary", "## Overview"))
        self.assertIn("required-sections", self._failed(evaluate(self.dir, 3)))
        self._write(_report(tail="\n## Appendix\n\nmore\n"))
        self.assertIn("required-sections", self._failed(evaluate(self.dir, 3)))

    def test_citation_range_fails(self):
        self._write(_report(extra_body="and [1-3]"))
        self.assertIn("no-citation-ranges", self._failed(evaluate(self.dir, 3)))

    def test_body_cite_without_row_fails(self):
        self._write(_report(extra_body="dangling [4]"))
        result = evaluate(self.dir, 3)
        self.assertIn("citations-resolve", self._failed(result))
        detail = next(c["detail"] for c in result["checks"] if c["name"] == "citations-resolve")
        self.assertIn("body-only=[4]", detail)

    def test_row_never_cited_fails(self):
        text = _report(n_sources=3).replace("[3]", "")
        self._write(text)
        self.assertIn("citations-resolve", self._failed(evaluate(self.dir, 3)))

    def test_non_consecutive_rows_fail(self):
        self._write(_report().replace("| 3 | 003", "| 5 | 003").replace("[3]", "[5]"))
        self.assertIn("citations-resolve", self._failed(evaluate(self.dir, 3)))

    def test_missing_or_blocked_note_fails(self):
        (self.dir / "sources" / "003.md").unlink()
        self._write(_report())
        self.assertIn("sources-have-notes", self._failed(evaluate(self.dir, 3)))
        store_note(self.slug, "https://e.com/3", "", status="blocked", reason="403",
                   agent_dir=self.agent)
        self.assertIn("sources-have-notes", self._failed(evaluate(self.dir, 3)))

    def test_fence_leak_fails(self):
        self._write(_report(extra_body='<nav-untrusted-source url="x"> leaked'))
        self.assertIn("no-fence-leak", self._failed(evaluate(self.dir, 3)))

    def test_critic_findings_require_patch_log(self):
        (self.dir / "findings" / "critic.json").write_text(json.dumps({"findings": []}))
        self._write(_report())
        self.assertIn("patch-log-resolved", self._failed(evaluate(self.dir, 3)))
        (self.dir / "patch-log.json").write_text(json.dumps(
            {"applied": [], "unresolved": [{"severity": "critical", "section": "Summary"}]}))
        self.assertIn("patch-log-resolved", self._failed(evaluate(self.dir, 3)))
        (self.dir / "patch-log.json").write_text(json.dumps(
            {"applied": [], "unresolved": [{"severity": "minor"}]}))
        self.assertNotIn("patch-log-resolved", self._failed(evaluate(self.dir, 3)))

    def test_sources_shrunk_after_patch_fails(self):
        set_meta(self.slug, "sources_rows_before_patch", 5, self.agent)
        self._write(_report())
        self.assertIn("sources-not-shrunk", self._failed(evaluate(self.dir, 3)))

    def test_min_sources(self):
        self._write(_report())
        self.assertIn("min-sources", self._failed(evaluate(self.dir, 8)))

    def test_untyped_or_no_findings_fail(self):
        self._write(_report(findings=["- untyped bullet [1]"]))
        self.assertIn("key-findings-typed", self._failed(evaluate(self.dir, 3)))
        self._write(_report(findings=[]))
        self.assertIn("key-findings-typed", self._failed(evaluate(self.dir, 3)))

    def test_cli_exit_codes_and_artifacts(self):
        self._write(_report(extra_body="dangling [4]"))
        proc = subprocess.run([sys.executable, str(SCRIPT), "--agent-dir", self.agent, "--run",
                               self.slug, "--min-sources", "3"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse((self.dir / "ship.json").exists())
        self.assertTrue((self.dir / "findings" / "ship-last.json").exists())
        self._write(_report())
        proc = subprocess.run([sys.executable, str(SCRIPT), "--agent-dir", self.agent, "--run",
                               self.slug, "--min-sources", "3"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertTrue(json.loads((self.dir / "ship.json").read_text())["ok"])


if __name__ == "__main__":
    unittest.main()
