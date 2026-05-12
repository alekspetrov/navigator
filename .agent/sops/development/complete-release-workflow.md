# Complete Release Workflow

**Category**: Development
**Created**: 2025-10-31
**Last Updated**: 2025-10-31

---

## Context

**When to use this SOP**:
When preparing to release a new version of Navigator plugin with completed features, bug fixes, or experimental functionality.

**Problem it solves**:
Ensures all version files are synchronized, documentation is complete, and release artifacts are properly published. Prevents common mistakes like missing version updates in plugin.json, outdated README badges, or incomplete release notes.

**Prerequisites**:
- All features/fixes committed to main branch
- Git tags and releases configured
- `gh` CLI installed and authenticated
- Write access to GitHub repository

---

## The Problem

### Symptoms
- Version drift across files (marketplace.json shows 4.3.0 but plugin.json shows 4.0.0)
- README showing outdated version badges
- GitHub releases missing comprehensive release notes
- Users confused about what changed in the release

### Root Cause
Manual release process with multiple files to update leads to:
1. Forgetting to update all version references
2. Incomplete documentation updates
3. Missing or rushed release notes
4. Inconsistent version numbers across artifacts

---

## The Solution

### Step 1: Analyze Current State

**Do this**:
```bash
# Check current versions
cat .claude-plugin/marketplace.json | grep version
cat .claude-plugin/plugin.json | grep version
head -10 README.md | grep version

# Check latest git tag
git tag --sort=-creatordate | head -1

# Check what's on main that's not released
git log --oneline $(git describe --tags --abbrev=0)..HEAD
```

**Why**:
Understanding version state prevents duplicate releases and ensures you're packaging the right commits.

**Expected output**:
```
marketplace.json: "version": "4.0.0"
plugin.json: "version": "4.0.0"
README.md: version-4.0.0
Latest tag: v4.0.0
New commits: 15 commits since v4.0.0
```

### Step 2: Determine Release Version

**Semantic versioning rules**:
- **Patch** (4.3.0 → 4.3.1): Bug fixes only, no new features
- **Minor** (4.3.0 → 4.4.0): New features, backward compatible
- **Major** (4.3.0 → 5.0.0): Breaking changes

**For experimental features**:
- Use minor version bump
- Mark as "pre-release" in GitHub
- Add experimental status badge to README

**Do this**:
```bash
# If bug fixes only
NEW_VERSION="4.3.1"

# If new features (backward compatible)
NEW_VERSION="4.4.0"

# If breaking changes
NEW_VERSION="5.0.0"
```

### Step 3: Update Version Files

**Do this**:
```bash
# 1. Update marketplace.json
# Find the version line and update
vim .claude-plugin/marketplace.json
# Change: "version": "4.0.0" → "version": "4.3.0"

# 2. Update plugin.json
vim .claude-plugin/plugin.json
# Change: "version": "4.0.0" → "version": "4.3.0"
# Update description if new major features added

# 3. Update README.md badges
vim README.md
# Change: version-4.0.0-blue.svg → version-4.3.0-blue.svg
# Add experimental badge if pre-release:
# [![Status](https://img.shields.io/badge/status-experimental-yellow.svg)](...)
```

**Why**:
All three files are version sources:
- `marketplace.json`: Claude Code marketplace reads this
- `plugin.json`: Plugin metadata and npm-style versioning
- `README.md`: User-facing version display

**Verification**:
```bash
grep -r "\"version\"" .claude-plugin/
grep "version-" README.md
```

### Step 4: Write Comprehensive Release Notes

**Do this**:
Create `RELEASE-NOTES-v{VERSION}.md` with this structure:

```markdown
# Navigator v{VERSION}: {Feature Name}

**Released**: {YYYY-MM-DD}
**Type**: {Patch|Minor|Major} release
**Status**: {Production|Experimental}

---

## 🎯 What's New

### {Main Feature Title}

**Problem solved**: {What problem does this solve?}

**Solution**: {How does the solution work?}

#### Core Features

**1. {Feature Name}**
- {Bullet point 1}
- {Bullet point 2}

**2. {Feature Name}**
- {Details}

---

## 📊 Test Results

**Validation**: {How was this tested?}

### ✅ Successful Workflows ({X}/{Y})
1. **{Test name}** - {Description}
2. **{Test name}** - {Description}

### ❌ Known Issues ({X}/{Y} failures)
- **{Issue category}** ({X} failures): {Description}
- **{Issue category}** ({X} failures): {Description}

### 🐛 Bug Fixes This Release
- Fixed {issue description} ({file:line})
- {Additional fixes}

**Success rate**: {X}% full completion
**Recommended**: {Usage guidance}

---

## 🚀 Getting Started

### Installation

\`\`\`bash
# Installation commands
\`\`\`

### Usage

\`\`\`bash
# Usage examples
\`\`\`

---

## ⚠️ Experimental Status (if applicable)

**Why experimental**:
- {Reason 1}
- {Reason 2}

**Production readiness**:
- ✅ {What works}
- ❌ {What doesn't}

**Recommendation**: {Usage guidance}

---

## 📦 Full Feature Breakdown

### v{VERSION} (This Release)
- {Feature list}

### v{PREVIOUS} (Included)
- {Previous features if bundled}

---

## 📝 Breaking Changes

{None or list of breaking changes}

---

## 📚 Resources

- **Documentation**: {Link}
- **GitHub**: {Link}
- **Issues**: {Link}
```

**Why**:
Comprehensive release notes serve multiple purposes:
- Users understand what changed
- GitHub release page has full context
- Historical record of features/fixes
- Marketing/announcement content ready

### Step 5: Update README with Release Info

**Do this**:
Add new version section after "Getting Started":

```markdown
## What's New in v{VERSION}

**{Feature Title}** - {One-line description}

### The {Concept}

**Problem**: {Problem statement}
- {Bullet 1}
- {Bullet 2}

**Solution**: {Solution description}
\`\`\`bash
# Example usage
\`\`\`

### Status: {Experimental|Production}

**Test results**: {X}% completion rate
- ✅ Works: {What works}
- ⚠️ Issues: {Known issues}
- 📋 Recommendation: {Guidance}

**Try it**:
\`\`\`bash
# Quick start commands
\`\`\`

[Full v{VERSION} release notes](RELEASE-NOTES-v{VERSION}.md)
```

**Why**:
README is first thing users see - must reflect current version and features.

### Step 6: Commit Version Updates

**Do this**:
```bash
git add -A

git commit -m "$(cat <<'EOF'
chore(v{VERSION}): bump version and add release notes

- Updated marketplace.json version: {OLD} → {NEW}
- Updated plugin.json version: {OLD} → {NEW}
- Created comprehensive RELEASE-NOTES-v{VERSION}.md
- Updated README.md with v{VERSION} section
- {Additional changes, e.g., bug fixes}

Breaking changes: {None or list}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Why**:
Single commit for all version-related changes keeps history clean and makes rollback easier if needed.

**Expected output**:
```
[main abc1234] chore(v4.3.0): bump version and add release notes
 4 files changed, 350 insertions(+), 8 deletions(-)
 create mode 100644 RELEASE-NOTES-v4.3.0.md
```

### Step 7: Create Git Tag

**Do this**:
```bash
git tag -a v{VERSION} -m "Navigator v{VERSION}: {Feature Title}

Major features:
- {Feature 1}
- {Feature 2}
- {Feature 3}

{Test validation summary}
Status: {Experimental|Production}

Bug fixes:
- {Fix 1}

Documentation:
- Complete RELEASE-NOTES-v{VERSION}.md
- Updated README.md

Breaking changes: {None or list}"
```

**Why**:
Annotated tags contain metadata and show up in GitHub releases. Tag message provides git-level documentation.

**Verification**:
```bash
git tag -l -n9 v{VERSION}
```

### Step 8: Push to Origin

**Do this**:
```bash
# Push commit and tag together
git push origin main && git push origin v{VERSION}
```

**Why**:
Both commit and tag need to be on origin for GitHub release to work properly.

**Expected output**:
```
To https://github.com/alekspetrov/navigator.git
   abc1234..def5678  main -> main
To https://github.com/alekspetrov/navigator.git
 * [new tag]         v{VERSION} -> v{VERSION}
```

### Step 9: Create GitHub Release (Automated)

**Automated via GitHub Action**:

When you push a git tag (Step 8), GitHub Actions automatically:
1. Detects the tag push
2. Reads `RELEASE-NOTES-v{VERSION}.md`
3. Determines if pre-release (checks marketplace.json for "Experimental")
4. Creates GitHub release
5. Attaches release notes file
6. Notifies watchers

**If the workflow fails**: re-run it instead of falling back to local
`gh release create` (which races the workflow and breaks idempotency).
The workflow is idempotent — both create and edit paths handle pre-existing
releases.

```bash
# Inspect failure
gh run view --log-failed "$(gh run list --workflow=release.yml --limit=1 --json databaseId --jq '.[0].databaseId')"

# Re-run after fixing
gh run rerun "$(gh run list --workflow=release.yml --limit=1 --json databaseId --jq '.[0].databaseId')"
```

Pre-release detection is automatic: tags containing `alpha`/`beta`/`rc`,
or repos whose `marketplace.json` description contains "Experimental",
get `--prerelease`. No manual flag needed.

**Why automated**:
- Zero manual steps after tag push
- Consistent release format
- Automatic pre-release detection
- Runs even if you forget

**Verify automation succeeded**:
```bash
# Check GitHub Action status
gh run list --workflow=release.yml --limit 1

# Expected: ✓ Publish Release completed
```

**Expected output**:
```
https://github.com/alekspetrov/navigator/releases/tag/v{VERSION}
```

### Step 10: Test User Upgrade Flow

**Critical**: Verify users can upgrade smoothly to new version.

**Test stable upgrade** (if releasing stable):
```bash
# In test project with Navigator installed
cd /tmp/test-project

# Simulate user upgrading
/plugin update navigator

# Should fetch new stable version
/plugin list | grep navigator  # Verify version updated

# Verify CLAUDE.md sync
# nav-upgrade should auto-invoke nav-update-claude
# Template should match new plugin version
```

**Test pre-release upgrade** (if releasing pre-release):
```bash
cd /tmp/test-project

# User runs nav-upgrade
# Should see:
✅ You're on latest stable version (v4.0.0)

⚡ Experimental version available: v4.3.0

New in v4.3.0 (Experimental):
• [Feature list from release notes]

Options:
[1] Stay on stable v4.0.0 (recommended)
[2] Try experimental v4.3.0 (early adopter)

Your choice:
```

**If user chooses [2]**:
```bash
# Should execute:
/plugin uninstall navigator
git clone https://github.com/alekspetrov/navigator.git /tmp/navigator-v4.3.0
cd /tmp/navigator-v4.3.0 && git checkout v4.3.0
/plugin install /tmp/navigator-v4.3.0

# Then verify
/plugin list | grep navigator  # Should show v4.3.0
```

**Verify template sync**:
```bash
# nav-update-claude should fetch from GitHub
# Check output:
✓ Using template from GitHub (v4.3.0)  # Not "bundled"

# Verify CLAUDE.md has v4.3.0 content
grep "Navigator Version" CLAUDE.md
# Should show: Navigator Version: 4.3.0 (or similar marker)
```

**Why this matters**:
- Users on v4.0.0 expect `/plugin update` to work
- Pre-releases require manual opt-in
- Template drift causes confusion (v4.0 templates with v4.3 plugin)
- This test caught the bug in actual usage

---

### Step 11: Verify Release
```bash
# Check GitHub release page
gh release view v{VERSION}

# Verify version consistency
echo "marketplace.json:" && grep version .claude-plugin/marketplace.json
echo "plugin.json:" && grep version .claude-plugin/plugin.json
echo "README.md:" && grep -o "version-[0-9.]*" README.md | head -1
echo "Latest tag:" && git describe --tags --abbrev=0
```

**Expected output**:
```
marketplace.json: "version": "4.3.0"
plugin.json: "version": "4.3.0"
README.md: version-4.3.0
Latest tag: v4.3.0
```

All versions should match.

---

## Complete Example

### Real Release: v4.3.0 (Multi-Claude Workflows)

**Step 1: Analyzed state**
```bash
$ git log --oneline v4.0.0..HEAD | wc -l
15

$ git log --oneline v4.0.0..HEAD
fb932a9 docs(v4.3.0): complete multi-Claude workflow documentation
19e79a4 feat(v4.3.0): enable Task agents in all sub-Claude phases
727099b feat(v4.2.0): add failure reporting
...
```

**Step 2: Determined version**
- 15 new commits with features → Minor version bump
- Experimental features → Pre-release flag
- Result: v4.3.0 (pre-release)

**Step 3: Updated files**
```bash
# marketplace.json: 4.0.0 → 4.3.0
# plugin.json: 4.0.0 → 4.3.0
# README.md: Added experimental badge + v4.3.0 section
```

**Step 4: Created release notes**
- File: `RELEASE-NOTES-v4.3.0.md`
- Size: 282 lines
- Sections: Features, test results, getting started, troubleshooting

**Step 5: Updated README**
- Added "What's New in v4.3.0" section
- Updated version badge
- Added experimental status badge

**Step 6-8: Committed and pushed**
```bash
$ git add -A
$ git commit -m "chore(v4.3.0): bump version and add release notes..."
[main c5da73c] chore(v4.3.0): bump version and add release notes
 3 files changed, 282 insertions(+), 3 deletions(-)

$ git tag -a v4.3.0 -m "Navigator v4.3.0: Multi-Claude..."
$ git push origin main && git push origin v4.3.0
```

**Step 9: Created GitHub release** (automated via GitHub Action)
```bash
# GitHub Action triggered by tag push automatically created release
# Check: gh run list --workflow=release.yml --limit 1
# Result: ✓ Publish Release completed

https://github.com/alekspetrov/navigator/releases/tag/v4.3.0
```

**Step 10: Improved Upgrade Experience**
```bash
# Fixed template drift issue (v4.3.1)
# Updated nav-update-claude to fetch from GitHub:
# - Detects plugin version
# - Fetches matching template from GitHub
# - Falls back to bundled if offline
# Result: Users always get version-matched templates

# Updated nav-upgrade with pre-release choice:
# - Detects stable + pre-release versions
# - Presents interactive choice
# - Auto-invokes nav-update-claude after update
# Result: Professional pre-release opt-in flow
```

**Step 11: Verified**
```bash
$ grep -r "\"version\"" .claude-plugin/
.claude-plugin/marketplace.json:  "version": "4.3.0",
.claude-plugin/plugin.json:  "version": "4.3.0",

$ git describe --tags --abbrev=0
v4.3.0

✅ All versions synchronized
```

---

## Testing

### Verify Release Checklist

**Before pushing**:
- [ ] All version files updated (marketplace.json, plugin.json, README.md)
- [ ] Release notes created (RELEASE-NOTES-v{VERSION}.md)
- [ ] README has new version section
- [ ] Commit message follows convention
- [ ] Git tag created with descriptive message

**After pushing**:
- [ ] GitHub release page shows correct version
- [ ] Release notes display properly
- [ ] Tarball/zip available for download
- [ ] All version numbers match across files

**User verification** (manual test):
```bash
# In test project
cd /tmp/navigator-test

# Update plugin
/plugin update navigator

# Verify new version installed
/plugin list | grep navigator
```

---

## Prevention

**How to avoid version drift**:
1. Update ALL version files in single commit
2. Use this SOP checklist every release
3. Verify consistency before pushing
4. Review GitHub release page after publishing

**Red flags to watch for**:
- Commit pushed without tag
- Tag pushed without GitHub release
- Version mismatch between files
- README showing old version after release

**Automation opportunities**:
- Version bump script (updates all files)
- Release notes template generator
- Pre-push hook to verify version consistency

---

## Troubleshooting

### Issue: Publish Release workflow fails with "release already exists"

**Symptoms**: Workflow run fails with `release with the same tag name already exists`

**Cause**: Someone (or a stale skill version) ran `gh release create` locally before the tag was pushed, racing the workflow.

**Fix**: Re-run the workflow. Since `bfe3b26` it's idempotent — it will detect the existing release and update it via `gh release edit` + `gh release upload --clobber` instead of failing.

```bash
gh run rerun "$(gh run list --workflow=release.yml --limit=1 --json databaseId --jq '.[0].databaseId')"
```

**Prevention**: Never run `gh release create` locally. The workflow owns release publication.

### Issue: Version mismatch discovered after release

**Symptoms**: marketplace.json shows v4.3.0 but plugin.json shows v4.0.0

**Cause**: Forgot to update plugin.json before committing

**Fix**:
```bash
# Update missing file
vim .claude-plugin/plugin.json
# Change version to match

# Commit fix
git add .claude-plugin/plugin.json
git commit -m "fix(v4.3.0): sync plugin.json version"

# Push fix (don't recreate tag)
git push origin main
```

### Issue: Forgot to mark as pre-release

**Symptoms**: Experimental feature released as stable

**Cause**: Forgot `--prerelease` flag

**Fix**:
```bash
# Edit release on GitHub
gh release edit v{VERSION} --prerelease

# Or via web UI: Edit release → Check "This is a pre-release"
```

### Issue: Release notes have formatting errors

**Symptoms**: Code blocks not rendering, broken links

**Cause**: Markdown syntax errors in RELEASE-NOTES file

**Fix**:
```bash
# Test locally first
gh release view v{VERSION}

# Edit release notes
vim RELEASE-NOTES-v{VERSION}.md

# Update GitHub release
gh release edit v{VERSION} --notes-file RELEASE-NOTES-v{VERSION}.md
```

---

## Related Documentation

**Navigator Docs**:
- Version Management SOP: `.agent/sops/development/version-management.md`
- Plugin Release Workflow: `.agent/sops/development/plugin-release-workflow.md`

**External**:
- [Semantic Versioning](https://semver.org/)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## Maintenance Notes

**Update when**:
- Release process changes
- New version files added
- GitHub release requirements change
- Automation scripts added

**Owner**: Navigator maintainers

**Review frequency**: After each release (continuous improvement)

---

## Success Metrics

Release is successful when:
- ✅ All version files synchronized
- ✅ GitHub release published with full notes
- ✅ README reflects current version
- ✅ Users can discover and understand changes
- ✅ No version drift reported

**Time investment**:
- Manual (without SOP): 30-45 minutes, high error rate
- With SOP: 15-20 minutes, low error rate
- Future automation: <5 minutes, zero errors

---

**Last Updated**: 2025-10-31
**Tested With**: Navigator v4.3.0 release (2025-10-31)
**Process validated**: Successfully released v4.3.0 using this workflow
