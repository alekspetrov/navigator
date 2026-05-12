# Plugin Release Workflow

**Category**: Development
**Created**: 2025-10-12
**Last Used**: v1.5.0 release
**Last Updated**: 2025-10-13

---

## Context

Standard operating procedure for releasing new versions of the Navigator Claude Code plugin. This workflow ensures consistent releases with proper versioning, documentation, and GitHub distribution.

---

## When to Use

Use this SOP when:
- Releasing a new plugin version (patch, minor, or major)
- After completing features that need distribution
- Publishing bug fixes to users
- Any change that affects plugin functionality

---

## Prerequisites

**BEFORE STARTING ANY RELEASE**:
1. **Read [Version Management SOP](./version-management.md)** - Understand version sync process
2. **Complete version consistency check** - Ensure no version drift exists

**Release Prerequisites**:
- [ ] All features implemented and tested
- [ ] Local testing completed in nav-test project
- [ ] Documentation updated (task docs, system docs)
- [ ] Working directory clean (no uncommitted changes)
- [ ] Version references audited and consistent

---

## Step-by-Step Release Process

### 0. Pre-Release Version Sync (MANDATORY)

**⚠️ CRITICAL: Complete this step BEFORE any other release steps**

See [Version Management SOP](./version-management.md) for complete instructions.

**Quick Checklist**:
1. Determine new version number (patch/minor/major)
2. Update `.claude-plugin/marketplace.json` (2 locations)
3. Update `README.md` (4 locations: status, badge, roadmap, footer)
4. Update `.agent/DEVELOPMENT-README.md` (1 location: footer)
5. Run audit script to verify consistency
6. Commit version bump separately with `chore:` prefix

**Audit command**:
```bash
# Set target version
NEW_VERSION="1.6.0"

# Quick audit
jq -r '.metadata.version' .claude-plugin/marketplace.json
jq -r '.plugins[0].version' .claude-plugin/marketplace.json
grep -E "Published v|version-.*-blue|v.*published|^\*\*Version\*\*:" README.md
grep -E "\(v[0-9]+\.[0-9]+\.[0-9]+\)" .agent/DEVELOPMENT-README.md
```

**⚠️ STOP if any mismatches found! Fix before proceeding.**

---

### 1. Determine Version Number

**Semantic Versioning Rules**:
- **Patch** (1.3.1): Bug fixes, typos, minor docs updates
- **Minor** (1.4.0): New features, new commands, non-breaking changes
- **Major** (2.0.0): Breaking changes, major refactoring

**Example**:
```
Current: 1.2.3
Adding /nav:start command → 1.3.0 (minor - new feature)
Fixing typo in template → 1.2.4 (patch - bug fix)
Changing command structure → 2.0.0 (major - breaking change)
```

### 2. Commit Feature Changes

**Use conventional commit format**:
```bash
git add -A
git commit -m "feat: add /nav:start command and PM tool auto-configuration

- New /nav:start command for session initialization
- Enhanced /nav:init with PM tool integration guidance
- Auto-generates Linear and GitHub integration SOPs
- Stronger CLAUDE.md enforcement of Navigator workflow
- Version bump to 1.3.0

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Commit message format**:
- First line: `type(scope): description`
- Body: Bullet points of changes
- Include Claude Code attribution
- Include Co-Authored-By line

**Commit types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `chore:` - Maintenance (version bump, dependencies)
- `refactor:` - Code restructuring

**Note**: Version bump should be committed separately in Step 0 with `chore:` prefix.

### 3. Create Git Tag

**Create annotated tag**:
```bash
git tag -a v1.3.0 -m "Version 1.3.0: Session start command and PM integration

Features:
- /nav:start command for consistent session initialization
- Automated PM tool integration setup (Linear, GitHub)
- Auto-generated integration SOPs
- Stronger Navigator workflow enforcement in CLAUDE.md

This release dramatically improves the onboarding experience and ensures
consistent Navigator workflow adoption across all sessions."
```

**Tag message format**:
- First line: "Version X.Y.Z: Brief description"
- Blank line
- "Features:" or "Changes:" section
- Bullet points of key changes
- Optional: Additional context paragraph

### 4. Push to GitHub

**Push commit and tag together**:
```bash
git push origin main && git push origin v1.3.0
```

**Verify push succeeded**:
```bash
git log --oneline -3
git tag -l | tail -3
```

**Check on GitHub**:
- Visit: https://github.com/alekspetrov/nav-plugin/tags
- Confirm new tag appears

### 5. GitHub Release (CI-owned)

The tag push from step 4 triggers `.github/workflows/release.yml`, which
publishes the GitHub release from `releases/RELEASE-NOTES-vX.Y.Z.md`. Do
NOT run `gh release create` locally — it races the workflow.

**Wait for the workflow run**:
```bash
gh run watch --exit-status "$(gh run list --workflow=release.yml --limit=1 --json databaseId --jq '.[0].databaseId')"
```

**Release notes file** (`releases/RELEASE-NOTES-v1.3.0.md`) structure:
1. **Title** with version and key feature
2. **What's New** - Feature highlights with examples
3. **Why This Matters** - Problem solved, benefits
4. **Upgrade Instructions** - For new and existing users
5. **Impact** - Metrics and improvements
6. **Documentation** - Links to task docs, architecture
7. **Feedback** - How to contribute or report issues
8. **Full Changelog** - Link to compare view

**Verify release**:
- Visit: https://github.com/alekspetrov/nav-plugin/releases
- Confirm release appears with notes

### 6. Document the Release (Navigator)

**Create task documentation**:
```bash
/nav:update-doc feature TASK-XX
```

**This creates**:
- `.agent/tasks/TASK-XX-feature.md` - Implementation plan
- Updates `.agent/DEVELOPMENT-README.md` - Adds to index
- Updates `.agent/system/project-architecture.md` - Version references

**Update SOP (this doc)**:
- Add "Last Used" date
- Note any issues encountered
- Add lessons learned section

### 7. Verify Installation

**Test in fresh project**:
```bash
cd /path/to/test/project
/plugin marketplace add alekspetrov/nav-plugin
/plugin install jitd
/nav:init
/nav:start
```

**Verify**:
- [ ] Plugin installs without errors
- [ ] Commands available (/nav:init, /nav:start, etc.)
- [ ] Templates copy correctly
- [ ] Version shows correctly in marketplace

---

## Troubleshooting

### Issue: Version Mismatch in marketplace.json

**Symptoms**: Two version fields don't match

**Solution**:
```bash
# Check both versions
grep version .claude-plugin/marketplace.json

# Update to match
# Edit file manually or use jq
```

### Issue: Git Tag Already Exists

**Symptoms**: `fatal: tag 'v1.3.0' already exists`

**Solution**:
```bash
# Delete local tag
git tag -d v1.3.0

# Delete remote tag (if pushed)
git push origin :refs/tags/v1.3.0

# Recreate tag
git tag -a v1.3.0 -m "..."
```

### Issue: Publish Release Workflow Fails

**Symptoms**: `gh run list --workflow=release.yml` shows the most recent run failed.

**Solutions**:
1. Inspect the failure: `gh run view --log-failed <run-id>`
2. Verify tag exists on remote: `git ls-remote --tags origin v1.3.0`
3. Confirm `releases/RELEASE-NOTES-vX.Y.Z.md` was committed before the tag
4. The workflow is idempotent — re-running it (`gh run rerun <run-id>`) is safe
5. Do NOT fall back to `gh release create` locally; the workflow owns publication

### Issue: GitHub CDN Cache

**Symptoms**: Users still getting old version after hours

**Solutions**:
1. Wait 1-2 hours for CDN refresh
2. Users can force specific commit:
   ```bash
   /plugin marketplace add alekspetrov/nav-plugin#422875d
   ```
3. Users can use local file for testing:
   ```bash
   /plugin marketplace add file:///path/to/nav-plugin
   ```

---

## Prevention

### Before Starting Release

- [ ] Run tests in nav-test project
- [ ] Verify all commands work
- [ ] Check for hardcoded version references
- [ ] Review CHANGELOG or commit history

### During Release

- [ ] Double-check version numbers match
- [ ] Test commands in release notes work
- [ ] Verify commit message follows conventions
- [ ] Check tag annotation has details

### After Release

- [ ] Verify tag on GitHub
- [ ] Check release notes render correctly
- [ ] Test installation in fresh project
- [ ] Update this SOP with any issues

---

## Checklist

Complete release checklist:

- [ ] **Step 0**: Complete version sync ([Version Management SOP](./version-management.md))
  - [ ] Determine version (patch/minor/major)
  - [ ] Update `.claude-plugin/marketplace.json` (both locations)
  - [ ] Update `README.md` (4 locations)
  - [ ] Update `.agent/DEVELOPMENT-README.md` (1 location)
  - [ ] Run audit script to verify consistency
  - [ ] Commit version bump with `chore:` prefix
- [ ] **Step 1-2**: Implement and commit feature changes
- [ ] Create annotated git tag
- [ ] Push commit and tag to GitHub
- [ ] Create GitHub release with detailed notes
- [ ] Document with `/nav:update-doc feature TASK-XX`
- [ ] Test installation in fresh project
- [ ] Verify commands work
- [ ] Update this SOP with lessons learned

---

## Metrics

### v1.3.0 Release (Example)

**Time to Release**: ~30 minutes
- Version update: 2 minutes
- Documentation: 10 minutes
- Git operations: 5 minutes
- GitHub release: 5 minutes
- Verification: 8 minutes

**Steps Completed**: 9/9

**Issues Encountered**: None

**Lessons Learned**:
- Letting `.github/workflows/release.yml` publish from `releases/RELEASE-NOTES-v*.md` is much cleaner than web UI or local `gh release create`
- Documenting with `/nav:update-doc` immediately after saves time
- Testing in nav-test project catches issues early

---

## Related Documentation

**SOPs** (read first!):
- [Version Management SOP](./version-management.md) - **MANDATORY** - Prevent version drift

**System Docs**:
- [Project Architecture](./../system/project-architecture.md) - Plugin structure
- [Plugin Patterns](./../system/plugin-patterns.md) - Development patterns

**Task Docs**:
- [TASK-01: Session Start & PM Integration](./../tasks/TASK-01-session-start-pm-integration.md)
- [TASK-04: Version Sync Fix](./../tasks/TASK-04-version-sync-release-process.md)

---

## Notes

### Version History of This SOP
- **2025-10-12**: Created during v1.3.0 release
- **2025-10-13**: Added mandatory Step 0 (version sync) and reference to Version Management SOP
- **Last Updated**: 2025-10-13

### Contributing
If you find issues with this workflow or have improvements:
1. Update this SOP
2. Add to "Lessons Learned" section
3. Update "Last Used" date
4. Commit changes

---

**This SOP ensures consistent, documented, and error-free plugin releases** 🚀
