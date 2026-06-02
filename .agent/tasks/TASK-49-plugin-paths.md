# TASK-49: Plugin-relative path resolution (skills + hooks work outside the source repo)

**Status**: 📋 Planned
**Created**: 2026-06-02
**Work-package**: `wp3-plugin-paths`
**Phase**: 4 — Independent tracks (parallel)
**Priority**: Medium
**Effort**: L — ~16 files. The two hook edits are S each (one is a one-token change; workflow_enforcer needs a ~15-line stdin-refactor since get_user_message reads stdin destructively). The skill edits are mechanical but voluminous: 41 bare `python3 skills/` lines across 12 files plus 4 bare `scripts/` files, each needing a resolver block prepended per code block. Audit under-counted ("9 skills"); actual is 12+4. Verification (running helpers from a non-repo cwd with the backstop bypassed) is the real time sink, pushing this to a low-end L rather than M.
**Risk**: med — workflow_enforcer.py is the only BLOCKING hook (UserPromptSubmit exit 2); its stdin-read refactor must preserve the never-block-on-missing-state invariant. SKILL.md edits ship in the published plugin manifest. No graph-data mutation risk (only executable paths change, not data args). The $HOME/.claude/plugins fallback chain must be verified since CLAUDE_PLUGIN_DIR availability in skill Bash is uncertain.
**Depends on**: none
**Recommendation**: `fix+test`
**Source**: audit `wf_0dc1b9ce-7d8` → plan `wf_187896bb-5af`; roadmap in TASK-42

---

## Summary

Make every Navigator skill helper invocation and hook config/state read resolve from the installed plugin/project location so knowledge-graph, stats, version-check, and workflow-enforcement features stop silently no-opping in real (non-source-repo) installs.

## Findings Addressed

- medium: nav_session_start.py:60 reads CLAUDE_PROJECT_ROOT while all 7 other hooks read CLAUDE_PROJECT_DIR
- low: workflow_enforcer.py:96,112 use cwd-relative paths for config and state, disagreeing with the absolute path written by nav_workflow_state.py:217
- medium: knowledge-graph helper paths are bare 'python3 skills/nav-graph/functions/...' in 12 SKILL.md files (41 invocation lines) and fail outside the source repo
- medium: nav-stats and nav-start invoke 'scripts/...' via bare cwd-relative paths (session-stats, check-version dead outside source repo); nav-install-multi-claude has the same bare 'scripts/install-multi-claude.sh' pattern

**Already resolved in v6.15.6** (excluded from this work):
- ~~CRITICAL deleted nav_commit_reminder.py hook still registered in plugin.json — removed in v6.15.6 (not part of this WP)~~

## Implementation

Three independent sub-fixes, all grounding on the resolution pattern already proven in nav-upgrade/SKILL.md:340-342 (`PLUGIN_DIR="${CLAUDE_PLUGIN_DIR:-$HOME/.claude/plugins/cache/navigator-marketplace/navigator}"` with a `$HOME/.claude/plugins/marketplaces/navigator-marketplace` second fallback) and the hook helper `_resolve_plugin_dir()` in nav_session_start.py:234-250.

(1) Hook env-var consistency (S): In hooks/nav_session_start.py:60 change `CLAUDE_PROJECT_ROOT` to `CLAUDE_PROJECT_DIR` to match the identical `_project_root` helpers in the 7 other hooks (nav_read_guard.py:78, nav_workflow_state.py:74, nav_profile_sync.py:52, nav_post_compact.py:47, nav_task_graph_sync.py:56, nav_pre_compact.py:56). Latent-only today because stdin `cwd` is preferred first, but it is the documented variable and the only env fallback.

(2) workflow_enforcer path agreement (S/M): hooks/workflow_enforcer.py:96 (`Path(".agent/.nav-config.json")`) and :112 (`Path(".agent/.nav-workflow-state.json")`) are cwd-relative, but the writer nav_workflow_state.py:217 writes `root/.agent/.nav-workflow-state.json` (absolute, derived from stdin cwd). Add a `_project_root(stdin_data)` helper mirroring the other hooks, then build both `config_path` and `state_path` under that root. Complication: `get_user_message()` (line 72) destructively does `sys.stdin.read()` and only extracts `prompt`. Refactor it to parse the stdin JSON once into a dict, return both the message and the parsed payload (or stash it), so `cwd` survives for root derivation. Keep the empty-dict-on-missing-state behavior (the "no signal, never block" contract at line 108-119) intact.

(3) Skill helper path resolution (M): In the 12 SKILL.md files with bare `python3 skills/nav-graph/functions/...` and the 4 with bare `scripts/...`, prepend a one-line resolver and rewrite invocations to `"$PLUGIN_DIR/skills/nav-graph/functions/X.py"` / `"$PLUGIN_DIR/scripts/X.sh"`. DO NOT use `$SKILL_BASE_DIR` as the audit rec suggests — the repo's own mem-018 / graph.json:1505 records that `$SKILL_BASE_DIR` is NOT a Claude Code built-in and is unset, which is exactly why v6.4.0 reverted nav-simplify away from it. Standardize on `${CLAUDE_PLUGIN_DIR:-...cache.../navigator}` with the marketplace fallback. The data-path args (`--graph-path .agent/knowledge/graph.json`, `--agent-dir .agent`) stay project-relative — only the helper executable path changes. While here, fix the inconsistent existing nav-start fallbacks (SKILL.md:90/217/354/548 point at `.../marketplaces/.../skills/nav-start` but :249 points at `.../cache/.../navigator`) to the single canonical form.

All three are doc/script-string edits plus one ~15-line Python helper; no helper .py logic changes. The source repo's `.claude/settings.json` backstop (present, per ls) is what has been masking these in dev — same masking that hid the v6.14.0 bug for two releases (nav-release/SKILL.md:83), so verification must explicitly run with CLAUDE_PLUGIN_DIR unset / from a temp non-repo cwd.

### Files

| File | Change |
| --- | --- |
| `hooks/nav_session_start.py` | Line 60: CLAUDE_PROJECT_ROOT -> CLAUDE_PROJECT_DIR for parity with the 7 other hooks. |
| `hooks/workflow_enforcer.py` | Add _project_root(stdin_data) helper; refactor get_user_message to retain parsed stdin (cwd); build config_path (line 96) and state_path (line 112) under that absolute root. |
| `skills/nav-graph/SKILL.md` | 17 invocation lines: prepend ${CLAUDE_PLUGIN_DIR}-based PLUGIN_DIR resolver; rewrite python skills/nav-graph/functions/*.py -> "$PLUGIN_DIR/skills/nav-graph/functions/*.py". |
| `skills/backend-endpoint/SKILL.md` | Lines 37,358: nav-graph helper paths -> $PLUGIN_DIR-resolved. |
| `skills/backend-test/SKILL.md` | Lines 30,147: nav-graph helper paths -> $PLUGIN_DIR-resolved. |
| `skills/frontend-component/SKILL.md` | Lines 37,353: nav-graph helper paths -> $PLUGIN_DIR-resolved. |
| `skills/frontend-test/SKILL.md` | Lines 28,32,144: nav-graph helper paths -> $PLUGIN_DIR-resolved. |
| `skills/database-migration/SKILL.md` | Lines 43,356: nav-graph helper paths -> $PLUGIN_DIR-resolved. |
| `skills/nav-profile/SKILL.md` | Line 249: correction_to_memory.py path -> $PLUGIN_DIR-resolved. |
| `skills/nav-marker/SKILL.md` | Line 198: graph_manager.py stats path -> $PLUGIN_DIR-resolved. |
| `skills/nav-task/SKILL.md` | Line 370: task_to_graph.py path -> $PLUGIN_DIR-resolved. |
| `skills/nav-simplify/SKILL.md` | 1 bare skills/ invocation -> $PLUGIN_DIR-resolved (note mem-018: do NOT reintroduce $SKILL_BASE_DIR). |
| `skills/nav-onboard/SKILL.md` | 6 bare skills/ invocation lines -> $PLUGIN_DIR-resolved. |
| `skills/nav-stats/SKILL.md` | Lines 46,53,72 (scripts/session-stats.sh) and line 75 (efficiency_scorer.py) -> $PLUGIN_DIR-resolved. |
| `skills/nav-start/SKILL.md` | Lines 68-69 (scripts/check-version.sh) -> $PLUGIN_DIR-resolved; unify the 5 existing SKILL_BASE_DIR fallbacks (90/217/249/354/548) to the single canonical CLAUDE_PLUGIN_DIR form. |
| `skills/nav-install-multi-claude/SKILL.md` | Line 150 (scripts/install-multi-claude.sh) -> $PLUGIN_DIR-resolved. |

## Acceptance Criteria

- [ ] grep for `python3 skills/` / `python skills/` across skills/*/SKILL.md returns zero bare (non-$PLUGIN_DIR/$CLAUDE_PLUGIN_DIR-prefixed) matches.
- [ ] grep for `bash scripts/` / `-f "scripts/` across skills/*/SKILL.md returns zero bare matches.
- [ ] No SKILL.md introduces or retains `$SKILL_BASE_DIR` as a helper-path base (consistent with mem-018 / v6.4.0 revert).
- [ ] hooks/nav_session_start.py uses CLAUDE_PROJECT_DIR; grep for CLAUDE_PROJECT_ROOT in hooks/ returns nothing.
- [ ] workflow_enforcer.py resolves config_path and state_path under the same absolute root that nav_workflow_state.py writes to; a unit/integration test pipes stdin {prompt, cwd:<tmpdir>} with a state file under <tmpdir>/.agent and asserts the enforcer reads it (and still returns no-block when the file is absent).
- [ ] Manual/scripted run: from a temp cwd that is NOT the source repo and with CLAUDE_PLUGIN_DIR unset, invoke a nav-graph helper line and scripts/session-stats.sh as rewritten and confirm they resolve and execute (current behavior: silent no-op).
- [ ] Existing hook tests (wp4) still pass; workflow_enforcer block/no-block behavior unchanged for the cwd==root case.

## Technical Decisions

- **Recommendation**: `fix+test`. workflow_enforcer.py is the only BLOCKING hook (UserPromptSubmit exit 2); its stdin-read refactor must preserve the never-block-on-missing-state invariant. SKILL.md edits ship in the published plugin manifest. No graph-data mutation risk (only executable paths change, not data args). The $HOME/.claude/plugins fallback chain must be verified since CLAUDE_PLUGIN_DIR availability in skill Bash is uncertain.

## Out of Scope

- Findings outside this work-package's listed scope (see TASK-42 roadmap for the full map).

## Refs

- TASK-42 — Audit Remediation Roadmap (umbrella)

## Verify

```bash
# See Acceptance Criteria; run the relevant tests/validators before marking done.
```

## Done

- [ ] All acceptance criteria checked
- [ ] Tests pass in CI (once TASK-43 gate exists)
- [ ] Committed + roadmap (TASK-42) status updated
