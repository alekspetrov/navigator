# Navigator v6.14.0 Release Notes

**Release Date**: 2026-05-12
**Type**: Minor — defensive hook guards + two skill renames

---

## Summary

v6.14.0 lands two changes:

- **Hook hardening** (defensive). Every hook command declared in `.claude-plugin/plugin.json` is now wrapped in `if [ -n "$CLAUDE_PLUGIN_DIR" ]; then ... fi`. When the variable is unset for any reason, hooks fail-open (exit 0) instead of running `python3 /hooks/X.py` and erroring out — which is what `UserPromptSubmit` was doing in projects where Claude Code didn't bind the plugin context, blocking every prompt including `/nav:init` (chicken-and-egg).
- **Skill renames** (breaking, no aliases). `nav-update-claude` → `nav-sync-claude`. `nav-task-mode` → `nav-workflow`. Removes verb collisions surfaced by a skill-catalog audit.

---

## Change A: shell guard around every plugin hook

**Symptom.** Some projects with Navigator installed reported:

```
[python3 "${CLAUDE_PLUGIN_DIR}/hooks/workflow_enforcer.py"]:
can't open file '/hooks/workflow_enforcer.py': No such file or directory
```

This was the same family of failure v6.13.0 set out to fix — but where v6.13.0 fixed the *distribution channel* (declare hooks in the plugin manifest so `${CLAUDE_PLUGIN_DIR}` substitutes), some installs still saw the variable expand to empty. The proximate cause: when a plugin is installed in Claude Code's registry but the active session doesn't fully load its plugin context, the variable is unset even though the manifest's hook entries still fire.

Because `workflow_enforcer.py` runs on every `UserPromptSubmit`, this turned into a hard block: no prompt could be submitted, including `/nav:init` which would have set up the local state needed to recover.

**Fix.** Every hook command is now structurally defensive:

```json
"command": "if [ -n \"$CLAUDE_PLUGIN_DIR\" ]; then python3 \"$CLAUDE_PLUGIN_DIR/hooks/workflow_enforcer.py\"; fi"
```

When the variable is bound — the normal case — hooks run exactly as before. When the variable is unset, the `if` body is skipped and the shell exits 0, so the hook fails open. No behavioral change in healthy installs; eliminates the prompt-blocking failure in the edge case.

All ten hooks across `SessionStart`, `PreCompact`, `PostCompact`, `Stop`, `UserPromptSubmit`, `PreToolUse:Read`, and three `PostToolUse` matchers got the same treatment.

---

## Change B: two skill renames

A skill-catalog audit (29 skills, all read) flagged two pairs where naming was the entire source of confusion — there was no functional overlap, just verb collisions.

### `nav-update-claude` → `nav-sync-claude`

- **`nav-upgrade`** updates the installed plugin binary.
- **`nav-update-claude`** (now `nav-sync-claude`) syncs the project's `CLAUDE.md` against the installed version, preserving customizations.

Both had "update" in the name. `nav-upgrade` orchestrates `nav-sync-claude` as Step 4 of its flow — it's a dependency, not duplication. The rename makes the file-sync role unambiguous.

### `nav-task-mode` → `nav-workflow`

- **`nav-task`** manages `.agent/tasks/` documentation: creates plans, archives completed tasks, updates the task index.
- **`nav-task-mode`** (now `nav-workflow`) is the workflow phase orchestrator (`RESEARCH → PLAN → IMPL → VERIFY → COMPLETE`) that auto-detects complexity and defers to matching skills.

Both had "task" in the name; one managed task docs, the other managed task workflow. Zero functional overlap. The rename makes the orchestration role unambiguous.

### What this affects

- **Skill auto-invocation triggers**: unchanged. The renames don't touch trigger phrases — saying "update my CLAUDE.md" still resolves to the renamed skill via its description.
- **Directory paths**: `skills/nav-update-claude/` → `skills/nav-sync-claude/`, `skills/nav-task-mode/` → `skills/nav-workflow/`.
- **Plugin manifest skills array**: updated to the new paths.
- **Cross-references**: live refs in `nav-upgrade`, `nav-simplify`, `DEVELOPMENT-README.md`, current task docs, SOPs, the knowledge graph, and `mem-011` were all updated. Historical references in `CHANGELOG.md`, prior release notes, and `.agent/tasks/archive/*` were left alone — renaming them would lie about history.
- **Backwards compatibility**: none. Old names stop resolving. Anyone with muscle memory for "nav-task-mode" needs to learn "nav-workflow".

---

## Migration

No action needed for most users. Existing projects continue to work — auto-invocation triggers are unchanged, so natural-language calls keep landing on the right skill.

If you have automation or scripts that reference the old skill names directly:

```bash
# In your code/scripts/docs:
sed -i '' 's/nav-update-claude/nav-sync-claude/g'  $files
sed -i '' 's/nav-task-mode/nav-workflow/g'         $files
```

After updating: `claude plugin marketplace update navigator-marketplace && claude plugin update navigator@navigator-marketplace`.

---

## Why not v6.13.1?

Semver-strictly, the hook guard alone is a patch. The skill renames are breaking (no aliases), which arguably justifies a major bump. Splitting the difference: bundled as a minor because Navigator has loose-semver precedent on similar refactors, and shipping the hook guard urgently was the user-visible priority — separate releases for two file edits would be ceremony.

---

## Commits

```
234b8ec fix(hooks): guard plugin.json hooks against unset CLAUDE_PLUGIN_DIR
14dc4f3 refactor(skills): rename nav-update-claude→nav-sync-claude, nav-task-mode→nav-workflow
1838cde chore: untrack .agent/.marker-log (accidentally added in 14dc4f3)
```
