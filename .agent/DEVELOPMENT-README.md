# Navigator: Context-Efficient AI Development

## The Problem I Kept Hitting

I was working on a feature in Claude Code. Loaded all my project docs at session start—seemed smart. "Better to have everything available," I thought.

Five exchanges in, Claude started forgetting my recent changes. Six exchanges, it hallucinated a function that didn't exist. Seven exchanges, session died. Context window full.

I checked: **150,000 tokens loaded**. Only used **8,000**.

**I was wasting 94% of my context window on documentation I never needed.**

## The Realization

This wasn't a bug. This was my workflow.

Every AI coding session, same pattern:
- Load everything upfront ("just in case")
- Context fills with irrelevant data
- AI gets overwhelmed
- Session crashes
- Start over
- Repeat

**The default approach—load everything—was the problem.**

## What I Built

Navigator: A framework for loading only what you need, when you need it.

**How it works**:
1. Start with a 2k-token navigator (index of what exists)
2. Navigate to what you need (task docs, system architecture)
3. Load on-demand (3-5k tokens per document)
4. Progressive refinement (fetch metadata, drill down if needed)

**Result**: 150k → 12k tokens. **92% reduction.**

Not estimates. Real data, verified with OpenTelemetry.

## Why It Works

**The principle**: Load what you need, when you need it.

Not "load everything just in case."
Not "better safe than sorry."

Strategic loading beats bulk loading.

---

## Understanding Context Efficiency

**Philosophy & Principles**:
- [Context Efficiency Manifesto](./philosophy/CONTEXT-EFFICIENCY.md) — Why Navigator exists
- [Anti-Patterns](./philosophy/ANTI-PATTERNS.md) — Common mistakes (upfront loading, etc.)
- [Success Patterns](./philosophy/PATTERNS.md) — What works and why

**Learning Guides**:
- [Context Budgets](./learning/CONTEXT-BUDGETS.md) — Token allocation
- [Preprocessing vs LLM](./learning/PREPROCESSING-VS-LLM.md) — Tool selection
- [Progressive Refinement](./learning/PROGRESSIVE-REFINEMENT.md) — Metadata → details
- [Token Optimization](./learning/TOKEN-OPTIMIZATION.md) — Complete strategy

**Hands-on**:
- [TRY-THIS-LAZY-LOADING.md](./learning/examples/TRY-THIS-LAZY-LOADING.md)
- [TRY-THIS-AGENT-SEARCH.md](./learning/examples/TRY-THIS-AGENT-SEARCH.md)
- [TRY-THIS-MARKERS.md](./learning/examples/TRY-THIS-MARKERS.md)

**Decision frameworks**:
- [When to Compact](./learning/frameworks/WHEN-TO-COMPACT.md)
- [Agent vs Manual Read](./learning/frameworks/AGENT-VS-MANUAL.md)
- [Preprocessing Decision Tree](./learning/frameworks/PREPROCESSING-DECISION-TREE.md)

---

## Project Quick Start

**Project**: Claude Code plugin for Navigator
**Tech**: Markdown skills, JSON manifests, Python hook scripts
**Plugin version**: see `.claude-plugin/plugin.json` (currently v6.15.3)

**New here?** Read in order:
1. [Project Architecture](./system/project-architecture.md) — plugin structure, manifest, hook wiring
2. [Plugin Patterns](./system/plugin-patterns.md) — skill / hook / function design

**Working on a feature**:
1. Check `.agent/tasks/` for in-flight work
2. Read the relevant system doc
3. Check `.agent/sops/` for a matching procedure
4. Test in `/Users/aleks.petrov/Projects/tmp/nav-test`

**Fixing a bug**:
1. Check `.agent/sops/debugging/` for known issues
2. Query the knowledge graph: `"What do we know about <topic>?"` — `mem-*` pitfalls cover hook composition, blocking semantics, output channels, recursive-block traps
3. After fixing, capture the lesson as a memory or SOP if novel

---

## Task Completion Protocol (Autonomous)

When implementation is complete, run these without prompting:

1. **Simplify** code (if enabled and code was modified)
2. **Commit** with conventional message
3. **Archive** the task doc into `.agent/tasks/archive/`
4. **Close** the PM ticket (if configured)
5. **Create** a completion marker
6. **Suggest** a compact

**Exception cases — ask first**:
- Secrets in uncommitted files
- Multiple unrelated tasks modified
- Tests failing or implementation incomplete

---

## Documentation Structure

```
.agent/
├── DEVELOPMENT-README.md     ← this navigator
├── tasks/                    ← in-flight implementation plans (archive/ for shipped)
├── system/                   ← architecture documentation
├── sops/                     ← Standard Operating Procedures
│   ├── development/
│   ├── deployment/
│   ├── integrations/
│   └── debugging/
├── philosophy/               ← context-efficiency manifesto + patterns
├── learning/                 ← guides, examples, decision frameworks
├── knowledge/                ← project knowledge graph (graph.json + memories/)
└── examples/                 ← real workflow case studies
```

---

## In-Flight Tasks

See `.agent/tasks/*.md` for current plans. Shipped work lives in `.agent/tasks/archive/`.

Current active threads (as of 2026-05-18):
- **TASK-05** — landing page content
- **TASK-13** — web documentation site (planning)
- **TASK-15** — marketing strategy & community adoption
- **TASK-25** — multi-Claude reliability fixes (planning, follow-up to v6.1.x)
- **TASK-35** — project memory (research)
- **TASK-37** — nav-simplify complexity / cost scoring (design)
- **TASK-39** — Next.js workshop prep
- **TASK-40** — Phase 3 hook migration v6.12 (partial — v6.12.0 + v6.12.1 shipped; v6.12.2 pending)

For shipped scope, query the knowledge graph or browse `CHANGELOG.md` / `releases/RELEASE-NOTES-*.md`.

---

## System Architecture

- [Project Architecture](./system/project-architecture.md) — plugin file layout, skill manifest, hook registration, settings flow
- [Plugin Patterns](./system/plugin-patterns.md) — skill design, predefined functions, hook lifecycle, three-layer Model/Hooks/Harness discipline

---

## Standard Operating Procedures

**Development**:
- [Version Management](./sops/development/version-management.md) — single source of truth, 6-file bump checklist
- [Complete Release Workflow](./sops/development/complete-release-workflow.md) — current canonical guide
- [Plugin Release Workflow](./sops/development/plugin-release-workflow.md) — Step 0 version sync, semantic versioning
- [Autonomous Completion](./sops/development/autonomous-completion.md) — what to do without being asked

**Integrations**:
- [OpenTelemetry Setup](./sops/integrations/opentelemetry-setup.md) — real-time session metrics, ROI measurement

**Deployment**:
- [Plugin Release](./sops/deployment/plugin-release.md) — pre-release checklist, tag → CI workflow, post-release verification

**Debugging**:
- Document as discovered. Capture novel diagnoses as memories in the knowledge graph (`mem-XXX.md` under `.agent/knowledge/memories/`).

---

## Lifecycle Hooks (v6.9.0 → v6.15.3)

Navigator ships ten Claude Code hooks via the plugin manifest (`.claude-plugin/plugin.json`). They make Navigator state survive every session boundary and replace fragile "model, remember to…" prose with deterministic enforcement.

### What ships

| Hook | Event | Purpose |
| --- | --- | --- |
| `nav_session_start.py` | SessionStart | Inject navigator + active marker + config + graph stats + profile into context; emit `<!-- nav-session-start-injected:v1 -->` sentinel so `nav-start` skips re-Reads |
| `nav_pre_compact.py` | PreCompact | Snapshot conversation + git state + active tasks into `before-compact-{manual,auto}-{ts}.md`; set `.active` marker |
| `nav_post_compact.py` | PostCompact | Append Claude Code's compact summary to the marker |
| `nav_task_graph_sync.py` | PostToolUse (Write/Edit on `.agent/tasks/TASK-*.md`) | Upsert task node into the knowledge graph |
| `nav_workflow_state.py` | Stop | Record per-turn signal (`check_shown`, `nav_status_shown`, `loop_phase`, `tools_used`) into `.agent/.nav-workflow-state.json` |
| `nav_profile_sync.py` | PostToolUse (Write/Edit on `.user-profile.json`) | Convert new corrections into graph memories |
| `workflow_enforcer.py` | UserPromptSubmit | Soft-warn on Loop Mode trigger, hard-block (exit 2) when prior turn skipped WORKFLOW CHECK AND `strict_block=true` |
| `nav_read_guard.py` | PreToolUse (Read on `.agent/`) | Count non-allowlisted reads per turn; warn at 3, block at 5 (`strict_block=true`) |
| `nav_commit_reminder.py` | PostToolUse (Bash matching commit patterns) | Side-effect reminder for archival after commits |
| `token_monitor.py` | (legacy) | OpenTelemetry token counter; superseded by official metrics on most installs |

### Composition lessons captured

- **mem-027** — three-layer Model / Hooks / Harness architecture; blocking-hook gating discipline
- **mem-034** — UserPromptSubmit exit-2 bypasses the model; stderr addresses the user; recursive-block trap via echoed trigger phrases
- **mem-035** — PreToolUse `stdout` and `hookSpecificOutput.additionalContext` are silently dropped; only `exit 2` + stderr affect behavior
- **mem-037** — Stop hook emitting state on non-task turns deadlocks the next loop-trigger prompt; emit conditionally (v6.15.3 tristate fix)

Query: `"What do we know about hooks?"` returns the full memory set + their cross-edges.

### Configuration

Each hook has an `<event>_hook.enabled` toggle in `.agent/.nav-config.json`. Defaults are all `true`. The two blocking hooks (`workflow_enforcer`, `nav_read_guard`) additionally take `strict_block`. See `nav-features` skill for the interactive toggle UI.

---

## When to Read What

**Scenario: adding a new skill**
1. This navigator
2. `system/plugin-patterns.md` → skill structure
3. Look at a similar shipped skill in `skills/`
4. Use `nav-skill-creator` skill or hand-author
5. Register in `.claude-plugin/plugin.json` skills array

**Scenario: changing hook behavior**
1. Read the relevant hook in `hooks/`
2. Check `mem-027/034/035/037` for composition constraints
3. If changing a blocking hook: explicit design review against three-layer architecture
4. Add an end-to-end smoke test that covers the cooperating-hook composition, not just unit behavior

**Scenario: releasing a new version**
1. `sops/development/complete-release-workflow.md`
2. Run `release_validator.py --check-all` and `--verify-hooks`
3. Bump 6 files (marketplace.json, plugin.json, README.md badge, CLAUDE.md, .nav-config.json, RELEASE-NOTES-*.md)
4. Tag → CI publishes via `release.yml`
5. Verify with `release_validator.py --verify-tag vX.Y.Z`

**Scenario: investigating a session deadlock or unexpected block**
1. Read `.agent/.nav-workflow-state.json` — what did the Stop hook record?
2. Read `.agent/.nav-read-counter.json` — read guard state
3. Query `"What do we know about hooks?"` for known pitfalls
4. If novel, capture as `mem-XXX.md` under `.agent/knowledge/memories/pitfalls/`

---

## Token Optimization Strategy

**Per session**:
- Always: `DEVELOPMENT-README.md` (~2k tokens) — injected by SessionStart hook, not Read
- Current work: task doc (~3k)
- As needed: system doc (~4-6k)
- If helpful: SOP (~2k)
- **Total**: ~9-13k vs ~150k loading everything (90%+ savings)

The SessionStart hook itself eliminates ~6 Read calls and ~1.5-2k tokens of tool-call ceremony per session boot.

---

## Development Workflow

```bash
# Local plugin testing
/plugin marketplace add file:///Users/aleks.petrov/Projects/startups/navigator
/plugin install navigator

# Test changes in nav-test
cd ~/Projects/tmp/nav-test
# invoke skill or hook via natural language
```

**Release**: see `sops/development/complete-release-workflow.md`.

---

## Natural Language Reference

```
"Start my Navigator session"
"Initialize Navigator in this project"
"Archive TASK-XX documentation"
"Create an SOP for debugging [issue]"
"Update system architecture documentation"
"What do we know about <topic>?"
"Clear context and preserve markers"
"Release plugin"
```

---

**Last Updated**: 2026-05-18 (v6.15.3 — workflow_enforcer deadlock fix; mem-037 captured)
**Powered By**: Navigator (Complete Framework)
