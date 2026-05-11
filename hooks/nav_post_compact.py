#!/usr/bin/env python3
"""
Navigator PostCompact hook — append Claude Code's compact summary to the
marker that PreCompact just wrote.

Fires after manual `/compact` or auto-compact finishes. Reads `.active`
to find the marker created by PreCompact, then appends a `## Compact
Summary (Claude Code)` section containing the official summary that
replaced the conversation.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#postcompact
- stdin JSON includes: cwd, transcript_path, session_id, compact_summary
- Always exit 0 — never block.
- If `.active` doesn't exist (PreCompact didn't fire), do nothing.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _safe_read(path: Path, max_bytes: int = 1000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception as e:
        print(f"nav_post_compact: skip {path}: {e}", file=sys.stderr)
        return None


def _safe_json(path: Path) -> dict | None:
    raw = _safe_read(path, max_bytes=200_000)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _project_root(stdin_data: dict) -> Path:
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def _hook_enabled(root: Path) -> bool:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    hook_cfg = cfg.get("compact_hook") or {}
    if not hook_cfg.get("enabled", True):
        return False
    return bool(hook_cfg.get("append_post_compact_summary", True))


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

    markers_dir = root / ".agent" / ".context-markers"
    active_path = markers_dir / ".active"
    active_name = _safe_read(active_path, max_bytes=200)
    if not active_name:
        # PreCompact didn't fire — nothing to append to.
        print(json.dumps({}))
        return 0

    active_name = active_name.strip()
    marker_path = markers_dir / active_name
    if not marker_path.is_file():
        print(f"nav_post_compact: marker {marker_path} missing", file=sys.stderr)
        print(json.dumps({}))
        return 0

    summary = stdin_data.get("compact_summary") or "_[no summary provided by Claude Code]_"
    if isinstance(summary, (dict, list)):
        summary = json.dumps(summary, indent=2, default=str)
    summary = str(summary).strip()

    try:
        with marker_path.open("a", encoding="utf-8") as fh:
            fh.write("\n\n---\n\n")
            fh.write("## Compact Summary (Claude Code)\n\n")
            fh.write(f"_Appended by PostCompact hook at {datetime.now().isoformat(timespec='seconds')}._\n\n")
            fh.write(summary + "\n")
        print(f"nav_post_compact: appended summary to {marker_path}", file=sys.stderr)
    except Exception as e:
        print(f"nav_post_compact: append failed: {e}", file=sys.stderr)

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
