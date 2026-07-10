#!/usr/bin/env python3
"""Transcript tail-reader for Navigator hook ops (TASK-59, Phase 5).

Extracted from ``hooks/nav_workflow_state.py`` (``_safe_read`` +
``_last_assistant_turn``) so every v7 op shares one reader instead of
re-implementing JSONL tail parsing. Behavior is parity-locked against the
v6 logic on a recorded fixture (see ``test_transcript.py``): same tail
slice, same JSON-line tolerance, same backward scan for the last
assistant turn.

Pure stdlib. Never writes to stderr — ``sentinels.py`` owns stderr
emission (mem-034); all failures here degrade to empty results.
"""
from __future__ import annotations

import json
from pathlib import Path

# v6 reads at most this many characters from the end of the transcript.
# (v6 named the parameter max_bytes but sliced the *decoded string* — so it
# is a character count; kept as-is for parity on multibyte content.)
DEFAULT_TAIL_CHARS = 500_000


def tail_text(path, max_chars: int = DEFAULT_TAIL_CHARS) -> str:
    """Last ``max_chars`` characters of ``path``; '' if missing/unreadable.

    Mirrors v6 ``_safe_read`` (utf-8, errors='replace', tail slice) except
    it returns '' instead of None and never prints to stderr.
    """
    try:
        p = Path(path).expanduser()
        if not p.is_file():
            return ""
        return p.read_text(encoding="utf-8", errors="replace")[-max_chars:]
    except Exception:
        return ""


def tail_entries(path, max_chars: int = DEFAULT_TAIL_CHARS) -> list:
    """Parsed JSON-line entries from the tail of a transcript file.

    Blank and undecodable lines are skipped — a tail slice may cut the
    first line mid-record; that partial line fails ``json.loads`` and is
    dropped, exactly as in the v6 reader. Non-dict top-level values (legal
    JSON, never emitted by the harness) are skipped too, so downstream
    ``.get`` calls are safe. Entries come back in file order.
    """
    entries = []
    for line in tail_text(path, max_chars).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def last_assistant_turn(path, max_chars: int = DEFAULT_TAIL_CHARS):
    """``(text, tool_names)`` for the most recent assistant turn.

    Parity port of the transcript-path branch of
    ``nav_workflow_state._last_assistant_turn``: scan entries backward,
    stop at the first assistant message that yields text chunks or
    tool_use names; join text blocks with newlines. The inline
    ``last_assistant_message`` stdin fallback stays caller policy — ops
    should prefer that field when the harness provides it.

    Missing/empty/unreadable transcript -> ``("", set())``.
    """
    chunks: list = []
    tools: set = set()
    for obj in reversed(tail_entries(path, max_chars)):
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
