#!/usr/bin/env python3
"""Tests for ship_gate.py + report_parse.py (TASK-74) — every failure mode has a fixture."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_parse import (MAX_PARAGRAPH_CHARS, body_citations, citation_ranges, key_findings,
                          long_paragraphs, paragraphs, sources_table, summary_structure)
from research_run import init_run, set_meta
from ship_gate import evaluate
from source_store import store_note

SCRIPT = Path(__file__).parent / "ship_gate.py"


SUMMARY = (
    "**Answer:** Trapped ions lead on fidelity {cites}. {extra}\n\n"
    "- **Cooling.** Laser cooling is standard [1]\n"
    "- **Depth.** Heating rates cap circuit depth [1]\n\n"
    "**Counter-position:** Neutral atoms scale faster [1]\n\n"
    "**Still open:** see Open questions\n"
)


def _report(n_sources=3, extra_body="", findings=None, tail="", summary=SUMMARY,
            body=""):
    findings = findings if findings is not None else [
        "- (pattern) Trapped ions use laser cooling [1]",
        "- (pitfall) Heating rates limit gate depth [2][3]",
    ]
    rows = "\n".join(f"| {i} | {i:03d} | Source {i} | https://e.com/{i} |"
                     for i in range(1, n_sources + 1))
    cites = " ".join(f"[{i}]" for i in range(1, n_sources + 1))
    return (
        "# Report\n\n> **Query:** gate tests\n\n## Summary\n\n{summary}\n"
        "```\ncode [99] is ignored\n```\n\n"
        "## Q1. Body\n\nA markdown link [text](https://x) is not a cite.\n\n{body}\n"
        "## Key findings\n\n{findings}\n\n"
        "## Open questions\n\n- **Which trap wins?** A head-to-head benchmark.\n\n"
        "## Sources\n\n| n | id | title | url |\n|---|---|---|---|\n{rows}\n{tail}"
    ).format(summary=summary.format(cites=cites, extra=extra_body), body=body,
             findings="\n".join(findings), rows=rows, tail=tail)


WALL = "Sentence number one about ions. " * 30  # ~960 chars, over the cap


class TestReportParse(unittest.TestCase):
    def test_citations_ignore_code_and_links_and_keep_first_use_order(self):
        text = "see [3] then [1] and [3] again\n```\n[7]\n```\n[link](u) [2]\n## Sources\n[9]"
        self.assertEqual(body_citations(text), [3, 1, 2])

    def test_ranges_detected(self):
        self.assertEqual(citation_ranges("a [3-5] b [1–2]"), ["[3-5]", "[1–2]"])

    def test_summary_structure_detects_answer_line_and_bullets(self):
        self.assertEqual(summary_structure(_report()), {"has_answer": True, "bullets": 2})
        plain = _report(summary="Just prose {cites}. {extra}\n")
        self.assertEqual(summary_structure(plain), {"has_answer": False, "bullets": 0})
        self.assertEqual(summary_structure("no summary here"),
                         {"has_answer": False, "bullets": 0})

    def test_paragraphs_split_on_blank_lines_bullets_and_skip_tables_code(self):
        text = (
            "# T\n\n> **Query:** q\n\n## Summary\n\npara one\nstill one\n\n"
            "- bullet a\n  continued\n- bullet b\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
            "```\n" + "x" * 2000 + "\n```\n\n## Sources\n\n" + "y" * 2000 + "\n"
        )
        blocks = paragraphs(text)
        self.assertEqual([b["section"] for b in blocks],
                         ["(header)", "Summary", "Summary", "Summary"])
        self.assertEqual([b["head"] for b in blocks][1:],
                         ["para one still one", "- bullet a continued", "- bullet b"])
        self.assertEqual(long_paragraphs(text), [])
        self.assertTrue(long_paragraphs("## Summary\n\n" + "z" * (MAX_PARAGRAPH_CHARS + 1)))

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
        self._write(_report().replace("## Open questions", "## Loose ends"))
        self.assertIn("required-sections", self._failed(evaluate(self.dir, 3)))
        self._write(_report(tail="\n## Appendix\n\nmore\n"))
        self.assertIn("required-sections", self._failed(evaluate(self.dir, 3)))

    def test_summary_without_answer_line_or_bullets_fails(self):
        self._write(_report(summary="Answer buried in prose {cites}. {extra}\n\n"
                                    "- **One.** bullet [1]\n- **Two.** bullet [1]\n"))
        self.assertEqual(self._failed(evaluate(self.dir, 3)), {"summary-scannable"})
        self._write(_report(summary="**Answer:** short {cites}. {extra}\n\n- only one [1]\n"))
        self.assertEqual(self._failed(evaluate(self.dir, 3)), {"summary-scannable"})
        self._write(_report(summary="**Answer**: colon outside works {cites}. {extra}\n\n"
                                    "- a [1]\n- b [1]\n"))
        self.assertTrue(evaluate(self.dir, 3)["ok"])

    def test_wall_of_text_fails_with_section_named(self):
        self._write(_report(body=WALL + "[1]\n\n"))
        result = evaluate(self.dir, 3)
        self.assertEqual(self._failed(result), {"no-wall-of-text"})
        detail = next(c["detail"] for c in result["checks"] if c["name"] == "no-wall-of-text")
        self.assertIn("[Q1. Body]", detail)
        self.assertIn("Sentence number one", detail)
        self._write(_report(summary=SUMMARY + "\n" + WALL + "\n"))
        self.assertIn("no-wall-of-text", self._failed(evaluate(self.dir, 3)))

    def test_wall_of_text_exempts_tables_code_and_measures_bullets_individually(self):
        cell = "w" * 400
        table = f"| a | b |\n|---|---|\n| {cell} | {cell} |\n\n"
        code = "```\n" + "c" * 2000 + "\n```\n\n"
        bullets = "".join(f"- item {i} " + "b" * 300 + " [1]\n" for i in range(6)) + "\n"
        self._write(_report(body=table + code + bullets))
        self.assertTrue(evaluate(self.dir, 3)["ok"], evaluate(self.dir, 3))
        self._write(_report(body="- one giant bullet " + "b" * 700 + " [1]\n\n"))
        self.assertIn("no-wall-of-text", self._failed(evaluate(self.dir, 3)))

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
