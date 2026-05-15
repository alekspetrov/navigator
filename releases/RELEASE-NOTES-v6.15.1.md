# Navigator v6.15.1 Release Notes

**Release Date**: 2026-05-15
**Type**: Patch — two hook silent-fail fixes

---

## Summary

Two related bugs in the v6.14.0 hook-distribution surface, both of which silently degraded `SessionStart` (and seven other hooks) in projects without a project-local `.claude/settings.json` backstop. Confirmed in the wild during a workshop-prep audit: a fresh Claude Code v2.1.142 session in a Nav-initialized project showed no `SessionStart` injection at all despite plugin and config being correct.

No behavioral changes when things were already working. The fix only changes how hooks resolve their target script — set-and-bound `$CLAUDE_PLUGIN_DIR` paths behave identically to v6.15.0.

---

## What changed

### 1. Stale marketplace name in hook fallback chains (commit `881348d`)

Three hook scripts hardcoded the pre-rename marketplace name in their `_resolve_plugin_dir()` fallback tiers:

- `hooks/nav_session_start.py:241`
- `hooks/nav_profile_sync.py:67`
- `hooks/nav_task_graph_sync.py:71`

Each had `~/.claude/plugins/cache/jitd-marketplace/navigator` and `~/.claude/plugins/marketplaces/jitd-marketplace` as tier-2 and tier-3 candidates. The actual cache has lived under `navigator-marketplace` for several releases — `auto_updater.py` and `nav-sync-claude/claude_updater.py` were already using the correct name. These three scripts were missed during the rename. Tier-4 (`Path(__file__).resolve().parent.parent`) masked the bug locally, but the broken tiers silently missed on every install where `CLAUDE_PLUGIN_DIR` was unset.

Renamed both candidates in all three scripts. Pure rename, no behavior change.

### 2. Manifest-level shell guard replaced with fallback path expansion (commit `5b3a328`)

`.claude-plugin/plugin.json` wrapped every hook command in:

```bash
if [ -n "$CLAUDE_PLUGIN_DIR" ]; then python3 "$CLAUDE_PLUGIN_DIR/hooks/X.py"; fi
```

The guard was added in v6.14.0 to prevent `workflow_enforcer.py` from hard-blocking every prompt when `$CLAUDE_PLUGIN_DIR` was unset (chicken-and-egg: couldn't even run `/nav:init` to recover). Side effect: every other hook silently no-opped in the same scenario — `SessionStart`, `PreCompact`, `PostCompact`, `Stop`, `PreToolUse:Read`, and three `PostToolUse` matchers all became invisible. In the navigator source repo, a project-local `.claude/settings.json` with explicit hook entries masked the issue. In any other Nav-initialized project relying solely on the plugin manifest, hooks fired zero times.

Replaced the guard with shell parameter-expansion fallback in all ten commands:

```bash
python3 "${CLAUDE_PLUGIN_DIR:-$HOME/.claude/plugins/marketplaces/navigator-marketplace}/hooks/X.py"
```

- `$CLAUDE_PLUGIN_DIR` set → identical to v6.15.0.
- Unset or empty → falls through to `~/.claude/plugins/marketplaces/navigator-marketplace`, the flat install path Claude Code maintains for every plugin. Contains all ten hook scripts.
- Missing path → python errors to stderr. No longer silent.

No regression to the v6.14.0 fix: `workflow_enforcer.py` still receives a valid script path when `$CLAUDE_PLUGIN_DIR` is unset, exits 0 on non-loop-trigger prompts, and does not block `/nav:init`.

---

## Verification

Smoke-tested three scenarios end-to-end before commit:

1. `$CLAUDE_PLUGIN_DIR` set to the cache path → sentinel `<!-- nav-session-start-injected:v1 -->` emitted in valid JSON.
2. `$CLAUDE_PLUGIN_DIR` explicitly unset (`env -u CLAUDE_PLUGIN_DIR`) → sentinel emitted via the fallback path. This is the case that was silently broken before.
3. `workflow_enforcer.py` invoked with `$CLAUDE_PLUGIN_DIR` unset on a non-loop-trigger prompt → exit 0, no spurious block.

---

## Upgrade notes

Restart Claude Code after the update so the patched plugin manifest is re-registered. The previous session's cached hook command table still uses the v6.15.0 strings.

If you have a Nav-initialized project that has *never* received SessionStart injection on a fresh session, this patch fixes it without any project-side changes. Confirm by starting a fresh Claude Code session in that project and looking for the sentinel in the first system reminder block, or by running `/context` immediately — `Messages` should show ~2k+ tokens from the injection instead of staying near zero.

---

## Compatibility

- No breaking changes.
- No skill changes.
- No config schema changes.
- Projects with project-local `.claude/settings.json` hook entries (typically written by `nav-init`) keep working exactly as before; the plugin manifest now acts as a reliable second layer instead of a silent no-op.

---

## Files modified

```
hooks/nav_session_start.py
hooks/nav_profile_sync.py
hooks/nav_task_graph_sync.py
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
README.md
CLAUDE.md
.agent/.nav-config.json
CHANGELOG.md
releases/RELEASE-NOTES-v6.15.1.md  (new)
```
