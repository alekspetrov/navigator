#!/usr/bin/env python3
"""
Navigator workflow-state writer hook (Opp 2 / v6.11.0).

Fires on every `Stop` event (after every assistant turn). Reads the last
assistant message from `transcript_path`, detects whether the WORKFLOW
CHECK block sentinel was emitted, and writes
`.agent/.nav-workflow-state.json`. This is silent infrastructure for
v6.12+'s blocking workflow_enforcer (Opp 1) — that hook will read this
state file to decide whether to block UserPromptSubmit when a loop
trigger appears.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#stop
- stdin JSON: session_id, transcript_path, stop_hook_active, last_assistant_message
- Exit 0 always — never block turn completion.
- Output empty JSON `{}` — pure side effect.
- IMPORTANT: never set decision="block" here; that would risk infinite loops.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Sentinel patterns we look for in assistant output. WORKFLOW CHECK uses a
# Unicode box drawing header that's unmistakable; NAVIGATOR_STATUS is the
# loop-mode block.
WORKFLOW_CHECK_RE = re.compile(r"WORKFLOW\s+CHECK", re.IGNORECASE)
NAV_STATUS_RE = re.compile(r"NAVIGATOR_STATUS", re.IGNORECASE)
LOOP_PHASE_RE = re.compile(r"\bPhase:\s*(INIT|RESEARCH|IMPL|VERIFY|COMPLETE)\b")

# Tool names that indicate the assistant turn acted on the codebase. Only
# when one of these appears (and no CHECK block is shown) do we record
# check_shown=False. Question-only or conversational turns leave the field
# as None ("not applicable") so the enforcer doesn't block the next prompt.
# See mem-035 / TASK-41-followup.
TASK_ACTION_TOOLS = frozenset({
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "Bash",
    "Task",
    "Agent",
})


def _safe_read(path: Path, max_bytes: int = 200_000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[-max_bytes:]
    except Exception as e:
        print(f"nav_workflow_state: skip {path}: {e}", file=sys.stderr)
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


def _hook_enabled(root: Path) -> bool:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    hook_cfg = cfg.get("workflow_state_hook") or {}
    return hook_cfg.get("enabled", True)


def _reset_read_counter(root: Path, session_id: str | None) -> None:
    """Reset .agent/.nav-read-counter.json on Stop (TASK-40 / v6.12.0).

    The read-guard hook (`nav_read_guard.py`) counts non-allowlisted .agent/
    reads per turn. This Stop hook clears the counter so the next turn starts
    at zero. Guarded by read_guard_hook.enabled so projects without the
    counter are unaffected.
    """
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    guard_cfg = cfg.get("read_guard_hook") or {}
    if guard_cfg.get("enabled", True) is False:
        return
    counter_path = root / ".agent" / ".nav-read-counter.json"
    payload = {
        "schema": 1,
        "session_id": session_id or "",
        "turn_count": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        counter_path.parent.mkdir(parents=True, exist_ok=True)
        counter_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"nav_workflow_state: counter reset failed: {e}", file=sys.stderr)


def _last_assistant_turn(stdin_data: dict) -> tuple[str, set[str]]:
    """Return (text, tool_names) for the most recent assistant turn.

    Falls back to inline `last_assistant_message` when Claude Code provides
    it (text only, no tool info available in that path).
    """
    inline = stdin_data.get("last_assistant_message")
    if isinstance(inline, str) and inline.strip():
        return inline, set()

    tpath = stdin_data.get("transcript_path")
    if not tpath:
        return "", set()
    p = Path(tpath).expanduser()
    raw = _safe_read(p, max_bytes=500_000)
    if not raw:
        return "", set()

    # Scan from the end backward for the last assistant message.
    chunks: list[str] = []
    tools: set[str] = set()
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message") or obj
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if isinstance(block.get("text"), str):
                    chunks.append(block["text"])
                if block.get("type") == "tool_use" and isinstance(block.get("name"), str):
                    tools.add(block["name"])
        if chunks or tools:
            break
    return "\n".join(chunks), tools


def main() -> int:
    raw_stdin = sys.stdin.read() if not sys.stdin.isatty() else ""
    stdin_data: dict[str, Any] = {}
    if raw_stdin.strip():
        try:
            stdin_data = json.loads(raw_stdin)
        except json.JSONDecodeError:
            stdin_data = {}

    # Guard against the stop_hook_active loop trap. This hook never returns
    # decision="block", so it cannot create a loop — but be defensive anyway.
    if stdin_data.get("stop_hook_active"):
        # Already in a Stop chain; no further action needed.
        print(json.dumps({}))
        return 0

    root = _project_root(stdin_data)
    if not (root / ".agent").is_dir():
        print(json.dumps({}))
        return 0

    if not _hook_enabled(root):
        print(json.dumps({}))
        return 0

    text, tools = _last_assistant_turn(stdin_data)
    check_present = bool(WORKFLOW_CHECK_RE.search(text))
    nav_status = bool(NAV_STATUS_RE.search(text))
    phase_match = LOOP_PHASE_RE.search(text)
    phase = phase_match.group(1) if phase_match else None

    # Tristate check_shown: True if CHECK block emitted; False only when the
    # turn actually attempted task work (codebase-mutating tools) without
    # showing it; None ("n/a") for conversational/question-only turns so the
    # enforcer doesn't block the next prompt. Fixes the AskUserQuestion
    # deadlock where declining a clarifier + a loop-trigger prompt left no
    # way out. See mem-035.
    if check_present:
        check_shown: bool | None = True
    elif tools & TASK_ACTION_TOOLS:
        check_shown = False
    else:
        check_shown = None

    state = {
        "schema": 1,
        "session_id": stdin_data.get("session_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_turn": {
            "check_shown": check_shown,
            "nav_status_shown": nav_status,
            "loop_phase": phase,
            "assistant_text_chars": len(text),
            "tools_used": sorted(tools),
        },
    }

    state_path = root / ".agent" / ".nav-workflow-state.json"
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as e:
        print(f"nav_workflow_state: write failed: {e}", file=sys.stderr)

    # Per-turn cleanup: reset the read-guard counter so the next turn starts
    # at zero. Silent no-op if read_guard_hook is disabled.
    _reset_read_counter(root, stdin_data.get("session_id"))

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
