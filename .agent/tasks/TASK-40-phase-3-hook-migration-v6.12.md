# TASK-40: Phase 3 Hook Migration — v6.12.x

**Status**: 📐 Planning (not yet implemented)
**Created**: 2026-05-11
**Builds on**: TASK-38 Phase 1 (v6.11.0), Phase 2 (v6.11.1 + v6.11.2 UX patch)
**Architectural pattern**: mem-027 (three-layer), mem-034 (blocking-hook discipline)

---

## Summary

Ship the final two hooks from TASK-38's roadmap: Opp 6 (`.agent/` bulk-read guard) and Opp 5 (commit archival reminder). Both are **conditional injectors** — they emit warnings into the assistant context, neither hard-blocks. Ship order: Opp 6 first as v6.12.0, Opp 5 second as v6.12.1, mirroring the v6.11.1 + v6.11.2 staging pattern.

---

## Headline Decisions

1. **Opp 6 ships warn-only, not blocking.** A read count alone is a heuristic; without a state-file confirmation of "model is currently in a bulk-load session," the mem-027 three-condition gate is not satisfied. If live telemetry shows warnings are ignored, a blocking variant can be added in v6.12.1+ behind `read_guard_hook.strict_block: true` with a companion state file.

2. **Opp 5 cannot block meaningfully.** `PostToolUse` fires after the commit completes. Exit 2 reads as "the tool failed" to the model — semantically wrong for an archival reminder. Use stdout / additionalContext. Always exit 0.

3. **Counter reset goes into `nav_workflow_state.py`**, not a new Stop hook. Adds 10 lines for `_reset_read_counter`. Single Stop entry stays simpler than splitting concerns prematurely. Extract to a dedicated cleanup hook later if a second per-turn cleanup task appears.

4. **Two-release split**: v6.12.0 (Opp 6 + counter reset + workflow_state.py extension), v6.12.1 (Opp 5). Reasons: higher tail-risk for Opp 6 ships first; Opp 5's false-positive risk warrants independent rollback.

---

## Files

**New**:
- `hooks/nav_read_guard.py` (~120 lines)
- `hooks/nav_commit_reminder.py` (~150 lines)
- `.agent/.nav-read-counter.json` (runtime, gitignored)

**Modified**:
- `hooks/nav_workflow_state.py` — add `_reset_read_counter` call after line 163
- `templates/claude-settings-hooks.json` — new PreToolUse Read entry + new PostToolUse Bash entry
- `.agent/.nav-config.json` — `read_guard_hook` + `commit_reminder_hook` sections
- `templates/CLAUDE.md` — config examples
- `.gitignore` — exclude `.nav-read-counter.json`

---

## Open Questions (BLOCK implementation until resolved)

| ID | Question | How to resolve |
|---|---|---|
| OQ-1 | Does `PreToolUse` deliver `tool_input.file_path` as absolute or as-typed? | Live test: have Claude Read a known-relative path, inspect stdin payload. Pattern from `nav_task_graph_sync.py:83-102` handles both. |
| OQ-2 | Does `PreToolUse` stdout get injected as model context, or silently discarded? | Live test: emit known sentinel string from a PreToolUse hook, check if it surfaces. If discarded, use `hookSpecificOutput.additionalContext` JSON shape. |
| OQ-3 | Same for `PostToolUse` stdout. (`token_monitor.py` writes stdout but it's not clear if surfaced.) | Same live test. Fallback: stderr on PostToolUse may surface as model context. |
| OQ-4 | Is `session_id` from Stop stdin stable across `--resume`? | Inspect actual JSONL payloads on a resumed session. Determines whether session-based counter reset is meaningful. |
| OQ-5 | `_find_inprogress_tasks` perf on Navigator repo (40+ task files) | Profile locally; if >50ms, sort by mtime and limit to first 20. |

OQ-1, OQ-2, OQ-3 are blockers — they determine the output-channel decision. Resolve via live behavior tests (mirror the v6.11.1 verification pattern: write a tiny probe hook, observe what surfaces).

---

## Opp 6 Design Summary (v6.12.0)

**Event**: `PreToolUse`, matcher `Read`
**Gating**: `tool_input.file_path` starts with `.agent/` AND basename not in allowlist
**Allowlist** (legitimate per-session reads): `DEVELOPMENT-README.md`, `.nav-config.json`, `.user-profile.json`, `knowledge/graph.json`
**Side effect**: `.agent/.nav-read-counter.json` `{schema, session_id, turn_count, updated_at}`
**Thresholds**: warn at 3, escalate at 5 (both configurable)
**Reset**: `nav_workflow_state.py` clears `turn_count` to 0 on every Stop
**Output**: stdout warn messages. No file paths or task IDs quoted (no recursive-trigger surface).
**Exit**: always 0.

**Config**:
```json
"read_guard_hook": {
  "enabled": true,
  "warn_threshold": 3,
  "escalate_threshold": 5,
  "allowlist": ["DEVELOPMENT-README.md", ".nav-config.json", ".user-profile.json", "knowledge/graph.json"]
}
```

---

## Opp 5 Design Summary (v6.12.1)

**Event**: `PostToolUse`, matcher `Bash`
**Gating** (ALL three required):
1. `tool_input.command` contains `git commit`
2. At least one `.agent/tasks/TASK-*.md` has `Status: 🚧 In Progress` (or text-only `In Progress`)
3. Commit message contains either a matching task ID OR one of: `complete`, `done`, `finish`, `closes`, `implements`
**Output**: stdout reminder naming the in-progress task(s) and suggesting archival
**Exit**: always 0 (failed commit → silent no-op)
**Source of commit message**: prefer `tool_response.output` line 1; fall back to parsing `-m '...'` from command

**Config**:
```json
"commit_reminder_hook": {
  "enabled": true,
  "completion_signals": ["complete", "done", "finish", "closes", "implements"],
  "require_task_id_match": false
}
```

---

## Acceptance Criteria

**v6.12.0**:
- `nav_read_guard.py` warns at count 3, escalates at 5
- Counter resets between turns (smoke test 5 explicitly verifies)
- Allowlist correctly exempts the four nav-start files
- No recursive-trigger leak (feed warn message through workflow_enforcer → exit 0)
- Hook disabled via `read_guard_hook.enabled: false` is a clean no-op
- `nav_workflow_state.py` continues passing existing tests after the 10-line extension

**v6.12.1**:
- Reminder fires only when all three gates pass
- WIP commits without completion signals → no fire
- Failed commits (exit_code != 0) → no fire
- Reminder content includes specific task ID(s) and file path(s)
- `_find_inprogress_tasks` perf <50ms on this repo (40+ task files)
- No recursive-trigger surface

---

## Ship Plan

**v6.12.0** (target: ~1 week of v6.11.2 live telemetry, then ship):
1. Resolve OQ-1, OQ-2, OQ-4
2. Write `nav_read_guard.py`
3. Extend `nav_workflow_state.py`
4. Update settings template + config schema
5. Smoke tests (7 cases for Opp 6)
6. Live verification
7. Update mem-027 "Examples shipped" list
8. Two commits (feat + chore release), tag, GH release

**v6.12.1** (target: after v6.12.0 confirms warn-only is sufficient signal):
1. Resolve OQ-3, OQ-5
2. Write `nav_commit_reminder.py`
3. Update settings template + config schema
4. Smoke tests (6 cases for Opp 5)
5. Live verification
6. Two commits, tag, GH release

---

## References

- Full implementation skeleton: planner output (this session)
- `mem-027` — three-layer Model/Hooks/Harness architecture + blocking-hook gating discipline
- `mem-034` — UserPromptSubmit bypass + recursive-block trap (constraints all blocking hooks inherit; relevant for any future Opp 6 strict_block variant)
- `releases/RELEASE-NOTES-v6.11.0.md` — Phase 1 silent hooks (pattern reference)
- `releases/RELEASE-NOTES-v6.11.1.md` + `v6.11.2.md` — Phase 2 (blocking hook + UX patch reference)
- `hooks/nav_task_graph_sync.py:83-102` — PreToolUse path resolution pattern (use this for OQ-1)
- `hooks/workflow_enforcer.py:39-69` — sentinel pattern (relevant if Opp 6 ever gains a blocking variant)

---

## Out of Scope

- Phase 3+ opportunities beyond Opp 5/6 (none planned in TASK-38)
- Schema validation against Claude Code settings.json (no public schema)
- Matcher collision detection in `settings_merger.py` (existing gap, tracked as TASK-39 follow-on)
- Knowledge graph compact-event memories (deferred from v6.10.0)
- `UserPromptSubmit` → graph memory pre-injection (deferred from TASK-38 out-of-scope list)
