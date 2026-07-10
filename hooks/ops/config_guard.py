#!/usr/bin/env python3
"""config_guard op — .nav-config.json validation warning (TASK-62 Phase 5).

ConfigChange responder on the systemMessage channel — no spike dependency in
the routing matrix (no mem-05x verdict required); the EVENT registration went
through the TASK-62 validate-or-drop step (`claude plugin validate` on CC
2.1.205 accepted ConfigChange — registration kept).

Behavior: on any ConfigChange event, re-parse ``.agent/.nav-config.json`` as
written on disk. Invalid JSON (or a non-object top level) yields ONE
``system_message`` warning naming the parse position; a missing/empty file is
legal (layered DEFAULTS apply) and a parseable file is silent. The warning is
user-facing state description, never payload text (mem-034: nothing from the
event payload is echoed).

Config: ``config_guard.enabled`` — seeded True in config.DEFAULTS (a
validation warning is a safety surface, not an injecting feature). No
ctx.pilot_executor gate: a broken config under Pilot degrades every feature
to defaults silently — the warning is MORE valuable there, and it blocks
nothing.
"""
from __future__ import annotations

import json

from nav_hook_lib import hio

CONFIG_RELPATH = ".agent/.nav-config.json"


def _invalid_detail(raw: str):
    """Parse-failure description for the warning, or None when valid."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return f"invalid JSON at line {exc.lineno} column {exc.colno}"
    except ValueError:
        return "invalid JSON"
    if not isinstance(data, dict):
        return f"top level is {type(data).__name__}, expected a JSON object"
    return None


def run(ctx):
    root = hio.project_root(ctx.payload)
    raw = hio.safe_read(root / ".agent" / ".nav-config.json")
    if raw is None or not raw.strip():
        return None  # absent/empty config is legal — DEFAULTS apply

    detail = _invalid_detail(raw)
    if detail is None:
        return None

    return {
        "system_message": (
            f"nav-config: {CONFIG_RELPATH} is unreadable ({detail}); "
            "Navigator is running on built-in defaults until the file parses."
        )
    }
