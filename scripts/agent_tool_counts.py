#!/usr/bin/env python3
"""Per-tool call counts and deduplicated token usage for one Claude Code transcript.

Usage:
    agent_tool_counts.py <transcript.jsonl> [--json]
    agent_tool_counts.py --latest-subagent [project_dir] [--json]

Why this exists (TASK-76): ``scripts/session-stats.sh`` sums ``message.usage`` per JSONL
line, but one API response spans several lines (same ``requestId``, ``apiBlockIndex``
0..n), each repeating input/cache tokens; only the last carries the final output count.
This script counts once per request (max per field) and counts ``tool_use`` blocks by
name — the ground truth for the research-agent A/B, independent of the model's own
Sampling Report.

Parse rules mirror ``hooks/nav_hook_lib/transcript.py`` (blank, undecodable and non-dict
lines are skipped) but the whole file is read, not a tail slice. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

LSP_OPS = (
    "goToDefinition", "findReferences", "hover", "documentSymbol", "workspaceSymbol",
    "implementation", "callHierarchy", "prepareCallHierarchy", "incomingCalls", "outgoingCalls",
)
USAGE_KEYS = (
    "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
)


def entries(path):
    """Yield dict entries from a JSONL transcript; skip blank/undecodable/non-dict lines."""
    text = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def lsp_op(tool_input) -> str:
    """LSP operation name from a tool_use input; the parameter key is not assumed."""
    for value in (tool_input or {}).values():
        if isinstance(value, str) and value in LSP_OPS:
            return value
    return "?"


def count(path) -> dict:
    tools, lsp_ops, read_paths, usage, stamps = Counter(), Counter(), set(), {}, []
    for obj in entries(path):
        msg = obj.get("message")
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        if obj.get("timestamp"):
            stamps.append(obj["timestamp"])
        if isinstance(msg.get("usage"), dict):
            key = obj.get("requestId") or obj.get("uuid")
            per_request = usage.setdefault(key, dict.fromkeys(USAGE_KEYS, 0))
            for field in USAGE_KEYS:
                per_request[field] = max(per_request[field], int(msg["usage"].get(field) or 0))
        for block in msg.get("content") or []:
            if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                continue
            name = block.get("name") or "?"
            tools[name] += 1
            if name == "LSP":
                lsp_ops[lsp_op(block.get("input"))] += 1
            elif name == "Read":
                read_paths.add((block.get("input") or {}).get("file_path"))
    totals = Counter()
    for per_request in usage.values():
        totals.update(per_request)
    return {
        "transcript": str(path),
        "tools": dict(tools),
        "lsp_ops": dict(lsp_ops),
        "read_distinct_paths": len(read_paths),
        "requests": len(usage),
        "usage": {field: totals[field] for field in USAGE_KEYS},
        "fresh_input": totals["input_tokens"] + totals["cache_creation_input_tokens"],
        "first_ts": stamps[0] if stamps else None,
        "last_ts": stamps[-1] if stamps else None,
    }


def latest_subagent(project_dir, projects_root=None):
    """Newest ``*/subagents/agent-*.jsonl`` for a project, using Claude Code's path encoding."""
    encoded = str(Path(project_dir).resolve()).translate(str.maketrans("/.", "--"))
    root = Path(projects_root or Path.home() / ".claude" / "projects") / encoded
    files = sorted(root.glob("*/subagents/agent-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def format_text(result: dict) -> str:
    lines = [f"Transcript: {result['transcript']}",
             f"Requests: {result['requests']}   Span: {result['first_ts']} -> {result['last_ts']}",
             "Tools:"]
    for name, n in sorted(result["tools"].items(), key=lambda kv: (-kv[1], kv[0])):
        ops = ", ".join(f"{op} x{k}" for op, k in sorted(result["lsp_ops"].items()))
        lines.append(f"  {name:<12}{n:>6}" + (f"  ({ops})" if name == "LSP" and ops else ""))
    lines.append(f"Read distinct paths: {result['read_distinct_paths']}")
    lines.append("Usage (once per request):")
    for field in USAGE_KEYS:
        lines.append(f"  {field:<28}{result['usage'][field]:>10}")
    lines.append(f"  {'fresh_input (input + cache_creation)':<28}{result['fresh_input']:>10}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcript", nargs="?", help="transcript .jsonl path")
    parser.add_argument("--latest-subagent", nargs="?", const=".", metavar="PROJECT_DIR",
                        help="newest subagent transcript for PROJECT_DIR (default: cwd)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)
    path = args.transcript
    if args.latest_subagent is not None:
        path = latest_subagent(args.latest_subagent)
        if path is None:
            parser.error(f"no subagent transcript found for {args.latest_subagent}")
    if not path or not Path(path).expanduser().is_file():
        parser.error("transcript path missing or not a file")
    result = count(path)
    print(json.dumps(result, indent=2) if args.json else format_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
