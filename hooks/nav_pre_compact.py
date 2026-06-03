#!/usr/bin/env python3
"""
Navigator PreCompact hook — compact-resilient marker writer.

Fires before manual `/compact` or auto-compact. Reads the conversation
transcript, extracts a heuristic summary, captures git state, and writes
a marker to `.agent/.context-markers/` along with the `.active` pointer.

On the next session start, `hooks/nav_session_start.py` picks up `.active`
and surfaces the marker for restore — so context survives both manual and
auto-compacts.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#precompact
- stdin JSON includes: cwd, transcript_path, session_id, trigger ("manual"|"auto")
- Always exit 0 — never block compact (exit 2 on auto-compact surfaces the
  underlying API error and breaks the session).
- stdout is empty JSON `{}` — we don't inject context, we write a file.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Utilities (mirror nav_session_start.py for cross-hook consistency)
# ──────────────────────────────────────────────────────────────────────────────

def _safe_read(path: Path, max_bytes: int = 200_000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception as e:
        print(f"nav_pre_compact: skip {path}: {e}", file=sys.stderr)
        return None


def _safe_json(path: Path) -> dict | None:
    raw = _safe_read(path)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"nav_pre_compact: invalid JSON in {path}: {e}", file=sys.stderr)
        return None


def _project_root(stdin_data: dict) -> Path:
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def _read_hook_config(root: Path) -> dict:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    hook_cfg = cfg.get("compact_hook") or {}
    return {
        "enabled": hook_cfg.get("enabled", True),
        "include_transcript_summary": hook_cfg.get("include_transcript_summary", True),
        "include_git_state": hook_cfg.get("include_git_state", True),
        "char_budget": int(hook_cfg.get("char_budget", 8000)),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Heuristic transcript summarization (mirrors marker_compressor.py)
# ──────────────────────────────────────────────────────────────────────────────

def _flatten_transcript(transcript_path: Path) -> str:
    """Read the JSONL transcript and flatten to plain text for heuristic scan."""
    if not transcript_path.is_file():
        return ""
    lines_out: list[str] = []
    try:
        with transcript_path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    lines_out.append(raw)
                    continue
                # Claude Code transcripts: nested message.content with various shapes
                msg = obj.get("message") or obj
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, str):
                    lines_out.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            text = block.get("text") or block.get("input") or block.get("output")
                            if isinstance(text, str):
                                lines_out.append(text)
                            elif text is not None:
                                lines_out.append(json.dumps(text, default=str)[:2000])
    except Exception as e:
        print(f"nav_pre_compact: transcript flatten failed: {e}", file=sys.stderr)
        return ""
    return "\n".join(lines_out)


# Path-shaped token: a slash/word run ending in a known source extension at a
# word boundary. Real path characters must precede the dot, so prose like
# "see the .py docs" is NOT captured while "hooks/token_monitor.py" is.
_PATH_RE = re.compile(r"[\w./-]+\.(?:tsx|json|md|ts|py|sh|js)\b")


def _compress_context(text: str, max_length: int = 5000) -> str:
    """Heuristic compressor — files/code/errors/recent context. Mirrors
    skills/nav-marker/functions/marker_compressor.py."""
    if not text:
        return "_[transcript unavailable]_"

    lines = text.split("\n")
    # Sample head + tail so paths/markers from both the conversation's start
    # (task setup) and end (recent work) survive; only the mid-section is
    # dropped when the transcript is long.
    scan_lines = lines[:100] + lines[-100:] if len(lines) > 200 else lines

    code_blocks: list[str] = []
    file_paths: list[str] = []
    errors: list[str] = []

    in_code_block = False
    code_buffer: list[str] = []

    for line in scan_lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code_block:
                code_blocks.append("\n".join(code_buffer))
                code_buffer = []
            in_code_block = not in_code_block
        elif in_code_block:
            code_buffer.append(line)

        file_paths.extend(_PATH_RE.findall(line))

        low = line.lower()
        if "error" in low or "failed" in low or "traceback" in low:
            errors.append(stripped)

    # "Recent" = the true tail of the transcript, independent of sampling.
    recent_context = lines[-20:]

    parts: list[str] = []
    if file_paths:
        unique = list(dict.fromkeys(file_paths))[:10]
        parts.append("**Files/paths mentioned**:\n" + "\n".join(unique))
    if code_blocks:
        parts.append("**Code snippets**:\n```\n" + "\n\n".join(code_blocks[:3]) + "\n```")
    if errors:
        unique_err = list(dict.fromkeys(errors))[:5]
        parts.append("**Errors / issues**:\n" + "\n".join(unique_err))
    parts.append("**Recent conversation**:\n" + "\n".join(recent_context))

    compressed = "\n\n---\n\n".join(parts)
    if len(compressed) > max_length:
        compressed = compressed[:max_length] + "\n\n[... truncated ...]"
    return compressed


# ──────────────────────────────────────────────────────────────────────────────
# Git state capture
# ──────────────────────────────────────────────────────────────────────────────

def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception as e:
        print(f"nav_pre_compact: git {args} failed: {e}", file=sys.stderr)
        return None


def _git_state(root: Path) -> str:
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root) or "(unknown)"
    head = _git(["log", "-1", "--oneline"], root) or "(no commits)"
    status = _git(["status", "--short"], root) or ""
    recent = _git(["log", "--oneline", "-5"], root) or ""

    parts = [
        f"**Branch**: `{branch}`",
        f"**HEAD**: `{head}`",
    ]
    if status:
        parts.append("**Working tree**:\n```\n" + status + "\n```")
    else:
        parts.append("**Working tree**: clean")
    if recent:
        parts.append("**Recent commits**:\n```\n" + recent + "\n```")
    return "\n\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# Active task hint
# ──────────────────────────────────────────────────────────────────────────────

def _active_task_hint(root: Path) -> str | None:
    tasks_dir = root / ".agent" / "tasks"
    if not tasks_dir.is_dir():
        return None
    candidates: list[str] = []
    try:
        for p in sorted(tasks_dir.glob("*.md")):
            if p.name.upper().startswith("README"):
                continue
            head = _safe_read(p, max_bytes=400) or ""
            low = head.lower()
            if "in progress" in low or "in-progress" in low or "🚧" in head:
                title = next(
                    (line.lstrip("# ").strip() for line in head.splitlines() if line.startswith("#")),
                    p.stem,
                )
                candidates.append(f"- `{p.name}` — {title}")
            if len(candidates) >= 5:
                break
    except Exception:
        return None
    if not candidates:
        return None
    return "**In-progress tasks**:\n" + "\n".join(candidates)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def _build_marker(stdin_data: dict, root: Path, cfg: dict) -> tuple[str, str]:
    """Return (filename, body) for the marker file."""
    trigger = stdin_data.get("trigger") or "manual"
    if trigger not in ("manual", "auto"):
        trigger = "manual"
    session_id = stdin_data.get("session_id") or "unknown"
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"before-compact-{trigger}-{ts}.md"

    header_lines = [
        f"# Before Compact ({trigger})",
        "",
        f"**Date**: {datetime.now().isoformat(timespec='seconds')}",
        f"**Trigger**: `{trigger}` ({'user ran /compact' if trigger == 'manual' else 'Claude Code auto-compacted'})",
        f"**Session**: `{session_id}`",
        "",
        "_Written by Navigator PreCompact hook. The companion PostCompact hook will append Claude Code's summary below once compact completes._",
        "",
    ]

    sections: list[str] = ["\n".join(header_lines)]

    if cfg["include_git_state"]:
        sections.append("## Git State\n\n" + _git_state(root))

    task_hint = _active_task_hint(root)
    if task_hint:
        sections.append("## Active Tasks\n\n" + task_hint)

    if cfg["include_transcript_summary"]:
        tpath_raw = stdin_data.get("transcript_path")
        if tpath_raw:
            tpath = Path(tpath_raw).expanduser()
            flat = _flatten_transcript(tpath)
            summary = _compress_context(flat, max_length=cfg["char_budget"] - 1000)
        else:
            summary = "_[transcript_path not provided]_"
        sections.append("## Conversation Summary (heuristic)\n\n" + summary)

    body = "\n\n---\n\n".join(sections) + "\n"
    if len(body) > cfg["char_budget"]:
        body = body[: cfg["char_budget"] - 60] + "\n\n[... truncated to char budget ...]\n"
    return filename, body


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

    cfg = _read_hook_config(root)
    if not cfg["enabled"]:
        print(json.dumps({}))
        return 0

    try:
        markers_dir = root / ".agent" / ".context-markers"
        markers_dir.mkdir(parents=True, exist_ok=True)

        filename, body = _build_marker(stdin_data, root, cfg)
        marker_path = markers_dir / filename
        marker_path.write_text(body, encoding="utf-8")

        active_path = markers_dir / ".active"
        active_path.write_text(filename + "\n", encoding="utf-8")

        print(f"nav_pre_compact: wrote {marker_path}", file=sys.stderr)
    except Exception as e:
        print(f"nav_pre_compact: failed to write marker: {e}", file=sys.stderr)

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
