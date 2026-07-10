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
import re
import subprocess
from pathlib import Path

from nav_hook_lib import config, hio, memory, sentinels, signals, transcript

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

# Tool names whose tool_use input carries an on-disk file path (TASK-65).
FILE_PATH_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})

# A turn ran the test suite when a Bash command matches this (mem-034: only
# fixed patterns, never transcript text, ever reach the reason string).
TEST_CMD_RE = re.compile(r"\b(make test|pytest|(python3?\s+-m\s+)?unittest)\b")


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


def _collect_tool_evidence(name: str, block: dict, file_paths: list, bash_uses: list):
    """Pull observable evidence out of one tool_use block (TASK-65).

    File-mutating tools contribute their target path (file_path or, for
    notebooks, notebook_path); Bash contributes ``(tool_use_id, command)`` so
    the caller can pair it with the is_error of the FOLLOWING tool_result.
    """
    inp = block.get("input")
    if not isinstance(inp, dict):
        return
    if name in FILE_PATH_TOOLS:
        for key in ("file_path", "notebook_path"):
            val = inp.get(key)
            if isinstance(val, str) and val:
                file_paths.append(val)
    elif name == "Bash":
        cmd = inp.get("command")
        if isinstance(cmd, str):
            bash_uses.append((block.get("id"), cmd))


def _turn_scan(payload: dict):
    """(last_assistant_text, turn_tool_names, evidence) for the ENDING turn.

    Tool names are collected across every assistant message back to the last
    genuine user prompt (string content or a text block — tool_result-only
    user entries are transcript plumbing, not a turn boundary). The text is
    the LAST assistant message's text, with the harness-provided inline
    ``last_assistant_message`` winning when present (v6 precedence) — but the
    inline field carries no tool information, so tools always come from the
    transcript (an inline-only payload therefore reads as non-mutating and
    never continues; the safe direction under mem-037).

    ``evidence`` (TASK-65) is gathered over the SAME turn span so the
    completion-indicator populator sees observable turn results: file paths
    from Edit/Write/MultiEdit/NotebookEdit inputs, and each Bash command paired
    with whether its matching tool_result was is_error (matched by
    tool_use_id; an unmatched command defaults to not-errored).
    """
    text = ""
    tools: set = set()
    file_paths: list = []
    bash_uses: list = []          # (tool_use_id, command) in the turn span
    result_errors: dict = {}      # tool_use_id -> is_error(bool)
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
            if isinstance(content, list):
                if any(
                    isinstance(block, dict) and block.get("type") == "text"
                    for block in content
                ):
                    break
                for block in content:  # tool_result plumbing: harvest is_error
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_result":
                        tid = block.get("tool_use_id")
                        if isinstance(tid, str):
                            result_errors[tid] = bool(block.get("is_error"))
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
                    name = block["name"]
                    tools.add(name)
                    _collect_tool_evidence(name, block, file_paths, bash_uses)
        if chunks and not text:
            text = "\n".join(chunks)
    inline = payload.get("last_assistant_message")
    if isinstance(inline, str) and inline.strip():
        text = inline
    bash = [(cmd, result_errors.get(tid, False)) for tid, cmd in bash_uses]
    return text, tools, {"file_paths": file_paths, "bash": bash}


def _git_clean(root) -> bool:
    """True when the git working tree at ``root`` is clean.

    ``git status --porcelain`` with a ~2s timeout: empty stdout AND
    returncode 0 → clean. ANY failure/timeout/non-repo → False (mem-034:
    subprocess output never touches stderr or the reason string).
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root), capture_output=True, text=True, timeout=2,
        )
    except Exception:
        return False
    return result.returncode == 0 and not result.stdout.strip()


def _derive_indicators(evidence: dict, cfg, payload: dict) -> dict:
    """Completion indicators inferred from OBSERVABLE turn evidence (TASK-65).

    Only True entries are returned; the caller ORs these with any explicit
    ``completion.indicators`` state (a state True still wins). The six-name
    vocabulary is covered as follows:

      code_committed   git working tree clean at the project root.
      tests_passing    a turn Bash command ran the suite and did NOT error.
      docs_updated     a turn touched a ``*.md`` file.
      marker_created   a turn touched a path under ``/.context-markers/``.
      ticket_closed    True only when no PM tool is configured
                       (project_management == 'none' → nothing to close). With
                       a PM configured this stays best-effort False: closing a
                       real ticket needs a PM API call this hook must not make.
      code_simplified  left unmet — no reliable observable signal exists for
                       "code was simplified" from transcript/disk evidence.
    """
    indicators = {}
    if _git_clean(hio.project_root(payload)):
        indicators["code_committed"] = True
    for command, is_error in evidence.get("bash", ()):
        if not is_error and TEST_CMD_RE.search(command or ""):
            indicators["tests_passing"] = True
            break
    paths = evidence.get("file_paths", ())
    if any(isinstance(p, str) and p.endswith(".md") for p in paths):
        indicators["docs_updated"] = True
    if any(isinstance(p, str) and "/.context-markers/" in p for p in paths):
        indicators["marker_created"] = True
    if config.get(cfg, "project_management", "none") == "none":
        indicators["ticket_closed"] = True
    return indicators


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

    text, tools, evidence = _turn_scan(payload)
    if not (tools & stop_state.TASK_ACTION_TOOLS):
        return None  # mem-037: never continue a non-mutating turn

    clean = sentinels.strip_all(text)  # mem-034: never scan unstripped text
    if any(sig.get("type") == "exit" for sig in signals.parse(clean)):
        return None  # explicit completion signal wins

    # Observable turn evidence (TASK-65) OR'd with any explicit state
    # indicators — a state True still wins, so other writers keep counting.
    state_ind = completion.get("indicators")
    state_ind = state_ind if isinstance(state_ind, dict) else {}
    derived = _derive_indicators(evidence, ctx.config, payload)
    filtered = {
        name: bool(state_ind.get(name)) or bool(derived.get(name))
        for name in INDICATOR_VOCABULARY
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
