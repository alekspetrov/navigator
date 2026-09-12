#!/usr/bin/env python3
"""
Ship gate for nav-deep-research (TASK-74).

A deterministic script, not an LLM judge: it reads the run directory and
decides whether ``report.md`` may ship. Prints ``{ok, checks:[{name, ok,
detail}]}``, writes the same JSON to ``ship.json`` (step 6 artifact) and exits
1 on failure. Gate failures are fixed by editing the report, never by
re-interpreting the checks.

Checks:
  report-exists          report.md is present and non-empty
  required-sections      ## Summary, ## Key findings, ## Open questions, ## Sources
                         present; Sources is last
  no-citation-ranges     no [3-5] style citations
  citations-resolve      set(body [n]) == set(table n); n is 1..K consecutive
  sources-have-notes     every table id maps to sources/NNN.md with status ok
  no-fence-leak          no <nav-untrusted-source ...> text in the report
  patch-log-resolved     when findings/critic.json exists, patch-log.json exists and
                         lists no unresolved critical findings
  sources-not-shrunk     Sources rows >= run.json meta.sources_rows_before_patch
  min-sources            K >= --min-sources
  key-findings-typed     at least one typed Key findings bullet, no untyped ones
  summary-scannable      ## Summary opens with a **Answer:** line and has >= 2 bullets
  no-wall-of-text        no paragraph, blockquote, or bullet before ## Sources exceeds
                         report_parse.MAX_PARAGRAPH_CHARS (tables/headings/code exempt)

Layout rules the last two checks enforce: reference/REPORT-FORMAT.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_parse import (MAX_PARAGRAPH_CHARS, MIN_SUMMARY_BULLETS,  # noqa: E402
                          REQUIRED_SECTIONS, body_citations, citation_ranges,
                          key_findings, long_paragraphs, sections, sources_table,
                          summary_structure, untyped_findings)
from source_store import parse_note  # noqa: E402
from untrusted import contains_fence  # noqa: E402

DEFAULT_MIN_SOURCES = 8


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def evaluate(run_directory: Path, min_sources: int = DEFAULT_MIN_SOURCES) -> dict:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    report_path = run_directory / "report.md"
    text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    check("report-exists", bool(text.strip()), str(report_path))
    if not text.strip():
        return {"ok": False, "checks": checks}

    titles = [t.lower() for t in sections(text)]
    missing = [s for s in REQUIRED_SECTIONS if s.lower() not in titles]
    sources_last = bool(titles) and titles[-1] == "sources"
    check("required-sections", not missing and sources_last,
          f"missing={missing}" if missing else
          ("ok" if sources_last else "## Sources must be the last section"))

    ranges = citation_ranges(text)
    check("no-citation-ranges", not ranges, f"ranges={ranges}" if ranges else "ok")

    cited = body_citations(text)
    rows = sources_table(text)
    table_ns = [r["n"] for r in rows]
    consecutive = table_ns == list(range(1, len(table_ns) + 1))
    body_set, table_set = set(cited), set(table_ns)
    check("citations-resolve", body_set == table_set and consecutive and bool(rows),
          f"body-only={sorted(body_set - table_set)} table-only={sorted(table_set - body_set)}"
          f" consecutive={consecutive} rows={len(rows)}")

    problems = []
    for row in rows:
        note = run_directory / "sources" / f"{row['id']}.md"
        if not note.exists():
            problems.append(f"{row['n']}:{row['id']} missing")
            continue
        meta, _ = parse_note(note.read_text(encoding="utf-8", errors="replace"))
        if meta.get("status") != "ok":
            problems.append(f"{row['n']}:{row['id']} status={meta.get('status')}")
    check("sources-have-notes", not problems, "; ".join(problems) if problems else "ok")

    check("no-fence-leak", not contains_fence(text), "ok" if not contains_fence(text)
          else "untrusted-source fence text leaked into the report")

    critic = run_directory / "findings" / "critic.json"
    patch_log = run_directory / "patch-log.json"
    if critic.exists():
        log = _load_json(patch_log)
        if log is None:
            check("patch-log-resolved", False, "findings/critic.json exists but patch-log.json "
                  "is missing or invalid (step 5 not run)")
        else:
            unresolved = [f for f in log.get("unresolved", [])
                          if str(f.get("severity", "")).lower() == "critical"]
            check("patch-log-resolved", not unresolved,
                  f"{len(unresolved)} unresolved critical finding(s)" if unresolved else "ok")
    else:
        check("patch-log-resolved", True, "no critic findings (critic skipped)")

    manifest = _load_json(run_directory / "run.json") or {}
    before = manifest.get("meta", {}).get("sources_rows_before_patch")
    if isinstance(before, int):
        check("sources-not-shrunk", len(rows) >= before, f"rows={len(rows)} before={before}")
    else:
        check("sources-not-shrunk", True, "no pre-patch row count recorded")

    check("min-sources", len(rows) >= min_sources, f"rows={len(rows)} min={min_sources}")

    typed, untyped = key_findings(text), untyped_findings(text)
    check("key-findings-typed", bool(typed) and not untyped,
          f"typed={len(typed)} untyped={len(untyped)}")

    summary = summary_structure(text)
    check("summary-scannable",
          summary["has_answer"] and summary["bullets"] >= MIN_SUMMARY_BULLETS,
          f"answer-line={summary['has_answer']} bullets={summary['bullets']} "
          f"(need **Answer:** line and >= {MIN_SUMMARY_BULLETS} bullets)")

    walls = long_paragraphs(text)
    check("no-wall-of-text", not walls,
          "; ".join(f"[{w['section']}] {w['chars']} chars: {w['head']!r}" for w in walls)
          if walls else f"ok (cap {MAX_PARAGRAPH_CHARS} chars)")

    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="nav-deep-research ship gate")
    parser.add_argument("--run", required=True)
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--min-sources", type=int, default=DEFAULT_MIN_SOURCES)
    parser.add_argument("--no-write", action="store_true", help="do not write ship.json")
    args = parser.parse_args(argv)

    run_directory = Path(args.agent_dir) / "research" / args.run
    if not run_directory.is_dir():
        print(json.dumps({"ok": False, "error": f"run directory missing: {run_directory}"}))
        return 1
    result = evaluate(run_directory, args.min_sources)
    result["run"] = args.run
    if not args.no_write:
        # ship.json is the step-6 artifact (resume treats it as "done"), so it is
        # written only on success; every evaluation is recorded in findings/.
        (run_directory / "findings").mkdir(exist_ok=True)
        (run_directory / "findings" / "ship-last.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if result["ok"]:
            (run_directory / "ship.json").write_text(json.dumps(result, indent=2) + "\n",
                                                     encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
