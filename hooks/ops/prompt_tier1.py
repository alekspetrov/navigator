#!/usr/bin/env python3
"""prompt_tier1 op — UserPromptSubmit Tier-1 deterministic responder (TASK-62 Phase 1).

Channel: mem-053 (S4 PASS, CC 2.1.205) — UserPromptSubmit block-as-answer via
``decision: block`` JSON answers at ZERO model invocation (num_turns=0). The
emitter is signals.prompt_block; exit-2 is deliberately impossible here (it
leaks hook command chrome into the visible answer — the losing spike shape).

Safety rails (plan risk register + mem-034):

  - EXACT-match table only, five seed commands, matched on the
    sentinels.strip_all()'d prompt, <=48 chars post-strip. No fuzzy matching:
    "nav stats please" reaches the model untouched.
  - Every answer is sentinel-wrapped in <nav-t1-response> (registered in
    sentinels.TAGS) and carries the escape line, so an echoed answer — plus
    the harness's 'Original prompt: <trigger>' echo (mem-053) — strips to
    nothing and can never re-trigger a matcher (mem-034 both halves).
  - Telemetry only, never behavior: a hit records ``turn.tier1_hit`` (+ the
    ``completion.tier1_fuse`` answered-this-turn marker the stop_state barrel
    re-arms); a near-identical re-prompt right after a hit increments
    ``tier1.false_positives`` (surfaced by /nav:stats) and still passes
    through to the model. "Near-identical" = the normalized prompt contains
    the hit command verbatim without being it (similarity threshold is a
    deferred TASK-62 decision; containment is the deliberately-simple seed).
  - Per-rule off-switch ``tier1.rules.<id>: false``; whole feature seeds OFF
    (config.DEFAULTS tier1.enabled=false; the registry config gate skips the
    op, and run() re-checks for standalone callers).
  - ctx.pilot_executor bypasses ENTIRELY (no answer, no telemetry): a Pilot
    dispatch loop must never have its prompt swallowed by a responder.

Answers are computed deterministically from local project artifacts (runtime
state, layered config, .agent/.context-markers listing, knowledge graph
stats, plugin manifest) — never from the model.
"""
from __future__ import annotations

import json
import os

from nav_hook_lib import config, hio, memory, sentinels, signals

SENTINEL_TAG = "nav-t1-response"
ESCAPE_LINE = "reply 'ask claude' to run the model"
MAX_PROMPT_CHARS = 48  # post-strip guard: longer prompts are never matched
MARKERS_DIR = ".context-markers"
MAX_MARKERS_SHOWN = 10

# The five seed commands (Tier-1 whitelist growth is out of TASK-62 scope).
# Exact match against the lowercased, strip_all()'d, whitespace-trimmed
# prompt; rule ids double as the tier1.rules.<id> toggle keys.
COMMANDS = {
    "nav stats": "nav_stats",
    "show features": "show_features",
    "list markers": "list_markers",
    "graph health": "graph_health",
    "nav version": "nav_version",
}
RULE_COMMANDS = {rule: command for command, rule in COMMANDS.items()}

# Feature blocks listed by "show features" — every block carries .enabled in
# config.DEFAULTS, so the answer is total and deterministic.
FEATURE_BLOCKS = (
    "task_mode",
    "loop_mode",
    "simplification",
    "auto_update",
    "knowledge_graph",
    "multi_agent",
    "session_start_hook",
    "workflow_enforcer_hook",
    "brief_hook",
    "read_guard_hook",
    "task_graph_sync_hook",
    "profile_sync_hook",
    "workflow_state_hook",
    "compact_hook",
    "dispatcher",
    "tier1",
    "stop_completion",
    "jit_memory",
    "subagent_context",
    "failure_diagnosis",
    "config_guard",
    "setup_hook",
)


def _user_message(payload: dict) -> str:
    """Prompt from payload (legacy env fallback), strip_all()'d (mem-034)."""
    prompt = payload.get("prompt") or payload.get("user_message") or ""
    if not prompt:
        prompt = os.environ.get("CLAUDE_USER_MESSAGE", "")
    return sentinels.strip_all(prompt)


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace (used ONLY for near-identical telemetry)."""
    return " ".join(text.lower().split())


def _agent_dir(ctx):
    return hio.project_root(ctx.payload) / ".agent"


def _graph(ctx) -> dict:
    return hio.safe_json(_agent_dir(ctx) / "knowledge" / "graph.json") or {}


def _marker_names(ctx) -> list:
    try:
        markers = _agent_dir(ctx) / MARKERS_DIR
        if not markers.is_dir():
            return []
        return sorted(p.name for p in markers.iterdir() if p.is_file())
    except Exception:
        return []


def _plugin_version() -> str:
    plugin_dir = memory._plugin_dir()  # the lib's plugin-root resolver
    if plugin_dir is None:
        return "unknown"
    manifest = hio.safe_json(plugin_dir / ".claude-plugin" / "plugin.json") or {}
    version = manifest.get("version")
    return version if isinstance(version, str) and version else "unknown"


# ---------------------------------------------------------------------------
# Deterministic answer builders (one per rule id)
# ---------------------------------------------------------------------------

def _answer_nav_stats(ctx) -> str:
    stats = _graph(ctx).get("stats") or {}
    reads = ctx.state.get("reads") or {}
    tier1 = ctx.state.get("tier1") or {}
    meta = ctx.state.get("meta") or {}
    op_errors = meta.get("op_errors") if isinstance(meta.get("op_errors"), list) else []
    return "\n".join([
        "Navigator stats (deterministic Tier-1 answer, zero model tokens)",
        "graph: {} nodes / {} edges / {} memories".format(
            stats.get("total_nodes", 0), stats.get("total_edges", 0),
            stats.get("memory_count", 0)),
        f"context markers: {len(_marker_names(ctx))}",
        f"reads this turn: {reads.get('turn_count', 0)}",
        "tier1: {} hits / {} suspected false positives".format(
            tier1.get("hits", 0), tier1.get("false_positives", 0)),
        f"recent op errors: {len(op_errors)}",
    ])


def _answer_show_features(ctx) -> str:
    lines = ["Navigator features (.agent/.nav-config.json <block>.enabled)"]
    for block in FEATURE_BLOCKS:
        enabled = config.get(ctx.config, f"{block}.enabled", None)
        if enabled is None:
            status = "unset"
        else:
            status = "on" if enabled else "off"
        lines.append(f"{block}: {status}")
    return "\n".join(lines)


def _answer_list_markers(ctx) -> str:
    names = _marker_names(ctx)
    if not names:
        return "No context markers in .agent/.context-markers/"
    lines = [f"Context markers ({len(names)} total, newest last):"]
    lines += names[-MAX_MARKERS_SHOWN:]
    if len(names) > MAX_MARKERS_SHOWN:
        lines.insert(1, f"... showing the last {MAX_MARKERS_SHOWN}")
    return "\n".join(lines)


def _answer_graph_health(ctx) -> str:
    graph = _graph(ctx)
    if not graph:
        return ("No knowledge graph (.agent/knowledge/graph.json missing) — "
                "say 'Initialize knowledge graph' to build one")
    stats = graph.get("stats") or {}
    concepts = graph.get("concept_index")
    return "\n".join([
        "Knowledge graph health",
        f"schema version: {graph.get('version', '?')}",
        f"last updated: {graph.get('last_updated', '?')}",
        "nodes: {} | edges: {} | memories: {}".format(
            stats.get("total_nodes", 0), stats.get("total_edges", 0),
            stats.get("memory_count", 0)),
        f"indexed concepts: {len(concepts) if isinstance(concepts, dict) else 0}",
    ])


def _answer_nav_version(ctx) -> str:
    plugin_version = _plugin_version()
    config_version = ctx.config.get("version")
    config_line = config_version if isinstance(config_version, str) else "unset"
    if plugin_version == "unknown" or not isinstance(config_version, str):
        drift = "undetermined"
    elif plugin_version == config_version:
        drift = "none"
    else:
        drift = f"config {config_version} != plugin {plugin_version}"
    return "\n".join([
        f"Navigator plugin: {plugin_version}",
        f"project config version: {config_line}",
        f"version drift: {drift}",
    ])


ANSWERS = {
    "nav_stats": _answer_nav_stats,
    "show_features": _answer_show_features,
    "list_markers": _answer_list_markers,
    "graph_health": _answer_graph_health,
    "nav_version": _answer_nav_version,
}


# ---------------------------------------------------------------------------
# Telemetry (state-only; never changes routing)
# ---------------------------------------------------------------------------

def _tier1_section(ctx) -> dict:
    section = ctx.state.get("tier1")
    if not isinstance(section, dict):
        section = {}
        ctx.state["tier1"] = section
    return section


def _record_hit(ctx, rule: str) -> None:
    turn = ctx.state.get("turn")
    if not isinstance(turn, dict):
        turn = {}
        ctx.state["turn"] = turn
    turn["tier1_hit"] = rule
    completion = ctx.state.get("completion")
    if not isinstance(completion, dict):
        completion = {}
        ctx.state["completion"] = completion
    # Answered-this-turn marker; the stop_state reset barrel re-arms it at
    # the next completed model turn (a Tier-1 hit itself fires no Stop).
    completion["tier1_fuse"] = True
    section = _tier1_section(ctx)
    section["hits"] = int(section.get("hits", 0) or 0) + 1


def _count_false_positive(ctx, normalized_prompt: str) -> None:
    """Hit followed by a near-identical re-prompt => telemetry only.

    The user answered a Tier-1 block by rephrasing the same command — a
    signal the deterministic answer was NOT what they wanted. Counted for
    /nav:stats; the prompt still passes through to the model unchanged.
    """
    turn = ctx.state.get("turn")
    if not isinstance(turn, dict):
        return
    command = RULE_COMMANDS.get(turn.get("tier1_hit"))
    if not command:
        return
    if command in normalized_prompt and normalized_prompt != command:
        section = _tier1_section(ctx)
        section["false_positives"] = int(section.get("false_positives", 0) or 0) + 1
        turn.pop("tier1_hit", None)  # one-shot window per hit


def run(ctx):
    # Pilot bypass: ENTIRELY — no answer, no telemetry (plan decision).
    if ctx.pilot_executor:
        return None
    # Belt for standalone callers; the registry config gate already skips
    # the op when tier1.enabled is false (which is the seeded default).
    if not config.get(ctx.config, "tier1.enabled", False):
        return None

    candidate = _user_message(ctx.payload).strip()
    if not candidate or len(candidate) > MAX_PROMPT_CHARS:
        return None

    rule = COMMANDS.get(candidate.lower())
    if rule and config.get(ctx.config, f"tier1.rules.{rule}", True) is not False:
        # Record BEFORE building: the nav-stats answer must reflect the hit
        # it is itself producing (tier1.hits includes this one).
        _record_hit(ctx, rule)
        answer = ANSWERS[rule](ctx)
        body = answer + "\n\n" + ESCAPE_LINE
        reason = sentinels.wrap(SENTINEL_TAG, body)
        # Channel shape comes from the spike-proven emitter (mem-053) —
        # decision:block JSON, NEVER exit-2. The runtime merges the parsed
        # keys into the single output document.
        doc = json.loads(signals.prompt_block(reason))
        return {"decision": doc["decision"], "reason": doc["reason"]}

    # Not an exact command: pass through (no fuzzy match, mem-053 rail),
    # but count a near-identical re-prompt right after a hit as a suspected
    # false positive (telemetry surfaced by /nav:stats).
    _count_false_positive(ctx, _normalize(candidate))
    return None
