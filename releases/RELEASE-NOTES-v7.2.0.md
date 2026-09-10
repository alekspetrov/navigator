# Navigator v7.2.0 Release Notes — "Three Candidates"

**Release Date**: 2026-09-10
**Type**: Minor — new skill; additive, no hook-path or state-schema changes

## Summary

v7.1.0 taught Navigator to name a contradiction and remember how it was resolved.
v7.2.0 makes it *use* that: when a task carries a real contradiction ("improving X worsens
Y"), the new `nav-triz` skill puts three genuinely different candidates on the table, each
with a named downside, and recommends one before any plan is written.

This is TRIZ Phase 2 (TASK-73). It fires only on an explicit ask or a declared
contradiction on a substantial task. Routine prompts never see it.

## What's New

**`nav-triz` skill.** Seven steps on one screen: state the contradiction → Ideal Final
Result → reuse inventory → prior resolutions + principle prompts → three candidates from
*different* separation modes → recommend one → capture the decision back to the graph.
Every candidate must say what it worsens; a candidate with no downside is a compromise
misdescribed, or the IFR.

Triggers: "find a better solution for X", "alternatives for X", "resolve the
contradiction", "triz this", or a nav-brief `Contradict` row that is not `none` on a
Task-Mode-substantial task. Does not fire on `none`, on "just do it" / "quick fix", or
when the approach is already named.

**`triz_suggest.py`.** Deterministic, stdlib, always exits 0:

```
python3 skills/nav-triz/functions/triz_suggest.py --contradiction "clean codebase vs rollback safety"

Prior resolutions in this graph (3):
  - mem-063: clean codebase vs rollback safety [separation: time]
      principle: temporary re-export shims for one major, delete in v8
  ...
Candidate principles (one per separation mode first):
  1. [space] #24 Intermediary — adapter, single emitter, gateway, shim, facade
  2. [time]  #11 Beforehand cushioning — additive-only migration, verified rollback, feature flag
  3. [condition] #15 Dynamization — config toggle, threshold, ship OFF then opt in
```

Keyword-ranks 21 software-mapped principles, takes one per separation mode first, pads with
prior action / dynamization / segmentation, and lists prior decisions from the knowledge
graph via `query_contradictions`. A generic fallback is labelled as such.

**`reference/PRINCIPLES.md`.** The four separation modes (time / space / condition /
level) with examples from this repo's own decisions, the ~20 principles that transfer to
software with the move each suggests, and the list of the ones that don't. Lazy-loaded.

**Hand-offs.** nav-brief hands off when a contradiction is declared on a substantial task;
the `navigator-research` agent supplies `triz_suggest` output as evidence in Phase 0.5;
Task Mode RESEARCH lists the divergence step before PLAN.

## Upgrade

Additive. No config changes. `/plugin update navigator`, then restart Claude Code.

## Rollback

`/plugin install navigator@7.1.0`. No data written by this release; decision memories
captured through the skill use the v7.1.0 fields.

## Known Limits

The principle keyword map is hand-curated. Contradictions phrased in vocabulary it hasn't
seen get the generic trio, visibly labelled. Feedback on misses is welcome.

## Tests

- 12 new tests in `skills/nav-triz/functions/test_triz_suggest.py` (catalog integrity,
  ranking, mode diversity, padding, plural/singular matching, graph priors, CLI JSON).
- Full suite green (`make test`, 15 suites); release validator passes.

## Refs

- TASK-73 (`.agent/tasks/TASK-73-triz-divergent-solving.md`), TASK-72 (Phase 1, v7.1.0)
- Commit f42de37
