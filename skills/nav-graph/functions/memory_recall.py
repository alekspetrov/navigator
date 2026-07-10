#!/usr/bin/env python3
"""
Memory Recall - deterministic relevant-memory ranking (v6.17.0)

The single ranking implementation behind both surfacing moments:
- SessionStart op (`hooks/ops/session_start.py`) shells to `--auto` for the
  "Relevant Memories" section
- nav-task Step 2.5 shells to `--concepts` for the task doc's
  "Known Pitfalls & Patterns" section

Design constraints:
- Never touches concept_index: memories are scored by overlap between the
  target concept set and each node's own `concepts` array, so consumer
  graphs without an index (pilot-style) work by construction.
- Schema-compat: `path` | `file` | `memory_file` nodes, nodes with no path
  at all, top-level `updated` instead of `last_updated` — all legal.
- Silence over noise: missing graph, no targets, or no matches print
  nothing and exit 0. Callers treat empty stdout as "no section".
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import load_graph, resolve_concept_alias, memory_file_ref


def is_resolved(mem: dict) -> bool:
    """A memory is out of the live set once resolved or superseded."""
    return bool(mem.get("resolved") or mem.get("superseded_by"))


def collect_auto_concepts(graph: dict, agent_dir: Path) -> list:
    """Union of concepts from open task nodes + the active context marker.

    'Open' = any task node whose status is not 'completed' — consumer graphs
    with unknown/absent statuses still contribute (intended: better to
    surface than to stay silent on a loosely-maintained graph).
    """
    concepts = []

    for task in graph.get("nodes", {}).get("tasks", {}).values():
        if str(task.get("status", "")).lower() == "completed":
            continue
        for c in task.get("concepts", []):
            if c not in concepts:
                concepts.append(c)

    # Active marker: .context-markers/.active names the marker file; the
    # graph indexes markers by id — match on stem containment either way.
    active_file = agent_dir / ".context-markers" / ".active"
    if active_file.is_file():
        try:
            marker_name = Path(active_file.read_text().strip()).stem
        except OSError:
            marker_name = ""
        if marker_name:
            for marker_id, marker in graph.get("nodes", {}).get("markers", {}).items():
                if marker_name in marker_id or marker_id in marker_name:
                    for c in marker.get("concepts", []):
                        if c not in concepts:
                            concepts.append(c)

    return concepts


def rank_memories(graph: dict, target_concepts: list,
                  limit: int = 5, min_confidence: float = 0.0) -> list:
    """Rank live memories by concept overlap with the target set.

    score = |mem.concepts ∩ targets| (after alias resolution of targets).
    Excluded: resolved/superseded memories, zero-overlap, below
    min_confidence. Sort: score desc, confidence desc, id asc (determinism).
    """
    targets = set()
    for c in target_concepts:
        c = str(c).strip().lower()
        if not c:
            continue
        targets.add(c)
        targets.add(resolve_concept_alias(graph, c).lower())
    if not targets:
        return []

    scored = []
    for mem_id, mem in graph.get("nodes", {}).get("memories", {}).items():
        if is_resolved(mem):
            continue
        confidence = mem.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0
        if confidence < min_confidence:
            continue
        overlap = len({str(c).lower() for c in mem.get("concepts", [])} & targets)
        if overlap == 0:
            continue
        scored.append((overlap, confidence, mem_id, mem))

    scored.sort(key=lambda t: (-t[0], -t[1], t[2]))
    return [
        {"id": mem_id, "score": overlap, **mem}
        for overlap, confidence, mem_id, mem in scored[:limit]
    ]


def render_compact(ranked: list) -> str:
    """- PITFALL: "summary" (90%) — for the session-start hook section."""
    lines = []
    for mem in ranked:
        mem_type = mem.get("type", "memory").upper()
        summary = mem.get("summary", mem["id"])
        confidence = int(round(float(mem.get("confidence", 0)) * 100))
        lines.append(f'- {mem_type}: "{summary}" ({confidence}%)')
    return "\n".join(lines)


def render_markdown(ranked: list) -> str:
    """- **PITFALL** (90%, mem-012): summary — for task docs."""
    lines = []
    for mem in ranked:
        mem_type = mem.get("type", "memory").upper()
        summary = mem.get("summary", mem["id"])
        confidence = int(round(float(mem.get("confidence", 0)) * 100))
        ref = memory_file_ref(mem)
        suffix = f" — `{ref}`" if ref else ""
        lines.append(f"- **{mem_type}** ({confidence}%, {mem['id']}): "
                     f"{summary}{suffix}")
    return "\n".join(lines)


def render_json(ranked: list) -> str:
    return json.dumps(
        [{"id": m["id"], "type": m.get("type"), "summary": m.get("summary"),
          "confidence": m.get("confidence"), "score": m["score"],
          "file": memory_file_ref(m)} for m in ranked],
        indent=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rank knowledge-graph memories relevant to given concepts")
    parser.add_argument("--graph-path", default=".agent/knowledge/graph.json",
                        help="Path to graph.json")
    parser.add_argument("--concepts",
                        help="Comma-separated target concepts")
    parser.add_argument("--auto", action="store_true",
                        help="Derive target concepts from open task nodes "
                             "and the active context marker")
    parser.add_argument("--agent-dir", default=".agent",
                        help=".agent directory (used with --auto)")
    parser.add_argument("--limit", type=int, default=5,
                        help="Max memories to return")
    parser.add_argument("--min-confidence", type=float, default=0.0,
                        help="Exclude memories below this confidence")
    parser.add_argument("--format", choices=["compact", "markdown", "json"],
                        default="compact", help="Output format")
    args = parser.parse_args()

    if not args.concepts and not args.auto:
        print("Error: pass --concepts or --auto", file=sys.stderr)
        return 1
    if args.concepts and args.auto:
        print("Error: --concepts and --auto are mutually exclusive",
              file=sys.stderr)
        return 1

    # Missing graph -> silence (callers treat empty stdout as "no section")
    if not Path(args.graph_path).is_file():
        return 0
    graph = load_graph(args.graph_path)

    if args.auto:
        targets = collect_auto_concepts(graph, Path(args.agent_dir))
    else:
        targets = [c for c in args.concepts.split(",") if c.strip()]
    if not targets:
        return 0

    ranked = rank_memories(graph, targets,
                           limit=args.limit,
                           min_confidence=args.min_confidence)
    if not ranked:
        return 0

    renderer = {"compact": render_compact,
                "markdown": render_markdown,
                "json": render_json}[args.format]
    print(renderer(ranked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
