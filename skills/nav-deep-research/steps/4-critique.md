# Step 4: Critique

**Who:** one `deep-research-critic` subagent, then at most one gap-fetch wave.
**Artifact:** `findings/critic.json`.

## Procedure

1. `python3 "$NDR/research_run.py" step --run <slug> --start 4`
2. Spawn ONE critic, `subagent_type: navigator:deep-research-critic`, model from
   `config.models.critic`. Prompt = spawn contract, then:
   ```
   atomic_items: <JSON list from run.json>
   draft_path: <run_dir>/report.md
   output_path: <run_dir>/findings/critic.json
   ```
   The critic has no Edit tool; it cannot touch the report. Do not give it one.
3. While it runs, update `<run_dir>/orchestrator-notes.md` with a tool call; no bare
   text turns.
4. Read `findings/critic.json` when it returns. Triage:
   - `findings` go to the patcher unchanged. You do not soften severities.
   - `structural` items are yours. For each, decide: (a) the corpus already holds the
     evidence and the patcher can add a paragraph-sized hunk, so convert it into a
     finding with an exact `quote` anchor and append it to `findings` with a new id; or
     (b) the corpus lacks a source, so it needs a gap fetch; or (c) it is out of scope
     for the verbatim query, so record it in `orchestrator-notes.md` and drop it.
5. **Gap fetch (once, only if (b) occurred).** Search for the missing sources, spawn one
   `deep-research-fetcher` with a small batch (`suggested_by: critic`), then convert
   the structural item into a finding whose `source_ids` names the new note. Ok notes
   fetched here may only enter the report through the patcher's Sources-append rule.
6. `python3 "$NDR/research_run.py" step --run <slug> --done 4`

## Exit criterion

`findings/critic.json` exists and every structural item has been converted, gap-fetched,
or explicitly dropped in the notes.

## Next

Read `steps/5-patch.md`.
