# TASK-04: Version Sync Fix & Release Process Improvement

**Status**: 🚧 In Progress
**Version**: 1.5.0 → 1.6.0
**Priority**: High (prevents documentation drift)
**Started**: 2025-10-13

---

## Problem Statement

### Current Issue

Version references are scattered across multiple files, leading to inconsistencies:

- `marketplace.json`: ✅ v1.5.0 (correct)
- `README.md`: ❌ v1.4.0 (outdated in 4 places)
- `.agent/DEVELOPMENT-README.md`: ✅ v1.5.0 (correct)

**Root Cause**: No single source of truth for version, no automated sync, no checklist in release workflow.

### Impact

- Users see wrong version number in README
- Confusion about actual plugin version
- GitHub releases missing for v1.3.0, v1.4.0, v1.5.0
- Trust erosion (docs don't match reality)

---

## Goals

### Primary
1. Fix current version inconsistency (README.md → v1.5.0)
2. Create missing GitHub releases with proper notes
3. Prevent future version drift with improved process

### Secondary
4. Add automated version sync checklist
5. Document version management SOP
6. Test the new process end-to-end

---

## Technical Analysis

### Files with Version References

```bash
# Current audit results:
./README.md:**Status**: ✅ Published v1.4.0
./README.md:[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)]
./README.md:- v1.4.0 published
./README.md:**Version**: 1.4.0

./.claude-plugin/marketplace.json:  "version": "1.5.0"  # ✅ Correct
./.agent/DEVELOPMENT-README.md:**Last Updated**: 2025-10-12 (v1.5.0)  # ✅ Correct
```

### Version Reference Locations

1. **Source of Truth**: `.claude-plugin/marketplace.json` → `metadata.version` and `plugins[0].version`
2. **User-Facing**: `README.md` (4 locations)
3. **Internal**: `.agent/DEVELOPMENT-README.md` (1 location)
4. **Git**: Tags (v1.5.0 exists)
5. **GitHub**: Releases (missing for v1.3.0, v1.4.0, v1.5.0)

---

## Implementation Plan

### Step 1: Fix Current Version (README.md)

**Update 4 locations**:

```markdown
# Line 5
**Status**: ✅ Published v1.5.0

# Line 8
[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)]

# Line 434
- v1.5.0 published

# Line 505
**Version**: 1.5.0
```

**Test**: Verify badge renders correctly, all references consistent.

---

### Step 2: Create Missing GitHub Releases

**v1.3.0 Release Notes** (from TASK-01):
```markdown
# Navigator v1.3.0 - Session Start & PM Integration

## 🚀 New Features

### `/nav:start` Command
- Loads documentation navigator automatically
- Checks for assigned tasks (Linear MCP, GitHub CLI support)
- Sets Navigator workflow context
- Shows token optimization status

### Enhanced `/nav:init`
- Auto-detects Linear MCP and GitHub CLI
- Generates setup guidance for PM tools
- Creates integration SOPs automatically
- Improved error handling

## 🔧 Improvements
- Stronger Navigator workflow enforcement in CLAUDE.md
- Better onboarding UX for new users
- PM tool configuration simplified

## 📦 What's Included
- 5 slash commands total
- Linear and GitHub integrations
- Auto-generated SOPs

**Full Changelog**: v1.0.1...v1.3.0
```

**v1.4.0 Release Notes** (from TASK-02):
```markdown
# Navigator v1.4.0 - Context Markers & README Overhaul

## 🚀 New Features

### `/nav:marker` Command
- Create conversation save points anytime
- Compress 130k sessions → 3k snapshots (97.7% reduction)
- Safety nets before risky changes
- Perfect handoffs between sessions

### Updated `/nav:init`
- Creates `.context-markers/` directory
- Adds `.context-markers/` to .gitignore
- Sets up marker infrastructure

## 📖 Documentation
- Comprehensive README rewrite
- Clear feature explanations with examples
- Token optimization strategy documented
- Context markers explained step-by-step

## 🔧 Improvements
- Better value proposition (understand Navigator in 30 seconds)
- Real-world workflow examples
- Metrics and benefits clearly shown

## 📦 What's Included
- 6 slash commands total
- Context marker system
- Updated templates

**Full Changelog**: v1.3.0...v1.4.0
```

**v1.5.0 Release Notes** (from TASK-03):
```markdown
# Navigator v1.5.0 - Interactive Marker Management & Auto-Resume

## 🚀 New Features

### `/nav:markers` Command
- **Interactive marker management**
  - List all markers with timestamps and descriptions
  - Load any marker with visual selection
  - Clean old markers (by age or count)
- **Performance**: <1s for 50+ markers
- **UX**: Arrow navigation, clear visual feedback

### Active Marker Auto-Resume
- **Automatic context restoration**
  - `/nav:compact` creates "active" marker
  - `/nav:start` detects and offers to load it
  - One-command resume (vs 3 manual steps)
- **Smart workflow**: Compact → Start → Continue

### Updated Commands
- `/nav:compact`: Now creates `.active` marker automatically
- `/nav:start`: Auto-detects active marker, prompts to load

## 🔧 Improvements
- Marker file naming: `YYYY-MM-DD_HH-MM-SS_name.md`
- Chronological sorting (newest first)
- Better error handling for corrupted markers
- Graceful degradation if no markers exist

## 📦 What's Included
- 7 slash commands total
- Interactive marker UI
- Auto-resume system
- Performance optimizations

## 💡 Workflow Impact

**Before v1.5.0**:
```bash
/nav:compact                          # Creates marker
# ...new session...
ls .agent/.context-markers/            # Find marker manually
Read .agent/.context-markers/file.md   # Load manually
```

**After v1.5.0**:
```bash
/nav:compact                          # Creates active marker
# ...new session...
/nav:start                            # Detects & loads automatically
# Continue working immediately!
```

**Full Changelog**: v1.4.0...v1.5.0
```

---

### Step 3: Enhance Release Workflow SOP

**Add to `.agent/sops/development/plugin-release-workflow.md`**:

#### New Section: "Pre-Release Version Sync Checklist"

```markdown
### Step 0: Pre-Release Version Sync (MANDATORY)

**Before making any changes, verify version consistency**:

1. **Determine new version**:
   ```bash
   # Check current version
   cat .claude-plugin/marketplace.json | jq -r '.metadata.version'

   # Determine bump type
   # - Patch (1.5.0 → 1.5.1): Bug fixes only
   # - Minor (1.5.0 → 1.6.0): New features, backward compatible
   # - Major (1.5.0 → 2.0.0): Breaking changes
   ```

2. **Update all version references** (NEW_VERSION = X.Y.Z):
   ```bash
   # Audit current references
   grep -r "version.*[0-9]\.[0-9]\.[0-9]" . \
     --include="*.md" \
     --include="*.json" \
     --exclude-dir=.git \
     --exclude-dir=node_modules

   # Files to update:
   # 1. .claude-plugin/marketplace.json (2 places)
   #    - metadata.version
   #    - plugins[0].version

   # 2. README.md (4 places)
   #    - Line ~5: **Status**: ✅ Published vX.Y.Z
   #    - Line ~8: [![Version](badge/version-X.Y.Z-blue.svg)]
   #    - Line ~434: - vX.Y.Z published
   #    - Line ~505: **Version**: X.Y.Z

   # 3. .agent/DEVELOPMENT-README.md (1 place)
   #    - Bottom: **Last Updated**: YYYY-MM-DD (vX.Y.Z)
   ```

3. **Verify consistency**:
   ```bash
   # All should show NEW_VERSION
   jq -r '.metadata.version' .claude-plugin/marketplace.json
   jq -r '.plugins[0].version' .claude-plugin/marketplace.json
   grep -A1 "Status" README.md | grep "Published"
   grep "Version.*badge" README.md
   grep "Last Updated" .agent/DEVELOPMENT-README.md
   ```

4. **Commit version bump**:
   ```bash
   git add .claude-plugin/marketplace.json README.md .agent/DEVELOPMENT-README.md
   git commit -m "chore: bump version to vX.Y.Z"
   ```

**⚠️ STOP**: If any version mismatch found, fix before proceeding!
```

---

### Step 4: Create Version Management SOP

**New file**: `.agent/sops/development/version-management.md`

```markdown
# Version Management - Standard Operating Procedure

**Last Updated**: 2025-10-13
**Applies To**: All Navigator plugin releases

---

## Overview

This SOP ensures version numbers stay consistent across all files during releases.

**Problem**: Version references scattered across 7+ locations
**Solution**: Single source of truth + automated checklist
**Result**: Zero version drift

---

## Single Source of Truth

**Primary**: `.claude-plugin/marketplace.json`
```json
{
  "metadata": {
    "version": "1.5.0"  // ← SSOT
  },
  "plugins": [
    {
      "version": "1.5.0"  // ← Must match metadata.version
    }
  ]
}
```

**All other files reference this version**.

---

## Version Reference Map

| File | Location | Format | Update Frequency |
|------|----------|--------|------------------|
| `marketplace.json` | `metadata.version` | `"1.5.0"` | Every release |
| `marketplace.json` | `plugins[0].version` | `"1.5.0"` | Every release |
| `README.md` | Line ~5 | `v1.5.0` | Every release |
| `README.md` | Line ~8 (badge) | `1.5.0` | Every release |
| `README.md` | Line ~434 (roadmap) | `v1.5.0` | Every release |
| `README.md` | Line ~505 (footer) | `1.5.0` | Every release |
| `DEVELOPMENT-README.md` | Bottom | `(v1.5.0)` | Every release |
| Git tag | Tag name | `v1.5.0` | Every release |
| GitHub release | Release version | `v1.5.0` | Every release |

---

## Pre-Release Checklist

**Use this checklist before every release**:

- [ ] Determine semantic version bump (patch/minor/major)
- [ ] Update `marketplace.json` (both locations)
- [ ] Update `README.md` (4 locations)
- [ ] Update `DEVELOPMENT-README.md` (1 location)
- [ ] Run version consistency audit
- [ ] Commit version bump separately
- [ ] Verify all references match

**Command**:
```bash
# Audit script (run before commit)
NEW_VERSION="1.6.0"  # Set your target version

echo "Checking marketplace.json..."
jq -r '.metadata.version' .claude-plugin/marketplace.json | grep "$NEW_VERSION"
jq -r '.plugins[0].version' .claude-plugin/marketplace.json | grep "$NEW_VERSION"

echo "Checking README.md..."
grep "Published v$NEW_VERSION" README.md
grep "version-$NEW_VERSION" README.md
grep "^- v$NEW_VERSION" README.md
grep "^\*\*Version\*\*: $NEW_VERSION" README.md

echo "Checking DEVELOPMENT-README.md..."
grep "(v$NEW_VERSION)" .agent/DEVELOPMENT-README.md

echo "✅ All version references consistent!"
```

---

## Post-Release Checklist

- [ ] Create Git tag: `git tag -a v1.6.0 -m "Version 1.6.0: Description"`
- [ ] Push tag: `git push origin v1.6.0`
- [ ] Create GitHub release with notes
- [ ] Verify badge renders correctly
- [ ] Update plugin marketplace listing (if applicable)

---

## Semantic Versioning Guide

**Patch (1.5.0 → 1.5.1)**:
- Bug fixes only
- No new features
- No breaking changes
- Example: Fix typo in template

**Minor (1.5.0 → 1.6.0)**:
- New features
- Backward compatible
- No breaking changes
- Example: Add new slash command

**Major (1.5.0 → 2.0.0)**:
- Breaking changes
- May require user action
- Changed APIs or workflows
- Example: Rename command, change file structure

---

## Troubleshooting

### Version Mismatch Detected

**Symptoms**: Grep shows different versions across files

**Solution**:
1. Identify which files are out of sync
2. Determine correct version (from `marketplace.json`)
3. Update all mismatched files
4. Re-run audit script
5. Commit fix separately

### Badge Not Rendering

**Symptoms**: Version badge shows old version or 404

**Solution**:
1. Check README.md badge URL format
2. Verify version number has no typos
3. Shield.io cache may need 5-10 minutes
4. Force refresh with `?v=timestamp` param

### Git Tag Already Exists

**Symptoms**: `tag 'v1.6.0' already exists`

**Solution**:
```bash
# Delete local tag
git tag -d v1.6.0

# Delete remote tag (if pushed)
git push origin :refs/tags/v1.6.0

# Recreate tag
git tag -a v1.6.0 -m "Version 1.6.0: Description"
git push origin v1.6.0
```

---

## Future Improvements

### Potential Automation
- [ ] Pre-commit hook to verify version consistency
- [ ] Script to bump all versions at once
- [ ] GitHub Action to validate PRs
- [ ] Bot to create release notes from task docs

**For now**: Manual checklist is sufficient for plugin development pace.

---

**This SOP prevents version drift and ensures professional release quality.**
```

---

### Step 5: Update Release Workflow SOP

**Modify**: `.agent/sops/development/plugin-release-workflow.md`

Add reference to new version management SOP at the beginning:

```markdown
## Prerequisites

**Before starting any release**:
1. Read [Version Management SOP](./version-management.md)
2. Complete version sync checklist
3. Verify no version mismatches exist
```

---

### Step 6: Test the Process

**Simulate a release**:
1. Create test branch
2. Bump version to 1.5.1 (simulated patch)
3. Run audit script
4. Verify checklist catches all locations
5. Roll back changes

**Success criteria**:
- Audit script detects all 7 version locations
- Checklist is easy to follow
- No manual hunting required

---

## Implementation Order

1. ✅ Create this task doc (TASK-04)
2. 🔄 Fix README.md → v1.5.0
3. 🔄 Create missing GitHub releases (v1.3.0, v1.4.0, v1.5.0)
4. 🔄 Create version management SOP
5. 🔄 Update release workflow SOP
6. 🔄 Test the new process
7. 🔄 Archive TASK-04

---

## Success Criteria

### Immediate
- [ ] README.md shows v1.5.0 everywhere
- [ ] GitHub releases exist for v1.3.0, v1.4.0, v1.5.0
- [ ] Version management SOP created
- [ ] Release workflow SOP updated

### Long-term
- [ ] Future releases have no version drift
- [ ] New contributors follow checklist
- [ ] Zero version-related user confusion
- [ ] Professional release quality maintained

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Forget to update location | Medium | Audit script catches it |
| Badge cache issues | Low | Wait 10 min or force refresh |
| Manual process errors | Medium | Checklist + audit script |
| Future files added | Low | Update SOP + map when detected |

---

## Documentation Impact

**Files created**:
- `.agent/tasks/TASK-04-version-sync-release-process.md` (this file)
- `.agent/sops/development/version-management.md` (new SOP)

**Files modified**:
- `README.md` (version updates)
- `.agent/sops/development/plugin-release-workflow.md` (checklist addition)

---

## Timeline

- **Day 1**: Fix current version, create GitHub releases
- **Day 1**: Create version management SOP
- **Day 1**: Test process
- **Day 1**: Archive task

**Estimated Time**: 2-3 hours

---

## Notes

- This issue surfaced because v1.5.0 was released without updating README.md
- Root cause: No systematic checklist in release workflow
- Prevention: Pre-release version sync becomes mandatory step
- Future: Consider automating with pre-commit hooks

---

**Next Steps**: Execute implementation plan, starting with README.md fix.
