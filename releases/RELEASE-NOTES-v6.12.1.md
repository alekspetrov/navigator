# Navigator v6.12.1 Release Notes

**Release Date**: 2026-05-11
**Type**: Patch — course correction after v6.12.0 live verification

---

## Summary

v6.12.0 shipped the `.agent/` bulk-read guard as warn-only. Live verification exposed that warn-only is **architecturally impossible on PreToolUse** — both stdout and `hookSpecificOutput.additionalContext` are silent to the model. The hook was counting correctly but the warnings never reached anyone.

v6.12.1 corrects course with three bundled changes:

1. **Read guard `strict_block` mode** — exit 2 at the escalation threshold so the bulk-load is actually prevented.
2. **PostToolUse probe** — 20-line probe hook to determine PostToolUse output channels before designing Opp 5.
3. **Plugin settings sync** — `.claude/settings.json` ships with all 7 lifecycle hooks. Template corrected (workflow_enforcer was wired to the wrong event).

Plus `mem-035` captures the architectural finding for every future PreToolUse hook author.

---

## What we learned (mem-035)

Live test on v6.12.0: cleared the counter, did 5 Read calls to non-allowlisted `.agent/` files. After completion:

- ✅ Counter advanced 0 → 5. The hook fired and incremented correctly.
- ❌ Neither the count-3 warn nor the count-5 escalation appeared anywhere in Claude's visible context.

Both output channels we coded defensively are dead for `PreToolUse`:
- `hookSpecificOutput.additionalContext` — works on `SessionStart`, silent here.
- Plain stdout — silently discarded.

The only behavior-affecting PreToolUse output is **exit 2**, which refuses the tool call and surfaces stderr to the user.

Full discussion in `.agent/knowledge/memories/pitfalls/mem-035.md`. Future PreToolUse hooks inherit this constraint.

---

## Change A: read guard gains `strict_block` mode

`hooks/nav_read_guard.py` — three changes:

1. **`strict_block: true` (default)**: at `count >= escalate_threshold`, the hook now exits 2 with a sentinel-wrapped stderr block message addressing the user.
2. **Warn path moved to stderr**: counts in the [warn, escalate) range emit advisory stderr text. Surfaces in the CC UI; doesn't influence model behavior (since the model never sees it).
3. **Dead `_emit()` removed**: the dual-channel function from v6.12.0 was an artifact of OQ-2 defensiveness. mem-035 confirms it does nothing. Replaced with `_warn()` (stderr, exit 0) and `_block()` (sentinel-wrapped stderr, exit 2).

The block message:

```
<nav-read-guard-block>
Navigator nav-read-guard: blocked at 5 .agent/ reads (escalate_threshold=5).
  Why: this turn has crossed the bulk-load threshold. Sequential
  .agent/ reads risk 50k+ token consumption and session crash.
  How to proceed (your choice):
    1. Use a Task or Explore agent for the remaining lookups — they
       read excerpts, not full files, and are designed for multi-file
       discovery.
    2. Split the work: end this turn, start a new one (the counter
       resets on every Stop event).
    3. Raise the threshold: set read_guard_hook.escalate_threshold
       to a higher number in .agent/.nav-config.json.
    4. Disable strict enforcement: set read_guard_hook.strict_block
       =false in .agent/.nav-config.json.
</nav-read-guard-block>
```

Notice the discipline (mem-034):
- Addresses the **user**, not Claude.
- Names neither the file path nor any loop trigger phrase — no recursive-trigger surface.
- Distinct sentinel `<nav-read-guard-block>` so future strip logic doesn't collide with `workflow_enforcer.py`'s `<nav-workflow-block>`.

### Why strict_block defaults to true

mem-027's three-condition gating discipline requires (a) trigger, (b) state-file confirmation, (c) opt-out. The TASK-40 plan briefly considered this not satisfied because "a count alone is a heuristic" — but the counter IS state-file ground truth. This hook writes `.agent/.nav-read-counter.json` on every prior PreToolUse Read event. Reading `count >= threshold-1` means "this hook has empirically observed N violations this turn." That's state-file confirmation, fully satisfying mem-027.

The Stop hook's `_reset_read_counter()` (shipped v6.12.0) clears the counter every turn, so the block never persists across turns. Starting a fresh turn always gives a clean slate.

---

## Change B: PostToolUse probe (`hooks/nav_commit_reminder.py`)

Opp 5 (commit archival reminder) was planned to use PostToolUse stdout. After mem-035, that's almost certainly silent too. Before designing the full Opp 5, we need to know which PostToolUse output channel reaches the model.

The probe is 20 lines:

```python
SENTINEL_STDERR = "NAV-PROBE-POSTTOOLUSE-STDERR-VISIBLE"
SENTINEL_STDOUT = "NAV-PROBE-POSTTOOLUSE-STDOUT-VISIBLE"

# on Bash PostToolUse: emit both, exit 0
sys.stderr.write(SENTINEL_STDERR + "\n")
print(SENTINEL_STDOUT)
```

Wired in `.claude/settings.json` for this repo. Next time a Bash tool is invoked, the assistant's context should (or should not) contain one of the sentinel strings. The result determines Opp 5's design for v6.12.2:

- Stderr surfaces → ship Opp 5 using stderr
- Stdout surfaces → ship Opp 5 using stdout
- Neither surfaces → Opp 5 must use a different mechanism (Stop hook diff of git log vs in-progress tasks)

Findings will be appended to mem-035.

---

## Change C: plugin settings sync + template correction

The plugin's shipped `.claude/settings.json` was missing 5 of 7 lifecycle hooks. Fresh users who installed v6.12.0 and didn't run `nav-init` never got SessionStart, PreCompact, PostCompact, Stop, PostToolUse task_graph_sync, or PostToolUse profile_sync. The plugin advertised these features and silently delivered none of them.

Synced `.claude/settings.json` with `templates/claude-settings-hooks.json` verbatim.

**Template correction**: `templates/claude-settings-hooks.json` had `workflow_enforcer.py` wired to `PreToolUse Edit|Write|Bash|Task`. But the hook's `get_user_message()` reads `data.get("prompt")` — a field that only exists on `UserPromptSubmit`. On PreToolUse, the equivalent payload is `tool_input.command` (for Bash) or other fields per tool. The PreToolUse wiring would have silently no-op'd the entire Phase 2 blocking-hook work for any project that used the template fresh.

Both files now wire workflow_enforcer to UserPromptSubmit, matching how it was always used in practice and how the hook code is written.

**Migration risk**: strictly additive per `settings_merger.py`'s command-string dedup logic. No existing user hook is removed.

---

## Verification

6/6 smoke-test scenarios pass:

```bash
# Setup
mkdir -p /tmp/test/.agent/tasks
echo '{"read_guard_hook":{"enabled":true,"warn_threshold":3,"escalate_threshold":5,"strict_block":true}}' \
  > /tmp/test/.agent/.nav-config.json

# A1: count < threshold → silent
# A2: count=3 → stderr warn, exit 0
# A3: count=4 → stderr warn, exit 0
# A4: count=5 + strict_block=true → exit 2, sentinel-wrapped stderr
# A5: count=5 + strict_block=false → stderr warn only, exit 0
# A6: block message piped to workflow_enforcer → exit 0 (no recursive trigger)
```

Test A4 stderr output verified to contain the count, threshold, and four recovery options. Test A6 verified the block message has no LOOP_TRIGGERS substring leak.

---

## Live verification path (post-restart)

For Change A:

1. Restart Claude Code
2. Clear counter: `rm -f .agent/.nav-read-counter.json`
3. Issue 5 Read tool calls on non-allowlisted `.agent/` files (e.g., memories, tasks, system docs)
4. Observe: the 5th Read should fail with "Tool blocked by hook" and the user should see the `<nav-read-guard-block>` message in the CC UI
5. Verify behavior change: this is qualitatively different from v6.12.0 where the hook ran silently with no model-visible effect

For Change B (probe):

1. Issue any Bash tool call (e.g., `git status`)
2. Watch for `NAV-PROBE-POSTTOOLUSE-STDERR-VISIBLE` or `NAV-PROBE-POSTTOOLUSE-STDOUT-VISIBLE` in the next assistant context
3. Record finding in mem-035

---

## Migration

**Existing v6.12.0 users**:
- Auto-update or run `nav-upgrade`.
- Restart Claude Code.
- If you don't want the block: set `read_guard_hook.strict_block: false` in `.agent/.nav-config.json` BEFORE restart.

**Default behavior change**: v6.12.0 was silent at the escalation threshold. v6.12.1 refuses the 5th Read. Users on v6.12.0 who hit the threshold regularly will notice. Recovery is documented in the block message itself.

---

## Files Changed

**Modified**:
- `hooks/nav_read_guard.py` — strict_block mode, stderr output, dead `_emit()` removed
- `templates/claude-settings-hooks.json` — workflow_enforcer moved from PreToolUse to UserPromptSubmit
- `.claude/settings.json` — synced with template, full 7-hook surface, probe wired
- `.agent/.nav-config.json` — added `strict_block: true` flag, version bump
- `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `README.md`, `CLAUDE.md` — version bump
- `CHANGELOG.md` — v6.12.1 entry

**Created**:
- `hooks/nav_commit_reminder.py` — PostToolUse probe (20 lines)
- `.agent/knowledge/memories/pitfalls/mem-035.md` — PreToolUse output channel finding
- `releases/RELEASE-NOTES-v6.12.1.md` (this file)

---

## Compatibility

- **Backward compatible.** Hook configs unchanged for opt-out paths. Default behavior tightens, but the block message is the recovery instruction.
- **No new dependencies.** Stdlib only.
- **Restart required** — Claude Code caches hook definitions at session start.

---

## What's next — v6.12.2 (closes TASK-38)

After the probe surfaces its result:

- **Opp 5 full implementation**: commit archival reminder using the confirmed PostToolUse output channel (stderr, stdout, or alternative-mechanism if both are silent).
- **mem-035 update**: append PostToolUse channel finding.
- **TASK-38 closed**.
