# Navigator v6.15.5 Release Notes

**Release Date**: 2026-05-26
**Type**: Patch — `## Workflow Discipline` section added to CLAUDE.md, surfaced by the 2026-05-25 Claude Code Insights audit

---

## Summary

Claude Code's internal `Insights` feature was run against the past 6 days of usage (428 messages, 25 sessions, multi-project: Navigator, Pilot, conference companion app). Three recurring friction patterns surfaced that cost real time across sessions:

1. **Premature execution before scoping** — Claude scaffolds when research was wanted; runs sequential rewrites when parallel was warranted.
2. **Investigation drift** — when debugging, Claude wanders into adjacent systems instead of the flagged failure.
3. **Missing context → rework** — wrong year slug, missing design URL, unstated "wins only" constraint supplied after the fact.

The report recommended codifying these as durable workflow guidance. This release adds the corresponding `## Workflow Discipline` section to `CLAUDE.md` — the only Navigator-side change that landed in this scope. Pilot-side artifacts (debug skill, executor-debugging CLAUDE.md section, four pitfall memories) live in the Pilot repo and ship out-of-band.

---

## What changed

### New `## Workflow Discipline` section in CLAUDE.md

Inserted before the existing `## Code Standards` section. Four rules:

- **Research before scaffolding** — For new projects/features, state phase (research / design / decomposition / implementation) in the first message and wait for confirmation before writing code.
- **Parallel for fan-out** — When the task is "apply pattern to N similar files", dispatch N parallel Task agents up front. Do not start sequentially and wait to be corrected. (Proven: workshop restyle = 41% line reduction.)
- **Reframe, don't re-litigate** — When the user corrects with "No X, we are doing Y", drop X entirely from outputs. Do not include the rejected framing in new artifacts.
- **State hypothesis before exploring** — For debugging, name the suspected failure mode and the file/artifact you'll inspect first. If the user pinned a specific failure, do not wander into adjacent systems.

### `.gitignore` adds `.agent/.marker-log`

Navigator's marker-creation log file (created by the marker skill) was unnecessarily showing as untracked in `git status`. Now gitignored alongside the other hook state files (`.nav-workflow-state.json`, `.nav-profile-sync-state.json`, `.nav-read-counter.json`).

---

## Why this shape

Navigator's existing `WORKFLOW CHECK` block (Loop/Task/Direct mode) enforces *mode selection* but does not encode the phase-first / parallel-default / reframe / hypothesis-first rules. The four new rules are complementary, not duplicative — they govern *behavior within a mode* rather than mode choice.

All four rules are derived directly from observed user corrections in the insights report's friction log:

| Rule | Example friction it would have prevented |
|---|---|
| Research before scaffolding | Companion app: Claude began scaffolding after one clarifying question, forcing redirect to research/design |
| Parallel for fan-out | Workshop restyle: Claude started sequential rewrites of parts 2–7 instead of parallel agents |
| Reframe, don't re-litigate | Runbook patch: Claude re-included rejected "base-branch failure" framing despite "wins only" constraint |
| State hypothesis before exploring | Pilot worktree bug: Claude wandered into session dirs and daemon config instead of the flagged failure |

---

## Verification

- All 5 standard version files at `6.15.5`: `marketplace.json`, `plugin.json`, `README.md` badge, `CLAUDE.md` footer, `.agent/.nav-config.json`.
- `CHANGELOG.md` prepended with `v6.15.5` entry pointing at this file.
- `.gitignore` entry added under the existing "Hook state files" group.
- Section ordering in `CLAUDE.md` preserved (Workflow Discipline → Code Standards → Forbidden Actions → …).

This release also smoke-tests the `release.yml` pipeline reworked in commits `bfe3b26` and `25614fc` (per the project memory `project_release_workflow_idempotent_unverified`). Next `v*` tag push validates the publication path on a low-risk patch.

---

## Upgrade notes

No config changes required. No migration. No code-path impact.

Restart Claude Code after upgrade so the patched `CLAUDE.md` is reloaded into context (standard for any Navigator release that touches `CLAUDE.md`).

---

## Files modified

```
CLAUDE.md                                      (## Workflow Discipline section)
.gitignore                                     (.agent/.marker-log)
.claude-plugin/marketplace.json                (version + changelog entry)
.claude-plugin/plugin.json                     (version bump)
README.md                                      (version badge)
.agent/.nav-config.json                        (version)
CHANGELOG.md                                   (new v6.15.5 entry)
releases/RELEASE-NOTES-v6.15.5.md              (new)
```
