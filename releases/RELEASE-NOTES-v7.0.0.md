# Navigator v7.0.0 Release Notes — "Hooks as Runtime"

**Release Date**: 2026-09-01
**Type**: Major — hook architecture replaced; behavior-compatible by golden parity

## Summary

v7 replaces nine independent hook scripts with one dispatcher runtime. Every
manifest event now routes through `hooks/nav_dispatch.py <event>` into a shared
stdlib library (`hooks/nav_hook_lib/`) that runs op modules from `hooks/ops/`
through a fixed pipeline: gates → responders → injectors → recorders. The v6
prose mandates in CLAUDE.md (WORKFLOW CHECK blocks, session-start ritual,
forbidden-actions list) are retired as mandates — each behavior is now an op
with a config off-switch, and CLAUDE.md documents the runtime instead of being
the mechanism (root CLAUDE.md 988 → 331 lines, template 206 → 47).

Everything shipped here was validated the hard way: six hook channels
empirically probed on a live harness before design (spike memories
mem-050..055), all nine v6 behaviors byte-matched against a recorded corpus
before any new behavior landed, and the whole runtime dogfooded on this repo
and a Pilot worker since 2026-07-10.

## What's New

**One dispatcher, 13 events.** `SessionStart`, `UserPromptSubmit`,
`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart`,
`PreCompact`, `PostCompact`, `TaskCreated`, `TaskCompleted`, `ConfigChange`,
`Setup`. Fail-open by design: a dispatcher crash never blocks the session;
dispatch health is surfaced rather than swallowed.

**Shared runtime (`nav_hook_lib`).** Single state file
(`.agent/.nav-runtime-state.json`, schema 2, flock + atomic tmp+rename,
fail-closed session scoping), sole-stderr-emitter sentinels module (redacting),
unified prompt scoring with a 49-prompt corpus, signals v3 with pilot-v2
compatibility, transcript/budget/memory helpers.

**New capabilities** (blocking features seed OFF — enable via
`.agent/.nav-config.json`):

- `prompt_tier1` — zero-token deterministic answers for five exact commands
  (`nav stats`, `show features`, `list markers`, `graph health`,
  `nav version`), rendered as rounded-frame TUI cards.
- `stop_completion` — completion gate that derives 6 indicators from
  observable turn evidence (tree digest, test runs, docs/marker paths) and can
  force one continuation on unfinished work. Full breaker: fuse, held-count
  cap, non-mutating-turn guard, hard-off under `PILOT_EXECUTOR`.
- `jit_memory` + `failure_diagnosis` — declarative knowledge-graph injection
  at prompt time and on tool failures.
- `subagent_context` — deterministic top-5 memory injection into subagents
  under a 2k budget.
- `config_guard`, `setup`, `TaskCreated`/`TaskCompleted` graph sync.

**Config migration is additive.** `config_migrator.py` adds
`VERSION_CONFIGS["7.0.0"]` blocks alongside your existing v6 keys; nothing is
removed, and missing blocks default safe via `nav_hook_lib.config.DEFAULTS`.

## Dogfood Hardening (TASK-65..71)

Seven weeks of live use on two real workloads produced and fixed:

- **stop_completion evidence populator (TASK-65)** — indicators derive from
  observable evidence, so committed+tested turns pass the gate.
- **read_guard double-increment (TASK-66)** — PreToolUse fires twice per Read
  tool-use in the harness; counting is idempotent per `tool_use_id`.
- **Task-status vocabulary (TASK-67)** — plain-text statuses map to canonical
  graph statuses, not just emoji forms.
- **Tier-1/subagent tuning (TASK-68)** — explicit similarity rules for
  near-miss telemetry; deterministic subagent top-K.
- **Comment-wrapped exit signals + read-only Bash (TASK-70)** — nav-signal v3
  exit lines hide inside HTML comments (GFM-invisible, verified live);
  read-only Bash turns no longer count as mutating.
- **Ops-turn false-fires (TASK-71)** — shell-aware read-only classifier
  (parses `gh pr view`, assignments, `[ ... ]`, loops) and tree-digest
  mutation evidence replacing whole-tree `git status` cleanliness.

## Upgrade

1. `/plugin update navigator` (or install fresh).
2. **Restart Claude Code** — the manifest hook set changed and skill paths are
   cached at session start.
3. Config migrates additively on first run. To try the new blocking features,
   flip them on explicitly: `tier1.enabled`, `stop_completion.enabled` +
   `continue_enabled`.

## Rollback

The v7 config migration is additive-only: your v6 config blocks are preserved
untouched, so downgrading is safe by design.

1. `claude plugin install navigator@6.18.1`
2. Restart Claude Code (re-registers the v6 manifest hook set).
3. Optional: remove the v7-only blocks from `.agent/.nav-config.json`
   (`tier1`, `stop_completion`, `dispatcher`, …) — v6 ignores them, so this is
   cosmetic.
4. `.agent/.nav-runtime-state.json` (v7 state) is inert under v6 and can be
   deleted.

## Known Issues

- `stop_completion`'s tree digest can count Navigator-owned state writes
  (`.agent/.nav-runtime-state.json`, `.agent/knowledge/graph.json`) as
  codebase mutation, occasionally forcing a continuation on a read-only turn
  (observed 2026-08-31). Ships seeded OFF; tracked as TASK-72.
- Harness-conformance results in this tag were recorded on Claude Code
  2.1.205 (`tests/harness-conformance/results/`). Re-drive per
  `tests/harness-conformance/run.md` when certifying a newer CC version.

## Tests

`make test` green (unit suites across hooks, ops, lib, skills, validator);
hook smoke test 26/26 across all 13 events with `CLAUDE_PLUGIN_ROOT` set and
unset; golden-parity corpus byte-match for all nine v6 behaviors; live
verification of tier1 cards, read_guard, stop_completion, and session_start
schema-2 state during the dogfood period.

## Refs

TASK-57..63 (transformation), TASK-64 (release gate), TASK-65..71 (dogfood
hardening); mem-050..055 (harness channel verdicts); mem-034..037 (hook
pitfalls this design encodes).
