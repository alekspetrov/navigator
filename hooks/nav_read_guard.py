#!/usr/bin/env python3
"""
Navigator `.agent/` bulk-read guard (Opp 6 / v6.12.0).

Fires on `PreToolUse` Read. Counts non-allowlisted reads of `.agent/` files
per turn and emits an escalating warning when the count crosses thresholds.

The tail-risk this prevents: sequential bulk-loads of `.agent/` documentation
(tasks, SOPs, system docs) that can consume 50k+ tokens in a single turn and
crash mid-session — the exact anti-pattern Navigator's lazy-loading strategy
exists to avoid.

Behavior (v6.12.1+):
  - Counter file: `.agent/.nav-read-counter.json` (per-session, reset on Stop)
  - Allowlist (do not count): DEVELOPMENT-README.md, .nav-config.json,
    .user-profile.json, knowledge/graph.json
  - Warn at count >= warn_threshold (default 3): stderr advisory, exit 0
  - Escalate at count >= escalate_threshold (default 5):
      * strict_block=true (default) → exit 2, sentinel-wrapped stderr block
      * strict_block=false → stderr advisory only, exit 0
  - Counter satisfies mem-027's three-condition gate: this hook writes the
    state file on prior invocations; reading count >= threshold IS state-file
    confirmation that violations already occurred this turn.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#pretooluse
  - stdin JSON: tool_name, tool_input.file_path, cwd, session_id
  - file_path may be absolute OR relative (handled per mem-027 discipline).
  - Output channel: stderr only. mem-035 confirmed PreToolUse stdout AND
    hookSpecificOutput.additionalContext are silent to the model. Block
    (exit 2) is the only behavior-affecting channel; warn (exit 0) text on
    stderr surfaces in the CC UI but does not influence model behavior.
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
# Primary counter reset is the Stop hook; if Stop did not fire (mem-036), a
# stale counter from a prior turn must not block this turn's legitimate reads.
# Treat the counter as fresh-from-zero once its last update predates this window.
DEFAULT_STALE_AFTER_SECONDS = 300


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


def _is_stale(updated_at: str | None, stale_after_s: int) -> bool:
    """True when the counter's last update predates the staleness window.

    Guards against a missed Stop reset (mem-036): a stale counter would
    otherwise persist into the next turn and falsely block. Missing or
    unparseable timestamps are treated as NOT stale (preserve prior behavior).
    """
    if not updated_at or stale_after_s <= 0:
        return False
    try:
        ts = datetime.fromisoformat(updated_at)
    except (ValueError, TypeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age > stale_after_s


def _increment_counter(
    root: Path, session_id: str | None, stale_after_s: int = DEFAULT_STALE_AFTER_SECONDS
) -> int:
    state = _load_counter(root)
    prior_session = state.get("session_id")
    # Reset when the session changed (secondary path; primary is the Stop hook)
    # or when the prior count is stale (Stop may not have fired — mem-036).
    if session_id and prior_session and prior_session != session_id:
        state = {}
    elif _is_stale(state.get("updated_at"), stale_after_s):
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


# Sentinel for stderr — distinct from workflow_enforcer's <nav-workflow-block>
# so future strip logic doesn't accidentally consume read-guard messages.
NAV_READ_BLOCK_OPEN = "<nav-read-guard-block>"
NAV_READ_BLOCK_CLOSE = "</nav-read-guard-block>"


def _warn(text: str) -> None:
    """Soft-warn output goes to stderr (PreToolUse stdout/additionalContext are
    silent to the model per mem-035). Exit 0 — Read still completes.
    """
    sys.stderr.write(text + "\n")


def _block(count: int, threshold: int) -> None:
    """Hard-block output: sentinel-wrapped, user-addressed stderr per mem-034.

    Block is the only behavior-affecting PreToolUse output channel — exit 2
    refuses the Read tool call. The message addresses the USER (Claude can
    technically continue after the tool error, but the user needs to choose
    a recovery path).

    Deliberately omits the triggering file_path — keeps the message free of
    arbitrary substrings that could become future recursive-trigger surfaces.
    """
    sys.stderr.write(
        NAV_READ_BLOCK_OPEN + "\n"
        f"Navigator nav-read-guard: blocked at {count} .agent/ reads "
        f"(escalate_threshold={threshold}).\n"
        "  Why: this turn has crossed the bulk-load threshold. Sequential "
        ".agent/ reads risk 50k+ token consumption and session crash.\n"
        "  How to proceed (your choice):\n"
        "    1. Use a Task or Explore agent for the remaining lookups — "
        "they read excerpts, not full files, and are designed for "
        "multi-file discovery.\n"
        "    2. Split the work: end this turn, start a new one (the "
        "counter resets on every Stop event).\n"
        "    3. Raise the threshold: set read_guard_hook.escalate_threshold "
        "to a higher number in .agent/.nav-config.json.\n"
        "    4. Disable strict enforcement: set read_guard_hook.strict_block"
        "=false in .agent/.nav-config.json.\n"
        + NAV_READ_BLOCK_CLOSE + "\n"
    )


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
    strict_block = cfg.get("strict_block", True)
    stale_after = int(cfg.get("stale_after_seconds", DEFAULT_STALE_AFTER_SECONDS))

    session_id = stdin_data.get("session_id")
    count = _increment_counter(root, session_id, stale_after)

    if count >= escalate_at and strict_block:
        _block(count, escalate_at)
        return 2
    if count >= escalate_at:
        _warn(
            f"[nav-read-guard] {count} .agent/ files read this turn. "
            "Bulk-load anti-pattern threshold crossed (risk: 50k+ tokens). "
            "Use a Task or Explore agent for multi-file discovery."
        )
    elif count >= warn_at:
        _warn(
            f"[nav-read-guard] {count} .agent/ files read this turn. "
            "Navigator lazy-loading pattern: load only what the task needs. "
            "For broader surveys, use a Task or Explore agent."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
