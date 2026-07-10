#!/usr/bin/env python3
"""Character budgets for hook-injected context (TASK-59, Phase 5).

The v7 routing matrix caps what each event may inject into model context:
SessionStart gets the big navigator payload, SubagentStart the 2k-char
context slice proven viable in the TASK-57 spike (mem-052). ``clamp``
enforces those caps with an explicit truncation marker so a cut payload
is visibly cut, never silently corrupted mid-sentence.

Pure stdlib. Never writes to stderr (mem-034 — ``sentinels.py`` owns it).
"""
from __future__ import annotations

# Per-event injection budgets in characters (v7 routing matrix).
BUDGETS = {
    "SessionStart": 9500,
    "SubagentStart": 2000,
}

TRUNCATION_MARKER = "\n[truncated by nav budget]"


def clamp(text: str, event: str) -> str:
    """Clamp ``text`` to the budget for ``event``.

    - Events without a budget entry pass through unchanged.
    - Within budget: returned as-is.
    - Over budget: truncated so ``len(result) <= BUDGETS[event]``, ending
      with ``TRUNCATION_MARKER``. The cut lands on the last complete line
      that fits; only a single line too long to fit at all is cut mid-line.
    """
    if text is None:
        return ""
    budget = BUDGETS.get(event)
    if budget is None or len(text) <= budget:
        return text

    room = budget - len(TRUNCATION_MARKER)
    if room <= 0:
        # Budget smaller than the marker itself — degenerate; hard cut.
        return text[:budget]

    head = text[:room]
    cut = head.rfind("\n")
    if cut > 0:
        # Never mid-line when a complete earlier line fits.
        head = head[:cut]
    return head + TRUNCATION_MARKER
