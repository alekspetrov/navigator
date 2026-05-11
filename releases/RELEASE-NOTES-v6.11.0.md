# Navigator v6.11.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor (Phase 1 of TASK-38 — three new silent lifecycle hooks)

---

## Summary

v6.9.0 (SessionStart) and v6.10.0 (PreCompact/PostCompact) demonstrated the pattern: **policy belongs in hooks, judgment stays in the model**. v6.11.0 starts executing the roadmap that comes from that insight — TASK-38, the hook-migration umbrella.

This release ships **Phase 1**: three silent side-effect hooks that migrate three "model, remember to..." rules out of CLAUDE.md prose and into deterministic Python. Zero injected tokens, zero new model responsibilities. Each one fires on a lifecycle event Claude Code already exposes; each one runs a Python script Navigator already had; each one was waiting to be wired.

**Net effect**: The knowledge graph stays in sync with tasks and corrections without the model narrating "now I'll sync to graph." Workflow state is tracked turn-by-turn for Phase 2's blocking enforcer to consume.

This release is built on top of v6.10.3's hardened `settings_merger.py` — the safety pass that made it safe to widen the hook surface.

---

## The three hooks

### `hooks/nav_task_graph_sync.py` — Opp 4

**Event**: `PostToolUse`, matcher `Edit|Write`
**Trigger**: file path matches `.agent/tasks/TASK-*.md`
**Action**: `python3 task_to_graph.py --action add --task-path <file> --graph-path .agent/knowledge/graph.json`

**Q1 verified (was an open question in TASK-38)**: `add_node` does `graph["nodes"]["tasks"][task_id] = data`, an upsert-by-id. Re-running on the same task file overwrites in place — no duplicate nodes, no special `--action upsert` needed. The concept index uses an existence check so reruns are clean there too.

**Replaces**: `nav-task` Step "If knowledge graph exists, sync task to graph" prose, which depended on the model remembering.

### `hooks/nav_workflow_state.py` — Opp 2

**Event**: `Stop` (every assistant turn)
**Action**: Read last assistant message (from stdin's `last_assistant_message` or scan the JSONL transcript), pattern-match for `WORKFLOW CHECK` / `NAVIGATOR_STATUS` / loop phase, write `.agent/.nav-workflow-state.json`:

```json
{
  "schema": 1,
  "session_id": "abc123",
  "updated_at": "2026-05-11T20:11:30+00:00",
  "last_turn": {
    "check_shown": true,
    "nav_status_shown": true,
    "loop_phase": "IMPL",
    "assistant_text_chars": 4280
  }
}
```

**Critical safety**: never returns `decision: "block"`. Early-exits when `stop_hook_active=true` to defuse the infinite-loop trap documented in the Claude Code hooks spec.

**Why it ships now (Phase 1) and not later**: it's silent infrastructure for **Phase 2's blocking workflow_enforcer** (Opp 1). That hook will read this state file to decide whether to block `UserPromptSubmit` when a loop trigger appears but no WORKFLOW CHECK was emitted in the prior turn. Shipping the state writer first means Phase 2 can be a one-file change.

### `hooks/nav_profile_sync.py` — Opp 3

**Event**: `PostToolUse`, matcher `Edit|Write`
**Trigger**: file path basename is `.user-profile.json`
**Action**: Load profile, count corrections. Read `.agent/.nav-profile-sync-state.json` for `last_synced_count`. If the array grew:

```bash
python3 correction_to_memory.py --action sync \
    --profile-path .agent/.user-profile.json \
    --graph-path .agent/knowledge/graph.json \
    --last-synced N
```

State counter only advances on success — failed syncs retry next write. Non-correction profile edits (preferences, goals) are pure no-ops.

**Replaces**: `nav-profile` SKILL.md prose "monitor ALL conversations for corrections" — which only fired when the model noticed.

**Live demonstration**: hooking this up on this repo discovered 4 backlogged corrections in `.agent/.user-profile.json` that had never been synced to the graph. The first invocation captured all four into graph memories. Exactly the kind of silent-correctness gain the pattern delivers.

---

## What this is NOT

- **Not the workflow blocker.** That's Phase 2 (Opp 1) — `workflow_enforcer.py` upgraded to `exit 2` when a loop trigger appears with no WORKFLOW CHECK. Will read this release's `.nav-workflow-state.json` to gate decisions. Ships as v6.11.1 or v6.12.0 after explicit design decision about "first blocking hook" precedent.
- **Not the read-guard.** That's Phase 3 (Opp 6) — `PreToolUse` counter that warns at 3+ `.agent/*.md` reads in a single turn. Tail-risk killer (prevents 50k+ bulk-load catastrophes).
- **Not the commit reminder.** That's Phase 3 (Opp 5) — `PostToolUse Bash` matcher on `git commit` with strict gating to avoid noise.

The full roadmap and ship order is in `.agent/tasks/TASK-38-hook-migration-roadmap-v6.11.md`.

---

## Configuration

`.agent/.nav-config.json` — three new sections, all default-on:

```json
{
  "task_graph_sync_hook": { "enabled": true },
  "workflow_state_hook":  { "enabled": true },
  "profile_sync_hook":    { "enabled": true }
}
```

Set any to `enabled: false` to make the hook a no-op without removing it from `.claude/settings.json`.

---

## New state files (all gitignored)

- `.agent/.nav-workflow-state.json` — regenerated every Stop turn
- `.agent/.nav-profile-sync-state.json` — `{"last_synced_count": N}` (idempotency anchor)

Both under `.agent/` per project convention. `.gitignore` updated to exclude both.

---

## Migration

**New projects**: `nav-init` installs all three new hooks automatically (in addition to v6.9/v6.10 hooks). The v6.10.3 safety pass handles foreign-hook detection + timestamped backups.

**Existing projects**: Run `nav-upgrade`. The merger picks up the new template entries idempotently — your existing user hooks are preserved (verified by 11-case test suite). **Restart Claude Code** afterward — hook definitions are cached at session start.

**Opt-out**: any combination of `enabled: false` flags. The hook scripts ship regardless; the config flag determines whether they do anything when fired.

---

## Verification

```bash
# 1. Settings merger regression — must still be 11/11 green
python3 -m unittest skills.nav-init.functions.test_settings_merger
# Ran 11 tests in <10ms — OK

# 2. Each hook standalone
echo '{"cwd":"<project>","tool_name":"Write","tool_input":{"file_path":".agent/tasks/TASK-38-foo.md"}}' \
    | python3 hooks/nav_task_graph_sync.py
# expect: "nav_task_graph_sync: upserted TASK-38-foo.md" to stderr, {} to stdout

echo '{"cwd":"<project>","session_id":"x","last_assistant_message":"WORKFLOW CHECK shown. Phase: IMPL"}' \
    | python3 hooks/nav_workflow_state.py
cat .agent/.nav-workflow-state.json
# expect: check_shown=true, loop_phase="IMPL"

echo '{"cwd":"<project>","tool_name":"Write","tool_input":{"file_path":".agent/.user-profile.json"}}' \
    | python3 hooks/nav_profile_sync.py
# expect (first run if corrections present): "synced N new correction(s)" to stderr
# expect (idempotent rerun): no-op, just {} to stdout

# 3. Non-Navigator project
echo '{"cwd":"/tmp"}' | python3 hooks/nav_task_graph_sync.py
echo '{"cwd":"/tmp"}' | python3 hooks/nav_workflow_state.py
echo '{"cwd":"/tmp"}' | python3 hooks/nav_profile_sync.py
# expect: all three emit just {} cleanly, no error
```

---

## Files Changed

**Created**:
- `hooks/nav_task_graph_sync.py` (~155 lines)
- `hooks/nav_workflow_state.py` (~160 lines)
- `hooks/nav_profile_sync.py` (~200 lines)
- `releases/RELEASE-NOTES-v6.11.0.md` (this file)

**Modified**:
- `templates/claude-settings-hooks.json` — Stop entry + two PostToolUse Write|Edit entries
- `.agent/.nav-config.json` — three new hook sections
- `.gitignore` — exclude `.nav-workflow-state.json` + `.nav-profile-sync-state.json`
- `skills/nav-init/SKILL.md` — Step 6 lists all seven Navigator hooks now
- `templates/CLAUDE.md` — config example includes the three new hook flags
- `.agent/DEVELOPMENT-README.md` — new "Phase 1 Lifecycle Hooks (v6.11.0+)" section
- `CHANGELOG.md` — v6.11.0 entry
- Version files: `plugin.json`, `marketplace.json`, `.nav-config.json`, `CLAUDE.md`, `README.md`

**Out of scope** (Phase 2 / Phase 3 per TASK-38):
- Opp 1 — `workflow_enforcer.py` exit-2 hard block on loop triggers
- Opp 5 — `PostToolUse Bash` commit archival reminder (strict gating required)
- Opp 6 — `PreToolUse Read` `.agent/` bulk-load counter

---

## Compatibility

- **Backward compatible.** No schema changes; new config sections are additive.
- **No new dependencies.** Hook scripts use stdlib (`json`, `subprocess`, `pathlib`, `re`, `datetime`).
- **Reuses existing graph CLIs.** No new sync code paths; the hooks are thin event-to-CLI adapters.
- **Restart required after upgrade** — Claude Code caches hook definitions at session start.
