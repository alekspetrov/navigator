# SOP: Diagnosing and Cleaning Corrupted Knowledge-Graph Memories

**Created**: 2026-07-09
**Trigger case**: nav-brief's memory recall surfaced `DECISION: "----------: -------- - -----------" (95%)` — a markdown table-separator row ingested as a decision memory, duplicated by a double task-sync (mem-038/mem-044…049). Fixed in v6.18.1.

## Symptom

Session-start "Relevant Memories" or any recall output (`memory_recall.py`, nav-brief injection, nav-graph queries) contains junk, duplicate, or nonsensical entries — often at high confidence, burning limited recall slots.

## Diagnosis

1. **Locate the node(s)** — search the raw graph, not just node summaries (junk can hide in any field):
   ```bash
   grep -o '"[^"]*<junk-substring>[^"]*"' .agent/knowledge/graph.json
   grep -rl -- '<junk-substring>' .agent/knowledge/memories/
   ```
2. **Dump the full memories bucket** and eyeball neighbors — corruption rarely arrives alone. In the trigger case the junk node exposed a *second* defect: a byte-identical duplicate set from a double sync (compare `created` dates and summaries).
3. **Identify the capture path** — which ingester wrote it? Candidates: `task_to_graph.py` (PostToolUse task-sync hook), `correction_to_memory.py`, `research_to_graph.py`, `execution_to_graph.py`. Match the memory's shape to the ingester's summary format (e.g. task decisions are `"{decision}: {chosen} - {reasoning}"`).
4. **Reproduce the parse** against the source doc before concluding — the bug is usually in extraction (regex/skip-list), not in `add_memory`.

## Cleanup

Use the graph's own removal path — never hand-edit `graph.json` (concept_index and edges must stay consistent):

```python
sys.path.insert(0, 'skills/nav-graph/functions')
from graph_manager import load_graph, save_graph, remove_node
from graph_maintenance import move_memory_file_to_resolved

graph = load_graph('.agent/knowledge/graph.json')
for mid in targets:
    node = graph['nodes']['memories'][mid]
    move_memory_file_to_resolved(node, '.', '.agent/knowledge')  # BEFORE remove
    graph = remove_node(graph, 'memories', mid)
save_graph('.agent/knowledge/graph.json', graph)
```

Key rules:
- **Archive the backing file to `resolved/` before removing the node** — otherwise the next `reconcile --execute` re-registers the file and resurrects the memory.
- `prune --execute` only removes below its confidence threshold (default 0.3); high-confidence junk needs explicit `remove-node`.
- After removal, run `graph_maintenance.py --action repair --execute` (idempotent) to clean any dangling edges, then `--action health` — expect 100/100.

## Verify

```bash
python3 skills/nav-graph/functions/memory_recall.py --auto \
  --agent-dir .agent --graph-path .agent/knowledge/graph.json \
  --limit 5 --format compact          # junk gone, real memories surface
python3 skills/nav-graph/functions/graph_maintenance.py --action health \
  --graph-path .agent/knowledge/graph.json
```

## Prevention (fix the ingester, not just the data)

Data cleanup without a parser fix means the junk returns on the next sync. In the trigger case, two code fixes shipped (v6.18.1, `task_to_graph.py`):
- Separator-row skip changed from exact-match (`'---'`, `'-'`) to `re.fullmatch(r'[-:\s]+', cell)` — catches wide (`----------`) and colon-aligned (`:---:`) cells.
- Re-sync dedupe: skip decision summaries already present in the graph.

Always add regression tests for the exact malformed input (see `test_task_to_graph.py::DecisionExtractionTest` / `DecisionDedupeTest`).

**Version caveat**: the sync hook runs from the *installed* plugin. Until users update past the fixed version, an old hook can re-ingest junk — call this out in release notes.

## Related

- mem-003 (memory-ID counter reset pitfall), mem-009 (dangling path pitfall)
- `releases/RELEASE-NOTES-v6.18.1.md` — the trigger case, full detail
- v6.17.0 release notes — resolve/reconcile/prune lifecycle semantics
