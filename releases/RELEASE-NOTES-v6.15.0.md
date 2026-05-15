# Navigator v6.15.0 Release Notes

**Release Date**: 2026-05-15
**Type**: Minor — `nav-features` exposes the full configurable surface

---

## Summary

The `nav-features` skill used to show five entries. The shipping `.nav-config.json` has thirteen toggleable features today. This release closes that gap: every configurable Navigator feature now shows up in the table, including the v6.0.0 Knowledge Graph, Multi-Agent orchestration, and the six lifecycle hooks that gate Navigator's safety guarantees.

No behavioral change to the features themselves. Just the discovery surface.

---

## What changed

### 8 features added to the table

Core (v6.0.0 features that existed but weren't surfaced):
- `knowledge_graph` — unified project knowledge + experiential memories
- `multi_agent` — parallel agent orchestration (the `nav-multi` skill)

Hooks (all six toggleable hooks now visible):
- `compact_hook` — pre-compact summary injection
- `workflow_enforcer_hook` — enforces the `WORKFLOW CHECK` block
- `read_guard_hook` — warns/blocks on excessive `.agent/` reads
- `workflow_state_hook` — tracks task/phase across the session
- `task_graph_sync_hook` — auto-syncs task files into the knowledge graph
- `profile_sync_hook` — auto-captures profile corrections

### Renames and fixes

- **`multi_claude` → `multi_claude_scripts`**: the install-check entry (PATH presence of `navigator-multi-claude.sh`) was renamed to disambiguate from the new `multi_agent` config flag. They check different things — sharing the `multi_claude` name was actively misleading.
- **`simplification.default = True`**: was `False`. The shipping config and CLAUDE.md both treat it as on; the default literal was just wrong. Only affected the fallback when the config section was entirely missing.
- **Name column 15 → 23 chars**: fits `workflow_enforcer_hook` (22 chars) without truncation.

### Docs

- `SKILL.md` sample output regenerated for the 14-row table; hardcoded `v5.6.0` strings replaced with `<version>` placeholder.
- Supported-features list split into **Core**, **Hooks**, **Install-based** sections with a caution note about disabling guardrail hooks like `workflow_enforcer_hook` and `read_guard_hook`.

---

## How to use it

```
"Show my Navigator features"
```

Renders the full table:

```
v6.15.0 Features:

┌─────────────────────────┬────────┬───────────────────────────────────────────────┐
│ Feature                 │ Status │ Description                                   │
├─────────────────────────┼────────┼───────────────────────────────────────────────┤
│ task_mode               │ [x]    │ Auto-detects task complexity, defers to sk... │
│ tom_features            │ [x]    │ Verification checkpoints, user profile, di... │
│ loop_mode               │ [ ]    │ Autonomous loop execution (enable when nee... │
│ simplification          │ [x]    │ Post-implementation code cleanup with Opus    │
│ auto_update             │ [x]    │ Auto-updates on session start                 │
│ knowledge_graph         │ [x]    │ Unified project knowledge + experiential m... │
│ multi_agent             │ [x]    │ Parallel agent orchestration (nav-multi sk... │
│ multi_claude_scripts    │ [*]    │ External shell scripts for multi-Claude wo... │
│ compact_hook            │ [x]    │ Injects rich summary into compacted sessions  │
│ workflow_enforcer_hook  │ [x]    │ Enforces WORKFLOW CHECK block before task ... │
│ read_guard_hook         │ [x]    │ Warns on excessive Reads (push to agents)     │
│ workflow_state_hook     │ [x]    │ Tracks current task/phase across the session  │
│ task_graph_sync_hook    │ [x]    │ Auto-syncs task files into the knowledge g... │
│ profile_sync_hook       │ [x]    │ Auto-captures preferences/corrections into... │
└─────────────────────────┴────────┴───────────────────────────────────────────────┘
```

Status legend:
- `[x]` — config-enabled
- `[ ]` — disabled
- `[*]` — install-detected (only used for `multi_claude_scripts`)

Toggle as before:
```
"Disable loop_mode"
"Enable knowledge_graph"
```

For details on a single feature:
```
"What does workflow_enforcer_hook do?"
```

---

## Compatibility

- No breaking changes to existing feature names. Only `multi_claude` renamed, and that entry was install-detected (no user-addressable toggle), so nobody was scripting against it.
- All toggle round-trips verified clean against the actual `.nav-config.json` schema.
- Disabling a guardrail hook (`workflow_enforcer_hook`, `read_guard_hook`) weakens Navigator's enforcement — the skill flags this in the supported-features doc but doesn't block the toggle.

---

## Files modified

```
skills/nav-features/functions/feature_manager.py
skills/nav-features/SKILL.md
.claude-plugin/marketplace.json
.claude-plugin/plugin.json
README.md
CLAUDE.md
.agent/.nav-config.json
CHANGELOG.md
releases/RELEASE-NOTES-v6.15.0.md  (new)
```
