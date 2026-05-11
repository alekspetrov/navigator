#!/usr/bin/env python3
"""
Navigator `.agent/` bulk-read guard (Opp 6 / v6.12.0).

Fires on `PreToolUse` Read. Counts non-allowlisted reads of `.agent/` files
per turn and emits an escalating warning when the count crosses thresholds.

The tail-risk this prevents: sequential bulk-loads of `.agent/` documentation
(tasks, SOPs, system docs) that can consume 50k+ tokens in a single turn and
crash mid-session — the exact anti-pattern Navigator's lazy-loading strategy
exists to avoid.

Behavior (v6.12.0):
  - Counter file: `.agent/.nav-read-counter.json` (per-session, reset on Stop)
  - Allowlist (do not count): DEVELOPMENT-README.md, .nav-config.json,
    .user-profile.json, knowledge/graph.json
  - Warn at count >= warn_threshold (default 3): suggest Task/Explore agent
  - Escalate at count >= escalate_threshold (default 5): name the anti-pattern
  - Never blocks (exit 0 always). A blocking variant is deferred until live
    telemetry shows warnings are ignored — would require a companion state
    file to satisfy mem-027's three-condition gate.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#pretooluse
  - stdin JSON: tool_name, tool_input.file_path, cwd, session_id
  - file_path may be absolute OR relative (handled defensively per mem-027
    path-resolution discipline).
  - Output: dual-channel — stdout plain text AND structured JSON with
    `hookSpecificOutput.additionalContext`. Whichever channel CC consumes
    will surface the warning. (OQ-2 open; defensive.)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COUNTER_FILE = ".agent/.nav-read-counter.json"

# Files in `.agent/` that Navigator itself reads during legitimate session
# start or on-demand patterns. These are exempt from the counter.
DEFAULT_ALLOWLIST = frozenset({
    "DEVELOPMENT-README.md",
    ".nav-config.json",
    ".user-profile.json",
    "knowledge/graph.json",
})

DEFAULT_WARN_THRESHOLD = 3
DEFAULT_ESCALATE_THRESHOLD = 5


def _safe_read(path: Path, max_bytes: int = 200_000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception:
        return None


def _safe_json(path: Path) -> dict | None:
    raw = _safe_read(path)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _project_root(stdin_data: dict) -> Path:
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def _hook_cfg(root: Path) -> dict:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    return cfg.get("read_guard_hook") or {}


def _resolve_agent_relative(file_path: str, root: Path) -> str | None:
    """Return the path relative to .agent/ if the file is under it, else None.

    Handles both absolute and relative file_path inputs (OQ-1 defensive).
    """
    if not file_path:
        return None
    p = Path(file_path)
    if not p.is_absolute():
        p = root / file_path
    try:
        resolved = p.resolve()
        rel = resolved.relative_to((root / ".agent").resolve())
    except (ValueError, OSError):
        return None
    return rel.as_posix()


def _is_counted(agent_rel: str, allowlist: frozenset[str]) -> bool:
    """Return True if this `.agent/`-relative path should increment the counter.

    Allowlist matches exact path-from-.agent (e.g., "DEVELOPMENT-README.md" or
    "knowledge/graph.json") — not basename. Knowledge graph subtree files
    other than graph.json (e.g., memory `.md` files) ARE counted.
    """
    return agent_rel not in allowlist


def _load_counter(root: Path) -> dict:
    data = _safe_json(root / COUNTER_FILE) or {}
    if not isinstance(data, dict):
        data = {}
    return data


def _save_counter(root: Path, data: dict) -> None:
    target = root / COUNTER_FILE
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"nav_read_guard: counter write failed: {e}", file=sys.stderr)


def _increment_counter(root: Path, session_id: str | None) -> int:
    state = _load_counter(root)
    prior_session = state.get("session_id")
    # Session change → reset (secondary reset path; primary is Stop hook).
    if session_id and prior_session and prior_session != session_id:
        state = {}
    new_count = int(state.get("turn_count", 0)) + 1
    state.update({
        "schema": 1,
        "session_id": session_id or prior_session or "",
        "turn_count": new_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_counter(root, state)
    return new_count


def _emit(text: str) -> None:
    """Dual-channel emit for OQ-2 defensive: structured JSON + plain stdout.

    Claude Code's PreToolUse output channel behavior is not fully documented.
    We emit both so whichever the harness consumes will surface the warning.
    """
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        },
    }
    print(json.dumps(payload))
    # Also emit plain text on a separate line in case stdout-text injection
    # is the path that surfaces. The structured JSON above is well-formed
    # on its own; this trailing text is harmless if discarded.
    print(text)


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
        # Not a Navigator project — fully silent.
        return 0

    cfg = _hook_cfg(root)
    if cfg.get("enabled", True) is False:
        return 0

    # Defensive: only act on Read tool calls.
    if stdin_data.get("tool_name") != "Read":
        return 0

    tool_input = stdin_data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str) or not file_path:
        return 0

    agent_rel = _resolve_agent_relative(file_path, root)
    if agent_rel is None:
        # Outside .agent/ — ignore.
        return 0

    allowlist_cfg = cfg.get("allowlist")
    if isinstance(allowlist_cfg, list):
        allowlist = frozenset(str(x) for x in allowlist_cfg)
    else:
        allowlist = DEFAULT_ALLOWLIST

    if not _is_counted(agent_rel, allowlist):
        # Allowlisted — counts toward zero.
        return 0

    warn_at = int(cfg.get("warn_threshold", DEFAULT_WARN_THRESHOLD))
    escalate_at = int(cfg.get("escalate_threshold", DEFAULT_ESCALATE_THRESHOLD))

    session_id = stdin_data.get("session_id")
    count = _increment_counter(root, session_id)

    if count >= escalate_at:
        _emit(
            f"[nav-read-guard] {count} .agent/ files read this turn. "
            "This matches the bulk-load anti-pattern (risk: 50k+ tokens). "
            "Stop sequential reads. Use a Task or Explore agent for "
            "multi-file discovery — it reads excerpts, not full files."
        )
    elif count >= warn_at:
        _emit(
            f"[nav-read-guard] {count} .agent/ files read this turn. "
            "Navigator lazy-loading pattern: load only what the current task "
            "needs. For broader surveys, use a Task or Explore agent."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
