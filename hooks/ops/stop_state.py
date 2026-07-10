#!/usr/bin/env python3
"""stop_state op — Stop-event turn recorder + THE turn-lifecycle reset barrel.

Parity port of hooks/nav_workflow_state.py (TASK-61 Phase 5, coupled with
ops/prompt_gate.py — mem-037: the pair never splits). Behavior:

  - Reads the last assistant turn (inline ``last_assistant_message`` first,
    else the transcript tail via nav_hook_lib.transcript) and stamps the
    TRISTATE ``turn.signals.check_shown``:
        True   only when the WORKFLOW CHECK sentinel was emitted;
        False  only when the turn used a codebase-mutating tool WITHOUT it;
        None   for conversational/question-only turns (never stamp — the
               v6.15.3 AskUserQuestion deadlock fix, mem-037).
  - Resets the turn-lifecycle slots in ONE audited code path
    (``reset_turn_slots``): the read-guard counter (``reads.turn_count``),
    the Tier-1 fuse slot (``completion.tier1_fuse``) and the
    continue-counter slot (``completion.held_count``). The fuse/counter
    slots are consumed by TASK-62; their reset semantics land here so Stop
    is the single reset writer from day one.
  - Returns ``{"ack": True}`` so the dispatcher emits the bare ``{}`` doc —
    the recorded v6 acknowledgment shape (golden: stop_state.json).

State moves from v6's .nav-workflow-state.json / .nav-read-counter.json to
the schema-2 runtime state (ctx.state) — the one sanctioned parity delta.
mem-034 discipline: assistant text is sentinels.strip_all()'d BEFORE any
pattern scan, so an echoed block notice (whose body mentions "workflow
check") can never fake a True stamp.

No ctx.pilot_executor check on purpose: v6 ran this recorder under Pilot
too (it blocks nothing), and the runtime belt covers blocking keys anyway.
"""
from __future__ import annotations

import re

from nav_hook_lib import config, sentinels, transcript

# Sentinel patterns from v6 nav_workflow_state.py (verbatim).
WORKFLOW_CHECK_RE = re.compile(r"WORKFLOW\s+CHECK", re.IGNORECASE)
NAV_STATUS_RE = re.compile(r"NAVIGATOR_STATUS", re.IGNORECASE)
LOOP_PHASE_RE = re.compile(r"\bPhase:\s*(INIT|RESEARCH|IMPL|VERIFY|COMPLETE)\b")

# Tool names that indicate the assistant turn acted on the codebase. Only
# when one of these appears (and no CHECK block is shown) do we record
# check_shown=False (v6.15.3 tristate fix).
TASK_ACTION_TOOLS = frozenset({
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "Bash",
    "Task",
    "Agent",
})


def _last_assistant_turn(payload: dict):
    """(text, tool_names) — inline last_assistant_message wins (v6 order)."""
    inline = payload.get("last_assistant_message")
    if isinstance(inline, str) and inline.strip():
        return inline, set()
    tpath = payload.get("transcript_path")
    if not tpath:
        return "", set()
    return transcript.last_assistant_turn(tpath)


def reset_turn_slots(ctx) -> None:
    """THE single audited turn-lifecycle reset path (TASK-61 Phase 5).

    Stop is the only writer that resets these slots — no other op may:
      - reads.turn_count -> 0 (v6 _reset_read_counter; skipped, exactly as
        in v6, when read_guard_hook.enabled is explicitly false);
      - completion.tier1_fuse -> False (Tier-1 single-shot fuse slot,
        consumed by TASK-62 prompt_tier1/stop_completion);
      - completion.held_count -> 0 (continue-counter slot, consumed by
        TASK-62 stop_completion; capped there by max_continues).
    """
    if config.get(ctx.config, "read_guard_hook.enabled", True) is not False:
        ctx.state["reads"] = {"turn_count": 0}
    completion = ctx.state.get("completion")
    if not isinstance(completion, dict):
        completion = {}
        ctx.state["completion"] = completion
    completion["tier1_fuse"] = False
    completion["held_count"] = 0


def run(ctx):
    # stop_hook_active guard (v6): already inside a Stop chain — acknowledge
    # and do nothing (no stamp, no resets), exactly like the v6 early exit.
    if ctx.payload.get("stop_hook_active"):
        return {"ack": True}

    raw_text, tools = _last_assistant_turn(ctx.payload)
    # mem-034: never scan unstripped text — an echoed block notice mentions
    # "workflow check" and would fake check_shown=True on the raw text.
    text = sentinels.strip_all(raw_text)

    check_present = bool(WORKFLOW_CHECK_RE.search(text))
    nav_status = bool(NAV_STATUS_RE.search(text))
    phase_match = LOOP_PHASE_RE.search(text)
    phase = phase_match.group(1) if phase_match else None

    # Tristate check_shown (mem-037) — see module docstring.
    if check_present:
        check_shown = True
    elif tools & TASK_ACTION_TOOLS:
        check_shown = False
    else:
        check_shown = None

    ctx.state["turn"] = {
        "signals": {
            "check_shown": check_shown,
            "nav_status_shown": nav_status,
            "loop_phase": phase,
        },
        "assistant_text_chars": len(text),
        "tools_used": sorted(tools),
    }

    reset_turn_slots(ctx)
    return {"ack": True}
