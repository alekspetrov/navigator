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


def _last_assistant_text(stdin_data: dict) -> str:
    """Prefer the inline last_assistant_message if Claude Code provides it;
    otherwise scan the JSONL transcript for the most recent assistant entry."""
    inline = stdin_data.get("last_assistant_message")
    if isinstance(inline, str) and inline.strip():
        return inline

    tpath = stdin_data.get("transcript_path")
    if not tpath:
        return ""
    p = Path(tpath).expanduser()
    raw = _safe_read(p, max_bytes=500_000)
    if not raw:
        return ""

    # Scan from the end backward for the last assistant message.
    chunks: list[str] = []
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
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    chunks.append(block["text"])
        if chunks:
            break
    return "\n".join(chunks)


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

    text = _last_assistant_text(stdin_data)
    check_shown = bool(WORKFLOW_CHECK_RE.search(text))
    nav_status = bool(NAV_STATUS_RE.search(text))
    phase_match = LOOP_PHASE_RE.search(text)
    phase = phase_match.group(1) if phase_match else None

    state = {
        "schema": 1,
        "session_id": stdin_data.get("session_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_turn": {
            "check_shown": check_shown,
            "nav_status_shown": nav_status,
            "loop_phase": phase,
            "assistant_text_chars": len(text),
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

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
