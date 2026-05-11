# Navigator v6.7.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor Release (Release Workflow Hardening + nav-simplify ROI Design)

---

## Summary

Two items, both deferred from prior markers:

1. **Release workflow hardening** — replaced `softprops/action-gh-release@v2` with native `gh release create`. Closes the last Node.js 20 deprecation warning surfaced during the v6.6.0 release. The release workflow now has zero third-party Node dependencies.
2. **nav-simplify complexity-cost scoring design** — design pass captured as TASK-37. Defines a cost/benefit ROI gate so the simplifier can decline to simplify when the math doesn't favor it. Not yet implemented; weights need real-data calibration before locking in.

---

## Changes

### Release workflow: `gh release create` migration

The v6.6.0 release surfaced a follow-on observation: `softprops/action-gh-release@v2` was still on Node.js 20 (only the `actions/checkout` bump to `@v5` had cleared the deprecation warning). v2 was the latest available for that action, so no further version bump was possible — we needed to replace the action entirely.

v6.7.0 replaces the action with a direct `gh release create` shell call:

```yaml
- name: Create Release
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    TAG: ${{ steps.version.outputs.tag }}
    NOTES_PATH: ${{ steps.check_notes.outputs.path }}
    NOTES_EXISTS: ${{ steps.check_notes.outputs.exists }}
    IS_PRERELEASE: ${{ steps.prerelease.outputs.is_prerelease }}
  run: |
    ARGS=("$TAG" --title "Navigator $TAG")
    if [ "$NOTES_EXISTS" = "true" ]; then
      ARGS+=(--notes-file "$NOTES_PATH" "$NOTES_PATH")
    else
      ARGS+=(--notes "Release $TAG"$'\n\n'"See commit history for changes.")
    fi
    if [ "$IS_PRERELEASE" = "true" ]; then
      ARGS+=(--prerelease)
    fi
    gh release create "${ARGS[@]}"
```

**Why this is better**:

- Uses the runner's pre-installed GitHub CLI (zero Node.js dependency)
- Future Node.js deprecations don't affect this step
- Secrets passed via env (avoids action-input shell injection risk)
- Behavior preserved: title, notes file *or* inline fallback, prerelease flag, release notes uploaded as a downloadable asset

**Note**: v6.7.0 is the first release tested under this new workflow. If `gh release create` syntax has any unanticipated quirks, the release job fails — but the rollback is trivial (revert one file).

### TASK-37: nav-simplify complexity-cost scoring (design only)

The current `nav-simplify` scoring (`code_analyzer.py:197`) uses naïve severity weights — high=3, medium=2, low=1, normalize, done. It tells you a file has issues. It doesn't tell you if fixing them is worth the refactor risk.

This matters most for autonomous runs (`auto_apply: true`). Without ROI gating, the simplifier can produce churn for trivial gains: 30 renames on a stable file, fresh chance for regressions, no real readability improvement.

TASK-37 captures the design for a cost/benefit ROI score:

- **Benefit** = issue density + severity-weighted impact + active-diff signal
- **Cost** = estimated touch lines + file LOC + git recency + import-reference count
- **ROI = B / max(C, 0.5)**, gated by configurable thresholds (`skip_below`, `suggest_below`, `auto_apply_at`)
- Backward compatible: existing `complexity_score` unchanged, new fields added
- Opt-in via `simplification.scoring.mode: "roi"`; default stays `"complexity"`

**Why design-only, not implemented**:

The weight tables (0.4/0.4/0.2 for benefit; 0.3/0.2/0.3/0.2 for cost) are educated guesses. They need calibration on real files in this repo before locking in. The cost signals — especially `import_reference_count` — are language-agnostic heuristics that may produce noise we'd want to evaluate before shipping. Six open questions are flagged in the task doc.

Implementation can pick up next session by tuning weights against real files and confirming the ROI ordering matches the "yeah, I'd touch that one but not that one" gut check.

See [TASK-37](../.agent/tasks/TASK-37-nav-simplify-complexity-cost-scoring.md) for the full design.

---

## Files Modified

```
.github/workflows/release.yml                — softprops action → gh release create
.agent/tasks/TASK-37-...md                   — design doc (new)
.claude-plugin/{plugin,marketplace}.json     — version 6.7.0
.agent/.nav-config.json                      — version 6.7.0
CHANGELOG.md, CLAUDE.md, README.md           — version stamps
releases/RELEASE-NOTES-v6.7.0.md             — these notes
```

---

## Knowledge Graph

No new memories. v6.7.0 is workflow hygiene + a design doc — nothing surprising or non-obvious that warrants persistence yet. TASK-37's weight calibrations will produce memories worth keeping once implemented.

Graph state unchanged: 114 nodes, 25 memories.

---

## Open Items (still deferred)

- **TASK-37 implementation** — design done; needs weight calibration on real files
- **database-migration per-framework template extraction** — bigger refactor; defer until someone runs the skill in anger
- **Social card + Threads posts** for v6.3.0 – v6.7.0 — still none drafted

---

## Upgrade

```
claude plugin update navigator
# restart Claude Code to load updated config
```

No config migration required. The new ROI scoring is opt-in and not yet implemented — current behavior unchanged.
