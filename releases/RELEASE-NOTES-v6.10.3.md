# Navigator v6.10.3 Release Notes

**Release Date**: 2026-05-11
**Type**: Patch (settings_merger safety — don't kill user hooks on init)

---

## Summary

v6.9.0 and v6.10.0 added Navigator's first lifecycle hooks (SessionStart, PreCompact, PostCompact), installed via `settings_merger.py`. The merger preserves user-defined hooks by design — but a `navigator-research` audit surfaced that the **operational safety** around the merger was weak:

- `nav-init` ran the merger with no backup of `.claude/settings.json` first.
- The merger wrote in-place via `Path.write_text` — a kill mid-write could leave corrupted JSON.
- Empty existing files silently bypassed the JSON-error guard.
- `nav-upgrade` had a backup, but each run overwrote the previous one.
- Zero unit tests covered the merger logic.

TASK-38 (the v6.11 hook-migration roadmap) is about to register five more hooks through this same merger. Before widening the surface, the foundation needs to be safe and tested. **v6.10.3 is that hardening pass — no new features.**

The headline guarantee: **nav-init can never silently lose a user's `.claude/settings.json` content.** Every failure mode either aborts cleanly with the original file intact, or leaves a timestamped backup the user can restore from.

---

## Changes

### `settings_merger.py` — atomic write, dry-run, warning

**File**: `skills/nav-init/functions/settings_merger.py` (~50 lines added)

**Atomic write** — `Path.write_text(...)` replaced with `_atomic_write()`:

```python
def _atomic_write(target_path, content):
    fd, tmp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    with os.fdopen(fd, "w") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())          # durable before rename
    os.replace(tmp, target_path)        # atomic on POSIX
```

- Tempfile in the same directory guarantees `os.replace` is atomic on POSIX (no cross-filesystem rename).
- `fsync` before rename means content is durable even if power-loss occurs after the rename returns.
- On exception, the temp file is cleaned up — no orphaned `.tmp` files left behind.

**`--dry-run` flag** — preview the merged JSON without touching disk:

```bash
python3 settings_merger.py --dry-run .claude/settings.json fragment.json
# stdout: full merged JSON
# disk: unchanged
```

Used by `nav-init`'s optional `--preview` mode and by the test suite for assertion isolation.

**Non-list incoming warning** — previously skipped silently:

```
settings_merger: incoming hooks['SessionStart'] is not a list (dict) —
skipping. Bug in fragment? Existing value (if any) is preserved untouched.
```

Surfaces malformed fragments (bugs in our own templates) without dropping user data.

**Empty file now aborts** — previously slipped through the JSON parser and got silently overwritten. Now explicitly refused with a clear error directing the user to delete the file for a fresh install.

### `nav-init` Step 6 — pre-flight + timestamped backup

**File**: `skills/nav-init/SKILL.md` (lines 169-237)

Before invoking the merger, `nav-init` now:

1. **Detects foreign hooks** — scans existing `.claude/settings.json` for hook commands that don't match Navigator's known set (`nav_session_start`, `nav_pre_compact`, `nav_post_compact`, `workflow_enforcer`, `token_monitor`, `monitor-tokens`).
2. **Surfaces them to the user** with event + command preview (truncated to 80 chars).
3. **Blocks via AskUserQuestion** — user must confirm `[1] Merge (backup will be created)` or `[2] Abort init` before proceeding.
4. **Writes a timestamped backup** — `.claude/settings.json.pre-nav-init.{YYYYMMDD-HHMMSS}` — never overwrites a prior backup.

**Preview mode** — users can pass `--preview` for a unified diff before applying:

```bash
python3 settings_merger.py --dry-run .claude/settings.json templates/claude-settings-hooks.json \
    > /tmp/nav-init-preview.json
diff -u .claude/settings.json /tmp/nav-init-preview.json | head -80
```

### `nav-upgrade` Step 5 — backup rotation

**File**: `skills/nav-upgrade/SKILL.md` (lines 339-348)

Single-shot `.claude/settings.json.backup` → timestamped `.claude/settings.json.pre-upgrade.{ts}`. Re-running upgrade no longer overwrites the pristine pre-Navigator backup. Inline note added: **the first-ever pre-upgrade backup is the pristine pre-Navigator state — keep it as your rollback point.**

### New test suite

**File**: `skills/nav-init/functions/test_settings_merger.py` (NEW — ~250 lines)

Plain `unittest`, no dependencies. 11 cases covering every preservation guarantee:

| # | Test | Verifies |
|---|---|---|
| 1 | `test_fresh_install_no_existing_file` | New install from blank state |
| 2 | `test_preserves_user_hooks_same_event` | User hook on `SessionStart` survives when Nav also adds to `SessionStart` |
| 3 | `test_preserves_user_hooks_different_event` | User hook on `Stop` survives when Nav adds to other events |
| 4 | `test_idempotent_rerun` | Second run produces byte-identical output |
| 5 | `test_dedupe_by_command_string` | Same command string isn't duplicated |
| 6 | `test_preserves_top_level_keys` | `permissions`, `mcpServers`, `model`, `outputStyle` all pass through |
| 7 | `test_invalid_existing_json_aborts` | Garbage JSON → exit 2, file untouched |
| 8 | `test_empty_existing_file_aborts` | Empty file → exit 2, file untouched |
| 9 | `test_non_list_hooks_skipped_with_warning` | Malformed fragment doesn't corrupt existing user data |
| 10 | `test_dry_run_does_not_write` | `--dry-run` leaves disk untouched, returns correct dict |
| 11 | `test_atomic_write_no_partial_state_on_failure` | Simulated `os.replace` failure leaves original intact, no orphan tempfile |

```
Ran 11 tests in 0.008s — OK
```

Every test uses `tempfile.TemporaryDirectory()` for isolation. No shared state.

---

## Migration

**Nothing required.** This is a pure-safety patch:

- Existing projects: next `nav-upgrade` run picks up the new merger automatically (no config change).
- New projects: `nav-init` now runs the pre-flight check by default. If `.claude/settings.json` doesn't exist (fresh project), the check finds nothing and proceeds silently.

**Restart Claude Code** after upgrading if hooks were already installed — same caveat as v6.9.0/v6.10.0 (Claude Code caches hook definitions at session start).

---

## Verification

After upgrading:

```bash
# 1. Test suite passes
python3 -m unittest skills.nav-init.functions.test_settings_merger
# Expected: Ran 11 tests in <10ms — OK

# 2. Dry-run preview works
python3 skills/nav-init/functions/settings_merger.py \
    --dry-run .claude/settings.json templates/claude-settings-hooks.json | head
# Expected: merged JSON on stdout, .claude/settings.json unchanged on disk
```

For projects with pre-existing hooks, re-running `nav-init` (or `nav-upgrade`) should:
- Create a timestamped backup at `.claude/settings.json.pre-{nav-init,upgrade}.{YYYYMMDD-HHMMSS}`
- Surface any foreign hooks via the pre-flight check (nav-init only)
- Leave the original settings.json untouched until merge succeeds

---

## Files Changed

**Created**:
- `skills/nav-init/functions/test_settings_merger.py` — 11-case unit test
- `releases/RELEASE-NOTES-v6.10.3.md` — this file

**Modified**:
- `skills/nav-init/functions/settings_merger.py` — atomic write, dry-run, non-list warning, empty-file abort
- `skills/nav-init/SKILL.md` — Step 6 pre-flight + AskUserQuestion + timestamped backup
- `skills/nav-upgrade/SKILL.md` — Step 5 backup rotation
- `CHANGELOG.md` — v6.10.3 entry
- Version files: `plugin.json`, `marketplace.json`, `.nav-config.json`, `CLAUDE.md`, `README.md`

**Out of scope** (tracked as TASK-39 follow-ons):
- Matcher collision detection (different commands with overlapping matchers)
- Schema validation against Claude Code's `settings.json` schema (no public schema yet)
- `nav-cleanup-backups` command for pruning old `.pre-*` backups
- CI test wire-up (no test workflow exists in `.github/workflows/` today)

---

## Compatibility

- **Backward compatible.** Existing merger behavior unchanged for valid inputs; only failure-mode and observability changes.
- **No new dependencies.** `unittest`, `tempfile`, `os.replace` — all stdlib.
- **No new config keys.** Pre-flight behavior is governed by the existence check, not a flag.

---

## What's Next

v6.11 picks up TASK-38 (hook-migration roadmap) — five more hooks registered through the now-hardened merger. Phase 1 (Opportunities 2, 3, 4) ships zero-risk silent side-effects; Phase 2 introduces the first blocking hook. See `.agent/tasks/TASK-38-hook-migration-roadmap-v6.11.md` for details.
