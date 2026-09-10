# Step 3: Draft

**Who:** one `deep-research-writer` subagent. **Artifact:** `report.md`, written once.

## Procedure

1. `python3 "$NDR/research_run.py" step --run <slug> --start 3`
2. Collect the writer's inputs from `run.json` (`python3 "$NDR/research_run.py" status
   --run <slug>`): `meta.atomic_items`, `meta.register`, `meta.coverage_gaps`.
3. Spawn ONE writer, `subagent_type: navigator:deep-research-writer`, model from
   `config.models.writer`. Prompt = spawn contract, then:
   ```
   atomic_items: <the JSON list>
   register: <analyze|survey|teach>
   coverage_gaps: <list or none>  (state these in Open questions; do not invent coverage)
   max_full_reads: <config.max_full_reads>
   Write <run_dir>/report.md in one Write call. Follow the citation contract exactly.
   ```
4. While it runs, keep `<run_dir>/orchestrator-notes.md` updated with a tool call; no
   bare text turns.
5. When the writer returns, run a quick pre-check without writing `ship.json`:
   ```bash
   python3 "$NDR/ship_gate.py" --run <slug> --min-sources <config.min_sources> --no-write
   ```
   Only `citations-resolve`, `required-sections`, `no-citation-ranges` and
   `key-findings-typed` matter here. If any of those fail, fix them with small Edit
   hunks yourself (a missing Sources row, a `[3-5]` range, an untyped bullet). Do not
   rerun the writer for these. Content problems are the critic's job, not yours.
6. Record the Sources row count so the gate can prove the patcher never shrank it:
   ```bash
   ROWS=$(grep -cE '^\| *[0-9]+ *\| *[0-9]{3} *\|' <run_dir>/report.md)
   python3 "$NDR/research_run.py" set --run <slug> --key sources_rows_before_patch --value "$ROWS"
   ```
7. `python3 "$NDR/research_run.py" step --run <slug> --done 3`

## Exit criterion

`report.md` exists with Summary, body sections, Key findings, Open questions, Sources;
the four structural gate checks pass.

## Next

If `config.critic_enabled` is false: skip 4 and 5
(`research_run.py step --run <slug> --skip 4 --reason "critic disabled"`, same for 5) and
read `steps/6-ship.md`. Otherwise read `steps/4-critique.md`.
