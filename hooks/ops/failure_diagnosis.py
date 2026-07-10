#!/usr/bin/env python3
"""failure_diagnosis op — tool-failure pitfall injector (TASK-62 Phase 3).

PostToolUseFailure injector: on a failed tool call, look up knowledge-graph
pitfalls keyed by the tool name plus an error-pattern substring match, and
surface only the matching lines. No match ⇒ silent (spec: no generic noise).

Channel verdict: PostToolUseFailure inherits mem-050's S1 PASS for the
``hookSpecificOutput.additionalContext`` envelope shape (routing matrix
recorded in mem-050); the EVENT itself was unproven by the spike, so its
manifest registration went through the TASK-62 validate-or-drop step
(`claude plugin validate` on CC 2.1.205 accepted it — registration kept).
Content is DECLARATIVE only, same constraint as jit_memory: imperative
tool-adjacent context is refused by the model as prompt injection.

Matching pipeline:
  1. tool name required; error text extracted defensively (the payload shape
     is not spike-pinned) and sentinel-stripped (mem-034 discipline).
  2. ``nav_hook_lib.memory.recall`` over concepts = tool name + error tokens
     (silence over noise: any recall failure collapses to '').
  3. Only PITFALL-typed lines from the compact recall output survive, and
     only when they share a >=4-char token with the error text (the
     "error-pattern substring match"). Raw error text is never echoed into
     the injected context — only knowledge-graph summaries travel.

Config: ``failure_diagnosis.enabled`` — seeded False in config.DEFAULTS
(injecting features ship OFF). No ctx.pilot_executor gate: declarative,
non-blocking output that Pilot's autonomous runs can use identically.
"""
from __future__ import annotations

import re

from nav_hook_lib import hio, memory, sentinels

RECALL_LIMIT = 5
RECALL_TIMEOUT = 3
MAX_ERROR_TOKENS = 8
MAX_LINES = 3

_TOKEN_RE = re.compile(r"[a-z][a-z0-9_\-]{3,}")

# Generic failure vocabulary that would substring-match almost any pitfall
# summary; dropped from both concepts and the substring gate.
TOKEN_STOPWORDS = frozenset({
    "error", "errors", "failed", "failure", "exception", "traceback",
    "cannot", "could", "would", "should", "with", "from", "when", "that",
    "this", "file", "line", "does", "have", "been", "while", "into",
})

PITFALL_LINE_RE = re.compile(r"^\s*-\s*PITFALL\b", re.IGNORECASE)


def _error_text(payload: dict) -> str:
    """Best-effort error string from an unpinned payload shape; '' if none."""
    for key in ("error", "error_message", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    response = payload.get("tool_response")
    if isinstance(response, str) and response.strip():
        return response
    if isinstance(response, dict):
        for key in ("error", "stderr", "message"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _error_tokens(error_text: str) -> list:
    """Deduped lowercase >=4-char tokens, generic failure vocabulary dropped."""
    tokens = []
    for token in _TOKEN_RE.findall(error_text.lower()):
        if token in TOKEN_STOPWORDS or token in tokens:
            continue
        tokens.append(token)
        if len(tokens) >= MAX_ERROR_TOKENS:
            break
    return tokens


def _matching_pitfall_lines(summary: str, tokens: list) -> list:
    """PITFALL lines from compact recall output sharing a token with the error."""
    matched = []
    for line in summary.splitlines():
        if not PITFALL_LINE_RE.match(line):
            continue
        lowered = line.lower()
        if any(token in lowered for token in tokens):
            matched.append(line.strip())
        if len(matched) >= MAX_LINES:
            break
    return matched


def run(ctx):
    payload = ctx.payload
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name:
        return None

    error_text = sentinels.strip_all(_error_text(payload))
    tokens = _error_tokens(error_text)
    if not tokens:
        return None  # no error pattern to match against — stay silent

    agent_dir = hio.project_root(payload) / ".agent"
    summary = memory.recall(
        concepts=[tool_name.lower()] + tokens,
        agent_dir=agent_dir,
        limit=RECALL_LIMIT,
        timeout_s=RECALL_TIMEOUT,
    )
    if not summary:
        return None

    matched = _matching_pitfall_lines(summary, tokens)
    if not matched:
        return None

    header = (
        f"Recorded pitfall(s) in the project knowledge graph matching this "
        f"{tool_name} failure:"
    )
    return {"additional_context": "\n".join([header] + matched)}
