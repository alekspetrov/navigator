# Step 5: Patch

**Who:** one `deep-research-patcher` subagent. **Artifact:** `patch-log.json` and the
edited `report.md`.

## Procedure

1. `python3 "$NDR/research_run.py" step --run <slug> --start 5`
2. Build the `available_sources` table the patcher needs (it has no Bash):
   ```bash
   python3 "$NDR/source_store.py" list --run <slug> --status ok
   ```
   Render as `| id | title | url | fetch_method |` rows.
3. Spawn ONE patcher, `subagent_type: navigator:deep-research-patcher`, model from
   `config.models.patcher`. Prompt = spawn contract, then:
   ```
   draft_path: <run_dir>/report.md
   findings_path: <run_dir>/findings/critic.json
   output_path: <run_dir>/patch-log.json
   available_sources:
   | id | title | url | fetch_method |
   ...
   ```
   The patcher's Write is for the patch log only. If its return line reports it wrote
   the report, treat the run as compromised: `git diff` the report, revert any
   wholesale change, and rerun this step.
4. While it runs, update `<run_dir>/orchestrator-notes.md` with a tool call; no bare
   text turns.
5. Read `patch-log.json`. For each `unresolved` critical finding: open the finding, find
   the intended anchor in the report yourself, and apply it as ONE Edit hunk. Then move
   it from `unresolved` to `applied` in the log with an Edit. If it truly cannot be
   anchored, leave it unresolved; the gate will block and the user decides.
6. `python3 "$NDR/research_run.py" step --run <slug> --done 5`

## Exit criterion

`patch-log.json` exists; every finding id is in exactly one of applied, rejected,
unresolved.

## Next

Read `steps/6-ship.md`.
