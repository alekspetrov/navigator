# Report format (nav-deep-research)

The writer produces this layout, the patcher preserves it, and `ship_gate.py` checks
the parts marked **gate**. The reader gets the answer from the first screen and can
stop at any heading without losing the thread. The citation contract (`[n]`, the
Sources table, typed Key findings) is unchanged and documented in the writer agent.

## Layout

```markdown
# <Title: the conclusion in at most 12 words, not a restatement of the question>

> **Query:** <the research query, verbatim>
> **Date:** YYYY-MM-DD · **Sources:** K · **Register:** analyze

## Summary

**Answer:** <one or two sentences that answer the query directly> [n]

- **<Lead phrase>.** <one sentence, cited> [n]
- **<Lead phrase>.** <one sentence, cited> [n]
- <three to six bullets in total: the load-bearing findings, most important first>

**Counter-position:** <the strongest case against the answer, one or two sentences> [n]

**Still open:** <one sentence; the list lives in Open questions>

## At a glance

| <entity or item> | <field> | <field> | <field> |
|---|---|---|---|
| <one row per entity the query names> | | | |

## <One section per atomic item, in item order>

<Lead: one to three sentences that answer this item.> [n]

**What the sources show**

- <one fact per bullet, cited> [n]
- <one fact per bullet, cited> [n]

**Caveats**

- <disagreement, weak sourcing, what the corpus does not cover> [n]

## Key findings

- (pattern|pitfall|decision|learning) <one self-contained sentence> [n]

## Open questions

- **<The question?>** <What source or measurement would settle it.>

## Sources

| n | id | title | url | lens |
|---|---|---|---|---|
| 1 | 007 | <title> | <url> | canonical |
```

## Rules

**Answer first.** The title states the conclusion. The Summary opens with an
`**Answer:**` line, then bullets, then the counter-position. Nothing in the Summary is
new: every bullet is expanded in a body section.

**Source lens (gate: `findings-corroborated`).** Every Sources row carries the lens that
found it, copied from the note: `canonical` (spec, vendor doc, paper, issue tracker),
`breadth`, `adversarial`, `gap`. A Key finding may not rest on a single `breadth` source —
cite a corroborating source too, or state it in Open questions. Fix by adding a citation,
never by relabelling a lens.

**Summary shape (gate: `summary-scannable`).** A line starting with `**Answer:**` and at
least two bullets (aim for three to six). The `**Counter-position:**` and `**Still
open:**` lines are required by the writer contract; the gate does not check them.

**Paragraph cap (gate: `no-wall-of-text`).** No paragraph, blockquote, or single bullet
longer than 700 characters, which is about five sentences. One idea per paragraph. When
a paragraph grows past the cap, split it at a sentence boundary or turn it into bullets.
Tables, headings, and fenced code are exempt.

**Required sections (gate: `required-sections`).** `## Summary`, `## Key findings`,
`## Open questions`, `## Sources`, with Sources last. Match the headings exactly.

**One section per atomic item.** Body H2s follow the atomic items in order. A heading is
plain words that name the item, at most eight words; the item id may prefix it
(`## Q2. Single-thread cost per version`). Each section opens with a lead of one to
three sentences that answers the item, then `**What the sources show**` bullets, then
optional `**Caveats**` bullets. Add H3s only when an item has named sub-parts.

**Tables for comparisons.** When the query names two or more entities, or asks "for each
X: A, B, C", put an `## At a glance` table right after the Summary with one row per
entity and one column per field. Sections keep their own tables where a comparison
needs more detail. Omit At a glance for single-subject queries.

**Bullets over prose.** Three or more parallel facts become bullets. A bullet is at most
two sentences. Bold the lead phrase of every Summary bullet.

**Numbers live in tables or bullets**, not in the middle of a paragraph. A version,
percentage, or date that changes what the reader does gets its own bullet or cell.

**Silence is labelled.** A cell or bullet that no source supports says
"not documented in this corpus". Never fill a gap with inference presented as fact.

**Wrap at 100 characters.** Blank line between paragraphs, bullets, tables, and headings.

## Fix path for a gate failure

- `summary-scannable`: add the missing `**Answer:**` line from the first sentence of
  the Summary, or split the opening paragraph into bullets. One Edit hunk.
- `no-wall-of-text`: the gate detail names the section and the first words of each
  offending paragraph. Split at a sentence boundary or convert to bullets. One Edit
  hunk per paragraph. Never delete a citation while splitting.
- `required-sections`: add the missing heading in its place. An Open questions
  section with one bullet naming what the corpus could not settle is enough.

## Example (abridged)

```markdown
# Free-threaded CPython is supported, opt-in, and not yet the default

> **Query:** What is the current status of free-threaded (no-GIL) CPython?
> **Date:** 2026-09-10 · **Sources:** 15 · **Register:** analyze

## Summary

**Answer:** Free-threaded CPython is officially supported since 3.14 but remains a
separate opt-in build, and no release has committed to making it the default [1][2].

- **Status by version.** 3.13 experimental, 3.14 supported (PEP 779), 3.15 adds a shared
  stable ABI [1][3].
- **Single-thread cost.** Roughly 5-10% in 3.14, down from 20-40% in 3.13 [3][5].
- **Ecosystem gate.** One extension without the opt-in flag re-enables the GIL for the
  whole process [4].

**Counter-position:** "Supported" describes the interpreter, not the ecosystem; an April
2026 survey still marked pandas as partially re-enabling the GIL [4].

**Still open:** whether that pandas re-enable is pandas itself or a dependency.

## At a glance

| Version | Status | Single-thread overhead | Default? |
|---|---|---|---|
| 3.13 | experimental | 20-40% [3] | no |
| 3.14 | supported (PEP 779) | 5-10% [3][5] | no |
| 3.15 | supported + stable ABI | not documented in this corpus | no |

## Q1. Which versions support the free-threaded build

3.13 shipped it as experimental and 3.14 promoted it to supported under PEP 779 [1][2].

**What the sources show**

- 3.13 installers offer the free-threaded binary as an option [5].
- 3.14 ships `python3.14t` as a separate binary the user opts into [4].

**Caveats**

- The Phase III (default) decision is deferred to a future PEP [2].

## Key findings

- (pattern) Free-threaded CPython is supported but opt-in as of 3.14 [1][2].
- (pitfall) Any extension without the free-threading flag re-enables the GIL [4].

## Open questions

- **Is the pandas GIL re-enable from pandas or a dependency?** A pandas issue tracker
  entry or a `sys._is_gil_enabled()` trace on import would settle it.

## Sources

| n | id | title | url | lens |
|---|---|---|---|---|
| 1 | 001 | What's New in Python 3.14 | https://docs.python.org/3.14/whatsnew/3.14.html | canonical |
| 2 | 002 | PEP 779 | https://peps.python.org/pep-0779/ | canonical |
```
