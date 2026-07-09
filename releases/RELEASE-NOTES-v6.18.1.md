# Navigator v6.18.1 Release Notes

**Release Date**: 2026-07-09
**Type**: Patch — knowledge-graph decision extraction correctness

## Summary

Found live minutes after v6.18.0 shipped — by nav-brief itself, fittingly:
the new hook's memory recall surfaced a 95%-confidence decision memory
whose summary was `"----------: -------- - -----------"`. Tracing it
exposed two defects in `task_to_graph.py`, the PostToolUse task-sync path.

## Fixes

**Separator rows ingested as decisions.** `extract_decisions` skipped
table header/separator rows only on exact match (`'decision'`, `'---'`,
`'-'`). Wide separator cells (`|----------|--------|`) slipped through
and became decision memories at 0.95 confidence (mem-038/mem-044 in the
source repo's own graph). Now any all-dash/colon/space cell is skipped
via `re.fullmatch(r'[-:\s]+', ...)` — covers `:---:` alignment syntax
too.

**Re-sync duplicated decision memories.** `add_task_to_graph` re-created
every extracted decision on each sync of the same completed task — a
double sync of TASK-54 produced mem-044…049 as byte-identical copies of
mem-038…043. Now summaries already present in the graph (type
`decision`) are skipped.

## Data cleanup (source repo graph)

7 nodes pruned (2 junk + 5 duplicates), backing files archived to
`memories/decisions/resolved/` so `reconcile --execute` can't resurrect
them; 1 dangling edge repaired. Health score 85 → 100.

Consumer graphs that synced completed tasks containing wide-separator
decision tables may carry the same junk pattern — `health_check` conflict
advisories will flag duplicate summaries, and `remove-node` +
`resolve-memory` clean them up.

## Tests

4 regression tests added to `test_task_to_graph.py`: wide, narrow, and
colon-aligned separator rows; double-sync dedupe.
