# TASK-32: Auto-Update Project Sync

**Status**: ✅ Completed
**Created**: 2025-01-22
**Version**: 5.8.0

---

## Context

**Problem**:
When Navigator auto-updates mid-session, only the plugin files update. Project files (CLAUDE.md, .nav-config.json) remain at old version, causing:
1. Version drift between plugin and project
2. Users following outdated CLAUDE.md patterns
3. Missing new config options in .nav-config.json
4. Skills exist but aren't invocable (cached paths issue)

**Root Cause**:
```
nav-upgrade skill:
  Step 2: Plugin Update ✅
  Step 4: Update Project CLAUDE.md ✅  ← Has this

auto_updater.py (used by nav-start):
  Update plugin ✅
  Sync project files ❌  ← Missing this
```

**Goal**:
Make auto-update behave like nav-upgrade - update both plugin AND project files.

**Success Criteria**:
- [ ] Auto-update syncs CLAUDE.md after successful plugin update
- [ ] Auto-update adds missing config sections to .nav-config.json
- [ ] Version drift detected on session start with warning
- [ ] Restart prompt shown after update (already done in previous commit)

---

## Implementation Plan

### Phase 1: Project Sync After Auto-Update
**Goal**: Sync project files after successful plugin update

**Tasks**:
- [ ] Add `sync_project_files()` function to auto_updater.py
- [ ] Call sync after successful plugin update
- [ ] Return sync status in result

**Files**:
- `skills/nav-start/functions/auto_updater.py` - Add sync logic

### Phase 2: Version Drift Detection
**Goal**: Detect and warn about plugin/project version mismatch

**Tasks**:
- [ ] Add `detect_version_drift()` function
- [ ] Compare plugin version vs .nav-config.json version
- [ ] Show warning in nav-start output if drift detected

**Files**:
- `skills/nav-start/functions/auto_updater.py` - Add detection
- `skills/nav-start/SKILL.md` - Add drift warning display

### Phase 3: Config Migration
**Goal**: Add missing config sections for new versions

**Tasks**:
- [ ] Add `migrate_config()` function
- [ ] Check for missing sections based on version
- [ ] Add defaults for new features

**Files**:
- `skills/nav-start/functions/auto_updater.py` - Add migration

---

## Technical Decisions

| Decision | Options Considered | Chosen | Reasoning |
|----------|-------------------|--------|-----------|
| Sync trigger | Always / On update only | On update only | Don't slow down normal session starts |
| CLAUDE.md sync | Full replace / Merge | Invoke nav-sync-claude | Preserves customizations, reuses existing logic |
| Config migration | Manual / Automatic | Automatic with defaults | Zero friction for users |

---

## Verify

```bash
# Test auto-update with project sync
python3 skills/nav-start/functions/auto_updater.py --config-path .agent/.nav-config.json

# Check version detection
python3 -c "from skills.nav_start.functions.auto_updater import detect_version_drift; print(detect_version_drift())"
```

---

## Done

- [ ] Auto-update syncs project CLAUDE.md after plugin update
- [ ] Version drift warning displayed on session start
- [ ] Config migrated with new feature defaults
- [ ] All existing tests pass

---

**Last Updated**: 2025-01-22
