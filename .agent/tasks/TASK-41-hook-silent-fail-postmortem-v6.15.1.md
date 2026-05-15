# TASK-41: Hook Silent-Fail Postmortem — v6.15.1

**Status**: ✅ Complete — v6.15.1 shipped 2026-05-15
**Type**: Postmortem / bug fix patch
**Created**: 2026-05-15
**Builds on**: v6.13.0 (manifest hook distribution), v6.14.0 (defensive guard)
**Captures**: mem-036 (silent-fail pitfall)

---

## Summary

v6.14.0 wrapped every plugin manifest hook command in `if [ -n "$CLAUDE_PLUGIN_DIR" ]; then ... fi` to prevent `workflow_enforcer.py` from hard-blocking prompts when Claude Code didn't bind `$CLAUDE_PLUGIN_DIR`. The guard solved that — and silently disabled all ten hooks in the same scenario. The Navigator source repo masked the bug via a project-local `.claude/settings.json` hook entry; any other Nav-initialized project relying solely on the plugin manifest got zero injection and zero error signal. Discovered 2026-05-15 during workshop-prep when `gitnation-companion` (no project-local backstop) showed `Messages: 13 tokens` on a fresh Claude Code v2.1.142 session despite plugin and config being correct.

Fix shipped in v6.15.1 as two surgical changes plus this postmortem.

---

## Diagnosis Chain

1. **Initial scope audit**: original plan called out the v6.14.0 guard as "every Navigator user gets degraded session-start." `navigator-research` agent verified and pushed back — only 3 of 10 hook scripts actually use plugin-dir resolution, the others are self-contained. Diagnosis narrowed from "everyone broken" to "guard-failure mode degrades graph stats / profile sync / task graph sync, but not core injection."

2. **Stale marketplace name discovered**: while auditing the 3 plugin-dir-resolving hooks, found their `_resolve_plugin_dir()` fallback tiers hardcoded `jitd-marketplace` — the old marketplace name. The cache lives under `navigator-marketplace`. Tiers 2–3 silently missed on every install; only tier 4 (`Path(__file__).resolve().parent.parent`) saved the script. This was a separate, definitely-live bug independent of the guard.

3. **Picked smallest scope (stale name only)**: shipped as commit `881348d`. Renamed `jitd-marketplace` → `navigator-marketplace` in three scripts. Did NOT strip the guard. Reasoning at the time: guard-failure mode wasn't empirically observed, plan's blast-radius claim seemed overstated, autoupdater was working, conservative.

4. **In-the-wild repro changed the picture**: `gitnation-companion`, a different Nav-initialized project, showed zero SessionStart injection on a fresh Claude Code v2.1.142 session even after Navigator was confirmed up-to-date. Smoke-testing the hook script directly produced valid JSON; the script worked. Initial hypothesis was stale-session — wrong, fresh CC update + fresh session reproduced the silent-fail. Second `navigator-research` agent's differential between navigator source repo (working) and gitnation-companion (broken) found the smoking gun: navigator source has a project-local `.claude/settings.json` with explicit `${CLAUDE_PROJECT_DIR}` hook entries that had been silently carrying the load; gitnation-companion has no `.claude/` at all.

5. **Root-cause fix shipped**: commit `5b3a328` replaced the v6.14.0 guard with shell parameter-expansion fallback in all 10 manifest hook commands:
   ```bash
   python3 "${CLAUDE_PLUGIN_DIR:-$HOME/.claude/plugins/marketplaces/navigator-marketplace}/hooks/X.py"
   ```
   - `$CLAUDE_PLUGIN_DIR` set → same as before.
   - Unset/empty → falls through to flat marketplaces path (contains all 10 hook scripts, maintained by CC for every plugin install).
   - Missing path → python errors to stderr — silent-fail mode eliminated.

6. **No v6.14.0 regression**: end-to-end smoke verified that `workflow_enforcer.py` invoked with `$CLAUDE_PLUGIN_DIR` unset and a non-loop-trigger prompt exits 0 cleanly. The chicken-and-egg fix the guard solved is preserved by the fallback path resolving to a real script.

7. **Released as v6.15.1**: tag `v6.15.1`, commit `2d6e9cf`. CI workflow `release.yml` published cleanly in 6s (also confirming the unverified release-publication migration from `bfe3b26 + 25614fc` works on `v*` tag push).

8. **Verified in the wild**: gitnation-companion fresh session post-update showed `Messages: 1.1k tokens` (was 13). Injection works, no project-local backstop needed.

---

## What Went Wrong

1. **v6.14.0's smoke tests bypassed the manifest layer.** The author tested `python3 hooks/X.py` directly, which doesn't exercise the shell guard. End-to-end manifest tests under unset `$CLAUDE_PLUGIN_DIR` would have surfaced the silent-fail immediately. **Lesson**: smoke tests must exercise the actual manifest command string, not the script body.

2. **The navigator source repo is a poor canary.** It has a project-local `.claude/settings.json` from prior versions (v6.13.0 era) that quietly carried plugin manifest hook coverage. Verification on that repo alone doesn't prove plugin manifest hooks work — it only proves *some* hook source works. **Lesson**: hook changes must be verified in a project without `.claude/settings.json`, which is the canonical "manifest-only" environment.

3. **Initial diagnosis underestimated blast radius.** The first scope decision picked "stale-name only" on the reasoning that the guard-failure was theoretical. The in-the-wild repro flipped that. **Lesson**: when an issue is described as "silent fail in every X," the burden of proof should be "show me it doesn't fail," not "show me it does."

4. **Cascade-rename audit was incomplete.** The `jitd-marketplace` → `navigator-marketplace` rename hit `auto_updater.py` and `claude_updater.py` correctly, but missed three hook scripts and eight SKILL.md doc references. Several releases shipped with stale references silently active in fallback tiers. **Lesson**: marketplace/plugin renames need a project-wide grep audit with sign-off, not best-effort updates.

---

## What Went Right

- **Two-stage agent research** was load-bearing. First agent narrowed the scope (caught the overclaim). Second agent did the differential between working and broken projects (found the project-local backstop). Without both, the fix would have shipped against the wrong root cause.
- **End-to-end smoke tests caught the regression risk.** Before commit, three scenarios were verified: `$CLAUDE_PLUGIN_DIR` set, unset, and `workflow_enforcer` on a benign prompt — directly addressed the v6.14.0 chicken-and-egg fear.
- **Release workflow held up.** v6.15.1 was the first release after `bfe3b26 + 25614fc` moved publication to `release.yml`; the workflow ran clean in 6s and published the release with notes asset. Memory `project_release_workflow_idempotent_unverified.md` can be cleared.
- **Live verification in `gitnation-companion`** closed the loop: `Messages: 13 → 1.1k tokens` post-update. Concrete proof the fix works without requiring `nav-init` in the affected project.

---

## Commits

```
2d6e9cf chore(release): bump version to 6.15.1
5b3a328 fix(hooks): replace CLAUDE_PLUGIN_DIR guard with fallback path expansion
881348d fix(hooks): correct stale jitd-marketplace path in plugin-dir fallback
```

Plus follow-up doc sweep (this task):
- 8 stale `jitd-marketplace` refs in `skills/nav-start/SKILL.md`, `skills/nav-init/SKILL.md`, `skills/nav-upgrade/SKILL.md` corrected to `navigator-marketplace`.

---

## Open Follow-Ups

1. **`skills/nav-sync-claude/skill.md` lowercase filename** — surfaced by `release_validator.py --verify-tag v6.15.1` as a false-positive "missing skill." Pre-existing since the v6.14.0 rename from `nav-update-claude`. Convention is `SKILL.md` (uppercase). Functional but inconsistent. Pure file rename, defer to next patch.

2. **`nav-release` smoke-test gap** — `release_validator.py --check-all` doesn't exercise hook commands. Add a `--verify-hooks` mode that runs each plugin manifest hook command under `env -u CLAUDE_PLUGIN_DIR bash -c "$CMD"` and asserts at least one of (stdout non-empty, exit code != 0). Would have caught the v6.14.0 silent-fail at pre-release time.

3. **`gitnation-companion` config schema drift** — `.agent/.nav-config.json` there is missing keys a fresh v6.15.x `nav-init` produces (`loop_mode`, `task_mode`, `knowledge_graph`, `tom_features`, `simplification`). Plus `.agent/grafana/` is non-standard for `nav-init`. None of this blocked v6.15.1 injection (smaller payload than navigator source repo, but functional). If richer injection desired there, run `nav-sync-claude` once it's pointed at the right schema.

---

## Related

- mem-036 — Pitfall: plugin manifest hooks that depend on `$CLAUDE_PLUGIN_DIR` fail silently when the variable is unset
- mem-035 — Pitfall: `PreToolUse` stdout / `additionalContext` silent (same class of lesson: harness behaviors must be end-to-end verified)
- TASK-38 — hook migration roadmap (moved hooks to plugin manifest in v6.13.0)
- TASK-40 — Phase 3 hook migration v6.12.x
- releases/RELEASE-NOTES-v6.15.1.md — full release notes
- releases/RELEASE-NOTES-v6.14.0.md — the guard introduction this patch corrects
- releases/RELEASE-NOTES-v6.13.0.md — the architectural change that exposed `$CLAUDE_PLUGIN_DIR` binding fragility
