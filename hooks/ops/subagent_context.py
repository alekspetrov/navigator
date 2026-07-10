#!/usr/bin/env python3
"""subagent_context op — session snapshot for subagents (TASK-62 Phase 4).

SubagentStart injector (mem-052, S3 PASS, CC 2.1.205): the
``hookSpecificOutput.additionalContext`` envelope delivers into the subagent
with both-way main/subagent isolation, viable at the 2k-char budget. The
feature therefore SHIPS; had S3 failed the plan decision was to drop it
entirely (no degraded mode).

Payload: a one-paragraph session snapshot plus top-K relevant memories —

  - active task: the DEVELOPMENT-README "Current task:" line when one exists
    (cheap head-scan; no line, no sentence — never guessed from elsewhere);
  - last marker name: ``.agent/.context-markers/.active`` or, failing that,
    the most recently modified marker file;
  - top-K memories: ``memory.recall(auto=True)`` (open tasks + active marker
    concepts), K from ``knowledge_graph.max_session_memories`` (default 5).

Everything is clamped by ``budget.clamp(text, 'SubagentStart')`` (2000 chars,
mem-052 budget), then hard-cut further if the user configured
``subagent_context.budget_chars`` below 2000. The runtime re-clamps at merge
as a belt. Content is declarative (mem-052: treated as trusted context, kept
declarative for uniformity with the other injectors).

Config: ``subagent_context.enabled`` — seeded False in config.DEFAULTS (v7
policy: injecting features ship OFF); the runtime owns the gate. No
ctx.pilot_executor gate: non-blocking declarative context that Pilot's
subagents benefit from identically.
"""
from __future__ import annotations

import re
from pathlib import Path

from nav_hook_lib import budget, config, hio, memory

TOP_K_DEFAULT = 5
RECALL_TIMEOUT = 3
README_SCAN_BYTES = 20_000
ACTIVE_TASK_MAX_CHARS = 160

# "Current task: ..." line in DEVELOPMENT-README (optional bullet/bold chrome).
CURRENT_TASK_RE = re.compile(
    r"^\s*(?:[-*]\s*)?\**current task\**\s*:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _active_task(root: Path):
    """The README current-task line, or None (cheap head-scan only)."""
    text = hio.safe_read(root / ".agent" / "DEVELOPMENT-README.md",
                         max_bytes=README_SCAN_BYTES)
    if not text:
        return None
    match = CURRENT_TASK_RE.search(text)
    if not match:
        return None
    task = match.group(1).strip()
    return task[:ACTIVE_TASK_MAX_CHARS] if task else None


def _last_marker(root: Path):
    """Marker name from .active, else the newest marker file's name, else None."""
    markers_dir = root / ".agent" / ".context-markers"
    active = (hio.safe_read(markers_dir / ".active", max_bytes=200) or "").strip()
    if active:
        return active
    try:
        candidates = [path for path in markers_dir.glob("*.md") if path.is_file()]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime).name
    except Exception:
        return None


def run(ctx):
    root = hio.project_root(ctx.payload)
    agent_dir = root / ".agent"

    snapshot_parts = []
    task = _active_task(root)
    if task:
        snapshot_parts.append(f"Active task: {task}.")
    marker = _last_marker(root)
    if marker:
        snapshot_parts.append(f"Last context marker: {marker}.")

    limit = int(config.get(
        ctx.config, "knowledge_graph.max_session_memories", TOP_K_DEFAULT))
    memories = memory.recall(auto=True, agent_dir=agent_dir, limit=limit,
                             timeout_s=RECALL_TIMEOUT)

    if not snapshot_parts and not memories:
        return None  # nothing worth a subagent's budget — stay silent

    lines = ["Navigator session snapshot (main-session state, declarative):"]
    if snapshot_parts:
        lines.append(" ".join(snapshot_parts))
    if memories:
        lines.append("Relevant project memories:")
        lines.append(memories)

    text = budget.clamp("\n".join(lines), "SubagentStart")
    budget_chars = config.get(ctx.config, "subagent_context.budget_chars", None)
    if isinstance(budget_chars, int) and not isinstance(budget_chars, bool) \
            and 0 < budget_chars < len(text):
        text = text[:budget_chars]
    return {"additional_context": text}
