# Navigator v6.10.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor Release (PreCompact + PostCompact Hooks — Compact-Resilient Markers)

---

## Summary

v6.9.0 shipped the SessionStart hook — Navigator state pre-loaded into the model's context window at session start, no `Read` calls. The matching gap was at the **other end** of the session lifecycle: compact.

Before v6.10.0, `nav-compact` skill required the user to invoke it explicitly before running `/compact`. If they forgot, or if Claude Code **auto-compacted** silently when the context approached the limit, no marker was written and the conversation state was lost on the next session. Users today often don't even know auto-compact happened — they just discover lost context.

v6.10.0 wires Claude Code's `PreCompact` and `PostCompact` hooks. Now every compact — manual OR silent auto-compact — automatically writes a marker before the conversation is summarized away, and appends Claude Code's official summary to that marker after compact completes. The next session's SessionStart hook picks up `.active` and offers restore.

**Effect**: combined with v6.9.0, zero state loss across:
- Manual `/compact`
- Silent auto-compact (the big win)
- New session start

The session lifecycle loop is now closed: harness writes the marker (PreCompact), harness restores it (SessionStart), the model never has to remember either step.

---

## Changes

### `hooks/nav_pre_compact.py` (new — ~330 lines)

Fires before every manual `/compact` or auto-compact. Receives `trigger: "manual" | "auto"`, `transcript_path`, `session_id` on stdin. Mirrors the v6.9.0 SessionStart hook structure (graceful error handling, JSON stdin, exit 0 always).

**Actions**:
1. Skip if not a Navigator project (`{}` and exit 0).
2. Skip if `compact_hook.enabled: false` in `.nav-config.json`.
3. Build marker filename: `before-compact-{trigger}-{YYYY-MM-DD-HHmm}.md`. The trigger token in the filename makes silent auto-compacts visible at a glance.
4. Compose marker body:
   - **Header**: date, trigger (with human description), session_id
   - **Git state**: branch, HEAD, working tree, recent commits
   - **Active tasks**: in-progress tasks scanned from `.agent/tasks/`
   - **Conversation summary**: JSONL transcript flattened to plain text, then run through the same heuristic compressor as `skills/nav-marker/functions/marker_compressor.py` (file paths, code blocks, errors, recent context — last 200 lines, max char budget)
5. Write marker to `.agent/.context-markers/before-compact-{...}.md`.
6. Set `.active` → marker filename. This is what triggers `nav-start`'s SessionStart hook to surface the marker on next session.

**Robustness**:
- **Always exits 0**, even on errors. Per Claude Code's hook semantics: exit 2 on auto-compact recovery mode surfaces the underlying API error and breaks the session. We never block.
- **Char-cap**: marker truncated to `char_budget` (default 8000) with a `[... truncated to char budget ...]` footer.
- **Non-Navigator project**: emits `{}` cleanly, no crash.
- **Missing transcript_path**: writes marker with `[transcript_path not provided]` placeholder.
- **Git unavailable**: skips git state section.

### `hooks/nav_post_compact.py` (new — ~100 lines)

Fires after compact succeeds. Receives `compact_summary` on stdin. Reads `.agent/.context-markers/.active` to find the marker PreCompact just created, then appends:

```markdown
---

## Compact Summary (Claude Code)

_Appended by PostCompact hook at 2026-05-11T21:38:09._

{compact_summary text}
```

If `.active` is missing (PreCompact didn't fire — e.g. user-disabled, hook crashed, race condition), PostCompact does nothing. Always exits 0.

### `templates/claude-settings-hooks.json` — add PreCompact + PostCompact

Two new entries alongside the existing SessionStart / PreToolUse / PostToolUse:

```json
"PreCompact": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_DIR}/hooks/nav_pre_compact.py\"",
        "timeout": 30
      }
    ]
  }
],
"PostCompact": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_DIR}/hooks/nav_post_compact.py\"",
        "timeout": 10
      }
    ]
  }
]
```

30s timeout on PreCompact because heuristic transcript extraction on a long conversation can take a few seconds. 10s on PostCompact (it just appends to a file).

`settings_merger.py` required no changes — it already handles arbitrary `hooks.{EventName}` keys.

### `skills/nav-compact/SKILL.md` — new Step 0 (hook detection)

Before any other action, the skill checks whether the PreCompact hook is installed:

```bash
grep -l "nav_pre_compact" .claude/settings.json .claude/settings.local.json
```

- **Hook present**: print a brief "PreCompact hook is installed — just run `/compact`" message and skip Steps 1–5 (manual marker + `.active`). Hook owns marker creation.
- **Hook absent** (legacy / opt-out): fall back to the v6.9.x manual flow unchanged.

Single source of truth — never creates duplicate markers when the hook is also writing them.

### Documentation

- `.agent/DEVELOPMENT-README.md` — new "PreCompact + PostCompact Hooks (v6.10.0+)" section
- `templates/CLAUDE.md` — adds `compact_hook` to the config example
- `skills/nav-init/SKILL.md` — Step 6 description now mentions all three lifecycle hooks
- `skills/nav-upgrade/SKILL.md` — upgrade prompt updated to mention v6.10.0 hooks

---

## Configuration

Default (`.agent/.nav-config.json`):

```json
{
  "compact_hook": {
    "enabled": true,
    "include_transcript_summary": true,
    "include_git_state": true,
    "char_budget": 8000,
    "append_post_compact_summary": true
  }
}
```

- `enabled: false` → both hooks become no-ops; `nav-compact` falls back to manual flow.
- `include_transcript_summary: false` → marker contains only git state + active tasks (smaller, faster).
- `include_git_state: false` → marker contains only conversation summary.
- `char_budget` → max marker file size; default 8000 leaves headroom for the PostCompact append.
- `append_post_compact_summary: false` → PostCompact becomes a no-op even when PreCompact fires.

---

## Migration

**New projects**: `nav-init` installs all three lifecycle hooks (SessionStart + PreCompact + PostCompact) automatically.

**Existing projects (v6.9.x)**: Run `nav-upgrade`. The skill prompts once before merging the new hook entries into `.claude/settings.json`. **Restart Claude Code** afterward — hook definitions are cached at session start.

**Opt-out**: Set `compact_hook.enabled: false`. The hooks still run but exit early; `nav-compact` skill falls back to manual marker flow.

---

## Verification

After upgrading and restarting Claude Code:

1. **Manual compact**:
   - Have a conversation with file reads, code generation, etc.
   - Run `/compact`
   - Verify: `ls -t .agent/.context-markers/before-compact-manual-*.md | head -1` shows a freshly created marker
   - Verify: the marker has both `## Conversation Summary (heuristic)` AND `## Compact Summary (Claude Code)` sections
   - Verify: `.agent/.context-markers/.active` points at the new marker

2. **Auto-compact**:
   - Fill context to near limit (long conversation with many reads)
   - Wait for auto-compact to trigger (Claude Code does this silently)
   - Verify: `ls -t .agent/.context-markers/before-compact-auto-*.md | head -1` shows a marker with `-auto-` in the filename
   - Verify session continues without breaking (hook must not have blocked compact)

3. **Marker restore on next session**:
   - Start a new Claude Code session in the same project
   - SessionStart hook surfaces the marker in injected context
   - `nav-start` renders `🔄 Active marker: before-compact-{manual,auto}-...` and offers to restore

4. **Hook detection in nav-compact**:
   - With hooks installed: invoking `nav-compact` should say "PreCompact hook is installed — just run /compact" and NOT create a duplicate marker
   - Without hooks (temporarily rename the SessionStart entry in settings.json): skill falls back to v6.9.x manual flow

5. **Opt-out**:
   - Set `compact_hook.enabled: false` in `.nav-config.json`
   - Run `/compact`
   - Verify no marker is written, hook exits 0 cleanly

---

## Files Changed

**Created**:
- `hooks/nav_pre_compact.py` (~330 lines)
- `hooks/nav_post_compact.py` (~100 lines)
- `releases/RELEASE-NOTES-v6.10.0.md` (this file)

**Modified**:
- `.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — version bump + changelog entry
- `.agent/.nav-config.json` — version bump + `compact_hook` section
- `CHANGELOG.md` — v6.10.0 entry
- `CLAUDE.md` — version footer
- `README.md` — version badge
- `templates/claude-settings-hooks.json` — PreCompact + PostCompact entries
- `templates/CLAUDE.md` — `compact_hook` config example
- `.agent/DEVELOPMENT-README.md` — new compact hook section
- `skills/nav-compact/SKILL.md` — Step 0 hook detection / fast-path
- `skills/nav-init/SKILL.md` — Step 6 prose mentions all three lifecycle hooks
- `skills/nav-upgrade/SKILL.md` — upgrade prompt mentions v6.10.0 hooks

---

## Compatibility

- **Backward compatible.** `nav-compact` skill detects the hook; absence → legacy path unchanged.
- **No breaking changes to configuration.** New `compact_hook` section is purely additive.
- **Hook script lives in the plugin install dir** (`${CLAUDE_PLUGIN_DIR}/hooks/`), so projects pick it up via plugin update — no per-project script copy needed.
- **Restart required after upgrade** to activate the hook (Claude Code caches hook definitions at session start). This is a Claude Code behavior, not a Navigator issue.

---

## What's Next

The session lifecycle is now fully harnessed. Future hook integrations being considered (out of scope for v6.10.0):

- **`UserPromptSubmit` → graph memory pre-injection**: when the user asks about a topic, the hook greps `graph.json` for related memories and injects them as `additionalContext`. Same pattern as SessionStart, per-prompt.
- **`PreToolUse` → workflow enforcement**: hard-gate `Edit`/`Write`/`Bash` if the WORKFLOW CHECK block hasn't fired on the current turn.
- **Knowledge graph integration on compact events**: PreCompact writes a `"compact_event"` memory node so the graph tracks session boundaries.

The general principle from v6.9.0 + v6.10.0: **policy belongs in hooks, judgment stays in the model.** Anything currently shaped as "model, remember to do X" can move to deterministic hook execution.
