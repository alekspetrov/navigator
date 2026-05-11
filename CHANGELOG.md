# Changelog

All notable changes to Navigator are recorded here. Detailed per-version notes live in [`releases/`](./releases/); each link below points to the full file. Versions without a release notes file have only summary lines.

This project follows [Semantic Versioning](https://semver.org/). The authoritative source of truth for versions is [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json) — see [`sops/development/version-management.md`](./.agent/sops/development/version-management.md).

---

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
