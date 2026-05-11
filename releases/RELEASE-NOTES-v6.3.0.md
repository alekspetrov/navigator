# Navigator v6.3.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor Release (Research Agent + Autonomous Loop + Reliability Fixes)

---

## Summary

Navigator v6.3.0 turns the `navigator-research` agent from a prose generator into a structured input for the knowledge graph, extends Loop Mode for true overnight runs, codifies the "context flooding" anti-pattern, and ships four reliability fixes for the nav-graph subsystem.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — particularly its NEVER STOP directive and discipline around verbose command output.

---

## Highlights

1. **navigator-research emits structured findings** that auto-flow into the knowledge graph — research persists across sessions.
2. **Loop Mode gains autonomous flags** (`iteration_approval`, `never_pause_on_stagnation`, `stagnation_diversify_strategy`) for unattended overnight runs.
3. **Anti-Pattern #9: Context Flooding** — codifies the "redirect → grep" rule for verbose command output.
4. **Four nav-graph reliability fixes** — memory ID collision, dangling file paths, missing concept aliases, write amplification.

---

## New: Structured Research Output

The `navigator-research` agent now appends a machine-parseable `research_findings` JSON block alongside its markdown summary. A new helper, `research_to_graph.py`, ingests those findings as graph memories.

### Agent upgrades (`agents/navigator-research.md`)

- **Phase 0: Navigator-first check** — consult `DEVELOPMENT-README.md` and `knowledge/graph.json` before exploring. Many questions are answered without a single Grep.
- **Language-agnostic entry points** — added Go, Rust, Java/Kotlin, .NET, Elixir, Ruby, PHP (was JS/Python-biased).
- **Unknowns / Out of Scope section** — research that doesn't surface gaps creates false confidence.
- **Real file counts** — `files_sampled` / `files_matched` replaces hand-waved token-savings estimates.
- **Disambiguated from generic `Explore`** — Explore for one-off lookups, navigator-research for architecture mapping that should persist.

### Ingestion (`skills/nav-graph/functions/research_to_graph.py`)

```bash
# Pipe agent output through
python3 skills/nav-graph/functions/research_to_graph.py findings.json
cat findings.json | python3 skills/nav-graph/functions/research_to_graph.py -

# Validate without writing
python3 skills/nav-graph/functions/research_to_graph.py findings.json --dry-run
```

- Default confidence: **0.7** (lower than corrections at 0.8, task decisions at 0.95 — research is inference)
- Memory types: `pattern`, `pitfall`, `decision`, `learning`
- Auto-extracts concepts from text if caller omits them
- Evidence path embedded into memory summary
- Invalid entries skipped with clear errors (exit 1 if any)

**Mirrors** the existing `correction_to_memory.py` and `task_to_graph.py` ingestion pattern.

---

## New: Autonomous Loop Mode

Three new keys in `loop_mode` config, all opt-in (defaults preserve existing behavior):

```json
{
  "loop_mode": {
    "iteration_approval": "none",
    "never_pause_on_stagnation": false,
    "stagnation_diversify_strategy": "combine"
  }
}
```

| Key | Values | Purpose |
|-----|--------|---------|
| `iteration_approval` | `"none"` \| `"strict"` \| `"periodic"` | When to prompt user between iterations |
| `never_pause_on_stagnation` | `bool` | When `true`, auto-diversify instead of `AskUserQuestion` pause |
| `stagnation_diversify_strategy` | `"combine"` \| `"radical"` \| `"reread"` | Which recovery to attempt |

### Per-iteration approval gate

New `Step 3.5` in `nav-loop` SKILL — runs after the NAVIGATOR_STATUS block, before stagnation/exit gates:

- `"strict"` — prompt after every iteration
- `"periodic"` — prompt every 3rd iteration (good for overnight check-ins)
- User can **Continue**, **Adjust** (incorporate feedback, no stagnation hash advance), or **Abort**

### Auto-diversification on stagnation

When `never_pause_on_stagnation: true`, stagnation triggers automatic recovery instead of an `AskUserQuestion` pause. Mirrors autoresearch's directive: *"If you run out of ideas, think harder — read papers, re-read in-scope files, try combining previous near-misses, try more radical architectural changes."*

| Strategy | What happens next iteration |
|----------|-----------------------------|
| `combine` | Combine 2 near-miss approaches from previous iterations |
| `radical` | Discard current approach, try substantially different design |
| `reread` | Re-read in-scope task/system docs for missed signals |

**Safety guard**: `never_pause_on_stagnation: true` requires `max_iterations` to be set explicitly. Loop also escalates to abort after 3 diversifications in a single run.

---

## New Anti-Pattern: Context Flooding from Command Output

Anti-Pattern #9 in `.agent/philosophy/ANTI-PATTERNS.md` codifies the "redirect verbose output to a file, then grep" rule.

**The bad pattern** — verbose output flows inline:
```bash
npm test                    # 8k tokens
python train.py             # 12k tokens of progress logs
grep -r "useState" src/     # 5k tokens of matches
```

**The fix** — redirect, then filter:
```bash
npm test > test.log 2>&1
grep -E "(FAIL|✗|^Tests:)" test.log | head -20
```

97% token savings on typical test runs. Cross-linked to Anti-Pattern #3 (LLM-parsing structured data) and Pattern #3 (Preprocessing Before LLM) — same principle, shell-level companion.

---

## Reliability Fixes (nav-graph)

These were surfaced by running the upgraded `navigator-research` agent on the nav-graph subsystem itself. The agent flagged 4 real issues; all are fixed in this release.

### Fix: Memory ID collision (mem-003)

`add_memory()` previously generated IDs via `len(memories) + 1`. Deleting any memory reset the counter and the next add would silently overwrite an existing ID.

**Now**: `_next_memory_id()` scans existing IDs and uses `max + 1`. Tested with sequential, gaps, 4-digit IDs, and malformed entries.

### Fix: Dangling memory file paths (mem-009)

`add_memory()` stored a path like `memories/pitfalls/mem-001.md` in the graph node but **never created the file**. Research and correction-sourced memories ended up with dangling paths.

**Now**: `add_memory()` calls `memory_writer.create_memory_file()` inline. New params:
- `base_dir` (default `.agent/knowledge`)
- `create_file` (default `True`; set `False` for transient/test graphs)
- Non-fatal on failure — the graph node is still valid even if file creation fails

8 pre-existing memories (`mem-002` through `mem-009`) had their backing files backfilled during the release.

### Fix: Missing concept aliases (mem-005)

`resolve_concept_alias()` had no entries for `perf`, `latency`, `sec`, `vuln`, `config`, `env` — so memories ingested under `performance`/`security`/`configuration` concepts were invisible to abbreviation queries.

**Now**: 6 new aliases added.

### Fix: Write amplification in correction sync (mem-004)

`correction_to_memory()` called `load_graph` + `save_graph` inside the per-item loop, causing N file I/O cycles for N corrections.

**Now**: Extracted `_correction_to_memory_in_graph()` (pure in-memory). `sync_corrections_to_graph()` loads once, mutates in memory, saves once — matches the `research_to_graph.py` pattern. Single-item `correction_to_memory()` kept for backward compatibility.

---

## Files Changed

| File | Change |
|------|--------|
| `agents/navigator-research.md` | Phase 0, lang-agnostic detection, Unknowns, JSON output schema |
| `skills/nav-graph/functions/research_to_graph.py` | **New** — ingest findings as memories |
| `skills/nav-graph/functions/graph_manager.py` | ID collision fix, file backing, 6 concept aliases |
| `skills/nav-graph/functions/correction_to_memory.py` | Batch I/O refactor |
| `skills/nav-graph/SKILL.md` | Documented research-ingestion path |
| `skills/nav-loop/SKILL.md` | Step 3.5 approval gate, autonomous stagnation branch |
| `.agent/.nav-config.json` | 3 new `loop_mode` keys, v6.3.0 |
| `.agent/philosophy/ANTI-PATTERNS.md` | New Anti-Pattern #9: Context Flooding |
| `CLAUDE.md` | v6.3.0 notes, Loop Mode docs |
| `.claude-plugin/plugin.json` | v6.3.0 |
| `.claude-plugin/marketplace.json` | v6.3.0 + breaking_changes entry |
| `README.md` | v6.3.0 badge |
| `.agent/knowledge/memories/` | 8 backfilled memory files + 8 new (review findings) |

---

## Upgrade Path

**From v6.1.0 / v6.2.1**: No breaking changes. All new flags are opt-in with backward-compatible defaults.

- Existing nav-loop tests pass (23/23) unchanged
- Existing `add_memory()` signature is backward compatible (new params have defaults)
- Existing graph queries still work; abbreviations that used to fail (`perf`, `config`, etc.) now resolve

**To opt into new behavior**:

```json
{
  "loop_mode": {
    "iteration_approval": "periodic",
    "never_pause_on_stagnation": true,
    "stagnation_diversify_strategy": "combine"
  }
}
```

---

## Meta: Self-Improving Loop

This release ran a genuine self-improving cycle:

1. Built `navigator-research` improvements + structured ingestion (3 commits)
2. **Used the new agent to review its own subsystem**
3. Agent flagged 4 real bugs — including a regression introduced in step 1
4. Fixed all 4 (3 commits)
5. Ingested the fix-verification memory through the same pipeline

The knowledge graph now contains 10 memories, all with backing files, all queryable by abbreviation. Validates the design end-to-end on the most demanding possible target: itself.

---

## Credits

- **karpathy/autoresearch** — for the NEVER STOP directive, capture-to-file discipline, and proof that `program.md` is "essentially a super lightweight skill"
- **navigator-research agent** — for finding 4 of its own bugs

---

**Powered By**: Navigator (Complete Framework)
