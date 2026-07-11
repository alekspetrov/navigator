#!/usr/bin/env python3
"""
Navigator hook-runtime signals — nav-signal v3 grammar + spike-proven channels.

nav-signal v3 is the compact single-line completion/status grammar every v7 op
emits and scans:

    nav-signal:v3:{"type":"exit","success":true,"reason":"All criteria met"}

One line, prefix ``nav-signal:v3:`` followed by a compact JSON object whose
``type`` is one of exit / status / check / brief / defer. ``parse()`` also
accepts the frozen pilot-signal v2 external contract (the fenced
```` ```pilot-signal ```` JSON blocks produced by
skills/nav-loop/functions/status_generator.py and documented for exit_gate.py)
and normalizes everything to v3 dicts.

Per-channel emit helpers exist ONLY for channels a TASK-57 spike memory proved
(mem-050..055). There is deliberately NO PreToolUse plain-stdout helper:
mem-054 proved that channel dead (hook-output logging only, never
model-visible).

PreToolUse is also deliberately ABSENT from additional_context(): the only
spike-proven PreToolUse delivery shape (mem-054) bundles
``permissionDecision: 'allow'``, which silently auto-approves the tool call —
a permission bypass no v7 op needs (jit_memory injects at the PostToolUse
position per TASK-62). PreToolUse injection stays out of this API until an op
needs it AND a probe proves a shape without permission side effects. Pure
stdlib.
"""

import json
import re

V3_PREFIX = "nav-signal:v3:"
V3_TYPES = ("exit", "status", "check", "brief", "defer")

# v3 line: optional indentation, prefix, one JSON object, optional trailing
# whitespace. `.` never matches \n, and the trailing class eats a bare \r, so
# CRLF documents parse without pre-normalization. The line may be wrapped in
# an HTML comment (`<!-- nav-signal:v3:{...} -->`): GFM rendering hides
# comments in assistant output (verified live 2026-07-11), so a wrapped signal
# satisfies the Stop gate without the user ever seeing protocol noise.
_V3_LINE = re.compile(
    r"^[ \t]*(?:<!--[ \t]*)?"
    + re.escape(V3_PREFIX)
    + r"(\{.*\})[ \t]*(?:-->)?[ \t\r]*$",
    re.MULTILINE,
)

# pilot-signal v2 fenced block. Pilot's own (frozen) extraction regex is the
# stricter r'```pilot-signal\n(.+?)\n```' — ours tolerates CRLF on input
# because we only ever *read* v2; emission is v3-only.
_V2_BLOCK = re.compile(r"```pilot-signal\r?\n(.+?)\r?\n```", re.DOTALL)


def emit(sig_type, **fields):
    """Render one nav-signal v3 line for ``sig_type`` with the given fields.

    Returns a single line (no embedded newlines): compact, key-sorted JSON so
    emit output is deterministic. Raises ValueError on an unknown type or on
    reserved field names (``type``/``v`` travel in the grammar itself).
    """
    if sig_type not in V3_TYPES:
        raise ValueError(f"unknown nav-signal v3 type: {sig_type!r} (know {V3_TYPES})")
    if "type" in fields or "v" in fields:
        raise ValueError("fields 'type' and 'v' are reserved by the v3 grammar")
    payload = {"type": sig_type}
    payload.update(fields)
    return V3_PREFIX + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _normalize(raw_json):
    """JSON text -> normalized v3 dict, or None when malformed/unknown-typed."""
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("type") not in V3_TYPES:
        return None
    signal = {"v": 3}
    signal.update({key: value for key, value in data.items() if key != "v"})
    return signal


def parse(text):
    """Extract every signal in ``text`` as normalized v3 dicts, document order.

    Accepts nav-signal v3 lines AND pilot-signal v2 fenced blocks (CRLF
    tolerated for both). Malformed JSON and unknown types are skipped
    silently — parse never raises on arbitrary transcript text. Each dict
    carries ``v: 3``, its ``type``, and all payload fields.
    """
    if not text:
        return []
    found = []
    for match in _V3_LINE.finditer(text):
        signal = _normalize(match.group(1))
        if signal is not None:
            found.append((match.start(), signal))
    for match in _V2_BLOCK.finditer(text):
        raw = match.group(1).replace("\r\n", "\n").replace("\r", "")
        signal = _normalize(raw)
        if signal is not None:
            found.append((match.start(), signal))
    found.sort(key=lambda item: item[0])
    return [signal for _, signal in found]


# ---------------------------------------------------------------------------
# Per-channel emit helpers — ONLY spike-proven channels (mem-050..055).
# Each returns the exact string a hook prints on stdout for that channel.
# ---------------------------------------------------------------------------

# additionalContext delivery proven per event: SessionStart (v6-proven live in
# hooks/nav_session_start.py; headless fire proven by mem-055), SubagentStart
# (mem-052), PostToolUse (mem-050, with PostToolUseFailure inheriting the
# verdict per the routing matrix recorded in mem-050). PreToolUse is EXCLUDED
# despite mem-054: its only proven shape auto-approves the tool call
# (permission bypass) — see the module docstring.
_ADDITIONAL_CONTEXT_EVENTS = (
    "SessionStart",
    "SubagentStart",
    "PostToolUse",
    "PostToolUseFailure",
)


def stop_block(reason):
    """Stop-hook forced continuation: ``decision: block`` JSON (mem-051).

    mem-051 proved ``continue: true`` is a NO-OP for forced continuation;
    ``decision: block`` + reason is the ONLY working mechanism (the reason is
    injected as a user-role 'Stop hook feedback:' message and produces exactly
    one continuation). Callers own runaway protection: honor
    ``stop_hook_active`` in the payload and keep a single-shot fuse (mem-037).
    """
    return json.dumps({"decision": "block", "reason": reason})


def prompt_block(reason):
    """UserPromptSubmit block-as-answer: ``decision: block`` JSON (mem-053).

    The spike-proven WINNER over exit-2 stderr: zero model invocation
    (num_turns=0, zero tokens) and clean rendering. Caution from mem-053:
    Claude Code appends 'Original prompt: <trigger>' to the block message, so
    the trigger phrase re-enters the transcript regardless of hook-side
    hygiene — scanners must strip/tolerate that echo (sentinels.strip_all).
    """
    return json.dumps({"decision": "block", "reason": reason})


def additional_context(event, text):
    """``hookSpecificOutput.additionalContext`` JSON for spike-proven events.

    DECLARATIVE-ONLY constraint (mem-050 / mem-052): content must be
    declarative — facts, data, memories. Imperative instructions delivered via
    tool-adjacent additionalContext ('you MUST quote this token') are flagged
    by the model as prompt injection and refused (2/2 runs, CC 2.1.205);
    declarative facts are used normally. SubagentStart injection is treated as
    trusted context (mem-052), but keep it declarative for uniformity.

    PreToolUse raises ValueError like every other unproven event: its only
    spike-proven delivery shape (mem-054) bundles ``permissionDecision:
    'allow'``, silently auto-approving the tool call — a permission bypass no
    v7 op needs (jit_memory injects at PostToolUse position, TASK-62). It
    re-enters this API only when an op needs it AND a probe proves a shape
    without permission side effects. This helper never emits any
    permissionDecision field.

    Raises ValueError for any event without a permission-clean spike memory
    (mem-035 discipline: unproven channels are excluded from the API surface).
    """
    if event not in _ADDITIONAL_CONTEXT_EVENTS:
        raise ValueError(
            f"no spike-proven additionalContext channel for event {event!r} "
            f"(proven: {_ADDITIONAL_CONTEXT_EVENTS})"
        )
    output = {"hookEventName": event, "additionalContext": text}
    return json.dumps({"hookSpecificOutput": output})


def user_prompt_context(text):
    """UserPromptSubmit plain stdout -> model context (v6-proven channel).

    Plain stdout on UserPromptSubmit is surfaced into the model's context —
    proven live by v6's workflow_enforcer soft-warn and nav_brief NAV-BRIEF
    instruction blocks. No envelope needed; returned unchanged so all channel
    emission still routes through this module.
    """
    return text
