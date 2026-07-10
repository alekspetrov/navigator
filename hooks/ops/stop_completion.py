#!/usr/bin/env python3
"""stop_completion op — Stop-event forced-continuation gate (TASK-62 Phase 2).

Channel: mem-051 (S2, CC 2.1.205) — Stop ``continue: true`` is a NO-OP;
``decision: block`` + reason IS the forced-continuation mechanism (exactly
one continuation; the reason is injected as 'Stop hook feedback:'). The
emitter is signals.stop_block; ``continue`` is never touched here.

Dual condition (BOTH must hold to continue):
  1. completion indicators UNMET — the exit_gate.evaluate_exit vocabulary
     (code_committed, tests_passing, code_simplified, docs_updated,
     ticket_closed, marker_created) read from state ``completion.indicators``
     and evaluated by skills/nav-loop/functions/exit_gate.py when importable
     (file-location import so the op stays standalone); the vendored
     vocabulary + min-heuristics fallback below covers a missing skill tree
     (a sync test pins the vendored constants against the skill source).
  2. NO nav-signal v3 ``exit`` in the last assistant text (signals.parse over
     strip_all()'d text, mem-034; frozen pilot-signal v2 blocks also count).

Circuit breaker, layered (risk register):
  - ``completion.stop_fuse`` consumed on emit — single-shot per turn. Re-armed
    ONLY by the stop_state reset barrel at the next CLEAN turn end (when this
    gate blocks, the runtime short-circuits stop_state: a forced continuation
    is the same turn, so the fuse deliberately survives it — after a forced
    continuation the very next turn stays suppressed until the barrel runs).
  - ``completion.held_count`` capped at stop_completion.max_continues
    (default 2); reset to 0 by the same stop_state barrel (slot name verified
    against ops/stop_state.py reset_turn_slots).
  - ``stop_hook_active`` short-circuit — the harness belt mem-051 proved real.
  - NEVER continues on a turn without mutating tool_use (mem-037: stamping /
    blocking on conversational turns deadlocked the v6 enforcer). Tool names
    come from the whole turn span of the transcript (nav_hook_lib.transcript
    entries scanned back to the last real user prompt — the final assistant
    message is usually text-only, so stop_state's single-message reader would
    read every real turn as non-mutating); the mutating vocabulary is
    stop_state.TASK_ACTION_TOOLS (one vocabulary, no drift).
  - Kill switches: stop_completion.enabled AND stop_completion.continue_enabled
    must BOTH be truthy (both seed OFF in config.DEFAULTS; a missing block is
    off). ctx.pilot_executor disables unconditionally, regardless of config —
    two loop supervisors must not fight.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from nav_hook_lib import config, memory, sentinels, signals, transcript

try:  # package context (runtime imports ops.stop_completion)
    from . import stop_state
except ImportError:  # bare sibling context (unittest discovery from ops/)
    import stop_state

# Vendored from skills/nav-loop/functions/exit_gate.py (documented indicator
# vocabulary + MIN_HEURISTICS_DEFAULT). Kept in sync by a test that reads the
# skill source; used only when the file-location import below is unavailable.
INDICATOR_VOCABULARY = (
    "code_committed",
    "tests_passing",
    "code_simplified",
    "docs_updated",
    "ticket_closed",
    "marker_created",
)
MIN_HEURISTICS = 2

EXIT_GATE_RELPATH = Path("skills") / "nav-loop" / "functions" / "exit_gate.py"

DEFAULT_MAX_CONTINUES = 2


def _load_exit_gate():
    """skills/nav-loop/functions/exit_gate.py as a module, or None.

    File-location import (no sys.path mutation) resolved through the lib's
    plugin-root resolver; ANY failure degrades to the vendored fallback so
    the op is importable and functional standalone.
    """
    try:
        plugin_dir = memory._plugin_dir()  # the lib's plugin-root resolver
        if plugin_dir is None:
            return None
        path = plugin_dir / EXIT_GATE_RELPATH
        if not path.is_file():
            return None
        spec = importlib.util.spec_from_file_location("nav_loop_exit_gate", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _evaluate_heuristics(filtered: dict):
    """(heuristics_satisfied, met) via exit_gate.evaluate_exit or the fallback."""
    gate = _load_exit_gate()
    if gate is not None:
        try:
            result = gate.evaluate_exit(
                filtered, exit_signal=False, min_heuristics=MIN_HEURISTICS
            )
            met = int(result.get("heuristics_met", 0))
            return bool(result.get("heuristics_satisfied", met >= MIN_HEURISTICS)), met
        except Exception:
            pass
    met = sum(1 for name in INDICATOR_VOCABULARY if filtered.get(name))
    return met >= MIN_HEURISTICS, met


def _turn_scan(payload: dict):
    """(last_assistant_text, turn_tool_names) for the ENDING turn.

    Tool names are collected across every assistant message back to the last
    genuine user prompt (string content or a text block — tool_result-only
    user entries are transcript plumbing, not a turn boundary). The text is
    the LAST assistant message's text, with the harness-provided inline
    ``last_assistant_message`` winning when present (v6 precedence) — but the
    inline field carries no tool information, so tools always come from the
    transcript (an inline-only payload therefore reads as non-mutating and
    never continues; the safe direction under mem-037).
    """
    text = ""
    tools: set = set()
    tpath = payload.get("transcript_path")
    entries = transcript.tail_entries(tpath) if tpath else []
    for obj in reversed(entries):
        msg = obj.get("message") or obj
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            if isinstance(content, str) and content.strip():
                break  # genuine user prompt: turn boundary
            if isinstance(content, list) and any(
                isinstance(block, dict) and block.get("type") == "text"
                for block in content
            ):
                break
            continue  # tool_result plumbing rides the user role
        if role != "assistant":
            continue
        chunks = []
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
        if chunks and not text:
            text = "\n".join(chunks)
    inline = payload.get("last_assistant_message")
    if isinstance(inline, str) and inline.strip():
        text = inline
    return text, tools


def _max_continues(cfg) -> int:
    value = config.get(cfg, "stop_completion.max_continues", DEFAULT_MAX_CONTINUES)
    try:
        result = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CONTINUES
    return result if result >= 0 else DEFAULT_MAX_CONTINUES


def _held_count(completion: dict) -> int:
    value = completion.get("held_count", 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def _reason(met: int, unmet: list) -> str:
    # Fixed strings + indicator names only — no payload/transcript text can
    # echo through the injected 'Stop hook feedback:' message (mem-034).
    return (
        "Navigator stop_completion: this turn mutated the codebase but looks "
        f"unfinished — {met}/{len(INDICATOR_VOCABULARY)} completion indicators met "
        f"(unmet: {', '.join(unmet)}) and no completion signal was emitted. "
        "Continue and finish the outstanding work (commit, tests, docs, ticket, "
        "marker — as applicable). When the task is genuinely complete, end your "
        'reply with a nav-signal:v3 line of type "exit". '
        "This forced continuation is single-shot for this turn."
    )


def run(ctx):
    # Unconditional Pilot disable — regardless of config (plan decision:
    # two loop supervisors must not fight). The runtime merge belt is the
    # backstop; this check is the mechanism.
    if ctx.pilot_executor:
        return None
    payload = ctx.payload
    if payload.get("stop_hook_active"):
        return None  # already inside a Stop chain (harness belt, mem-051)

    # Both kill switches must be truthy; both seed OFF (config.DEFAULTS), so
    # a missing block means off. The registry config gate covers .enabled
    # too; re-checked here for standalone callers.
    if not config.get(ctx.config, "stop_completion.enabled", False):
        return None
    if not config.get(ctx.config, "stop_completion.continue_enabled", False):
        return None

    stored = ctx.state.get("completion")
    completion = stored if isinstance(stored, dict) else {}
    if completion.get("stop_fuse"):
        return None  # single-shot per turn; re-armed by the stop_state barrel
    held = _held_count(completion)
    if held >= _max_continues(ctx.config):
        return None  # continue-counter cap (belt under the fuse)

    text, tools = _turn_scan(payload)
    if not (tools & stop_state.TASK_ACTION_TOOLS):
        return None  # mem-037: never continue a non-mutating turn

    clean = sentinels.strip_all(text)  # mem-034: never scan unstripped text
    if any(sig.get("type") == "exit" for sig in signals.parse(clean)):
        return None  # explicit completion signal wins

    indicators = completion.get("indicators")
    indicators = indicators if isinstance(indicators, dict) else {}
    filtered = {
        name: bool(value)
        for name, value in indicators.items()
        if name in INDICATOR_VOCABULARY
    }
    satisfied, met = _evaluate_heuristics(filtered)
    if satisfied:
        return None

    # Emit: consume the fuse + count the hold BEFORE returning the block.
    if ctx.state.get("completion") is not completion:
        ctx.state["completion"] = completion
    completion["stop_fuse"] = True
    completion["held_count"] = held + 1
    completion["signal"] = {
        "exit_seen": False,
        "heuristics_met": met,
        "held_at": ctx.now,
    }
    unmet = [name for name in INDICATOR_VOCABULARY if not filtered.get(name)]
    # Channel shape from the spike-proven emitter (mem-051): decision:block
    # + reason; continue:true is never used (it is a no-op).
    doc = json.loads(signals.stop_block(_reason(met, unmet)))
    return {"decision": doc["decision"], "reason": doc["reason"]}
