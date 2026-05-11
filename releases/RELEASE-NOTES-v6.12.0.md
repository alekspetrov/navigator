# Navigator v6.12.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor (Phase 3 of TASK-38 begins — `.agent/` bulk-read guard)

---

## Summary

Phase 1 (v6.11.0) shipped three silent infrastructure hooks. Phase 2 (v6.11.1 + v6.11.2) introduced and hardened the first blocking hook. **Phase 3 starts now with v6.12.0** — the bulk-read guard that kills the highest-tail-risk anti-pattern Navigator was designed to prevent.

The 50k-token bulk-load. The "I'll just check what's in `.agent/` to make sure I haven't missed anything" anti-pattern. The one that crashes a session at exchange 7. Until now, Navigator only had prose in CLAUDE.md telling the model not to do it. Now there's a Python script that watches.

---

## The new hook

### `hooks/nav_read_guard.py` — Opp 6

**Event**: `PreToolUse`, matcher `Read`
**Logic**:
1. Check `tool_input.file_path`. If outside `.agent/`, exit silently.
2. Resolve the file path relative to `.agent/`. If basename matches the allowlist, exit silently.
3. Increment counter in `.agent/.nav-read-counter.json`.
4. If count ≥ 5, emit escalation message. Else if count ≥ 3, emit warn message. Else silent.
5. Always exit 0.

**Allowlist** (the legitimate per-session-start surface):

- `DEVELOPMENT-README.md`
- `.nav-config.json`
- `.user-profile.json`
- `knowledge/graph.json`

Reading any of those does not increment the counter. They're the four files `nav-start` reads to bootstrap a session — exempting them keeps the counter signal clean.

**Threshold messages**:

At count = 3 (configurable via `warn_threshold`):

```
[nav-read-guard] 3 .agent/ files read this turn.
Navigator lazy-loading pattern: load only what the current task needs.
For broader surveys, use a Task or Explore agent.
```

At count ≥ 5 (configurable via `escalate_threshold`):

```
[nav-read-guard] 5 .agent/ files read this turn.
This matches the bulk-load anti-pattern (risk: 50k+ tokens).
Stop sequential reads. Use a Task or Explore agent for multi-file
discovery — it reads excerpts, not full files.
```

Neither message quotes file paths, task IDs, or loop trigger phrases — no recursive-trigger surface (verified via smoke test).

---

## Why warn-only and not blocking

This was the first design call of Phase 3. The plan briefly considered a blocking variant: exit 2 at count ≥ 5 and force the model to stop reading.

**The argument against** (which won):

- mem-027's three-condition gating discipline requires a deterministic state-file confirmation that the violation already occurred. A raw read count is a heuristic, not state-file ground truth.
- v6.11.1's first blocking hook (workflow_enforcer) only blocks when *prior turn already failed* (state file says `check_shown=false`). The read guard has no analogous "model already bulk-loaded" signal — only the in-progress count, which is mid-violation.
- False-positive cost: a legitimate sequential load of 5 task files for cross-referencing would be blocked. Warning + escalation is the right tool for that signal-to-noise ratio.

**If telemetry shows warnings are ignored**, a future patch can add `read_guard_hook.strict_block: true` with a companion state file (e.g., `.nav-read-guard-prior-turn.json` written on Stop, recording whether the threshold was crossed last turn). That state file would let the *next* `PreToolUse Read` block with the three-condition gate satisfied. Deferred for now.

---

## Counter reset on Stop

The counter is per-turn, not cumulative. `hooks/nav_workflow_state.py` (shipped v6.11.0) was extended in this release with `_reset_read_counter()` — called after the workflow state is written, resets `turn_count` to 0 while preserving `session_id` continuity.

Single Stop hook entry, single per-turn cleanup function. If a second cleanup task appears (e.g., when Opp 5 ships in v6.12.1), the function can be extracted into a dedicated `nav_turn_cleanup.py`. For now: 12 lines added to an existing hook is cleaner than a new file.

---

## Output channel (OQ-2)

Claude Code's PreToolUse hook output spec doesn't make the stdout-vs-additionalContext path fully explicit. v6.12.0 emits **both**:

1. A structured JSON payload with `hookSpecificOutput.hookEventName: "PreToolUse"` and `additionalContext: <message>`.
2. The plain message text on a trailing line.

Whichever channel Claude Code consumes will surface the warning. The structured JSON is well-formed alone; the trailing text is harmless if discarded.

If live verification shows only one channel actually works, v6.12.1 can drop the unused one.

---

## Configuration

`.agent/.nav-config.json` — new section, default-on:

```json
{
  "read_guard_hook": {
    "enabled": true,
    "warn_threshold": 3,
    "escalate_threshold": 5,
    "allowlist": [
      "DEVELOPMENT-README.md",
      ".nav-config.json",
      ".user-profile.json",
      "knowledge/graph.json"
    ]
  }
}
```

| Flag | Effect |
|---|---|
| `enabled: false` | Hook is a no-op. No counter, no warnings. Stop hook also skips the counter reset call. |
| `warn_threshold: N` | First warning emitted at count = N |
| `escalate_threshold: N` | Escalation emitted at count ≥ N |
| `allowlist: [...]` | Paths relative to `.agent/` that do NOT increment the counter |

---

## Verification

7/7 smoke-test scenarios pass:

```bash
# Set up test project
mkdir -p /tmp/test/.agent/tasks
echo '{"read_guard_hook":{"enabled":true,"warn_threshold":3,"escalate_threshold":5}}' \
  > /tmp/test/.agent/.nav-config.json

# 1. Allowlisted file → no output, no counter increment
echo '{"cwd":"/tmp/test","tool_name":"Read","tool_input":{"file_path":"/tmp/test/.agent/DEVELOPMENT-README.md"}}' \
  | python3 hooks/nav_read_guard.py
# exit 0, stdout empty

# 2. First non-allowlisted read → counter=1, silent
# 3. count=3 → warn emitted
# 4. count=5 → escalation emitted
# 5. nav_workflow_state.py Stop hook resets counter to 0
# 6. Warn message fed through workflow_enforcer.py → exit 0 (no recursion)
# 7. enabled=false → fully silent, no counter file written
```

---

## Migration

**Existing projects**:
- Auto-update on next session start (or run `nav-upgrade`).
- Restart Claude Code to load the updated hooks.
- No config changes required — defaults are reasonable.

**Opt-out** (preserve v6.11.2 behavior):

```json
"read_guard_hook": { "enabled": false }
```

---

## Files Changed

**Created**:
- `hooks/nav_read_guard.py` (~190 lines)
- `releases/RELEASE-NOTES-v6.12.0.md` (this file)
- `.agent/tasks/TASK-40-phase-3-hook-migration-v6.12.md` (Phase 3 plan)

**Modified**:
- `hooks/nav_workflow_state.py` — added `_reset_read_counter()`
- `templates/claude-settings-hooks.json` — PreToolUse Read matcher entry
- `.agent/.nav-config.json` — `read_guard_hook` section
- `.gitignore` — exclude `.nav-read-counter.json`
- `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `README.md`, `CLAUDE.md` — version bump
- `CHANGELOG.md` — v6.12.0 entry

---

## What's next — v6.12.1

**Opp 5** (commit archival reminder) — `PostToolUse` Bash matcher on `git commit`. Three-gate filter: command contains `git commit`, in-progress task exists, commit message has completion signal OR matches a task ID. Targets v6.12.1.

After v6.12.1, TASK-38 is complete. The hook-migration roadmap closes.

---

## Compatibility

- **Backward compatible.** New hook, new state file, new config section. No schema changes.
- **No new dependencies.** Stdlib only (`json`, `re`, `pathlib`, `datetime`).
- **Restart required after upgrade** — Claude Code caches hook definitions at session start.
