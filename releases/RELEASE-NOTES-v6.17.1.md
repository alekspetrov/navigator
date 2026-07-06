# Navigator v6.17.1 Release Notes

**Release Date**: 2026-07-06
**Type**: Patch — consumer-graph write compatibility

## Summary

Hotfix found minutes after v6.17.0 shipped, while dispatching tasks in a
consumer repo: `add_node` (and `remove_node`/`add_edge`) hard-crashed with
`KeyError: 'concept_index'` on graphs that lack the `concept_index` /
`edges` keys — exactly the consumer schema v6.17.0's READ paths were built
to tolerate. `task_to_graph.py --action add` died syncing a new task into
the pilot repo graph.

## Fix

`graph_manager.add_node` / `remove_node` / `add_edge` now `setdefault` the
missing keys instead of assuming them. Pre-existing bug; surfaced by the
first real consumer-graph write after v6.17.0's compat work. 3 regression
tests added (pilot-shaped fixture: nodes only, no concept_index, no edges).
