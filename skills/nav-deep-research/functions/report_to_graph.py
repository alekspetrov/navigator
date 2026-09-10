#!/usr/bin/env python3
"""
Report → knowledge graph bridge for nav-deep-research (TASK-74).

Reads ``report.md`` of a run, turns every typed ``## Key findings`` bullet
(``- (pattern|pitfall|decision|learning) text [n]``) into a memory whose
evidence is the cited source URL(s), and hands the batch to the existing
``skills/nav-graph/functions/research_to_graph.py`` ingestion path. The URL
is folded into the evidence text because ``build_summary()`` there already
appends ``[evidence]`` to the summary — no graph schema change.

Usage:
  report_to_graph.py --run SLUG [--agent-dir .agent] [--graph-path PATH] [--dry-run]
Prints JSON: {topic, memories:[...], ingest:{ingested, skipped, memory_ids, errors}}.
Exit 0 on success, 1 when the run/report is missing, 2 when the graph skill is absent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "nav-graph" / "functions"))
from report_parse import key_findings, sources_table  # noqa: E402
from research_run import read_query  # noqa: E402

try:
    from research_to_graph import ingest_findings  # noqa: E402
except Exception:  # pragma: no cover - graph skill stripped from the install
    ingest_findings = None

DEFAULT_CONFIDENCE = 0.7  # research is inference, not user-confirmed


def build_findings(report_text: str, topic: str, slug: str) -> dict:
    """research_findings payload from a report (no graph access)."""
    url_by_n = {row["n"]: row["url"] for row in sources_table(report_text)}
    memories = []
    for finding in key_findings(report_text):
        urls = [url_by_n[n] for n in finding["cites"] if n in url_by_n]
        evidence = ", ".join(urls) if urls else f"nav-deep-research run {slug}"
        memories.append({
            "type": finding["type"],
            "summary": finding["text"],
            "evidence": evidence,
            "confidence": DEFAULT_CONFIDENCE,
        })
    rows = len(url_by_n)
    return {
        "topic": topic or slug,
        "files_sampled": rows,
        "files_matched": rows,
        "memories": memories,
        "unknowns": [],
    }


def run(slug: str, agent_dir: str = ".agent", graph_path: str = ".agent/knowledge/graph.json",
        dry_run: bool = False) -> tuple[dict, int]:
    run_directory = Path(agent_dir) / "research" / slug
    report = run_directory / "report.md"
    if not report.exists():
        return {"error": f"no report at {report}"}, 1
    text = report.read_text(encoding="utf-8")
    topic = read_query(slug, agent_dir).splitlines()[0][:120] if read_query(slug, agent_dir) else slug
    findings = build_findings(text, topic, slug)
    out = {"topic": findings["topic"], "memories": findings["memories"]}
    if ingest_findings is None:
        out["ingest"] = {"error": "nav-graph skill not available"}
        return out, 2
    out["ingest"] = ingest_findings(findings, graph_path, dry_run=dry_run)
    if not dry_run:
        (run_directory / "findings").mkdir(exist_ok=True)
        (run_directory / "findings" / "graph-ingest.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out, 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="nav-deep-research → knowledge graph")
    parser.add_argument("--run", required=True)
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--graph-path", default=".agent/knowledge/graph.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    out, code = run(args.run, args.agent_dir, args.graph_path, args.dry_run)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
