# Navigator v7.6.0 Release Notes — "Provenance, Not Reputation"

**Release Date**: 2026-09-14
**Type**: Minor — source lens recorded end to end, thirteenth ship-gate check, fifth critic pass

## Summary

nav-deep-research has always planned its searches from three lenses — breadth, canonical
(primary sources), adversarial — and then thrown that information away. Every source note
in the first live run read `suggested_by: seed`, so nothing downstream could tell a spec
from a blog that a generic search happened to surface.

v7.6.0 carries the lens through (TASK-78): from the search queue into the source note,
into the writer's digest, into the report's Sources table. One new gate check uses it:
a Key finding may not rest on a single `breadth`-lens source.

The deliberate non-feature is a quality score. A number attached to a source is a model
opinion dressed as a metric, and the ship gate only keeps checks a script can settle.
The lens is a fact about which search found a URL, not a judgment about the source, so it
is checkable. Source quality proper stays with the critic, which now runs a fifth pass
for exactly this case.

## What prompted it

A question on the launch post: given a critic and a deterministic gate but no
source-quality scoring, has citation coverage been enough in practice? Counting the one
live run by hand: 22 sources, 14 primary by domain, and 12 of the 17 citations behind the
findings pointing at primary sources. The weak sources — news re-posts, a forum thread,
two SEO blogs — never reached a finding. They only padded the body. Good enough for the
findings, not for the body, and nothing in the pipeline recorded why.

## What's New

**The lens travels.** `source_store.py` defines the vocabulary (`breadth`, `canonical`,
`adversarial`, `gap`) and normalizes anything else to `unspecified`. Fetchers pass
`--lens`; `--suggested-by` still works. The digest shows a `lens:` line per source, and
the writer copies it into a fifth Sources column.

**`findings-corroborated`** (gate check thirteen). Fails when a Key finding's only
citation is a `breadth`-lens source, naming the finding. A lone `canonical` or
`adversarial` source passes: a spec, a vendor doc or a bug report can stand alone.
Reports without a lens column are exempt, so runs from earlier versions still gate.

**Corroboration pass** (critic pass five). Flags the same case at severity major before
the gate sees it. Fix by citing a corroborating source already on disk, or by moving the
claim to Open questions — never by relabelling a lens.

## Upgrade note

Runs from earlier versions keep `unspecified` lenses and are exempt from the new check.
The Sources table gained a column; the parser accepts both shapes.

## Files

- `skills/nav-deep-research/functions/` — `source_store.py`, `report_parse.py`, `ship_gate.py`
- `skills/nav-deep-research/steps/` — `2-sweep.md`, `6-ship.md`; `reference/REPORT-FORMAT.md`
- `agents/` — `deep-research-fetcher.md`, `deep-research-writer.md`, `deep-research-critic.md`
- `.agent/tasks/TASK-78-source-lens-and-corroboration.md`
