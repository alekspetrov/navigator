# Navigator v6.11.1 Release Notes

**Release Date**: 2026-05-11
**Type**: Patch (Phase 2 of TASK-38 — first blocking hook)

---

## Summary

v6.11.0 shipped the silent infrastructure: three `PostToolUse` / `Stop` hooks that quietly improved correctness without injecting tokens. **v6.11.1 crosses the architectural line v6.11.0 set up for** — `hooks/workflow_enforcer.py` is now the first Navigator hook that can `exit 2` and block a user prompt.

The block fires only when a deterministic state file (`.agent/.nav-workflow-state.json`, written by v6.11.0's Opp 2 writer) confirms the prior assistant turn skipped its WORKFLOW CHECK block. **No state file → no block.** False-positive rate is near zero by design.

This closes the "model skips WORKFLOW CHECK ~30% of the time" gap that motivated the entire TASK-38 roadmap.

---

## The change

### `hooks/workflow_enforcer.py` — Opp 1

**Event**: `UserPromptSubmit` (already wired since v5.9.0)
**Mode**: soft-warn → hard-block (when gated)

**Block conditions (all three must hold)**:

1. Prompt contains a Loop Mode trigger phrase (`"run until done"`, `"do all"`, `"keep going"`, `"iterate until"`, etc. — see `skills/nav-start/functions/workflow_detector.py:LOOP_TRIGGERS`)
2. `.agent/.nav-workflow-state.json` exists AND `last_turn.check_shown == false`
3. `workflow_enforcer_hook.strict_block == true` in `.agent/.nav-config.json` (default `true`)

**When blocked**, the hook:

- Prints the soft-warn block (LOOP MODE TRIGGER + WORKFLOW CHECK reminder) to stdout
- Writes to stderr a structured message Claude Code surfaces back to the model:

```
Navigator workflow_enforcer: blocked.
  Reason: loop trigger 'run until done' detected, but the prior
  assistant turn did not show a WORKFLOW CHECK block
  (.agent/.nav-workflow-state.json: check_shown=false).
  Action: emit the WORKFLOW CHECK block at the top of the next
  response, then continue with NAVIGATOR_STATUS for Loop Mode.
  Opt-out: set workflow_enforcer_hook.strict_block=false in
  .agent/.nav-config.json.
```

- `exit 2`

**Fallback behavior** (existing projects without state file):

- Missing `.nav-workflow-state.json` → soft-warn only, `exit 0`. Phase 1 projects that haven't installed Opp 2 yet are unaffected by this upgrade.
- `check_shown == true` → soft-warn only, `exit 0`. Working as intended.
- No loop trigger in prompt → silent `exit 0`.

---

## Architectural precedent

Every Navigator hook shipped before this release exited 0 unconditionally. v6.11.1 is the first hook in the codebase that can refuse a user prompt.

**Rationale for crossing the line now**:

- The block is gated on a deterministic state file written by another hook, not on heuristics. The model can't accidentally trigger it; it has to have measurably skipped a CHECK block in the previous turn.
- Loop Mode is the highest-value enforcement target: the entire point of Loop Mode is autonomous iteration, and missing WORKFLOW CHECK breaks the iteration contract.
- The opt-out is a single config flag (`strict_block: false`) — users who don't want this behavior can disable it without removing the hook.

**Recorded in** `mem-027` (Three-layer Model/Hooks/Harness architecture pattern). Future blocking hooks should follow the same three-condition gating discipline: trigger + state file confirmation + config opt-out.

---

## Configuration

`.agent/.nav-config.json` — new section, default-on:

```json
{
  "workflow_enforcer_hook": {
    "enabled": true,
    "strict_block": true
  }
}
```

| Flag | Effect |
|---|---|
| `enabled: false` | Hook is a no-op. No warn, no block. |
| `enabled: true, strict_block: false` | Soft-warn behavior only (v6.11.0 parity). |
| `enabled: true, strict_block: true` (default) | Hard-block when gated; soft-warn otherwise. |

---

## Verification

5/5 smoke-test scenarios pass:

```bash
# 1. Loop trigger + state says check_shown=false → BLOCK (exit 2)
echo '{"last_turn":{"check_shown":false}}' > .agent/.nav-workflow-state.json
echo '{"prompt":"run until done: ship phase 2"}' | python3 hooks/workflow_enforcer.py
# exit=2, stderr contains "Navigator workflow_enforcer: blocked."

# 2. Loop trigger + state says check_shown=true → ALLOW (exit 0)
echo '{"last_turn":{"check_shown":true}}' > .agent/.nav-workflow-state.json
echo '{"prompt":"run until done: ship phase 2"}' | python3 hooks/workflow_enforcer.py
# exit=0, soft-warn only

# 3. Loop trigger + missing state file → ALLOW (exit 0, soft-warn)
rm .agent/.nav-workflow-state.json
echo '{"prompt":"run until done: ship phase 2"}' | python3 hooks/workflow_enforcer.py
# exit=0 — Phase 1 projects unaffected

# 4. No loop trigger → SILENT (exit 0, no output)
echo '{"prompt":"explain how this works"}' | python3 hooks/workflow_enforcer.py
# exit=0, no stdout

# 5. strict_block=false → ALLOW even when prior turn missed
# (config-flag toggle, soft-warn behavior preserved)
```

---

## Migration

**Existing projects**:
- Run `nav-upgrade` (or wait for the next session — auto-update is on by default).
- Restart Claude Code so the upgraded `workflow_enforcer.py` is loaded.
- If `.agent/.nav-workflow-state.json` doesn't exist yet (v6.11.0 hooks haven't fired), the hook stays in soft-warn mode automatically. After a few turns of v6.11.0's `nav_workflow_state.py` running, the state file appears and the block becomes active.

**Opt-out** (preserve soft-warn behavior):

```json
"workflow_enforcer_hook": { "strict_block": false }
```

---

## Files Changed

**Modified**:
- `hooks/workflow_enforcer.py` — added state file read + hard-block gate
- `.agent/.nav-config.json` — `workflow_enforcer_hook` section
- `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `README.md`, `CLAUDE.md` — version bump
- `CHANGELOG.md` — v6.11.1 entry

**Created**:
- `releases/RELEASE-NOTES-v6.11.1.md` (this file)

---

## What's next

**Phase 3 (target v6.12.x)**:

- Opp 6 — `PreToolUse Read` counter, warns at 3+ `.agent/*.md` reads in a single turn (tail-risk killer for 50k+ bulk-load catastrophes)
- Opp 5 — `PostToolUse Bash` matcher on `git commit` with strict gating, archival reminder

Both follow the same gating discipline established here: state file confirmation + config opt-out.

The full roadmap remains in `.agent/tasks/TASK-38-hook-migration-roadmap-v6.11.md`.

---

## Compatibility

- **Backward compatible.** Missing state file → soft-warn. No state schema changes.
- **No new dependencies.** Reuses existing config + state file from v6.11.0.
- **Restart required after upgrade** — Claude Code caches hook definitions at session start.
