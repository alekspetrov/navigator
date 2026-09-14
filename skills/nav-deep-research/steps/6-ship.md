# Step 6: Ship

**Who:** main session. **Artifact:** `ship.json` (written only when the gate passes),
graph memories, an index line in `.agent/DEVELOPMENT-README.md`.

## Procedure

1. `python3 "$NDR/research_run.py" step --run <slug> --start 6`
2. **Gate.**
   ```bash
   python3 "$NDR/ship_gate.py" --run <slug> --min-sources <config.min_sources>
   ```
   Exit 0 means shippable. On exit 1, read the failing checks and fix the report with
   Edit hunks: add the missing Sources row, remove the dangling `[n]`, type the untyped
   bullet, apply the unresolved critical finding. Rerun. Three rounds without a pass:
   `research_run.py step --run <slug> --block 6 --reason "<failing checks>"` and tell
   the user which checks fail. Never change `--min-sources`, the gate script, or the
   meaning of a check.
3. **Graph ingestion.** Dry run first, then real:
   ```bash
   python3 "$NDR/report_to_graph.py" --run <slug> --dry-run
   python3 "$NDR/report_to_graph.py" --run <slug>
   ```
   Every typed Key findings bullet becomes a memory with the cited URLs as evidence,
   each tagged `fetched YYYY-MM-DD, sha256 <12 hex>` from the run's local source note
   (URL only when the note is missing). `source_store.py refetch` compares the hash.
   Skip this when `.agent/knowledge/graph.json` does not exist and say so.
4. **Index line.** Append one line to the `## Documentation Structure` section of
   `.agent/DEVELOPMENT-README.md` under a `### Research Reports (research/)` heading
   (create the heading on first use):
   ```
   - `research/<slug>/report.md` — <report title> (<K> sources, <date>)
   ```
5. **Marker.** Create `.agent/.context-markers/research-<slug>-<YYYYMMDD-HHMM>.md` with
   the query, the slug, the gate summary, and the memory ids ingested, so a later
   session can find the run.
6. `python3 "$NDR/research_run.py" step --run <slug> --done 6`
7. **Tell the user**, in this shape and nothing longer:
   ```
   **Research shipped:** `.agent/research/<slug>/report.md`

   - Sources: K cited (ok=…, blocked=…, skipped=…)
   - Critic: a applied, 0 unresolved
   - Graph: n memories added (ids …)
   - Open questions: <count> (listed in the report)

   ## Summary
   <the report's ## Summary section, verbatim: the **Answer:** line, the bullets,
   the counter-position, the still-open line>
   ```
   The Summary is the reader's whole first screen, so it is quoted as written; do not
   paraphrase or compress it.

## Hyperresearch backend

When `run.json.backend` is `hyperresearch`: copy `research/notes/final_report_*.md`
(newest) to `<run_dir>/report.md`, mark steps 1-5 skipped with reason `hyperresearch`,
skip the gate (different citation format) and run only items 3, 5, 6, 7 above with
`report_to_graph.py`. Its report must still carry a `## Key findings` section with typed
bullets for ingestion; if it lacks one, add it yourself from the report's conclusions,
citing nothing, and say so.

## Exit criterion

`ship.json` exists with `ok: true`, the graph ingest JSON shows no errors, the README
line is in place.
