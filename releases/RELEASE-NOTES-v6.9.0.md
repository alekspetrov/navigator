# Navigator v6.9.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor Release (SessionStart Hook — Zero-Read Context Injection)

---

## Summary

Navigator's `nav-start` skill used to make ~6 `Read` tool calls at the start of every session — pulling in `DEVELOPMENT-README.md`, `.nav-config.json`, the active marker, the user profile, knowledge graph stats, and OTel stats. Each `Read` cost tool-call ceremony, transcript bloat, and round-trips before the user's first real prompt — the very tax Navigator exists to eliminate.

v6.9.0 replaces all six reads with a single Claude Code **`SessionStart` hook**. The hook script computes the navigator payload once, on the harness side, and Claude Code injects it as a system reminder via `additionalContext` — already in the model's context window before the first user turn. The skill itself becomes a thin display layer: it detects a sentinel string and renders the session summary directly, with zero file reads.

**Local validation** (this repo, fresh sessions):

| | Legacy path (v6.8.0) | Fast path (v6.9.0) |
|---|---|---|
| Total session start tokens | 73.3k | 37.8k |
| `Read` tool calls | 6 | 0 |
| nav-start completion | tool-call orchestration | direct render |

**~35k tokens saved per session start.** Fully backward compatible — projects without the hook (or with it disabled) fall back to the legacy Read path automatically.

---

## Changes

### `hooks/nav_session_start.py` (new — 355 lines)

The SessionStart hook script. Reads project state from disk on the harness side, emits a JSON payload whose `additionalContext` is injected into the conversation. Parity goal: produce the **same content** `nav-start` was rendering, only via injection instead of LLM-initiated Reads.

**Payload composition** (9500-char cap, leaves headroom under Claude Code's 10k limit):

| Section | Source | Notes |
|---|---|---|
| Navigator content | `.agent/DEVELOPMENT-README.md` | Currently ~2k tokens; pass through |
| Active marker | `.agent/.context-markers/.active` → pointed file | Hoisted to top on `--resume` |
| Config snapshot | `.agent/.nav-config.json` | Version, PM tool, feature flags |
| Knowledge graph stats | `skills/nav-graph/functions/graph_manager.py --action stats` | Same call nav-start makes |
| User profile | `.agent/.user-profile.json` | Preferences + recent corrections |
| Auto-update result | `skills/nav-start/functions/auto_updater.py` | Same JSON nav-start parses |
| Open tasks | `.agent/tasks/*.md` scan | Title + status one-liners |

**Robustness**:
- Each section is **gracefully optional** — missing file → skip section, never error.
- **Non-Navigator projects** (no `.agent/` directory) → emits empty `{}`, no crash.
- **Char-cap exceeded** → truncates at the navigator tail (the biggest, most expendable section) with a `[truncated: ask nav-start for full detail]` footer.
- **Source-aware**: when `stdin.source == "resume"`, prepends a "RESUMED FROM PREVIOUS SESSION" header and hoists the active marker section to the top.

**Sentinel**: every successful injection emits `<!-- nav-session-start-injected:v1 -->`. The `nav-start` skill checks for this string in its system context to decide whether to use the fast path or the legacy Read path.

### `skills/nav-init/functions/settings_merger.py` (new — 110 lines)

Idempotent JSON merger for `.claude/settings.json`. Used by `nav-init` Step 6 and `nav-upgrade` Step 5 to install the SessionStart + PostToolUse + PreToolUse hooks without clobbering user-defined hooks.

**Properties**:
- **Fresh install**: creates `.claude/settings.json` from the template.
- **Existing settings**: deep-merges `hooks` arrays by event name. Dedupes entries by command string — re-running is a no-op.
- **User hooks preserved**: any `PostToolUse`/`PreToolUse` entry with a different command string is kept as-is.
- **Safety**: refuses to clobber invalid JSON (exits 2 instead of overwriting).
- **Other top-level keys** in `settings.json` (e.g. `userKey: "value"`) are preserved.

### `skills/nav-start/SKILL.md` — new Step 0 (fast-path detection)

Before doing anything else, the skill checks for the sentinel:

```
<!-- nav-session-start-injected:v1 -->
```

- **Sentinel present** → fast path. Skip Steps 1–7 (all the file reads). Render the session summary directly from injected data.
- **Sentinel absent** → legacy path. Execute Steps 1–7 as before. Same behavior as pre-v6.9.0.

User-visible output is **byte-identical** between the two paths — users should not be able to tell which mode produced their session summary.

### `skills/nav-init/SKILL.md` — Step 6 rewrite

Replaces the prior `cat > .claude/settings.json` approach with an idempotent merge via `settings_merger.py` against `templates/claude-settings-hooks.json`. The template now installs all three Navigator hooks (SessionStart, PreToolUse, PostToolUse) in one call.

Idempotent: safe to re-run `nav-init` on existing projects — won't duplicate hooks or clobber custom settings.

### `skills/nav-upgrade/SKILL.md` — Step 5 rewrite (migration prompt)

Existing projects must opt-in once before we add the SessionStart hook to their `.claude/settings.json`. The skill now asks via `AskUserQuestion`:

```
Activate zero-Read session start hook? (v6.9.0+)

[1] Yes, install SessionStart hook (recommended)
[2] No, keep PostToolUse only
```

If accepted, the merger preserves any existing user hooks and adds the new entries. A restart-required notice follows (Claude Code caches hook definitions at session start).

### `templates/claude-settings-hooks.json` — env var fix

The template referenced `${CLAUDE_PROJECT_ROOT}`, which is **not** a Claude Code environment variable. The actual variable is `${CLAUDE_PROJECT_DIR}`. This was a latent bug — the template's PreToolUse/PostToolUse entries wouldn't have resolved correctly on fresh installs (existing projects use relative paths in their tracked `settings.json`, so they were unaffected).

Fixed in this release alongside the SessionStart wiring.

### Documentation

- `templates/CLAUDE.md` — added `session_start_hook` to the example config block.
- `.agent/DEVELOPMENT-README.md` — new "SessionStart Hook (v6.9.0+)" section documenting the protocol.
- `skills/nav-init/SKILL.md` — added `settings_merger.py` to the predefined functions list.

---

## Configuration

Default (`.agent/.nav-config.json`):

```json
{
  "session_start_hook": {
    "enabled": true,
    "include_sections": ["navigator", "marker", "config", "graph", "profile", "tasks", "auto_update"],
    "char_budget": 9500
  }
}
```

- `enabled: false` → hook still runs but emits empty `{}`; `nav-start` falls back to legacy Read path.
- `include_sections` → opt out of specific sections by removing them from the list.
- `char_budget` → reduce if you want a tighter payload (default leaves 500 chars headroom under Claude Code's 10k limit).

---

## Migration

**New projects**: `nav-init` installs the hook automatically. No action required.

**Existing projects**: Run `nav-upgrade` after updating the plugin. The skill will ask once before merging the SessionStart entry into `.claude/settings.json`. **Restart Claude Code** after `nav-upgrade` — the hook definition is cached at session start, so the running session won't pick up the new hook until restart.

**Opt-out**: Set `session_start_hook.enabled: false` in `.agent/.nav-config.json`. The hook will exit early and `nav-start` will fall back to the legacy Read-based path.

**Disabling for one session**: Edit `.claude/settings.json` and remove (or comment out) the `SessionStart` entry, then restart. Idempotent: re-running `nav-upgrade` adds it back if you change your mind.

---

## Verification

After upgrading:

1. **Restart Claude Code** (hook definitions cached at session start).
2. Run `/context` immediately in a fresh session. If `Messages` shows ≥ ~2.5k tokens, the hook injected successfully. (Baseline empty session is < 100 tokens.)
3. Run `Start my Navigator session`. The session summary should appear with **no `Read` tool calls** in the transcript. Look for the line `📖 Navigator: Loaded (from SessionStart hook)` — that's the fast-path signal.

If the hook doesn't fire, check:
- `/hooks` slash command — confirms the SessionStart entry is registered.
- `${CLAUDE_PROJECT_DIR}` is set in the hook's runtime env (Claude Code exports this automatically for hook execution).
- `python3 hooks/nav_session_start.py` runs cleanly when invoked manually (with `CLAUDE_PROJECT_DIR=$(pwd)` set).

---

## Files Changed

**Created**:
- `hooks/nav_session_start.py` (355 lines)
- `skills/nav-init/functions/settings_merger.py` (110 lines)
- `releases/RELEASE-NOTES-v6.9.0.md` (this file)

**Modified**:
- `.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — version bump + changelog entry
- `.agent/.nav-config.json` — version bump
- `CHANGELOG.md` — v6.9.0 entry
- `CLAUDE.md` — version footer
- `README.md` — version badge
- `templates/claude-settings-hooks.json` — env var fix + SessionStart block
- `templates/CLAUDE.md` — `session_start_hook` config example
- `.agent/DEVELOPMENT-README.md` — new SessionStart Hook section
- `skills/nav-init/SKILL.md` — Step 6 rewrite + `settings_merger.py` reference
- `skills/nav-start/SKILL.md` — Step 0 fast-path detection
- `skills/nav-upgrade/SKILL.md` — Step 5 rewrite (migration prompt)

---

## Compatibility

- **Backward compatible.** Skills detect the sentinel; absence → legacy path.
- **No breaking changes to configuration.** New config section is purely additive.
- **Plugin install path-agnostic.** Hook script resolves `${CLAUDE_PLUGIN_DIR}` (downstream installs) or falls back to relative paths.
- **Restart required after upgrade** — Claude Code caches hook definitions at session start. This is a Claude Code behavior, not a Navigator issue. The plugin update itself does not require a restart; only the hook activation does.
