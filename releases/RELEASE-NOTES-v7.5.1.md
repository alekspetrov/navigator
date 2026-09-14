# Navigator v7.5.1 Release Notes — "Provenance"

**Release Date**: 2026-09-14
**Type**: Patch — deep-research graph memories carry fetch date and content hash per cited URL; citation parser fix

## Summary

Deep research commits the report, the critic's findings and the graph memories, but the
fetched page bodies stay local as third-party text. A memory read from the repo gave a
claim and a URL, and no way to know when the page was read or whether it changed since.

v7.5.1 folds the two facts that make a citation auditable into the committed memory
(TASK-77): each cited URL now reads
`https://… (fetched 2026-09-10, sha256 aab8bb007ea7)`. `source_store.py refetch` compares
the same hash, so drift is detectable from the repo alone. When the notes are absent, the
URL stands alone as before.

The same task fixed a parser bug: writers wrap Key findings bullets at about 90 columns,
the `[n]` citation lands on the continuation line, and the line-based parser dropped it.
On the first live report that left 0 of 12 memories with a URL. It is now 12 of 12.

## Changes

- `skills/nav-deep-research/functions/report_to_graph.py` — `provenance_by_url()`,
  tagged evidence in `build_findings()`.
- `skills/nav-deep-research/functions/report_parse.py` — `bullet_items()`; `key_findings()`
  parses joined bullets; trailing punctuation cleanup.
- Tests, `steps/6-ship.md`, CLAUDE.md.

## Upgrade note

Runs ingested before v7.5.1 keep URL-only evidence. Re-run
`report_to_graph.py --run <slug>` on the machine that still holds the run's `sources/`
to re-tag them.
