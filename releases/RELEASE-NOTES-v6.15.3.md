# Navigator v6.15.3 Release Notes

**Release Date**: 2026-05-18
**Type**: Patch — `workflow_enforcer` deadlock fix

---

## Summary

Recurring user-visible deadlock between two cooperating hooks. `nav_workflow_state.py` (Stop hook) was over-eager about recording "the prior assistant turn skipped its required WORKFLOW CHECK block" and the resulting state made `workflow_enforcer.py` (UserPromptSubmit hook) refuse the next Loop Mode prompt. The recovery paths the block message offered are all manual (different prompt, hand-edit the state file, or disable strict enforcement) — all annoying when the user just wants to keep working.

This release tristates the state field so non-task turns no longer poison the state.

---

## What changed

### Tristate `check_shown`

`hooks/nav_workflow_state.py` previously did:

```python
check_shown = bool(WORKFLOW_CHECK_RE.search(text))
```

Every assistant turn lacking the literal "WORKFLOW CHECK" string was stamped `check_shown=false` — including:

- `AskUserQuestion`-only turns (the assistant asked a clarifying question; no CHECK block was needed)
- Pure-text replies (session-start summaries, short clarifiers like "Acknowledged")

The next user prompt with a Loop Mode trigger (`"run until done"`, `"keep going"`, etc.) then tripped `workflow_enforcer.py:146-150` and exited 2.

**Reproduction in the wild** (gitnation-companion project, 2026-05-18):

1. Assistant asked a resume-or-review clarifier via `AskUserQuestion`.
2. User declined to answer.
3. User typed `"Run until done via loop mode"` — blocked.

**Fix**: `check_shown` is now tristate.

| Prior turn | `check_shown` | Enforcer behavior on loop prompt |
| --- | --- | --- |
| Contained "WORKFLOW CHECK" | `True` | Soft-warn (exit 0) |
| Used a codebase-mutating tool, no CHECK shown | `False` | Block (exit 2) — unchanged |
| Used only `AskUserQuestion` / no tools / read-only tools | `None` | Soft-warn (exit 0) |

Task-action tools that flip `check_shown=False`: `Edit`, `Write`, `MultiEdit`, `NotebookEdit`, `Bash`, `Task`, `Agent`.

The state writer now parses `tool_use` blocks out of the transcript JSONL alongside text, and records a `tools_used` array in the state file for transparency.

`workflow_enforcer.py` is unchanged — it already gates on `check_shown is False`, so `None` falls through to soft-warn cleanly.

---

## Verification

Four-case smoke test through `nav_workflow_state.py`:

| Turn shape | Expected | Observed |
| --- | --- | --- |
| `AskUserQuestion`-only | `null` | `null` ✓ |
| `Edit` without CHECK | `false` | `false` ✓ |
| `Edit` with CHECK | `true` | `true` ✓ |
| Pure-text reply | `null` | `null` ✓ |

End-to-end enforcer test with a Loop Mode trigger:

| State | Exit |
| --- | --- |
| `check_shown=null` | `0` (soft-warn) ✓ |
| `check_shown=false` | `2` (block) ✓ |

Pre-release: `release_validator.py --check-all` → 29/29 skills validated, 5/5 version files at 6.15.3, zero uncommitted/untracked skills.

---

## Upgrade notes

No config changes required. Existing `workflow_enforcer_hook.strict_block=true` continues to enforce on genuine workflow violations.

Restart Claude Code after upgrade so the patched hook script is re-registered (standard for any Navigator release).

**If you were stuck in the deadlock right now**: edit `.agent/.nav-workflow-state.json` and set `last_turn.check_shown` to `null` (or any non-`false` value). One-time unblock; the patched hook keeps it that way.

---

## Files modified

```
hooks/nav_workflow_state.py                (tristate logic + tool_use parsing)
.claude-plugin/plugin.json                 (version bump)
.claude-plugin/marketplace.json            (version + changelog entry)
README.md                                  (version badge)
CLAUDE.md                                  (version)
.agent/.nav-config.json                    (version)
CHANGELOG.md
releases/RELEASE-NOTES-v6.15.3.md          (new)
```
