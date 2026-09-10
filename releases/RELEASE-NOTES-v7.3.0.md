# Navigator v7.3.0 Release Notes — "Deep Research"

**Release Date**: 2026-09-10
**Type**: Minor — new skill + four agents + one config block; ships OFF; one read-guard
default widened (directory allowlist)

## Summary

Navigator's research so far meant codebase research: the `navigator-research` agent
mapping your own repo into the knowledge graph. v7.3.0 adds research about the outside
world. Say "deep research on X" and the new `nav-deep-research` skill turns the question
into a cited `report.md` built from fetched web sources, attacked by an adversarial critic,
patched by hunks, checked by a deterministic ship gate, and folded into the knowledge
graph as typed memories with URLs as evidence.

The design borrows the load-bearing ideas of the hyperresearch harness and drops its
weight: no SQLite vault, no academic APIs, no browser lane, no pip dependencies. Every
heavy step runs in a subagent, so the main session's context stays lean (TASK-74).

The feature ships **off**. Enable it with `"enable deep_research"` or
`deep_research.enabled: true` in `.agent/.nav-config.json`. A run fetches dozens of
third-party pages and spends several opus subagent calls; that is an opt-in.

## What's New

**`nav-deep-research` skill.** A thin router: enabled check, functions-dir resolver,
pipeline table, spawn contract, invariants, recovery table. Each step's procedure lives in
its own file (`steps/1-decompose.md` … `6-ship.md`) and is loaded with `Read` when the
step starts, so a two-hour run never depends on a procedure that compaction evicted.

| Step | Who | Artifact |
|---|---|---|
| 1 Decompose | main session | atomic items + three-lens search plan (breadth, canonical, adversarial) |
| 2 Sweep | WebSearch + N parallel fetchers | `sources/NNN.md` |
| 3 Draft | one writer subagent | `report.md`, written once |
| 4 Critique | one critic subagent | `findings/critic.json` |
| 5 Patch | one patcher subagent | `patch-log.json` |
| 6 Ship | main session | `ship.json`, graph memories, README index line |

**Four agents.** `deep-research-fetcher` (sonnet; stdlib fetch first, WebFetch only as a
tagged fallback), `deep-research-writer` (opus; digests all sources, full-reads at most
`max_full_reads`), `deep-research-critic` (opus; four passes — dialectic, support, quote
integrity, instruction — no Edit tool), `deep-research-patcher` (opus; Read + Edit only,
applies findings as surgical hunks, forwards anything larger as structural).

**Untrusted-content fence.** Every fetched body is stored inside
`<nav-untrusted-source url="…">` with a treat-as-data preamble. Forged fence tags inside a
page are renamed, not removed; the URL attribute is escaped with control characters
stripped. Agents are told, in writing, that nothing inside a fence is an instruction.

**Citation contract + ship gate.** `[n]` citations in first-use order, a `## Sources`
table `| n | id | title | url |` as the last section, typed `## Key findings` bullets.
`ship_gate.py` checks ten things and exits 1 on any failure: report exists, required
sections, no ranges, body citations == table rows, every row has an ok note, no fence
leak, no unresolved critical findings, Sources never shrank after patching, minimum
source count, findings typed. Gate failures are fixed in the report, never by changing
the gate.

**Resume.** `run.json` records every step; `research_run.py resume` returns the next step
from the manifest, falling back to an artifact scan when the manifest is stale.

**Graph ingestion.** `report_to_graph.py` turns each Key findings bullet into a memory
whose evidence is the cited URL(s) and hands the batch to the existing
`research_to_graph.ingest_findings` (0.7 confidence, same four memory types, no schema
change).

**Hyperresearch handoff.** A project with a `.hyperresearch/` directory gets the heavier
harness for the run and Navigator only ingests its final report.

## Changed

- **Read guard**: allowlist entries ending in `/` now match by prefix, and `research/` is
  in the default allowlist. Subagents reading many source notes in one turn would
  otherwise hit the escalate threshold. Exact-match entries behave as before.
- **Config**: new `deep_research` block in `DEFAULTS` (enabled false, max_sources 30,
  min_sources 8, fetchers 4, max_full_reads 10, critic_enabled true, per-role models);
  seeded into existing installs by `VERSION_CONFIGS["7.3.0"]`; toggle row in nav-features.
- **`.gitignore`**: `.agent/research/*/sources/` (fetched bodies are third-party text and
  large; `source_store.py refetch` rebuilds them and reports sha mismatches).
- `agents/navigator-research.md` description points web questions at the new skill.

## Verified

- `make test` green; 65 new stdlib unit tests for the helpers (fence, canonical URLs,
  fetch classification via injected opener, concurrent id allocation, every gate failure
  mode, ingestion mapping, resume from stale manifests).
- End-to-end dry run on "current status of free-threaded CPython": 15 sources, critic 20
  findings (1 critical) all applied, gate 10/10, removing one Sources row by hand fails
  two checks, ingestion validated against a temp graph copy.

## Known limitations

- WebFetch fallback returns model-summarized text; such sources are tagged
  `fetch_method: webfetch` and may be paraphrased, never quoted. The gate has no verbatim
  oracle for this.
- PDFs are recorded as skipped; no extraction.
- The new agent types exist only after the plugin update and a session restart. The
  frontmatter tool locks were not exercised live before this release.

## Upgrade

`claude plugin update navigator`, restart the session, then optionally
`"enable deep_research"`. Existing configs gain the block on the next `nav-sync-claude`
run. No breaking changes; downgrade is a plain plugin downgrade.

Task: `.agent/tasks/TASK-74-nav-deep-research.md`.
