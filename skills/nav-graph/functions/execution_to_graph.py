#!/usr/bin/env python3
"""
Execution to Graph - Ingest structured execution summaries into the knowledge graph.

Consumes the `execution_summary` JSON block emitted by code-writing skills
(frontend-component, backend-endpoint, database-migration) and persists each
recorded pattern/decision/pitfall as a graph memory. Mirrors
research_to_graph.py.

Input schema (an `execution_summary` object):
{
  "skill": "string",                       # e.g. "frontend-component"
  "task": "string",                        # e.g. "UserProfile component"
  "files_created": ["string", ...],        # optional
  "files_modified": ["string", ...],       # optional
  "tests_added": ["string", ...],          # optional
  "stack_detected": "string",              # optional, e.g. "react+typescript"
  "patterns_followed": [                   # optional
    {
      "summary": "string",
      "concepts": ["string", ...],         # optional, auto-extracted if missing
      "confidence": 0.0-1.0,               # optional, defaults to 0.75
      "evidence": "path/file.ts:42"        # optional, embedded into summary
    }
  ],
  "decisions_made": [...],                 # same shape as patterns_followed
  "pitfalls_avoided": [...],               # same shape as patterns_followed
  "assumptions_made": ["string", ...]      # optional, ignored for ingestion
}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Import from sibling module
sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import load_graph, save_graph, add_memory

# Map summary section name → memory type
SECTION_TO_TYPE = {
    "patterns_followed": "pattern",
    "decisions_made": "decision",
    "pitfalls_avoided": "pitfall",
    "learnings_captured": "learning",  # optional fourth section
}

DEFAULT_CONFIDENCE = 0.75  # Execution captures are first-hand, higher than research

# Concept keyword map — kept in sync with research_to_graph.py / correction_to_memory.py
KEYWORD_MAP = {
    "auth": "authentication", "login": "authentication",
    "jwt": "authentication", "oauth": "authentication",
    "api": "api", "endpoint": "api", "rest": "api", "graphql": "api",
    "test": "testing", "spec": "testing",
    "component": "frontend", "react": "frontend", "vue": "frontend",
    "database": "database", "migration": "database", "schema": "database",
    "deploy": "deployment", "ci": "deployment", "cd": "deployment",
    "style": "code-style", "naming": "code-style", "format": "code-style",
    "perf": "performance", "performance": "performance", "latency": "performance",
    "security": "security", "vuln": "security",
    "config": "configuration", "env": "configuration",
}


def extract_concepts_from_text(text: str) -> list:
    """Auto-extract concepts when the entry didn't supply them."""
    concepts = set()
    text_lower = text.lower()
    for keyword, concept in KEYWORD_MAP.items():
        if keyword in text_lower:
            concepts.add(concept)
    if not concepts:
        concepts.add("general")
    return sorted(concepts)


def build_summary(entry: dict, skill: str = None) -> str:
    """Combine summary + evidence + skill tag into one self-contained string."""
    summary = entry.get("summary", "").strip()
    evidence = entry.get("evidence", "").strip()
    parts = [summary]
    if evidence and evidence not in summary:
        parts.append(f"[{evidence}]")
    if skill and f"({skill})" not in summary:
        parts.append(f"(via {skill})")
    return " ".join(parts)


def validate_entry(entry: dict, section: str, idx: int) -> Optional[str]:
    """Validate a single memory entry. Returns error string or None."""
    if not isinstance(entry, dict):
        return f"{section}[{idx}] is not an object"
    if not entry.get("summary", "").strip():
        return f"{section}[{idx}].summary is empty"
    conf = entry.get("confidence", DEFAULT_CONFIDENCE)
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        return f"{section}[{idx}].confidence={conf!r} out of range [0,1]"
    return None


def ingest_summary(summary: dict, graph_path: str,
                   dry_run: bool = False) -> dict:
    """Persist execution summary entries as graph memories.

    Returns:
        {
            "ingested": int,
            "skipped": int,
            "memory_ids": [str],
            "errors": [str],
            "by_type": {"pattern": int, "decision": int, "pitfall": int}
        }
    """
    result = {
        "ingested": 0,
        "skipped": 0,
        "memory_ids": [],
        "errors": [],
        "by_type": {"pattern": 0, "decision": 0, "pitfall": 0, "learning": 0},
    }

    if not isinstance(summary, dict):
        result["errors"].append("summary is not an object")
        return result

    skill = summary.get("skill")
    source_task = summary.get("task")

    # Collect all entries from each section
    pending = []  # (memory_type, entry, section_label, idx)
    for section, memory_type in SECTION_TO_TYPE.items():
        entries = summary.get(section, [])
        if not isinstance(entries, list):
            result["errors"].append(f"{section} is not an array")
            continue
        for idx, entry in enumerate(entries):
            err = validate_entry(entry, section, idx)
            if err:
                result["errors"].append(err)
                result["skipped"] += 1
                continue
            pending.append((memory_type, entry, section, idx))

    if not pending:
        return result  # No-op, not an error

    graph = load_graph(graph_path)

    for memory_type, entry, section, idx in pending:
        entry_summary = build_summary(entry, skill=skill)
        concepts = entry.get("concepts") or extract_concepts_from_text(
            entry_summary
        )
        if not isinstance(concepts, list) or not concepts:
            concepts = ["general"]

        confidence = float(entry.get("confidence", DEFAULT_CONFIDENCE))

        if dry_run:
            result["ingested"] += 1
            result["by_type"][memory_type] += 1
            result["memory_ids"].append(
                f"(dry-run {section}[{idx}] → {memory_type})"
            )
            continue

        try:
            memory_id = add_memory(
                graph=graph,
                memory_type=memory_type,
                summary=entry_summary,
                concepts=concepts,
                confidence=confidence,
                source_task=source_task,
            )
        except (OSError, FileExistsError, ValueError) as e:
            # add_memory is fail-loud since v6.17.0 — record and skip so one
            # bad entry doesn't abort the whole ingest.
            result["errors"].append(f"{section}[{idx}]: {e}")
            continue
        result["ingested"] += 1
        result["by_type"][memory_type] += 1
        result["memory_ids"].append(memory_id)

    if not dry_run and result["ingested"] > 0:
        if not save_graph(graph_path, graph):
            result["errors"].append("save_graph() returned False")

    return result


def load_summary(source: str) -> dict:
    """Load execution summary JSON from a file path or '-' for stdin.

    Accepts either the bare `execution_summary` object or a wrapper
    `{"execution_summary": {...}}`.
    """
    if source == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(source).read_text()

    data = json.loads(raw)
    if isinstance(data, dict) and "execution_summary" in data \
            and len(data) == 1:
        return data["execution_summary"]
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Ingest execution summary into the knowledge graph"
    )
    parser.add_argument(
        "input",
        help="Path to execution_summary JSON file, or '-' to read from stdin",
    )
    parser.add_argument(
        "--graph-path",
        default=".agent/knowledge/graph.json",
        help="Path to knowledge graph (default: .agent/knowledge/graph.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report, but do not write to graph",
    )
    args = parser.parse_args()

    try:
        summary = load_summary(args.input)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to load summary: {e}", file=sys.stderr)
        sys.exit(2)

    result = ingest_summary(summary, args.graph_path, dry_run=args.dry_run)

    skill = summary.get("skill", "(no skill)")
    task = summary.get("task", "(no task)")
    files_created = len(summary.get("files_created", []))
    files_modified = len(summary.get("files_modified", []))
    tests_added = len(summary.get("tests_added", []))
    stack = summary.get("stack_detected", "(unspecified)")

    print(f"Skill: {skill}")
    print(f"Task: {task}")
    print(f"Stack: {stack}")
    print(
        f"Files: {files_created} created, {files_modified} modified, "
        f"{tests_added} tests"
    )
    print(
        f"Ingested: {result['ingested']} memories"
        f"{' (dry-run)' if args.dry_run else ''}"
    )
    by_type = result["by_type"]
    type_summary = ", ".join(
        f"{k}={v}" for k, v in by_type.items() if v > 0
    )
    if type_summary:
        print(f"By type: {type_summary}")

    if result["memory_ids"]:
        # Cap the printed list to avoid context flooding
        ids = result["memory_ids"]
        if len(ids) > 10:
            print(
                f"Memory IDs: {', '.join(ids[:10])}, "
                f"... ({len(ids) - 10} more)"
            )
        else:
            print(f"Memory IDs: {', '.join(ids)}")

    if result["skipped"]:
        print(f"Skipped: {result['skipped']}", file=sys.stderr)
    if result["errors"]:
        print("Errors:", file=sys.stderr)
        for err in result["errors"]:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
