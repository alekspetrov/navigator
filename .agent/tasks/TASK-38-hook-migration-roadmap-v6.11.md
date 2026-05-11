# TASK-38: Hook-Migration Roadmap — v6.11 (Umbrella)

**Status**: 📐 Design (not yet implemented)
**Created**: 2026-05-11
**Priority**: High
**Builds on**: v6.9.0 (SessionStart hook), v6.10.0 (PreCompact/PostCompact hooks), v6.10.1 (token_monitor rename)
**Architectural pattern**: mem-027 — Three-layer AI tooling architecture (Model / Hooks / Harness)

---

## Summary

Migrate six "model, remember to..." rules from CLAUDE.md prose into deterministic Claude Code hooks. Each rule today depends on model attention (and fails ~10–30% of the time); each candidate maps cleanly to a lifecycle event where it can fire deterministically.

This is the natural follow-on to v6.9.0 + v6.10.0, which together demonstrated that **policy belongs in hooks, judgment stays in the model**. v6.11 applies the pattern to the remaining high-leverage opportunities surfaced by a `navigator-research` agent survey on 2026-05-11.

**Headline outcomes**:
- WORKFLOW CHECK actually enforced (currently skipped ~30% of the time)
- Knowledge graph stays in sync with tasks + corrections without model narration
- Bulk-load anti-pattern guarded against (tail-risk: 50k+ token catastrophe → ~50-token warning)
- First **blocking** hook in the codebase ships, after explicit design decision

---

## Problem Statement

### What's wrong today

Six rules in `CLAUDE.md` and the skills currently read "the model should remember to do X." Each is **deterministic** (objectively true/false at a moment in time) and **frequent** (fires across most sessions), but lives in the model layer where rules are unreliable:

| Rule (current location) | Failure mode |
|---|---|
| "ALWAYS show WORKFLOW CHECK block" (`CLAUDE.md:760`) | Skipped silently when model attention drifts |
| Loop trigger detection (`CLAUDE.md:763`) | Same — model reads prose, sometimes ignores it |
| "Monitor ALL conversations for corrections" (`skills/nav-profile/SKILL.md:192`) | Only fires when model notices; corrections leak |
| "If knowledge graph exists, sync task" (`skills/nav-task/SKILL.md:363`) | Model often forgets after task file write |
| "NEVER wait for explicit commit prompts" (`CLAUDE.md:767`) | Archival skipped after commit |
| "NEVER load all `.agent/` docs at once" (`CLAUDE.md:771`) | Bulk-load anti-pattern crashes sessions occasionally |

Token-economy estimate: net ~1–3k saved per session, but the real value is **correctness over efficiency** — fewer "you forgot to do X" correction cycles.

### Architectural inflection

`workflow_enforcer.py` (Opportunity 1) would be **the first blocking hook** in the codebase. Every shipped Navigator hook so far has exited 0 unconditionally (`nav_session_start.py`, `nav_pre_compact.py`, `nav_post_compact.py`, `token_monitor.py`). Crossing this line deserves an explicit design decision before v6.11 ships.

---

## Design — Six Opportunities

### Opportunity 1: Workflow Enforcer → Hard Block (Phase 2)

| | |
|---|---|
| **Hook event** | `UserPromptSubmit` (already wired) |
| **Effort** | Trivial |
| **File** | `hooks/workflow_enforcer.py:8-9` |
| **Change** | `exit(0)` → `exit(2)` when loop trigger detected AND no `NAVIGATOR_STATUS` block in prior assistant turn |
| **Reads** | `.agent/.nav-workflow-state.json` (written by Opp 2) |
| **Token cost** | ~150 tok/fire (injected WORKFLOW CHECK block) |
| **Token savings** | ~300–500 tok/fire (avoided correction loop) |
| **Risk** | Friction on benign follow-ups inside an active loop session |
| **Mitigation** | Gate on state file (Opp 2). Only block when state file says "no check shown in prior turn." |

**Architectural decision required**: this is the first blocking hook. Document the precedent in `mem-027`.

### Opportunity 2: Stop Hook → Workflow State Writer (Phase 1)

| | |
|---|---|
| **Hook event** | `Stop` (every assistant turn) |
| **Effort** | Trivial (~30 lines) |
| **File** | New: `hooks/nav_workflow_state.py` |
| **Logic** | Read `transcript_path`, grep last assistant message for `WORKFLOW CHECK` sentinel, write `.agent/.nav-workflow-state.json` with `{loop_active, check_shown, iteration, turn_id}` |
| **Token cost** | 0 (silent side-effect) |
| **Risk** | Low — Stop fires every turn, but I/O is local and quick |

Ships **before** Opp 1 so the state file exists before the blocker reads it.

### Opportunity 3: PostToolUse → Auto-Sync Profile Corrections

| | |
|---|---|
| **Hook event** | `PostToolUse`, matcher: `Write\|Edit` |
| **Effort** | Moderate (~60 lines) |
| **File** | New: `hooks/nav_profile_sync.py` |
| **Logic** | If `tool_input.file_path` ends with `.user-profile.json`, diff old vs new corrections array; if grew, run `correction_to_memory.py --action sync` |
| **Token cost** | 0 (silent) |
| **Token savings** | ~200 tok/correction (model no longer narrates sync) |
| **Risk** | Double-sync on non-correction profile writes |
| **Mitigation** | Compare correction count before/after, only run on increase |

### Opportunity 4: PostToolUse → Auto-Sync Task to Graph (Phase 1)

| | |
|---|---|
| **Hook event** | `PostToolUse`, matcher: `Write\|Edit` |
| **Effort** | Trivial (~25 lines) — `task_to_graph.py` exists |
| **File** | New: `hooks/nav_task_graph_sync.py` |
| **Logic** | If `tool_input.file_path` matches `.agent/tasks/TASK-*.md`, run `task_to_graph.py --action upsert --file <path>` |
| **Token cost** | 0 |
| **Token savings** | ~150 tok/task write |
| **Risk** | Duplicate graph nodes if `task_to_graph.py` doesn't support upsert |
| **Open question** | Verify upsert semantics in `task_to_graph.py` before shipping |

**Lowest-risk opportunity. Ship first.**

### Opportunity 5: PostToolUse Bash → Commit Archival Reminder

| | |
|---|---|
| **Hook event** | `PostToolUse`, matcher: `Bash` |
| **Effort** | Moderate (~50 lines) |
| **File** | New: `hooks/nav_commit_reminder.py` |
| **Logic** | Match `git commit` in `tool_input.command`; scan `.agent/tasks/` for `Status: 🚧 In Progress`; if commit message mentions a task ID, emit reminder to stdout |
| **Token cost** | ~80 tok/fire |
| **Token savings** | ~400 tok/fire if archival prompt prevented |
| **Risk** | False positives on dev-cycle commits → annoying noise |
| **Mitigation** | **Gate strictly** on (a) commit message contains "complete/done/finish" OR task ID, AND (b) in-progress task file exists |

Skip without strict gating — costs > savings otherwise.

### Opportunity 6: PreToolUse Read → .agent/ Bulk-Read Guard

| | |
|---|---|
| **Hook event** | `PreToolUse`, matcher: `Read` |
| **Effort** | Moderate (~40 lines) |
| **File** | New: `hooks/nav_read_guard.py` |
| **Logic** | If `tool_input.file_path` starts with `.agent/` and isn't `DEVELOPMENT-README.md` or `.nav-config.json`, increment per-turn counter in `.agent/.nav-read-counter.json`; warn at 3+, suggest agent at 5+ |
| **Token cost** | ~50 tok at threshold (rare) |
| **Token savings** | 50k+ tok in worst-case bulk-load prevention |
| **Risk** | Legitimate sequential loading flagged as bulk |
| **Mitigation** | Per-turn (not per-session) counter resets on `Stop` |

**Highest tail-risk reduction. Ships any session bad enough to need it.**

---

## Phased Ship Order

### Phase 1 — Zero-Risk Foundation (target: v6.11.0)

1. **Opp 4** (task→graph auto-sync). Smallest blast radius, scripts exist, ships first.
2. **Opp 2** (Stop workflow state writer). Silent infrastructure for Opp 1.
3. **Opp 3** (profile correction sync). Same `PostToolUse` Write pattern as #4.

All three are silent side-effects (zero injected tokens). Pure correctness improvements. No architectural decision required.

### Phase 2 — First Blocking Hook (target: v6.11.1 or v6.12.0)

4. **Opp 1** (workflow enforcer hard-block). Requires explicit design decision: are Navigator hooks allowed to block? Document the precedent.

Ship only after Phase 1 has run in production for ~1 week, since Opp 2's state file needs to be reliably written before Opp 1 reads it.

### Phase 3 — Conditional Injectors (target: v6.12.x)

5. **Opp 6** (`.agent/` read guard). Ship after Phase 2 because it injects reminders; users will tolerate this better once the blocking-hook precedent is established.
6. **Opp 5** (commit reminder). Ship last — requires the strictest gating to avoid being annoying noise.

---

## Open Questions (resolve before each phase)

1. **Phase 1**: Does `task_to_graph.py` support `--action upsert`, or does it create duplicate nodes? (Need to inspect; if not, add upsert mode as part of Opp 4.)
2. **Phase 2**: Does `UserPromptSubmit` exit 2 actually block the prompt? (Documented for `PreToolUse`; behavior on `UserPromptSubmit` needs verification.)
3. **Phase 2**: When a hook blocks, does Claude Code surface stderr to the user, stdout, both, or just the exit code?
4. **Phase 3**: Counter persistence — does `PreToolUse` get called once per `Stop` cycle reliably enough for the counter to be useful, or do we need a different reset signal?

---

## Verification (per opportunity)

Each opportunity ships with the same shape of verification (mirrors v6.9.0 / v6.10.0 patterns):

1. **Smoke test**: Run the hook script manually with simulated stdin JSON. Verify expected side-effect (file written, exit code, stdout content).
2. **Integration test**: Install via `settings_merger.py` against `templates/claude-settings-hooks.json`. Restart Claude Code. Trigger the hook event naturally and verify expected behavior.
3. **Failure modes**:
   - Non-Navigator project → hook exits 0, no side-effect
   - Missing files / broken JSON → hook logs to stderr, exits 0
   - Hook disabled in `.nav-config.json` → hook exits early
4. **Token budget check**: Run `/context` before and after a representative session; injected hook context should match estimates in the design table above.

---

## Files to Create / Modify

**New hooks** (one Python file each):
- `hooks/nav_workflow_state.py` (Opp 2)
- `hooks/nav_task_graph_sync.py` (Opp 4)
- `hooks/nav_profile_sync.py` (Opp 3)
- `hooks/nav_read_guard.py` (Opp 6)
- `hooks/nav_commit_reminder.py` (Opp 5)

**Modified hooks**:
- `hooks/workflow_enforcer.py` (Opp 1: change exit code, read state file)

**Templates**:
- `templates/claude-settings-hooks.json` — register new `Stop` + `PreToolUse` entries; add matchers for new `PostToolUse` script lines

**Config**:
- `.agent/.nav-config.json` — add per-hook enabled flags (one section per hook, parallel to existing `compact_hook` / `session_start_hook`)

**Docs**:
- `templates/CLAUDE.md` — add config examples for new hooks
- `.agent/DEVELOPMENT-README.md` — new section per phase as it ships
- `skills/nav-init/SKILL.md` + `skills/nav-upgrade/SKILL.md` — prose updates mentioning the new hooks

**Reuse, do not duplicate**:
- `_safe_read`, `_safe_json`, `_project_root` utilities from `hooks/nav_session_start.py`
- `_flatten_transcript` from `hooks/nav_pre_compact.py` (for hooks that scan transcripts)
- `task_to_graph.py`, `correction_to_memory.py` (existing scripts)
- `settings_merger.py` (no changes needed — handles arbitrary event keys)

---

## Out of Scope (v6.12+)

- **Knowledge graph compact-event memories**: Deferred from v6.10.0. Would write a `compact_event` memory node on every PreCompact for cross-session compact analysis.
- **UserPromptSubmit → graph memory pre-injection**: Greps `graph.json` for memories matching current prompt, injects top 2–3 as additionalContext. Higher complexity (concept matching to stay relevant).
- **`SubagentStop` integration**: Hook fires when subagents finish; could auto-ingest research_findings JSON into graph. Deferred until at least one phase ships.
- **`StopFailure` handling**: Rate-limit events; logging / alerting use case, not enforcement.

---

## Success Criteria

v6.11 is complete when:
- All Phase 1 hooks (Opps 2, 3, 4) ship and silently improve correctness without injected token cost.
- A representative session shows zero "you forgot to sync graph" / "you forgot to capture correction" cycles.
- `task_to_graph.py` upsert verified working (or upsert mode added).
- Design decision on blocking hooks is documented (either via shipping Opp 1 in v6.11.x or deferring to v6.12 with explicit rationale).

v6.12 is complete when:
- Either Opp 1 ships with the state-file gating verified, OR an alternative non-blocking enforcement design is chosen and documented.
- Opps 5 and 6 ship with conditional injection rules calibrated against real-session telemetry.

---

## References

- `mem-027` — Three-layer architecture pattern (the underlying design principle)
- `releases/RELEASE-NOTES-v6.9.0.md` — SessionStart hook (reference implementation)
- `releases/RELEASE-NOTES-v6.10.0.md` — PreCompact/PostCompact hooks (second reference)
- `hooks/nav_session_start.py` — pattern for zero-Read injection hooks
- `hooks/nav_pre_compact.py` — pattern for transcript-scanning hooks
- `skills/nav-init/functions/settings_merger.py` — idempotent settings merging
