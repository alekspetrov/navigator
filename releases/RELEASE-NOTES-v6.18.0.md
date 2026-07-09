# Navigator v6.18.0 Release Notes

**Release Date**: 2026-07-09
**Type**: Minor — new skill + hook: nav-brief (intent-brief enforcement, TASK-56)

## Summary

The expensive failure mode in AI coding sessions is not context overflow —
it's rework. An ambiguous task prompt ("fix the bug", "clean this up") gets
implemented on guessed scope, then corrected over 2–4 exchanges. Ambiguity
is not complexity: a one-line change can be maximally ambiguous.

v6.18.0 adds a third scoring axis — **ambiguity** — and closes the loop
before implementation starts: ambiguous task prompts now trigger a
one-screen INTENT BRIEF the user confirms before any file is modified.

## New: `nav_brief.py` hook (UserPromptSubmit)

A sibling entry to `workflow_enforcer.py` in the plugin manifest. On every
prompt it:

1. **Scores ambiguity** via `skills/nav-brief/functions/ambiguity_scorer.py`
   — deliberately a separate scorer from both complexity implementations
   (TASK-48 precedent). Question/confirmation prompts zero out; task verbs
   set a 0.5 base; vague-scope terms add; file paths, numbers, limiter
   words, and acceptance criteria subtract. Word-boundary regex only.
2. **At/above threshold** (default 0.5) injects a `NAV-BRIEF` instruction
   block plus relevant knowledge-graph memories (via `memory_recall.py
   --concepts`, 3s timeout, silent degradation, 1200-char budget).
3. **Never blocks** — exit 0 + stdout only. mem-034: exit 2 on
   UserPromptSubmit stops the model entirely; this hook is advisory by
   construction.

`PILOT_EXECUTOR=1` bypasses the hook for autonomous dispatch runs.

## New: `nav-brief` skill

When a `NAV-BRIEF` block is present in context, Claude renders a one-screen
brief and waits for confirmation before modifying files:

```
INTENT BRIEF
  Goal:     …
  Scope:    …
  Approach: …
  Limits:   …
  Verify:   …
  Won't do: …
```

- Defaults pre-filled from the injected memories
- Max **2** open questions
- Mid-task scope excursions raise `BRIEF DRIFT` and re-ask

**Passthrough**: no NAV-BRIEF block this turn, the prompt answers a pending
brief's questions, or the user says "just do it" / "quick fix" / "skip the
brief".

## Configuration

```json
"brief_hook": {
  "enabled": true,
  "ambiguity_threshold": 0.5,
  "memory_budget_chars": 1200
}
```

## Tests

42 new tests: 25 scorer, 16 hook subprocess, 1 two-hook composition case
(workflow_enforcer + nav_brief on the same UserPromptSubmit event) in the
smoke suite.

## Also in this release

**Updater: plugin.json ↔ release-tag consistency validation.** A GitHub
release tag published without a matching `plugin.json` version bump would
be offered every session and reported as a successful update that never
changed the installed version. `version_detector.py` now walks releases
newest-first, validates each tag's `plugin.json` version before offering
it, skips mismatches with a stderr warning, and fails open on network
errors.

## Deferred (explicitly out of v1)

v1 is stateless. Pending-brief tracking across turns, strict gating
(blocking until confirmation), and briefs-shown metrics are documented in
TASK-56 as future work.
