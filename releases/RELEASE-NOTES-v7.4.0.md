# Navigator v7.4.0 Release Notes — "Readable Reports"

**Release Date**: 2026-09-12
**Type**: Minor — nav-deep-research report layout + two ship-gate checks; no config change

## Summary

v7.3.0 shipped deep research that was correct and well cited, and hard to read. The first
live run's Summary was one paragraph of 1,969 characters; ten body blocks ran past 700
characters; the ship step quoted that paragraph back to the user. The writer contract
fixed section names and the citation form, nothing about shape, so the writer wrote an
essay.

v7.4.0 fixes the shape (TASK-75). Every report now opens with an `**Answer:**` line and
three to six bullets, puts comparisons in an `## At a glance` table, gives each atomic
item its own section with a lead sentence and "What the sources show" bullets, and keeps
every paragraph under 700 characters. The ship gate enforces the two parts that can be
checked mechanically, so the layout does not depend on the writer remembering it.

## What's New

**`reference/REPORT-FORMAT.md`.** The layout, the rules, the fix path for each gate
failure, and an abridged example. The writer reads it before planning the outline; the
orchestrator uses its fix path when a gate check fails.

```markdown
# <Title: the conclusion in at most 12 words>

> **Query:** <verbatim>
> **Date:** 2026-09-12 · **Sources:** 22 · **Register:** survey

## Summary
**Answer:** <one or two sentences> [n]
- **<Lead phrase>.** <one sentence> [n]      (three to six bullets)
**Counter-position:** <one or two sentences> [n]
**Still open:** <one sentence>

## At a glance                               (comparisons only)
| entity | field | field |

## <one section per atomic item>
<lead of one to three sentences> [n]
**What the sources show**
- <one fact per bullet> [n]
**Caveats**
- <disagreement or gap> [n]

## Key findings · ## Open questions · ## Sources   (unchanged contract)
```

**Two new ship-gate checks** (twelve in total):

| Check | Rule | Detail on failure |
|---|---|---|
| `summary-scannable` | `## Summary` has a line starting `**Answer:**` and at least two bullets | answer-line / bullet count |
| `no-wall-of-text` | no paragraph, blockquote, or single bullet before `## Sources` exceeds 700 characters; tables, headings, fenced code exempt; bullets measured item by item | section + first words of each offending block |

`## Open questions` joins the required sections. Same rule as before: a failure is fixed in
the report with an Edit hunk, never by changing the gate.

**Ship message.** Step 6 now prints a four-bullet status block and then the report's
Summary verbatim, which is the reader's first screen by construction.

## Changed

- `agents/deep-research-writer.md` — new `report_format` input; reads the layout file
  first; plans the At-a-glance table and the Answer sentence before writing.
- `agents/deep-research-patcher.md` — keeps the paragraph cap when applying hunks; never
  merges bullets into prose; keeps the Answer line.
- `steps/3-draft.md` — passes `report_format`; the pre-check covers the six structural
  checks so layout problems are fixed before the critic runs.
- `functions/report_parse.py` — `summary_structure()`, `paragraphs()`,
  `long_paragraphs()`; `REQUIRED_SECTIONS` includes `Open questions`.
- No config keys added. `deep_research` still ships OFF.

## Verified

- `make test` green; the skill's functions dir runs 70 tests (26 in `test_ship_gate.py`,
  new cases for the Answer line, bullet minimum, wall detection naming the section,
  table/code/bullet exemptions, Open questions required).
- New gate against both v7.3.0 reports: 10/12 pass; the two failures are exactly the two
  new checks, on the Summary paragraph and the long body blocks. Finished runs keep their
  `ship.json`; the gate is not re-run on them.
- Writer A/B on identical inputs: the WebGPU run's 22 source notes and atomic items were
  seeded into a scratch run and one writer was spawned with the new prompt. New gate
  12/12 on the draft, before any critic or patcher pass.

| | v7.3.0 report | v7.4.0 draft |
|---|---|---|
| Blocks over 700 chars | 10 | 0 |
| Longest block | 1,969 chars (the Summary) | 323 chars |
| Bullets | 29 | 59 |
| Tables | 3 | 2 (At a glance + feature matrix) |
| Words | 4,182 | 2,430 |
| Sources cited / typed findings | 22 / 12 | 22 / 12 |

  The v7.3.0 column is the shipped report after 11 critic findings were applied; the
  v7.4.0 column is an unreviewed draft, so word counts are not like for like. The
  scratch run was deleted after the comparison.

## Known limitations

- The cap is a character count, not a readability score. Five long sentences pass.
- The critic does not judge layout; the gate does. A patcher hunk that overflows the cap
  is caught at step 6 and split by the orchestrator.
- Existing reports keep the old layout; rerun a query to get the new one.

## Upgrade

`claude plugin update navigator`, restart the session. No config migration; no breaking
changes. Downgrade is a plain plugin downgrade.

Task: `.agent/tasks/TASK-75-readable-research-reports.md`.
