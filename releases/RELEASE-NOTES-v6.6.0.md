# Navigator v6.6.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor Release (Release Hygiene + Loop Mode Flexibility)

---

## Summary

A compact pass clearing three deferred items from prior release markers:

1. **GitHub Actions Node.js 24 readiness** — ahead of GitHub's June 2026 deprecation deadline
2. **Loop Mode `periodic_interval`** — `iteration_approval: "periodic"` was hardcoded to every 3rd iteration; now configurable
3. **Branch-per-run convention** documented in `nav-multi` — prevents commit interleaving when running parallel workflows

No new features. No new bugs surfaced. Pure maintenance.

---

## Changes

### GitHub Actions: Node.js 24 ready

- `actions/checkout@v4` → **`actions/checkout@v5`**
- `softprops/action-gh-release@v1` → **`softprops/action-gh-release@v2`**

Both v1/v4 actions were running on the deprecated Node.js 20 runtime. v2/v5 are Node.js 24 ready. GitHub's hard deadline is **September 16, 2026** (forced upgrade June 2, 2026). v6.6.0 closes this ahead of time.

### Loop Mode `periodic_interval`

The `iteration_approval: "periodic"` setting (v6.3.0) used to prompt every 3rd iteration with the cadence hardcoded. v6.6.0 adds `loop_mode.periodic_interval` (default `3`) to control the cadence.

**Use cases**:
- Overnight runs: set higher (`5`, `10`) for less frequent check-ins
- Risky work: set lower (`2`) for more oversight
- Default behavior unchanged: `3` matches prior fixed cadence

**Config**:
```json
{
  "loop_mode": {
    "iteration_approval": "periodic",
    "periodic_interval": 5
  }
}
```

### nav-multi branch-per-run convention (Step 5.5)

`skills/nav-multi/SKILL.md` gained an explicit step documenting the recommended pattern:

```bash
BRANCH="nav-multi/${SESSION_ID}"
git checkout -b "$BRANCH"
```

**Why**: parallel multi-agent runs that commit to the same branch produce interleaved history that's nearly impossible to bisect or review. A per-run branch isolates each workflow's commits, enables clean PR review, and supports `git branch -D` for failed-workflow rollback.

The convention pairs with v6.4.0's `SESSION_ID` PID disambiguation: each run gets a unique session ID, which produces a unique branch.

---

## Files Modified

```
.github/workflows/release.yml                — checkout@v5, action-gh-release@v2
skills/nav-loop/SKILL.md                     — periodic_interval documentation
skills/nav-multi/SKILL.md                    — Step 5.5 branch-per-run convention
.agent/.nav-config.json                      — periodic_interval: 3 default
.claude-plugin/{plugin,marketplace}.json     — version 6.6.0
CHANGELOG.md, CLAUDE.md, README.md           — version stamps
releases/RELEASE-NOTES-v6.6.0.md             — these notes
```

---

## Knowledge Graph

No new memories. v6.6.0 is hygiene work — nothing surprising or non-obvious worth persisting.

Graph state unchanged: 114 nodes, 25 memories.

---

## Open Items (still deferred)

- **nav-simplify complexity-cost scoring** — design pass needed; warrants its own release
- **database-migration per-framework template extraction** — bigger refactor; can wait until someone runs the skill in anger
- **Social card + Threads posts** for v6.3.0/v6.4.0/v6.5.0/v6.6.0 — still none drafted

---

## Upgrade

```
claude plugin update navigator
# restart Claude Code to load updated skills
```

No config migration required. If you want to tune `periodic_interval`, add it to `.agent/.nav-config.json`:

```json
{ "loop_mode": { "periodic_interval": 5 } }
```
