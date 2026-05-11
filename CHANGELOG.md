# Changelog

All notable changes to Navigator are recorded here. Detailed per-version notes live in [`releases/`](./releases/); each link below points to the full file. Versions without a release notes file have only summary lines.

This project follows [Semantic Versioning](https://semver.org/). The authoritative source of truth for versions is [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json) — see [`sops/development/version-management.md`](./.agent/sops/development/version-management.md).

---

## [v6.10.2] — 2026-05-11

**Auto-updater fix — SessionStart auto-update now actually works.** The `"Auto-update failed. Run nav-upgrade manually."` banner shown at the top of every session was the result of three stacked bugs in `skills/nav-start/functions/auto_updater.py`. (1) The plugin was being referenced by its unqualified name `navigator` — Claude Code requires the qualified form `navigator@navigator-marketplace` and rejects the bare name. (2) Even with the qualified name, `claude plugin update` reported "already at latest" because the local marketplace cache was stale; Claude Code does not auto-refresh it before update. A new `refresh_marketplace()` helper now runs `claude plugin marketplace update navigator-marketplace` first. (3) `get_current_version` parsed `claude plugin list` expecting the version on the same line as the plugin name, but the actual output puts `Version: X.Y.Z` on a separate indented line — so the regex always missed and the auto-updater short-circuited with "Could not detect current Navigator version" before the version comparison ever ran. Parser now scans forward from the plugin entry header. End-to-end verified: auto-updater reports accurate `current_version` and either `up-to-date` or `updated` correctly.

→ [Full release notes](./releases/RELEASE-NOTES-v6.10.2.md)

## [v6.10.1] — 2026-05-11

**Bug fixes for code generators + hook filename.** Four fixes surfaced by a full workshop-prep audit. `frontend-component` template no longer leaves a bare interface identifier in generated TSX — `${PROPS_INTERFACE}` placeholder split into `${PROPS_INTERFACE_BLOCK}` (full body, with a sensible default) and `${PROPS_INTERFACE}` (name only for the `React.FC<>` type ref). `backend-endpoint` template no longer leaks an unevaluated JS ternary into generated Express routes — `${MIDDLEWARE_CHAIN ? MIDDLEWARE_CHAIN + ',' : ''}` replaced with a `${MIDDLEWARE_BLOCK}` that the generator pre-computes as either a clean middleware line or an empty string. `hooks/monitor-tokens.py` renamed to `hooks/token_monitor.py` so the filename matches both the in-tree settings template and the rest of the hook directory (`workflow_enforcer.py`, `nav_session_start.py`, `nav_pre_compact.py`, `nav_post_compact.py`) — previously, fresh installs configured Claude Code to call a file that didn't exist and token monitoring silently never ran. `nav-loop` `test_exit_gate.test_empty_dict` assertion synced with `TOTAL_INDICATORS=6` (was stale at 5). No new features, no behavior changes for working flows.

→ [Full release notes](./releases/RELEASE-NOTES-v6.10.1.md)

## [v6.10.0] — 2026-05-11

**PreCompact + PostCompact hooks — compact-resilient markers.** Pairs with v6.9.0 SessionStart to close the session-lifecycle loop. Navigator state now survives every compact, including silent auto-compacts that users previously didn't even notice happening. New `hooks/nav_pre_compact.py` fires on every manual `/compact` or auto-compact: reads the JSONL transcript, runs the same heuristic summarizer as `marker_compressor.py`, captures git state + active tasks, writes `.agent/.context-markers/before-compact-{manual,auto}-{ts}.md` and sets `.active`. The trigger token in the filename makes silent auto-compacts visible. New `hooks/nav_post_compact.py` appends Claude Code's official `compact_summary` to the same marker after compact completes, so restores get both heuristic and authoritative summaries. `nav-compact` skill Step 0 detects the hook and skips manual marker creation when installed (single source of truth). Opt-out via `compact_hook.enabled: false`; legacy projects fall back to manual nav-compact flow automatically.

→ [Full release notes](./releases/RELEASE-NOTES-v6.10.0.md)

## [v6.9.0] — 2026-05-11

**SessionStart hook for zero-Read context injection.** Claude Code's `SessionStart` hook now pre-loads Navigator state (navigator + active marker + config + graph stats + user profile + open tasks + auto-update) into the model's context window via `additionalContext` — before the first user turn. The `nav-start` skill detects a sentinel and skips its 6 file reads, eliminating ~35k tokens per session start in local measurement (73.3k → 37.8k). New `hooks/nav_session_start.py` builds the parity payload (9500-char cap, source-aware: `--resume` hoists marker first); new `skills/nav-init/functions/settings_merger.py` provides idempotent `.claude/settings.json` merging that preserves user-defined hooks. Templates fix `${CLAUDE_PROJECT_ROOT}` (non-existent) → `${CLAUDE_PROJECT_DIR}` (actual Claude Code env var). Opt-out via `session_start_hook.enabled: false`; legacy projects fall back to the Read-based path automatically.

→ [Full release notes](./releases/RELEASE-NOTES-v6.9.0.md)

## [v6.8.0] — 2026-05-11

**nav-simplify ROI scoring shipped.** TASK-37 implementation: cost/benefit ROI gate so the simplifier can decline to simplify when the math doesn't favor it. New `cost_analyzer.py` adds four cost signals (touch lines, file LOC, git recency, import references); benefit composed of issue density + severity impact + active-diff signal. Three-tier gate (`skip` / `suggest` / `apply`) with configurable thresholds. Opt-in via `simplification.scoring.mode: "roi"` — default stays `"complexity"` for backward compat. 20 unit tests cover scoring math and gate logic. Calibrated on this repo's actual files; ROI ordering matches intuition (active-diff messy files prioritize; stable clean files de-prioritize).

→ [Full release notes](./releases/RELEASE-NOTES-v6.8.0.md)

## [v6.7.0] — 2026-05-11

**Release workflow hardening + nav-simplify ROI design.** Replaced `softprops/action-gh-release@v2` with native `gh release create` — closes the last Node.js 20 deprecation warning by removing the third-party Node action entirely (uses the runner's pre-installed GitHub CLI). Design pass for `nav-simplify` complexity-cost scoring captured in TASK-37: cost/benefit ROI gate so the simplifier can decline to simplify when the math doesn't favor it (opt-in via `simplification.scoring.mode`; weights need real-data calibration before implementation).

→ [Full release notes](./releases/RELEASE-NOTES-v6.7.0.md)

## [v6.6.0] — 2026-05-11

**Release hygiene + Loop Mode flexibility.** Compact maintenance pass: GitHub Actions bumped to Node.js 24-ready versions (`checkout@v5`, `action-gh-release@v2`) ahead of June 2026 deprecation; `loop_mode.periodic_interval` (default 3) parameterizes the previously-hardcoded `iteration_approval: "periodic"` cadence for tunable overnight runs; `nav-multi` documents branch-per-run convention (`nav-multi/{SESSION_ID}`) for parallel workflow safety.

→ [Full release notes](./releases/RELEASE-NOTES-v6.6.0.md)

## [v6.5.0] — 2026-05-11

**Execution-layer parity completion.** v6.4.0 fixed the bugs; v6.5.0 closes the parity gaps with the research agent. New `execution_to_graph.py` mirrors `research_to_graph.py`. All 5 code-writing skills (frontend-component, backend-endpoint, database-migration, backend-test, frontend-test) emit `execution_summary` JSON for ingestion. Phase 0 (graph check) added as Step 0 on the three primary code-writing skills. `code_analyzer.py` auto-detects indent unit (fixes 4-space false positives). `backend-test` / `frontend-test` expanded from 38-line stubs to working skills with the same Phase 0 → generate → verify → summary pattern.

→ [Full release notes](./releases/RELEASE-NOTES-v6.5.0.md)

## [v6.4.0] — 2026-05-11

**Execution-layer parity pass.** Self-audit of the execution layer (skills that write code + orchestration that wraps them) using v6.3.0's sharpened `navigator-research` agent surfaced 10 concrete bugs and gaps. All fixed: `workflow_enforcer.py` hook wired (was dead code), test skill triggers route correctly, `nav-simplify` no longer silently pauses autonomous flows, Loop Mode thresholds aligned via shared constants, `stagnation_detector` gains `--autonomous` mode, `nav-multi` SESSION_ID collision fixed, 12 execution-layer concept aliases added to the graph, `$SKILL_BASE_DIR` removed.

→ [Full release notes](./releases/RELEASE-NOTES-v6.4.0.md)

## [v6.3.0] — 2026-05-11

**Structured research output + autonomous Loop Mode.** `navigator-research` agent emits a `research_findings` JSON block that `research_to_graph.py` ingests into the knowledge graph — research persists across sessions. Loop Mode gains `iteration_approval`, `never_pause_on_stagnation`, and `stagnation_diversify_strategy` for overnight runs (inspired by karpathy/autoresearch's NEVER STOP directive). New ANTI-PATTERN #9: Context Flooding from Command Output. Four nav-graph reliability fixes (memory ID collision, file backing, concept aliases, batch I/O).

→ [Full release notes](./releases/RELEASE-NOTES-v6.3.0.md)

## [v6.2.2] — 2026-02-13

Portable `timeout` in `tests/test-monitor.sh` for macOS (GNU timeout → gtimeout → background-process fallback).

## [v6.2.1] — 2026-02-12

Release packaging bump.

## [v6.1.0] — 2026-01-23

**Multi-Agent Production.** Parallel Claude agents with visual dashboard. Natural language trigger ("Run multi-agent workflow for TASK-XX"). 5 role templates (orchestrator, implementer, tester, reviewer, documenter) with minimal context (~5k each). Real-time terminal dashboard. 3x faster than sequential. Reliability fixes for research tasks.

## [v6.0.0] — 2026-01-23

**Project Knowledge Graph.** Unified search across tasks, SOPs, system docs, and experiential memories. Patterns, pitfalls, decisions, and learnings persist across sessions. Query via "What do we know about X?". Auto-surfaces relevant memories on session start.

## [v5.9.0]

**Workflow Enforcement.** Mandatory WORKFLOW CHECK block before task responses. Loop Mode and Task Mode triggers auto-detected. Complexity scoring. Hook-based enforcement available.

## [v5.8.0]

**Auto-Update Project Sync.** Auto-update syncs project config after plugin update. Version drift detection. Restart prompt after mid-session updates.

## [v5.7.0] — 2026-01-22

**Feature Management.** View and toggle Navigator features via `nav-features` skill. Shows feature table on first session after install/update.

→ [Full release notes](./releases/RELEASE-NOTES-v5.7.0.md)

## [v5.6.0] — 2026-01-22

**Task Mode.** Unified workflow orchestration that coordinates between skills, loop mode, and direct execution. Auto-detects complexity and defers to appropriate handler.

→ [Full release notes](./releases/RELEASE-NOTES-v5.6.0.md)

## [v5.5.0]

**Auto-Update on Session Start.** Automatic plugin updates when newer version detected. Zero friction for daily releases.

## [v5.4.0]

**Code Simplification.** `nav-simplify` skill. Multi-Claude simplifier role. Autonomous completion integration. Loop Mode VERIFY phase integration. Based on Anthropic's internal code-simplifier pattern: clarity over brevity, functionality preserved absolutely.

## [v5.3.0]

**Task Verification Enhancement.** Verify/Done sections in task docs. `verify_extractor.py`. Multi-Claude Review integration.

## [v5.2.0] — 2026-01-20

**"Finish What You Start" positioning.** README rewrite, benefit-first documentation.

→ [Full release notes](./releases/RELEASE-NOTES-v5.2.0.md)

## [v5.1.0] — 2026-01-13

**Loop Mode.** Structured completion signals (NAVIGATOR_STATUS block). Dual-condition exit gates (heuristics + EXIT_SIGNAL). Stagnation detection circuit breaker. Phases INIT → RESEARCH → IMPL → VERIFY → COMPLETE. Inspired by Ralph's autonomous loop framework.

→ [Full release notes](./releases/RELEASE-NOTES-v5.1.0.md)

## [v5.0.0]

**Theory of Mind integration.** Based on Riedl & Weidmann 2025 research. `nav-profile` (bilateral modeling), `nav-diagnose` (quality detection), ToM verification checkpoints for high-stakes skills, enhanced markers capturing user intent.

## [v4.7.0] — 2025-12-09

Interactive onboarding skill (`nav-onboard`) with hands-on learning.

→ [Full release notes](./releases/RELEASE-NOTES-v4.7.0.md)

## [v4.6.0] — 2025-11-28

Native agents, token monitoring hooks, architecture optimization.

→ [Full release notes](./releases/RELEASE-NOTES-v4.6.0.md)

## [v4.5.0] — 2025-11-02

Multi-Claude workflow reliability fixes: retry logic, timeout monitoring, state persistence, workflow resume (`sub-claude-monitor.sh`, `resume-workflow.sh`). Enhanced marker verification with central logging.

→ [Full release notes](./releases/RELEASE-NOTES-v4.5.0.md)

## [v4.3.1] — 2025-11-01

Fixed template drift and professional pre-release upgrade flow. `nav-update-claude` now fetches templates from GitHub (version-matched). `nav-upgrade` presents interactive pre-release choice. Zero template drift.

→ [Full release notes](./releases/RELEASE-NOTES-v4.3.1.md)

## [v4.3.0] — 2025-11-01

Multi-Claude agentic workflow automation (experimental). Automated multi-Claude orchestration scripts for parallel execution. Task agents enabled in sub-Claude phases for 60-80% token savings. Failure reporting and recovery guidance.

→ [Full release notes](./releases/RELEASE-NOTES-v4.3.0.md)

## [v4.0.0] — 2025-10-24

**Major transformation: tool → complete framework.** Comprehensive education layer (learning guides, interactive examples, decision frameworks). Philosophical foundation documented (context efficiency manifesto, patterns, anti-patterns). Real metrics validation (`nav-stats` skill with efficiency scoring).

→ [Full release notes](./releases/RELEASE-NOTES-v4.0.0.md)

## [v3.4.0] — 2025-10-22

→ [Full release notes](./releases/RELEASE-NOTES-v3.4.0.md)

## [v3.3.1] — 2025-10-21

→ [Full release notes](./releases/RELEASE-NOTES-v3.3.1.md)

## [v3.3.0] — 2025-10-21

Visual Regression Integration Skill.

→ [Full release notes](./releases/RELEASE-NOTES-v3.3.0.md)

## [v3.2.0] — 2025-10-21

Product Design Skill with Figma MCP Integration.

→ [Full release notes](./releases/RELEASE-NOTES-v3.2.0.md)

## [v3.1.0] — 2025-10-20

OpenTelemetry Session Statistics. Replaced file-size estimation with official Claude Code metrics.

→ [Full release notes](./releases/RELEASE-NOTES-v3.1.0.md)

## [v3.0.0]

**Breaking: removed all slash commands (`/nav:*`).** Skills-only architecture. Use natural language: "Start my Navigator session".

---

For releases prior to v3.0, see the [GitHub Releases page](https://github.com/alekspetrov/navigator/releases).
