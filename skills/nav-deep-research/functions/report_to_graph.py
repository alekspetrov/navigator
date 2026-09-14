#!/usr/bin/env python3
"""
Report → knowledge graph bridge for nav-deep-research (TASK-74).

Reads ``report.md`` of a run, turns every typed ``## Key findings`` bullet
(``- (pattern|pitfall|decision|learning) text [n]``) into a memory whose
evidence is the cited source URL(s), each tagged with the fetch date and a
content-hash prefix read from the run's local source note, and hands the batch
to the existing ``skills/nav-graph/functions/research_to_graph.py`` ingestion
path. Everything is folded into the evidence text because ``build_summary()``
there already appends ``[evidence]`` to the summary — no graph schema change.

Why the tag: source notes are gitignored third-party text, so the committed
memory is what a teammate audits from. ``fetched YYYY-MM-DD, sha256 <12 hex>``
says when the page was read and which content version supported the claim;
``source_store.py refetch`` reports ``sha_match`` against the same hash.
Notes missing (another machine, pruned run) → URL-only evidence as before.

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
from source_store import load_notes  # noqa: E402

try:
    from research_to_graph import ingest_findings  # noqa: E402
except Exception:  # pragma: no cover - graph skill stripped from the install
    ingest_findings = None

DEFAULT_CONFIDENCE = 0.7  # research is inference, not user-confirmed
SHA_PREFIX = 12  # enough to detect drift on refetch; keeps the evidence text readable


def provenance_by_url(slug: str, agent_dir: str = ".agent") -> dict:
    """URL → ``fetched YYYY-MM-DD, sha256 <prefix>`` from the run's local source notes.

    Keyed by every URL form a note carries (requested, final, canonical) so the
    report's Sources table matches whichever one the writer used. Blocked or
    skipped notes have no body hash and are left out.
    """
    tags: dict = {}
    for meta, _, _ in load_notes(slug, agent_dir):
        digest = str(meta.get("sha256") or "")
        if meta.get("status") != "ok" or not digest:
            continue
        tag = f"fetched {str(meta.get('fetched_at', ''))[:10]}, sha256 {digest[:SHA_PREFIX]}"
        for key in ("url", "final_url", "canonical_url"):
            if meta.get(key):
                tags.setdefault(str(meta[key]), tag)
    return tags


def build_findings(report_text: str, topic: str, slug: str,
                   provenance: dict | None = None) -> dict:
    """research_findings payload from a report (no graph access).

    ``provenance`` (see ``provenance_by_url``) tags each cited URL; absent → URL only.
    """
    url_by_n = {row["n"]: row["url"] for row in sources_table(report_text)}
    tags = provenance or {}
    memories = []
    for finding in key_findings(report_text):
        urls = [url_by_n[n] for n in finding["cites"] if n in url_by_n]
        cited = [f"{u} ({tags[u]})" if u in tags else u for u in urls]
        evidence = ", ".join(cited) if cited else f"nav-deep-research run {slug}"
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
    query = read_query(slug, agent_dir)
    topic = query.splitlines()[0][:120] if query else slug
    findings = build_findings(text, topic, slug, provenance_by_url(slug, agent_dir))
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
