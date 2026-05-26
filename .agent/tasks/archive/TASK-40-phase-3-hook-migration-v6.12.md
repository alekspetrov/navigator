# TASK-40: Phase 3 Hook Migration — v6.12.x

**Status**: ✅ Closed 2026-05-26 — v6.12.0 shipped (Opp 6 warn-only), v6.12.1 shipped (strict_block + course correction + Opp 5 probe), v6.12.2 cancelled (Opp 5 dropped — PostToolUse channels confirmed silent, SessionStart task list is sufficient coverage). Closes TASK-38 Phase 3.
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

## v6.12.1 Section — Course Correction (Shipped 2026-05-11)

### Findings from v6.12.0 live verification

1. **PreToolUse stdout AND `hookSpecificOutput.additionalContext` are silent to the model.** The dual-channel `_emit()` from v6.12.0 was dead code. Counter advanced correctly on 5 Reads; warnings never surfaced. Closes OQ-2 with answer: neither channel works.
2. **The counter IS state-file ground truth.** Earlier analysis claimed "a count alone fails mem-027's three-condition gate." Wrong — this hook's prior invocations write the counter, so reading count >= threshold IS empirical state-file confirmation.
3. **Plugin's `.claude/settings.json` was missing 5 of 7 hooks.** Fresh installs never got the v6.11+ lifecycle hooks without manually running `nav-init`.
4. **Template wired `workflow_enforcer.py` to wrong event.** Template had it on `PreToolUse`; hook code reads `data.get("prompt")` which only exists on `UserPromptSubmit`. Latent no-op for any fresh user.

### Changes shipped in v6.12.1

- **Change A**: `nav_read_guard.py` strict_block mode (default true). exit 2 at escalate_threshold. Sentinel-wrapped user-addressed stderr. Dead `_emit()` removed. Warn path moved to stderr.
- **Change B**: 20-line PostToolUse probe at `hooks/nav_commit_reminder.py`. Wired temporarily in this repo's `.claude/settings.json`. Will be replaced by full Opp 5 in v6.12.2 once probe channel is confirmed.
- **Change C**: `.claude/settings.json` synced with corrected template. workflow_enforcer moved from PreToolUse → UserPromptSubmit in BOTH files.

### Knowledge captured

- `mem-035` (pitfall): "PreToolUse stdout and additionalContext are silent — exit 2 is the only behavior-affecting channel." Future PreToolUse hooks inherit this constraint.
- mem-027 update pending (after v6.12.2 closes the phase).

### Open questions status

| ID | Status | Answer |
|---|---|---|
| OQ-1 | Closed in v6.12.0 | file_path is absolute. Defensive path resolution still in place. |
| OQ-2 | Closed in v6.12.1 | Both stdout and additionalContext silent on PreToolUse. exit 2 only. |
| OQ-3 | Probe in flight | nav_commit_reminder.py probe shipped in v6.12.1; result expected in next live session. |
| OQ-4 | Closed | session_id stable across resume (counter session-change reset is defensive but not load-bearing). |
| OQ-5 | Deferred to v6.12.2 | Profile `_find_inprogress_tasks` perf when full Opp 5 lands. |

### v6.12.2 plan (closes TASK-38)

After live session surfaces probe result:
1. Read which sentinel appears (stderr / stdout / neither) in mem-035
2. Replace `nav_commit_reminder.py` probe with full Opp 5 logic using the confirmed channel
3. If neither surfaces: redesign Opp 5 as a Stop hook that diffs git log vs in-progress task statuses (different mechanism, separate ticket)
4. Update mem-027 examples list with read guard + commit reminder
5. Ship v6.12.2 → TASK-38 closed

---

## v6.12.2 Closeout — Opp 5 Cancelled (2026-05-26)

### OQ-3 resolution

The `nav_commit_reminder.py` probe shipped in v6.12.1 was wired to PostToolUse `Bash` and fired on every Bash invocation across a full live session (2026-05-26). Both sentinels were emitted on stdout and stderr from the probe (verified by manual invocation: `echo '{"tool_name":"Bash",...}' | python3 hooks/nav_commit_reminder.py` prints both lines, exit 0). Neither sentinel ever appeared in the model's visible context across 8+ Bash calls in the session.

**Conclusion**: PostToolUse stdout and stderr are silent to the model, matching PreToolUse (mem-035). The `hookSpecificOutput.additionalContext` JSON shape on PostToolUse was not separately probed; given parity with PreToolUse (also silent), the working assumption is no JSON shape will work either. Exit 2 on PostToolUse is semantically wrong (tool already ran) and not a viable alternative.

mem-035 has been updated to reflect the PostToolUse finding.

### Why Opp 5 is cancelled, not redesigned as a Stop hook

The natural fallback (TASK-40 line 192) was "Stop hook diffs git log vs in-progress task statuses." Two problems killed this:

1. **Stop hooks have no model-visible output channel either** (mem-035 line 38). A Stop hook can write a pending-reminder state file but cannot itself surface anything.
2. **The only proven surfacing channel is SessionStart `additionalContext`**, which already runs `_section_open_tasks` (see `hooks/nav_session_start.py:316`). The next session start already lists every in-progress task. Opp 5's incremental value would have been "cross-reference the most recent completion-signal commit against in-progress tasks" — marginal gain over the existing list, since users see the same task names either way.

Cost/benefit doesn't justify the implementation. The probe was wired locally only, no templates touched, no public API exposed. Removal is clean.

### Cleanup actions

- `hooks/nav_commit_reminder.py` deleted
- PostToolUse `Bash` entry pointing at the probe removed from `.claude/settings.json`
- `templates/claude-settings-hooks.json` was never modified (probe was local-only) — verified
- mem-035 updated with PostToolUse finding and TASK-40 cross-reference
- Concepts list extended with `posttooluse`, `stderr`

### Phase 3 net delivery (v6.12.x)

- **Opp 6 (read guard)**: shipped in v6.12.0 + v6.12.1 (strict_block default + sentinel-wrapped stderr). Production hook.
- **Opp 5 (commit reminder)**: cancelled. Use cases handled adequately by SessionStart open-tasks section.
- **Composition fixes**: v6.12.1 also corrected template wiring of `workflow_enforcer` (PreToolUse → UserPromptSubmit) and synced `.claude/settings.json` with the corrected template.

TASK-38 Phase 3 is closed.

---

## Out of Scope

- Phase 3+ opportunities beyond Opp 5/6 (none planned in TASK-38)
- Schema validation against Claude Code settings.json (no public schema)
- Matcher collision detection in `settings_merger.py` (existing gap, tracked as TASK-39 follow-on)
- Knowledge graph compact-event memories (deferred from v6.10.0)
- `UserPromptSubmit` → graph memory pre-injection (deferred from TASK-38 out-of-scope list)
