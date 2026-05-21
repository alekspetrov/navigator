# Navigator v6.15.4 Release Notes

**Release Date**: 2026-05-21
**Type**: Patch — nav-task template upgrade (Pilot-compatible by default)

---

## Summary

The canonical nav-task template had drifted away from how task docs are actually written in this repo (and in downstream projects). Active task docs (TASK-37, TASK-40, TASK-example) had organically converged on `## Acceptance Criteria / ## Out of Scope / ## References` — the canonical template still emitted `## Implementation Plan / ## Success Metrics / ## Testing Plan / ## Done`. The skill was documenting one shape and producing another.

The drifted shape happens to match Pilot's GitHub spec validator regex. This release codifies the drift — adopting the better shape standardizes Nav's own surface and makes `gh issue create --body-file .agent/tasks/TASK-XX.md` pass Pilot's structural check without any flag or sidecar skill.

---

## What changed

### New canonical template (both writers)

```
## Context
## Acceptance Criteria   ← new (- [ ] checkable outcomes)
## Implementation         ← renamed from "Implementation Plan"
## Out of Scope           ← new (explicit non-goals)
## Technical Decisions    ← kept (SKILL.md only; task_to_graph.py parses it)
## Verify                 ← kept verbatim
## Done                   ← kept verbatim
## Refs                   ← new (replaces ad-hoc trailing "Source:" patterns)
## Related Tasks          ← kept
## Notes                  ← kept
```

Dropped: `## Success Metrics` and `## Testing Plan` (folded into Acceptance Criteria), `## Dependencies` and `## Completion Checklist` (no parsers, redundant with Done/Refs).

### Two writers updated in lockstep

- `skills/nav-task/functions/task_formatter.py` — the Python writer used via `--title/--id` CLI
- `skills/nav-task/SKILL.md` Step 3A create template — the LLM-instruction template Claude follows for natural-language invocation
- `skills/nav-task/SKILL.md` "Task Document Template Structure" summary block updated to match

The two templates had been drifting from each other since v6.5.x — the archive template at SKILL.md:193 already said `## Implementation`, while the create template at SKILL.md:81 still said `## Implementation Plan`. This release closes that latent inconsistency.

---

## Why this shape

`## Acceptance Criteria` (with `- [ ]` items) + `## Out of Scope` + `## Refs` are engineering hygiene that benefits every task doc — not Pilot-specific bending. The fact that Pilot's structural validator (`pilot/internal/adapters/github/spec_validator.go:22`, regex `^##\s+(Acceptance|Implementation|Context|Background|Approach|Design|Refs)\b`) accepts these headings is a happy alignment, not the cause. Pilot users get a usable issue body from `gh issue create --body-file .agent/tasks/TASK-XX.md`; non-Pilot users get a better-structured task doc with explicit acceptance + explicit non-goals.

The regex's trailing `\b` (word boundary) matters: `## Acceptance Criteria` matches the `Acceptance` alternative cleanly, so Nav's preferred heading works without any Pilot-side regex change.

No "pilot" label is required for polling. Pilot's poller uses a deployment-configurable label, not a hardcoded constant (`internal/adapters/github/poller.go`). The `pilot-*` labels in `types.go:95-111` are all *outputs* applied by Pilot (`pilot-in-progress`, `pilot-done`, `pilot-spec-incomplete`, etc.), plus one opt-out (`pilot-skip-spec-check`).

---

## Audit before the rename

Before touching either writer, every parser of task-doc headings was traced:

| Consumer | Heading dependency | Risk |
| --- | --- | --- |
| `hooks/nav_task_graph_sync.py` | None (matches by filename) | Safe |
| `skills/nav-graph/functions/task_to_graph.py` | `## Technical Decisions` only (full-text scan otherwise) | Kept |
| `skills/nav-task/functions/verify_extractor.py:34,69` | `## Verify` + `## Done` hardcoded regex literals | Preserved verbatim |
| `skills/product-design/functions/implementation_planner.py` | Independent writer with its own headings | Out of scope — different doc type |

Renaming `## Verify` or `## Done` would silently return empty results (regex miss, no error). Both preserved.

Existing `.agent/tasks/*.md` docs in user projects are unaffected — old docs remain fully readable; only new task docs (generated post-upgrade) use the new shape.

---

## Verification

Generated a fresh task doc via the new `task_formatter.py` template (`TASK-99 "Test task"`) and round-tripped through `verify_extractor.py`:

```
Verify Commands:
  $ [test command for this feature]
  $ [type check command]
  $ [build command]

Done Criteria:
  [ ] [Specific file/API exists and exports expected interface]
  [ ] [Tests pass - specify count or coverage target]
  [ ] [Build succeeds without errors]
  [ ] [User-observable behavior works as specified]

Status: 0/4 (0%)
```

Heading audit on generated output:

```
## Context
## Acceptance Criteria
## Implementation
## Out of Scope
## Verify
## Done
## Refs
## Related Tasks
## Notes
```

Four headings (Context, Acceptance, Implementation, Refs) satisfy Pilot's structural regex — passes by wide margin.

Pre-release: `release_validator.py --check-all` → 29/29 skills validated, 5/5 version files at 6.15.4, zero uncommitted skills. `--verify-hooks` → 20/20 hook smoke-tests passed across `set` and `unset` `CLAUDE_PLUGIN_DIR`.

---

## Upgrade notes

No config changes required. No migration needed for existing task docs — they continue to parse and render the same way.

Restart Claude Code after upgrade so the patched skill templates are re-registered (standard for any Navigator release).

To queue a Nav task doc to a Pilot deployment:

```bash
gh issue create --body-file .agent/tasks/TASK-XX-slug.md --title "TASK-XX: ..."
```

The structural check passes without a flag. Apply your deployment's polling label per your Pilot configuration.

---

## Files modified

```
skills/nav-task/functions/task_formatter.py   (template superset)
skills/nav-task/SKILL.md                      (Step 3A + summary block)
.claude-plugin/plugin.json                    (version bump)
.claude-plugin/marketplace.json               (version + changelog entry)
README.md                                     (version badge)
CLAUDE.md                                     (version)
.agent/.nav-config.json                       (version)
CHANGELOG.md
releases/RELEASE-NOTES-v6.15.4.md             (new)
```
