# Navigator v6.15.6 Release Notes

**Release Date**: 2026-06-02
**Type**: Patch — critical hook-manifest fix (deleted hook still registered for every installed user)

---

## Summary

`.claude-plugin/plugin.json` still registered a `PostToolUse(Bash)` hook pointing at `hooks/nav_commit_reminder.py` — a file that was **deleted in `a2b4e59` (shipped in v6.15.5)** when the commit-reminder probe was retired.

That cleanup updated `.claude/settings.json` and `templates/claude-settings-hooks.json` but **missed the canonical published manifest**. `plugin.json` is the hooks configuration delivered to every installed user; `.claude/settings.json` is only the development backstop in this repo. Because the dev settings *were* cleaned, the regression was invisible locally — the classic "masked-until-shipped" pattern.

**Effect on installed users**: on every `Bash` tool call, Claude Code invoked
`python3 ".../hooks/nav_commit_reminder.py"` which failed with
`can't open file … No such file or directory`. A per-Bash-call error for 100% of installs running v6.15.5 (and, depending on cache state, since the hook was first registered in the manifest in v6.13.0).

This was surfaced by a 10-dimension, adversarially-verified project audit and confirmed independently (`ls hooks/nav_commit_reminder.py` → no such file; `grep nav_commit_reminder .claude-plugin/plugin.json` → 1 match; `.claude/settings.json` → 0 matches).

---

## What changed

### Removed the dead hook block from `.claude-plugin/plugin.json`

The `PostToolUse(Bash)` → `nav_commit_reminder.py` block was deleted. `PostToolUse` now contains only live hooks:

| Matcher | Hook |
|---|---|
| `Edit\|Write\|Bash` | `token_monitor.py` |
| `Edit\|Write` | `nav_task_graph_sync.py` |
| `Edit\|Write` | `nav_profile_sync.py` |

No other hook events changed. The nine hooks now on disk all resolve to a registered, existing file.

### Corrected `.agent/DEVELOPMENT-README.md` hook documentation

- Heading `Lifecycle Hooks (v6.9.0 → v6.15.3)` → `(v6.9.0 → v6.15.6)`.
- "Navigator ships **ten** Claude Code hooks" → "**nine**".
- Removed the `nav_commit_reminder.py` row from the "What ships" table.
- Synced stale version references (`v6.15.3` → `6.15.6`) and the "Last Updated" line.

---

## Why it slipped through

`a2b4e59`'s commit reasoning concluded "no public surface change" because it inspected `.claude/settings.json` and `templates/claude-settings-hooks.json` — **not** `.claude-plugin/plugin.json`, which is the actual published surface. The dev backstop in `.claude/settings.json` masked the failure on the maintainer's machine.

This is the same class of failure called out in the v6.15.1 notes ("the navigator source repo masked the bug via a project-local hook entry"). The durable fix is a release-time check.

### Follow-up (not in this patch)

Add a validation step to `nav-release` / CI that asserts **every** hook command path in `.claude-plugin/plugin.json` resolves to an existing file under `hooks/`. A deleted hook would then fail the release instead of shipping registered. Tracked as a high-priority audit finding alongside "CI runs no tests" — `release.yml` currently performs no validation before publishing.

---

## Verification

- `python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"` → valid.
- `grep -c nav_commit_reminder .claude-plugin/plugin.json` → `0`.
- `ls hooks/*.py | wc -l` → `9`, all registered in the manifest.
- All standard version files at `6.15.6`: `marketplace.json`, `plugin.json`, `README.md` badge, `CLAUDE.md` footer, `.agent/.nav-config.json`.
- `CHANGELOG.md` prepended with the `v6.15.6` entry pointing at this file.

---

## Upgrade notes

No config changes. No migration.

**Restart Claude Code after upgrade** so the corrected plugin manifest is re-registered — the dead hook is removed from `PostToolUse` only after the manifest reloads.

---

## Files modified

```
.claude-plugin/plugin.json                     (removed dead nav_commit_reminder block + version bump)
.claude-plugin/marketplace.json                (version + changelog entry)
.agent/DEVELOPMENT-README.md                   (nine hooks, table row removed, version sync)
README.md                                      (version badge)
CLAUDE.md                                      (version footer)
.agent/.nav-config.json                        (version)
CHANGELOG.md                                   (new v6.15.6 entry)
releases/RELEASE-NOTES-v6.15.6.md              (new)
```
