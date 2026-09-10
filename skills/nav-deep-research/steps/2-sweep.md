# Step 2: Sweep

**Who:** main session (WebSearch, batching) + N `deep-research-fetcher` subagents.
**Artifact:** `sources/NNN.md` notes, at least `min_sources` with `status: ok`.

**Goal:** every atomic item has at least two usable sources; total usable sources
between `min_sources` and `max_sources`.

## Procedure

1. `python3 "$NDR/research_run.py" step --run <slug> --start 2`
2. **Build the URL queue.** Run the searches in `search-plan.md` with `WebSearch`. From
   each result set keep the 2-4 most promising URLs, tagged with the atomic item and
   lens. Drop obvious junk (link farms, product listings, social feeds). Do not open
   pages yourself; fetchers do that. Stop adding when the queue reaches about
   1.5x `max_sources` (some fetches will fail).
3. **Batch and spawn.** Split the queue into `fetchers` disjoint batches, balanced across
   atomic items so one blocked site cannot empty an item. Spawn all fetchers in ONE
   message with `subagent_type: navigator:deep-research-fetcher`, model from
   `config.models.fetcher`. Each prompt follows the spawn contract and then lists:
   ```
   batch (yours alone):
   | url | atomic_item | suggested_by |
   | https://... | Q1 | seed |
   max_chars: 40000
   ```
4. **While fetchers run, do not emit a bare text turn.** Append your evolving notes to
   `<run_dir>/orchestrator-notes.md` (what you expect each item to show, which items
   look thin) with a tool call.
5. **Coverage check** after all fetchers return:
   ```bash
   python3 "$NDR/source_store.py" list --run <slug> --status ok
   ```
   Map ok notes back to atomic items using the fetcher reports. Any item with fewer
   than two ok sources is a gap. Any fetcher report row marked `junk` does not count.
6. **One gap wave, at most.** For gap items only: run 2-3 new searches per item (prefer
   canonical and adversarial lenses), build a small queue, spawn one or two fetchers.
   Then re-check. If an item still has fewer than two sources, record it:
   ```bash
   python3 "$NDR/research_run.py" set --run <slug> --key coverage_gaps --value '["E3"]'
   ```
   The writer will state the gap in Open questions instead of papering over it.
7. If ok sources are below `min_sources` after the gap wave, block the run and say so:
   `python3 "$NDR/research_run.py" step --run <slug> --block 2 --reason "only K ok sources"`.
   Do not proceed to drafting on a corpus the gate will reject.
8. `python3 "$NDR/research_run.py" step --run <slug> --done 2`

## Exit criterion

ok sources >= `min_sources`, every atomic item has >= 2 ok sources or is listed in
`coverage_gaps`.

## Next

Read `steps/3-draft.md`.
