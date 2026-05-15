#!/usr/bin/env python3
"""
Navigator task → knowledge graph sync hook (Opp 4 / v6.11.0).

Fires on `PostToolUse` after `Write` or `Edit` calls. When the touched file
is a `.agent/tasks/TASK-*.md` task document, this hook runs
`task_to_graph.py --action add` to upsert the task into the knowledge
graph. Replaces the soft "if knowledge graph exists, sync task" rule that
the nav-task skill used to depend on the model remembering.

Per Q1 verification: `task_to_graph.py --action add` calls `add_node`,
which assigns by `node_id` and is effectively upsert — re-running on the
same task file overwrites in place, no duplicate nodes.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#posttooluse
- stdin JSON: tool_name, tool_input (with file_path), cwd
- Exit 0 always — never block tool execution.
- stdout is empty JSON `{}` — pure side effect.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


TASK_PATH_RE = re.compile(r"\.agent/tasks/(TASK[-_][\w\-.]+)\.md$")


def _safe_read(path: Path, max_bytes: int = 200_000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception as e:
        print(f"nav_task_graph_sync: skip {path}: {e}", file=sys.stderr)
        return None


def _safe_json(path: Path) -> dict | None:
    raw = _safe_read(path)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"nav_task_graph_sync: invalid JSON in {path}: {e}", file=sys.stderr)
        return None


def _project_root(stdin_data: dict) -> Path:
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def _hook_enabled(root: Path) -> bool:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    hook_cfg = cfg.get("task_graph_sync_hook") or {}
    return hook_cfg.get("enabled", True)


def _resolve_plugin_dir() -> Path | None:
    env = os.environ.get("CLAUDE_PLUGIN_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    candidates = [
        Path.home() / ".claude" / "plugins" / "cache" / "navigator-marketplace" / "navigator",
        Path.home() / ".claude" / "plugins" / "marketplaces" / "navigator-marketplace",
    ]
    for c in candidates:
        if (c / "skills" / "nav-graph").is_dir():
            return c
    here = Path(__file__).resolve().parent.parent
    if (here / "skills" / "nav-graph").is_dir():
        return here
    return None


def _extract_task_path(stdin_data: dict, root: Path) -> Path | None:
    """Return the absolute task file path if this tool call touched one."""
    tool_input = stdin_data.get("tool_input") or {}
    candidate = tool_input.get("file_path")
    if not isinstance(candidate, str) or not candidate:
        return None
    p = Path(candidate)
    if not p.is_absolute():
        p = root / candidate
    try:
        rel = p.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    rel_str = rel.as_posix()
    if not TASK_PATH_RE.search(rel_str):
        return None
    if not p.is_file():
        # Was deleted or never landed — nothing to sync
        return None
    return p


def main() -> int:
    raw_stdin = sys.stdin.read() if not sys.stdin.isatty() else ""
    stdin_data: dict[str, Any] = {}
    if raw_stdin.strip():
        try:
            stdin_data = json.loads(raw_stdin)
        except json.JSONDecodeError:
            stdin_data = {}

    root = _project_root(stdin_data)
    if not (root / ".agent").is_dir():
        print(json.dumps({}))
        return 0

    if not _hook_enabled(root):
        print(json.dumps({}))
        return 0

    graph_path = root / ".agent" / "knowledge" / "graph.json"
    if not graph_path.is_file():
        # No graph initialized — skip silently
        print(json.dumps({}))
        return 0

    task_path = _extract_task_path(stdin_data, root)
    if not task_path:
        print(json.dumps({}))
        return 0

    plugin_dir = _resolve_plugin_dir()
    if plugin_dir is None:
        print("nav_task_graph_sync: plugin dir not found", file=sys.stderr)
        print(json.dumps({}))
        return 0

    syncer = plugin_dir / "skills" / "nav-graph" / "functions" / "task_to_graph.py"
    if not syncer.is_file():
        print(f"nav_task_graph_sync: {syncer} missing", file=sys.stderr)
        print(json.dumps({}))
        return 0

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(syncer),
                "--action",
                "add",
                "--task-path",
                str(task_path),
                "--graph-path",
                str(graph_path),
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0:
            print(
                f"nav_task_graph_sync: sync failed (rc={result.returncode}): "
                f"{(result.stderr or result.stdout).strip()[:300]}",
                file=sys.stderr,
            )
        else:
            print(
                f"nav_task_graph_sync: upserted {task_path.name}",
                file=sys.stderr,
            )
    except subprocess.TimeoutExpired:
        print("nav_task_graph_sync: subprocess timeout", file=sys.stderr)
    except Exception as e:
        print(f"nav_task_graph_sync: subprocess failure: {e}", file=sys.stderr)

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
