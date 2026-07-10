#!/usr/bin/env python3
"""jit_memory op — hook-code pitfall injector (TASK-62 Phase 3, S1-gated).

PostToolUse injector (registry matcher Edit|Write|MultiEdit|NotebookEdit):
when an edit touched a Python file under ``hooks/`` — the Navigator hook
runtime itself — inject a DECLARATIVE one-liner summary of mem-034 + mem-035
at the tool-result position, once per session.

Channel verdict (mem-050, S1 PASS, CC 2.1.205): PostToolUse
``hookSpecificOutput.additionalContext`` DELIVERS to the model, superseding
mem-035 for this sub-channel. Content must be DECLARATIVE — imperative
instructions delivered tool-adjacent are flagged by the model as prompt
injection and refused (2/2 spike runs). The constant below states facts only.

Dedupe: ``jit.injected[]`` in the schema-2 runtime state. The section is
session-scoped (state.SESSION_SCOPED_SECTIONS), so "once per session" falls
out of the fail-closed session gate; a second qualifying edit in the same
session injects nothing.

Scope note: the TASK-62 brief says "edits touching hooks/*.py"; this op
matches ANY ``.py`` under ``hooks/`` (nav_dispatch.py, nav_hook_lib/, ops/)
because mem-034/035 constrain all hook-runtime code, not just the top level.

Config: ``jit_memory.enabled`` — seeded False in config.DEFAULTS (v7 policy:
injecting features ship OFF); the runtime owns the gate via OpSpec.config_key.
No ctx.pilot_executor check on purpose: the injection is declarative and
non-blocking, and Pilot's autonomous runs face the same pitfalls.
"""
from __future__ import annotations

import re
from pathlib import Path

from nav_hook_lib import hio

# The two memories this injector delivers (dedupe keys in jit.injected[]).
MEMORY_IDS = ("mem-034", "mem-035")

# Project-relative POSIX paths that count as Navigator hook code.
HOOK_FILE_RE = re.compile(r"^hooks/.+\.py$")

# DECLARATIVE one-liner summaries (mem-050 constraint: facts only, no
# imperatives — imperative tool-adjacent context is refused as injection).
PITFALL_CONTEXT = (
    "Recorded Navigator pitfalls for code under hooks/ (knowledge graph, "
    "injected once per session):\n"
    "- mem-034 (pitfall, 1.0): a UserPromptSubmit hook that exits 2 blocks "
    "the model from running entirely, and stderr that echoes the trigger "
    "phrase verbatim re-triggers the block recursively on later prompts.\n"
    "- mem-035 (pitfall, 1.0): PreToolUse/PostToolUse plain stdout and "
    "additionalContext were silently dropped in v6 (live-verified v6.12.0); "
    "the TASK-57 spike memories, not harness docs, are the record of which "
    "hookSpecificOutput sub-channels actually deliver."
)


def _edited_hook_file(payload: dict, root: Path):
    """Project-relative path when this edit touched hooks/**.py, else None."""
    tool_input = payload.get("tool_input") or {}
    candidate = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(candidate, str) or not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = root / candidate
    try:
        rel = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None  # outside the project — not our hook code
    rel_posix = rel.as_posix()
    if not HOOK_FILE_RE.match(rel_posix):
        return None
    return rel_posix


def run(ctx):
    payload = ctx.payload
    root = hio.project_root(payload)
    if _edited_hook_file(payload, root) is None:
        return None

    jit = ctx.state.setdefault("jit", {})
    injected = jit.get("injected")
    if not isinstance(injected, list):
        injected = []
        jit["injected"] = injected
    if all(mem_id in injected for mem_id in MEMORY_IDS):
        return None  # already delivered this session (jit.injected[] dedupe)

    for mem_id in MEMORY_IDS:
        if mem_id not in injected:
            injected.append(mem_id)
    return {"additional_context": PITFALL_CONTEXT}
