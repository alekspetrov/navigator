#!/usr/bin/env python3
"""
Research to Graph - Ingest structured research findings into the knowledge graph.

Consumes the `research_findings` JSON block emitted by the navigator-research
agent and persists each finding as a graph memory. Mirrors correction_to_memory.py.

Input schema (a `research_findings` object):
{
  "topic": "string",
  "files_sampled": int,
  "files_matched": int,
  "memories": [
    {
      "type": "pattern|pitfall|decision|learning",
      "summary": "string",
      "evidence": "path/file.ts:42",      # optional, embedded into summary
      "concepts": ["string", ...],         # optional, auto-extracted if missing
      "confidence": 0.0-1.0                # optional, defaults to 0.7
    }
  ],
  "unknowns": ["string", ...]              # optional, ignored for ingestion
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

VALID_MEMORY_TYPES = {"pattern", "pitfall", "decision", "learning"}
DEFAULT_CONFIDENCE = 0.7  # Research is inference, not user-confirmed

# Concept keyword map — kept in sync with correction_to_memory.py
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
    """Auto-extract concepts when the finding didn't supply them."""
    concepts = set()
    text_lower = text.lower()
    for keyword, concept in KEYWORD_MAP.items():
        if keyword in text_lower:
            concepts.add(concept)
    if not concepts:
        concepts.add("general")
    return sorted(concepts)


def build_summary(memory: dict) -> str:
    """Combine summary + evidence reference into a single self-contained string."""
    summary = memory.get("summary", "").strip()
    evidence = memory.get("evidence", "").strip()
    if evidence and evidence not in summary:
        return f"{summary} [{evidence}]"
    return summary


def validate_memory(memory: dict, idx: int) -> Optional[str]:
    """Validate a single memory entry. Returns error string or None."""
    if not isinstance(memory, dict):
        return f"memories[{idx}] is not an object"
    if memory.get("type") not in VALID_MEMORY_TYPES:
        return (
            f"memories[{idx}].type='{memory.get('type')}' not in "
            f"{sorted(VALID_MEMORY_TYPES)}"
        )
    if not memory.get("summary", "").strip():
        return f"memories[{idx}].summary is empty"
    conf = memory.get("confidence", DEFAULT_CONFIDENCE)
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        return f"memories[{idx}].confidence={conf!r} out of range [0,1]"
    return None


def ingest_findings(findings: dict, graph_path: str,
                    dry_run: bool = False) -> dict:
    """Persist research findings as graph memories.

    Returns:
        {
            "ingested": int,
            "skipped": int,
            "memory_ids": [str],
            "errors": [str]
        }
    """
    result = {"ingested": 0, "skipped": 0, "memory_ids": [], "errors": []}

    if not isinstance(findings, dict):
        result["errors"].append("findings is not an object")
        return result

    memories = findings.get("memories", [])
    if not isinstance(memories, list):
        result["errors"].append("findings.memories is not an array")
        return result

    if not memories:
        return result  # No-op, not an error

    graph = load_graph(graph_path)

    for idx, mem in enumerate(memories):
        err = validate_memory(mem, idx)
        if err:
            result["errors"].append(err)
            result["skipped"] += 1
            continue

        summary = build_summary(mem)
        concepts = mem.get("concepts") or extract_concepts_from_text(summary)
        if not isinstance(concepts, list) or not concepts:
            concepts = ["general"]

        confidence = float(mem.get("confidence", DEFAULT_CONFIDENCE))

        if dry_run:
            result["ingested"] += 1
            result["memory_ids"].append(f"(dry-run mem-{idx})")
            continue

        memory_id = add_memory(
            graph=graph,
            memory_type=mem["type"],
            summary=summary,
            concepts=concepts,
            confidence=confidence,
            source_task=None,  # Research findings are not tied to a task
        )
        result["ingested"] += 1
        result["memory_ids"].append(memory_id)

    if not dry_run and result["ingested"] > 0:
        if not save_graph(graph_path, graph):
            result["errors"].append("save_graph() returned False")

    return result


def load_findings(source: str) -> dict:
    """Load findings JSON from a file path or '-' for stdin.

    Accepts either the bare `research_findings` object or a wrapper
    `{"research_findings": {...}}`.
    """
    if source == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(source).read_text()

    data = json.loads(raw)
    # Unwrap if wrapped
    if isinstance(data, dict) and "research_findings" in data \
            and len(data) == 1:
        return data["research_findings"]
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Ingest navigator-research findings into the knowledge graph"
    )
    parser.add_argument(
        "input",
        help="Path to findings JSON file, or '-' to read from stdin",
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
        findings = load_findings(args.input)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to load findings: {e}", file=sys.stderr)
        sys.exit(2)

    result = ingest_findings(findings, args.graph_path, dry_run=args.dry_run)

    topic = findings.get("topic", "(no topic)")
    sampled = findings.get("files_sampled", "?")
    matched = findings.get("files_matched", "?")
    print(f"Topic: {topic}")
    print(f"Sampling: {sampled} sampled / {matched} matched")
    print(f"Ingested: {result['ingested']} memories"
          f"{' (dry-run)' if args.dry_run else ''}")

    if result["memory_ids"]:
        print(f"Memory IDs: {', '.join(result['memory_ids'])}")
    if result["skipped"]:
        print(f"Skipped: {result['skipped']}", file=sys.stderr)
    if result["errors"]:
        print("Errors:", file=sys.stderr)
        for err in result["errors"]:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
