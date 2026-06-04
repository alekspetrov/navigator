# Version Management - Standard Operating Procedure

**Category**: Development
**Created**: 2025-10-13
**Last Updated**: 2026-06-04

---

## Context

This SOP keeps the version number consistent across every file that carries it
during a release. Version drift confuses users and erodes documentation trust.

**Problem**: the version is repeated in several manifests and docs
**Solution**: one single source of truth + a 6-file bump checklist + an audit script
**Result**: zero version drift

> This list is kept in sync with the authoritative 6-file checklist in
> `.agent/DEVELOPMENT-README.md` ("Scenario: releasing a new version"). If the
> two ever disagree, DEVELOPMENT-README wins and this SOP must be corrected.

---

## When to Use

- Before every plugin release (patch, minor, major)
- When updating version references
- To audit version consistency before tagging
- When onboarding contributors to the release process

---

## Single Source of Truth

**SSOT**: `.claude-plugin/marketplace.json` -> `metadata.version`

```json
{
  "metadata": {
    "version": "6.15.6"
  },
  "plugins": [
    { "name": "navigator", "source": "./" }
  ]
}
```

> The marketplace `plugins[]` entries carry only `name` and `source` — there is
> **no** `plugins[0].version` field. `.claude-plugin/plugin.json` `version` is
> the manifest version that must match the SSOT; tooling
> (`config_migrator.py`, `release_validator.py`) reads the plugin manifest, not
> a marketplace plugin entry.

---

## Version Reference Map (the 6 bump locations)

Every release bumps the same six files. Five carry a matchable version string;
the sixth is a new per-version release-notes file.

| # | File | Location | Format |
|---|------|----------|--------|
| 1 | `.claude-plugin/marketplace.json` | `metadata.version` (SSOT) | `"6.15.6"` |
| 2 | `.claude-plugin/plugin.json` | `version` | `"6.15.6"` |
| 3 | `README.md` | badge (line ~8) | `version-6.15.6-blue` |
| 4 | `CLAUDE.md` | footer `**Navigator Version**:` (+ the config-sample `"version"`) | `6.15.6` |
| 5 | `.agent/.nav-config.json` | `version` | `"6.15.6"` |
| 6 | `releases/RELEASE-NOTES-v6.15.6.md` | new file per release | filename |

**Also refreshed (not gated by the audit):** `.agent/DEVELOPMENT-README.md`
footer carries a `(vX.Y.Z …)` note — update it opportunistically, but it is not
one of the six canonical bump locations.

Git tag (`vX.Y.Z`) and the GitHub release are produced by CI from the tag (see
`release.yml`); they are not hand-edited files and so are not in the bump set.

---

## Pre-Release Version Sync Checklist

Run this **before** making release commits.

### 1. Determine the new version

```bash
# Current SSOT version
jq -r '.metadata.version' .claude-plugin/marketplace.json

# Bump type:
#   Patch (6.15.6 -> 6.15.7): bug fixes only
#   Minor (6.15.6 -> 6.16.0): new features, backward compatible
#   Major (6.15.6 -> 7.0.0):  breaking changes
NEW_VERSION="6.16.0"   # set this
```

### 2. Update the six locations

1. `.claude-plugin/marketplace.json` -> `metadata.version`
2. `.claude-plugin/plugin.json` -> `version`
3. `README.md` -> badge `version-${NEW_VERSION}-blue`
4. `CLAUDE.md` -> footer `**Navigator Version**: ${NEW_VERSION}` (and the
   `"version"` literal in the config sample)
5. `.agent/.nav-config.json` -> `version`
6. `releases/RELEASE-NOTES-v${NEW_VERSION}.md` -> create it

### 3. Verify consistency (audit script)

Save as `scripts/audit-version.sh` and run from the repo root. It derives the
target version from the SSOT and checks the other locations against it, so there
is no version literal to keep in sync inside the script.

```bash
#!/usr/bin/env bash
# Verify the 6 canonical version locations agree with the SSOT.
set -uo pipefail

SSOT_FILE=".claude-plugin/marketplace.json"
V="$(jq -r '.metadata.version' "$SSOT_FILE")"
echo "Auditing version consistency against SSOT v${V} (${SSOT_FILE} metadata.version)"
echo ""
ERRORS=0

check() {            # check <label> <command...>
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "OK  ${label}"
  else
    echo "ERR ${label}"
    ERRORS=$((ERRORS + 1))
  fi
}

# 2. plugin.json version must equal the SSOT
check ".claude-plugin/plugin.json version == ${V}" \
  bash -c "[ \"\$(jq -r '.version' .claude-plugin/plugin.json)\" = \"${V}\" ]"

# 3. README.md badge
check "README.md badge version-${V}-blue" \
  grep -q "version-${V}-blue" README.md

# 4. CLAUDE.md footer (the config sample tracks it too; the footer is canonical)
check "CLAUDE.md footer Navigator Version: ${V}" \
  grep -q "Navigator Version\*\*: ${V}" CLAUDE.md

# 5. .agent/.nav-config.json version
check ".agent/.nav-config.json version == ${V}" \
  bash -c "[ \"\$(jq -r '.version' .agent/.nav-config.json)\" = \"${V}\" ]"

# 6. Release notes file for this version exists
check "releases/RELEASE-NOTES-v${V}.md exists" \
  test -f "releases/RELEASE-NOTES-v${V}.md"

echo ""
if [ "$ERRORS" -eq 0 ]; then
  echo "All 6 canonical version locations agree on v${V}."
  exit 0
else
  echo "${ERRORS} mismatch(es). Fix before tagging."
  exit 1
fi
```

The project also ships `skills/nav-release/functions/release_validator.py`
(`--check-all`, `--verify-hooks`, `--verify-tag`) which is the canonical
release gate; the script above is the quick manual equivalent.

### 4. Commit the version bump

```bash
git add .claude-plugin/marketplace.json .claude-plugin/plugin.json \
        README.md CLAUDE.md .agent/.nav-config.json \
        releases/RELEASE-NOTES-v${NEW_VERSION}.md
git commit -m "chore: bump version to v${NEW_VERSION}"
```

---

## Post-Release Checklist

Releases publish via CI from the pushed tag (`release.yml`), not by hand.

- [ ] Tag the bump commit: `git tag -a vX.Y.Z -m "Version X.Y.Z: ..."`
- [ ] Push commit and tag: `git push origin main && git push origin vX.Y.Z`
- [ ] Confirm the GitHub Action published the release
- [ ] Verify with `release_validator.py --verify-tag vX.Y.Z`
- [ ] Confirm the README badge renders (Shields.io CDN cache: 5-10 min)

---

## Semantic Versioning Guide

### Patch (6.15.6 -> 6.15.7)
- Bug fixes, typo/doc corrections, no new features, no breaking changes
- e.g. fix a hook path bug, correct a README typo

### Minor (6.15.6 -> 6.16.0)
- New features/skills, backward compatible, no breaking changes
- e.g. add a new skill, enhance existing output

### Major (6.15.6 -> 7.0.0)
- Breaking changes requiring user action
- e.g. rename a skill's trigger, change `.agent/` structure, change config schema

---

## Troubleshooting

### Version mismatch detected
1. Read the SSOT (`marketplace.json` `metadata.version`)
2. Update the mismatched location(s) from the Reference Map
3. Re-run `scripts/audit-version.sh`
4. Commit the fix with a `chore:` prefix

### Badge not rendering
1. Check the badge URL format: `version-6.15.6-blue`
2. Shields.io CDN cache takes 5-10 minutes; hard-refresh the browser

### Git tag already exists
```bash
git tag -d vX.Y.Z                       # delete local
git push origin :refs/tags/vX.Y.Z       # delete remote
git tag -a vX.Y.Z -m "Version X.Y.Z"    # recreate
git push origin vX.Y.Z
```

### A doc still shows the old version
- Search by pattern, not line number (line numbers drift): `grep -n "6.15.6" <file>`
- Remember the config sample in CLAUDE.md carries the version in addition to the footer

---

## Related Documentation

- [Complete Release Workflow](./complete-release-workflow.md) — canonical end-to-end guide
- [Plugin Release Workflow](./plugin-release-workflow.md) — Step 0 version sync
- [Plugin Release (deployment)](../deployment/plugin-release.md) — tag -> CI -> verify
- `.agent/DEVELOPMENT-README.md` — authoritative 6-file bump checklist

---

## Version History

- **2025-10-13**: Created during TASK-04 (version sync fix)
- **2026-06-04**: Rewritten for wp9/TASK-52 — corrected the SSOT (removed the
  phantom `plugins[0].version`), replaced the non-existent README
  status/roadmap/footer lines with the real six bump locations, and rewrote the
  audit script to derive the target from the SSOT and check only locations that
  exist (exits 0 at the current release).
