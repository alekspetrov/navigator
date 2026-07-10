#!/usr/bin/env python3
"""nav_hook_lib.registry — declarative EVENT -> ordered OpSpec lists (TASK-60 Phase 2).

The single dispatcher (hooks/nav_dispatch.py -> nav_hook_lib.runtime.dispatch)
consults EVENT_OPS to decide which op modules run for a given hook event, in
which phase order, behind which config toggle. This module is pure data: it
imports no op modules (runtime imports them lazily, only when their event
fires and their matcher hits) and performs no I/O.

Registry semantics consumed by runtime.dispatch:

  - Phases execute in PHASE_ORDER (gates -> responders -> injectors ->
    recorders). A blocking result from a 'gates' op short-circuits every
    phase to its right. Ops in phase 'gates' are exempt from the soft
    deadline — they always run.
  - Within one event, list order IS merge order (additional_context strings
    are concatenated in registry order, then budget.clamp'd).
  - OpSpec.config_key names the EXISTING v6 toggle block in
    .agent/.nav-config.json (see fixtures/nav-config-v6.18.1.json);
    runtime gates each op on config.get(cfg, config_key + '.enabled', True).
  - OpSpec.matcher is a regex tested against payload tool_name for
    PreToolUse/PostToolUse; None means the op always runs for its event.
  - A missing op module (the normal state until TASK-61 lands the ports) is
    skipped with a meta.op_errors note — never a crash.

Pilot-executor policy is NOT expressed here: runtime evaluates
config.is_pilot_executor() once at dispatch entry and passes it to ops as
ctx.pilot_executor (the registry stays posture-agnostic).

Pure Python stdlib only (guard test in test_config.py).
"""
from __future__ import annotations

from dataclasses import dataclass

# Pipeline phase order. runtime.dispatch executes phases left to right; the
# strings below are the only valid OpSpec.phase values.
PHASE_ORDER = ("gates", "responders", "injectors", "recorders")

# The seven v6 manifest event surfaces. New events (SubagentStart,
# PostToolUseFailure, ConfigChange, ...) are registered in TASK-62 per spike
# verdicts — never here with no op behind them (v5.1.0 lesson).
EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "PreCompact",
    "PostCompact",
)

# Coarse tool matcher shared by the PostToolUse recorders (kept coarse for
# spawn suppression; fine filtering happens inside the ops).
MUTATING_TOOLS = "Edit|Write|MultiEdit|NotebookEdit"


@dataclass(frozen=True)
class OpSpec:
    """One dispatchable operation — exactly these five fields (TASK-60 contract).

    name:       op module hooks/ops/<name>.py exposing run(ctx) -> dict|None
    phase:      one of PHASE_ORDER
    matcher:    regex against payload tool_name (Pre/PostToolUse); None = always
    config_key: v6 toggle block name; <config_key>.enabled gates the op
    budget_ms:  advisory per-op soft time budget. NOT enforced by the TASK-60
                runtime (which applies the event-level soft deadline); recorded
                for TASK-61 tuning and future per-op telemetry.
    """

    name: str
    phase: str
    matcher: str | None
    config_key: str
    budget_ms: int


# ---------------------------------------------------------------------------
# EVENT -> ordered ops (the eight TASK-61 rows; op modules land in TASK-61).
#
# Spike-gated FUTURE rows (TASK-62) appear ONLY as comments below, each with
# its mem-05x verdict + fallback — never as live OpSpecs in this file.
# ---------------------------------------------------------------------------
EVENT_OPS: dict[str, list[OpSpec]] = {
    "SessionStart": [
        OpSpec("session_start", "injectors", None, "session_start_hook", 8000),
        # TASK-62: setup (injectors) — mem-055 (S6, CC 2.1.205):
        #   ${CLAUDE_PLUGIN_ROOT} binds correctly in plugin-manifest hook
        #   commands, including headless -p sessions (SessionStart fires
        #   there too). Unset/empty env is a LOUD failure (exit 2), not
        #   mem-036's silent no-op — the :-fallback stays prudent. Fallback:
        #   none needed; row lands live in TASK-62.
    ],
    "UserPromptSubmit": [
        OpSpec("prompt_gate", "gates", None, "workflow_enforcer_hook", 1500),
        OpSpec("prompt_brief", "injectors", None, "brief_hook", 2000),
        # TASK-62: prompt_tier1 (responders) — mem-053 (S4, CC 2.1.205):
        #   UserPromptSubmit block-as-answer WORKS with zero model invocation
        #   (num_turns=0, duration_api_ms=0); WINNER is decision:block JSON —
        #   exit-2 leaks raw hook command chrome into the visible answer.
        #   Caution: the harness appends 'Original prompt: <trigger>' to the
        #   block message, so context-scanning ops must tolerate that echo.
        #   Fallback if the channel regresses: demote Tier-1 to an advisory
        #   injection ("answer verbatim from this data").
    ],
    "PreToolUse": [
        # read_guard stays deny-only regardless of mem-054 (S5, CC 2.1.205):
        # plain stdout is DEAD (reconfirms mem-035 for stdout) while
        # hookSpecificOutput.additionalContext DELIVERS (supersedes mem-035
        # for that sub-channel) — the advisory redesign is a v7.x follow-up,
        # not TASK-61.
        OpSpec("read_guard", "gates", "Read", "read_guard_hook", 1000),
    ],
    "PostToolUse": [
        OpSpec("graph_sync", "recorders", MUTATING_TOOLS, "task_graph_sync_hook", 2000),
        OpSpec("profile_sync", "recorders", MUTATING_TOOLS, "profile_sync_hook", 2000),
        # TASK-62: jit_memory (injectors) — mem-050 (S1, CC 2.1.205):
        #   PostToolUse hookSpecificOutput.additionalContext DELIVERS to the
        #   model (supersedes mem-035 for this sub-channel); content must be
        #   DECLARATIVE — imperative instructions are flagged by the model as
        #   prompt injection and refused (2/2 runs). Fallback if the channel
        #   regresses: queue in state, surface at the next UserPromptSubmit.
    ],
    "Stop": [
        OpSpec("stop_state", "recorders", None, "workflow_state_hook", 2000),
        # TASK-62: stop_completion (gates) — mem-051 (S2, CC 2.1.205):
        #   Stop 'continue: true' is a NO-OP for forced continuation;
        #   'decision: block' + reason IS the working mechanism (exactly one
        #   continuation; stop_hook_active harness belt + single-shot
        #   flag-file fuse both verified). Ships on decision:block with
        #   continue:true OFF permanently; default OFF, and always OFF under
        #   the Pilot executor (two loop supervisors must not fight).
    ],
    "PreCompact": [
        OpSpec("compact_marker", "recorders", None, "compact_hook", 25000),
    ],
    "PostCompact": [
        OpSpec("compact_marker", "recorders", None, "compact_hook", 4000),
    ],
}

# ---------------------------------------------------------------------------
# TASK-62 rows on events OUTSIDE the seven v6 surfaces (new manifest entries
# land in TASK-62 alongside their ops — never here):
#
#   PostToolUseFailure: failure_diagnosis (injectors) — inherits mem-050's S1
#     verdict per the routing matrix (additionalContext delivers; declarative
#     content only). Fallback: state-queue + next-event surfacing, same as
#     jit_memory.
#   SubagentStart: subagent_context (injectors) — mem-052 (S3, CC 2.1.205):
#     hookSpecificOutput.additionalContext WORKS with both-way main/subagent
#     isolation; feature viable at the 2k-char budget (budget.BUDGETS).
#     Fallback: drop the feature.
#   ConfigChange: config_guard (injectors) — systemMessage channel; no spike
#     dependency in the routing matrix (no mem-05x verdict required).
# ---------------------------------------------------------------------------
