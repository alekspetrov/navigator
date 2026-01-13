# SOP: Navigator Plugin Release

**Created**: 2025-01-13
**Trigger**: After v5.1.0 release issues (missing nav-profile, stale cache)

## Problem This Prevents

1. Skills referenced in `plugin.json` but not committed
2. Git tag created before fix commits
3. Stale plugin cache causing install failures
4. Stale marketplace references in user settings

---

## Pre-Release Checklist

### 1. Verify All Referenced Skills Exist

```bash
# Extract skill paths from plugin.json and verify each exists
jq -r '.skills[]' .claude-plugin/plugin.json | while read skill; do
  if [ ! -f "${skill#./}/SKILL.md" ]; then
    echo "❌ MISSING: $skill"
  else
    echo "✅ Found: $skill"
  fi
done
```

**If any missing**: Add and commit before proceeding.

### 2. Verify All Files Are Committed

```bash
# Check for untracked skill files
git status --short skills/

# Should show NO untracked (??) or modified (M) files
# If any exist, add and commit them
```

### 3. Version Consistency Check

Verify version is consistent across all files:

```bash
# Check all version references
grep -r '"version"' .claude-plugin/*.json
grep "Navigator Version" CLAUDE.md
grep "version-" README.md
```

All should show same version (e.g., `5.1.0`).

---

## Release Process

### Step 1: Commit All Changes

```bash
git add .
git status  # Verify what's being committed
git commit -m "feat(vX.Y.Z): description"
```

### Step 2: Push to Origin

```bash
git push origin main
```

### Step 3: Create Tag (AFTER all commits)

```bash
# CRITICAL: Only tag after ALL changes are pushed
git tag -a vX.Y.Z -m "Navigator vX.Y.Z: Release description"
git push origin vX.Y.Z
```

### Step 4: Create GitHub Release

```bash
gh release create vX.Y.Z --title "Navigator vX.Y.Z: Title" --notes-file RELEASE-NOTES-vX.Y.Z.md
```

### Step 5: Verify Release

```bash
# Check tag contains all files
git ls-tree vX.Y.Z skills/ | grep -E "nav-profile|nav-loop|nav-diagnose"
```

---

## Post-Release Verification

### Test Installation (Clean Environment)

```bash
# Clear local cache
rm -rf ~/.claude/plugins/cache/navigator-marketplace/

# Reinstall
# In Claude Code:
/plugin install navigator

# Verify no errors in plugin list
```

### If Errors Occur

**"skills path not found"**:
1. Check if file exists in tag: `git ls-tree vX.Y.Z skills/[name]/`
2. If missing: Commit file, delete tag, recreate tag, force push
3. Clear cache: `rm -rf ~/.claude/plugins/cache/navigator-marketplace/`
4. Reinstall plugin

**"Plugin not found in marketplace X"**:
1. Check `~/.claude/settings.json` for stale marketplace references
2. Remove old entries from `enabledPlugins`
3. Keep only: `"navigator@navigator-marketplace": true`

---

## Fix Tag After Release (Emergency)

If you need to update a tag after release:

```bash
# Delete local tag
git tag -d vX.Y.Z

# Recreate tag at current HEAD
git tag -a vX.Y.Z -m "Message"

# Force push (overwrites remote tag)
git push origin --force vX.Y.Z

# Update GitHub release if needed
gh release edit vX.Y.Z --notes-file RELEASE-NOTES-vX.Y.Z.md
```

---

## Common Mistakes

| Mistake | Prevention |
|---------|------------|
| Tag before all commits | Always commit → push → THEN tag |
| Untracked skills | Run verification script before release |
| Stale cache | Clear cache after tag updates |
| Version mismatch | Use checklist to verify all version refs |
| Missing functions/ | Check subdirectories, not just SKILL.md |

---

## Quick Reference

```bash
# Full release sequence
git add . && git commit -m "feat(vX.Y.Z): description"
git push origin main
git tag -a vX.Y.Z -m "Navigator vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --generate-notes

# Fix tag after release
git tag -d vX.Y.Z
git tag -a vX.Y.Z -m "Navigator vX.Y.Z"
git push origin --force vX.Y.Z
rm -rf ~/.claude/plugins/cache/navigator-marketplace/
```

---

**Last Updated**: 2025-01-13
**Version**: 1.0.0
