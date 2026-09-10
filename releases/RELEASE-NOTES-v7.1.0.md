# Navigator v7.1.0 Release Notes — "Contradictions"

**Release Date**: 2026-09-10
**Type**: Minor — additive; no hook-path or state-schema changes

## Summary

Navigator has been good at finding *a* solution fast. v7.1.0 is the first step toward
finding a *better* one. It borrows the one TRIZ move that transfers cleanly to software:
name the contradiction ("improving X worsens Y"), record how it was resolved, and look it
up the next time the same shape of problem appears.

Three places you already pass through before code changes now carry that question:

1. **The intent brief** asks for a contradiction (or `none`).
2. **Decision memories** can record the contradiction they resolved and the separation
   move that worked, and the knowledge graph can be queried by it.
3. **The research and planning agents** ask for the Ideal Final Result ("what if this
   needed no new code?") and a reuse inventory ("what already does 80% of this?") before
   mapping code.

Everything is optional and additive. Untagged memories are byte-identical to v7.0.0.
This is Phase 1 (TASK-72); Phase 2 (divergent research producing competing candidates,
a software-mapped principles reference) is gated on whether Phase 1 gets used.

## What's New

**Brief: `Contradiction` row.** NAV-BRIEF injection lists a seventh field. Most tasks are
routine and the honest answer is `none`; when a real tension is declared, the skill queries
prior resolutions before filling `Approach`. Off-switch: `brief_hook.contradiction_field`
(default on; disabling restores the v7.0.0 line byte-for-byte).

**Decision memories: three optional footer fields.**

```
**Contradiction**: clean codebase vs rollback safety
**Separation**: time
**Principle**: temporary re-export shims for one major, delete in v8
```

- Written by `memory_writer.py` / `graph_manager.py --action add-memory` via
  `--contradiction`, `--separation`, `--principle`.
- Parsed by `graph_maintenance._parse_memory_file`; `reconcile` reports `field_updates`
  and applies them disk → node with `--execute`. Never clears a field removed on disk,
  never re-syncs `summary`.
- New `reconcile --execute --fields-only`: apply the field sync without registering
  unindexed files. Needed in any repo whose `resolved/` archive holds deliberately pruned
  memories (a plain `--execute` re-registers them under fresh ids).

**Query: `graph_manager.py --action contradictions [--filter "<terms>"]`.** Every filter
word must match, case-insensitively, across contradiction + summary + principle. Sorted by
confidence. Always exits 0 (callers are model-side prompts).

```
Contradictions "rollback" (2)
  - DECISION: "Old scorer paths: ≤5-line re-export shims ..." (95%) ↔ clean codebase vs rollback safety [separation: time]
      principle: temporary re-export shims for one major, delete in v8
  - DECISION: "Rollback strategy: verified downgrade to @6.18.1 ..." (95%) ↔ big-bang runtime replacement vs reversibility [separation: time]
      principle: beforehand cushioning: additive-only config migration + verified downgrade
```

Session-start and nav-brief recall append ` ↔ A vs B` to tagged memories.

**Agents: Ideal Final Result + reuse inventory.** `navigator-research` gains Phase 0.5
with two mandatory one-line answers and a matching output section; `task-planner` gains
step 1.5 and an `**Ideal Final Result**` line in its plan template; nav-workflow's RESEARCH
phase lists both. Prose only, zero runtime change.

**Retrofit.** Eleven decisions in this repo's graph now carry contradictions (mem-043,
060–066, 072, 073, and 074 captured during the release). The separation-mode table in
`skills/nav-graph/SKILL.md` Step 3B uses them as examples.

## Upgrade

Additive. No config migration required; `brief_hook.contradiction_field` defaults to
`true` when absent. Existing graphs and memories are untouched until you tag something.

```
/plugin update navigator   # then restart Claude Code
```

## Rollback

`/plugin install navigator@7.0.0` (or the v7.0.0 procedure). Tagged memory files carry
three extra footer lines that v7.0.0's parser ignores; graph nodes carry three extra keys
that nothing validates. No data loss either direction.

## Tests

- 24 new tests across `skills/nav-graph/functions/` (writer byte-identity, parser,
  reconcile field sync + `--fields-only` + idempotence, query, renderers, builder
  preservation) and `hooks/ops/test_prompt_brief.py` (row present / off-switch / memories
  block still last).
- Full suite green (`make test`, 14 suites); goldens unchanged.

## Refs

- TASK-72 (`.agent/tasks/TASK-72-triz-contradictions.md`)
- Commits b8228af, bcb8892, dfc25da, a48faa5, 6a465ae
