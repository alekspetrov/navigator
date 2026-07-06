# Navigator v6.17.0 Release Notes

**Release Date**: 2026-07-06
**Type**: Minor — closes the memory loop; backward compatible

---

## Summary

**Memories are now written safely, stay consistent with the graph, and
surface automatically at the two moments they matter** — session start and
task planning.

Motivated by a live audit of a consumer repo (pilot, 2026-07-05/06): **52 of
84 memory files had zero graph presence**, 42 freeform concept tags had no
concept nodes, **19 superseded memories would have been served as truth**,
and zero automatic recall existed — `auto_surface_relevant` had been a
config flag with prose instructions since v6.0.0 that no code ever read.

Every root cause found in that audit is closed by this release.

---

## What changed

### 1. Automatic recall — the headline

**Session start** (`hooks/nav_session_start.py`): a new `## Relevant
Memories` block is injected by the SessionStart hook — top-N memories whose
concepts overlap your open tasks and active context marker. Gated by
`knowledge_graph.auto_surface_relevant` (default `true`), capped by
`max_session_memories` (default 5). Placed before the navigator section so
budget truncation can never eat it. Third hook subprocess runs at
`timeout=3` to respect the 10s hook budget (real cost <300ms).

**Task planning** (`nav-task` Step 2.5): the CREATE flow now queries the
graph for concepts inferred from the feature description and writes a
`## Known Pitfalls & Patterns` section into the task doc — which flows into
GitHub issues and Pilot executor prompts. Recalled pitfalls must be
reflected in the Implementation phases. Empty recall → no section, silently.

Both surfaces use one deterministic ranker: **`memory_recall.py`** (new).
Score = concept overlap (alias-resolved) → confidence → id. Resolved
memories excluded. Never touches `concept_index`, so consumer graphs
without one work by construction. Silence over noise: missing graph / no
targets / no matches → empty stdout, exit 0.

### 2. Write-loop integrity

- **`add_memory` is fail-loud and ordered**: backing `.md` written BEFORE
  the node; file failures propagate with the graph unmutated (previously
  swallowed with a warning → path-points-at-nothing nodes). CLI rolls the
  file back when the graph save fails. All 4 programmatic call sites wrap
  the new exceptions (record + skip; sync hooks never die mid-batch).
- **Write-time concept validation** at the CLI boundary: unknown concepts
  reject the write and print the valid vocabulary; `--allow-new-concept`
  registers them instead. Vocabulary = concept nodes + aliases —
  deliberately NOT `concept_index`, which self-legitimizes every tag ever
  written. Graphs without a curated vocabulary skip validation.
- **Rebuilds no longer wipe memories**: `graph_builder` used to initialize
  `memories: {}` on every rebuild. It now preserves the `memories`/`files`
  buckets and their edges (memories carry graph-only fields no scan can
  reconstruct). `--no-preserve-memories` opts into a from-scratch rebuild.

### 3. Disk-vs-graph reconciliation (`graph_maintenance.py`)

- `find_broken_file_links` / `find_unindexed_memory_files` /
  `find_invalid_concept_refs` — the drift detectors the audit had to
  hand-write. Schema-compatible with consumer graphs (`path` | `file` |
  `memory_file` keys, root-relative or base_dir-relative, summary-only
  nodes legal).
- **`--action reconcile`**: dry-run drift report; `--execute` registers
  unindexed files (type from parent dir, `resolved/` parent →
  `resolved: true`, frontmatter/heading parsing, conservative 0.5-confidence
  fallback). Broken-link nodes are never auto-deleted; concept refs never
  rewritten.
- **`health_check`** gains score-affecting `Broken File Links` +
  `Unindexed Memory Files` and advisory concept-drift / archived-files
  counts. ⚠️ **Consumer graphs with real drift will see their health score
  drop — that is the point.** `--root` supports running from outside the
  project.
- `repair` drops orphaned `concept_index` entries; `prune --execute` moves
  backing files to `resolved/` so reconcile can't resurrect pruned memories.

### 4. Supersession lifecycle

**`--action resolve-memory --node-id X [--superseded-by Y]`**: memories
that stop being true are resolved, not deleted — `resolved: true` +
`resolved_date` on the node, backing file moved to the sibling `resolved/`
directory (codifies the convention consumer repos evolved organically),
`supersedes` edge when a replacement is named. Resolved memories are
excluded from recall, skipped by stale/decay sweeps, and flagged
`[resolved]` in query output.

---

## Config

No new keys. `knowledge_graph.auto_surface_relevant` and
`max_session_memories` (both shipped in the v6.0.0 defaults) are now
enforced by code. Note: the memories hook section is gated by the
`knowledge_graph` flag, not `session_start_hook.include_sections` —
existing explicit `include_sections` lists predate the section and the
block-additive migrator cannot append to them.

## Verification

- 46 new/extended unit tests across `graph_manager`, `graph_builder`,
  `graph_maintenance`, `memory_recall`, `nav_session_start`; full
  `make test` green
- Live-validated against the pilot consumer graph (85 memories, `file:`
  schema, no concept_index): recall ranks correctly and excludes resolved;
  health reports 0 broken links / 0 unindexed active files on the
  freshly-reconciled corpus; hook end-to-end 0.51s with the memories
  section surviving budget truncation

## Follow-ups (not in this release)

- Consumer CI drift gate: `graph_maintenance.py --action health --root .`
- Pilot executor prompt injection via `memory_recall.py` (pilot-repo task)
