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
**Plugin version**: see `.claude-plugin/plugin.json` (currently v6.18.1)

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

Current active threads (as of 2026-07-10):

**v7.0.0 program — "Hooks as Runtime"** — ALPHA COMPLETE 2026-07-10 (uncommitted→committed same
day; local testing phase, no release tagged; critical path 57→59→60→61→62→64 all landed, 58/63
parallel both landed):
- **TASK-57** ✅ — spike: six channel verdicts recorded as mem-050..055 (CC 2.1.205)
- **TASK-58** ✅ — harness-conformance suite + checked-in cc-2.1.205 results, make conformance-check
- **TASK-59** ✅ — nav_hook_lib: nine stdlib modules, 217+ tests, scoring corpus ≤1 tier
- **TASK-60** ✅ — nav_dispatch fail-open dispatcher + registry + manifest rewrite (p95 ~41ms)
- **TASK-61** ✅ — nine v6 hooks ported to ops at golden byte-parity; old hooks deleted
- **TASK-62** ✅ — prompt_tier1, stop_completion, jit_memory, failure_diagnosis, subagent_context,
  config_guard, setup, graph_sync lifecycle events (13 manifest events, all validated)
- **TASK-63** ✅ — VERSION_CONFIGS["7.0.0"] additive migrator, template 47 lines, root CLAUDE.md
  annotated (mandates → hook enforcement), nav-sync-claude liveness guard
- **TASK-64** — release gate NOT run (alpha is local-only by decision 2026-07-10); RC soak,
  Pilot sign-off, and rollback doc remain before any v7.0.0 tag

**Dogfood hardening** (live use of the alpha, 2026-07-10/11):
- **TASK-65** ✅ — stop_completion indicators derived from observable turn evidence
  (git clean, test cmd ran, .md/marker touched) instead of unpopulated state
- **TASK-66** ✅ — read_guard double-increment fixed (idempotent per tool_use_id;
  PreToolUse fires twice per Read)
- **TASK-67** ✅ — task-status vocabulary: plain-text statuses map to canonicals
- **TASK-68** ✅ — tier1 near-miss similarity telemetry + subagent_context deterministic top-K
- **TASK-69** ✅ — use-case content for the landing/docs site (work in navigator-site repo)
- **TASK-70** ✅ — exit signals accept HTML-comment wrapping (invisible in assistant output;
  verified live) + read-only Bash classifier kills "mutated the codebase" false-fires
- Tier-1 answers render as grot-style TUI cards (Pilot design language); sentinel wrapper
  dropped — block reasons render as plain text, so Tier-1 is self-safe via exact-match rail

Other threads:
- **TASK-15** — marketing strategy & community adoption (plan needs a refresh pass; predates the live site + v6.18.x)
- **TASK-35** — project memory (research)
- **TASK-37** — nav-simplify complexity / cost scoring (design)
- **TASK-55** — landing + docs site: built + deployed (navigator-site.vercel.app); only DNS cutover left

Closed 2026-07-09: TASK-05/13 (superseded by TASK-55), TASK-39 (workshop delivered 2026-05-22), TASK-42 (audit roadmap complete incl. wp12 security re-sweep), TASK-56 (nav-brief, shipped v6.18.0).

For shipped scope, query the knowledge graph or browse `CHANGELOG.md` / `releases/RELEASE-NOTES-*.md`.

---

## System Architecture

- [Project Architecture](./system/project-architecture.md) — plugin file layout, skill manifest, hook registration, settings flow
- [Plugin Patterns](./system/plugin-patterns.md) — skill design, predefined functions, hook lifecycle, three-layer Model/Hooks/Harness discipline

---

## Standard Operating Procedures

**Development**:
- [Release Workflow](./sops/development/release-workflow.md) — canonical end-to-end release SOP (SSOT, 6-file bump, CI publish, semver)
- [Autonomous Completion](./sops/development/autonomous-completion.md) — what to do without being asked

**Integrations**:
- [OpenTelemetry Setup](./sops/integrations/opentelemetry-setup.md) — real-time session metrics, ROI measurement

**Deployment**:
- [Plugin Release](./sops/deployment/plugin-release.md) — pre-release checklist, tag → CI workflow, post-release verification

**Debugging**:
- [Knowledge-Graph Memory Corruption](./sops/debugging/knowledge-graph-memory-corruption.md) — diagnose junk/duplicate memories, clean via remove-node + resolved/ archiving, fix the ingester
- Document as discovered. Capture novel diagnoses as memories in the knowledge graph (`mem-XXX.md` under `.agent/knowledge/memories/`).

---

## Lifecycle Hooks (v7.0.0 dispatcher + ops)

Navigator registers ONE hook command per Claude Code event via the plugin manifest (`.claude-plugin/plugin.json`): `python3 hooks/nav_dispatch.py <event>`. The dispatcher loads shared runtime services from `hooks/nav_hook_lib/` (config layering, schema-2 state, sentinels/redaction, budget clamps) and routes each event to the ops registered in `hooks/nav_hook_lib/registry.py`, executing them in phase order (gate → injector → recorder). The nine v6 per-hook scripts were ported byte-parity to `hooks/ops/` in TASK-61 and deleted; `tests/golden/` locks the recorded v6 stdout/exit behavior.

Hook commands resolve via `${CLAUDE_PLUGIN_ROOT}` (the installed plugin directory) with a marketplace-path fallback (mem-036: the unset-env path is contract-tested, never a silent no-op). Per-turn/session state lives in `.agent/.nav-runtime-state.json` (`"schema": 2`); the v6 per-hook state files are archived to `.agent/.nav-v6-state.bak/` by the SessionStart op — never deleted, `.agent/.context-markers/` untouched.

### What ships

| Op (`hooks/ops/`) | Event (phase) | Purpose |
| --- | --- | --- |
| `session_start.py` | SessionStart (injector) | Inject navigator + active marker + config + graph stats + profile into context; emit `<!-- nav-session-start-injected:v1 -->` sentinel so `nav-start` skips re-Reads; archive v6 state files to `.nav-v6-state.bak/` |
| `compact_marker.py` | PreCompact + PostCompact (recorder) | PreCompact: snapshot conversation + git state + active tasks into `before-compact-{manual,auto}-{ts}.md`, set `.active` marker. PostCompact: append Claude Code's compact summary to that marker |
| `graph_sync.py` | PostToolUse Write/Edit on `.agent/tasks/TASK-*.md` (recorder) | Upsert task node into the knowledge graph |
| `stop_state.py` | Stop (recorder) | Record per-turn signal (`check_shown` tristate, `nav_status_shown`, `loop_phase`, `tools_used`) into the schema-2 state file; the single audited turn-lifecycle reset barrel (read counter + tier-1 fuse slot + continue-counter slot) |
| `profile_sync.py` | PostToolUse Write/Edit on `.user-profile.json` (recorder) | Convert new corrections into graph memories |
| `prompt_gate.py` | UserPromptSubmit (gate) | Soft-warn on Loop Mode trigger, hard-block (exit 2) when prior turn skipped WORKFLOW CHECK AND `strict_block=true` (config key stays `workflow_enforcer_hook`) |
| `prompt_brief.py` | UserPromptSubmit (injector) | Score prompt ambiguity (TASK-56, shipped v6.18.0); on ambiguous task-shaped prompts inject a NAV-BRIEF instruction + relevant graph memories so the model renders an intent brief before implementing. Never blocks (exit 0 only — mem-034). Composes with `prompt_gate` on the same event. Live-validated 2026-07-09: full cycle (brief → confirmation → BRIEF DRIFT on scope growth → re-confirmation) ran on a real bug, and the hook's own memory recall surfaced the graph corruption fixed in v6.18.1 — see `sops/debugging/knowledge-graph-memory-corruption.md` |
| `read_guard.py` | PreToolUse Read on `.agent/` (gate) | Count non-allowlisted reads per turn; warn at 3, block at 5 (`strict_block=true`); deny-only channel (mem-035) |

### Composition lessons captured

- **mem-027** — three-layer Model / Hooks / Harness architecture; blocking-hook gating discipline
- **mem-034** — UserPromptSubmit exit-2 bypasses the model; stderr addresses the user; recursive-block trap via echoed trigger phrases
- **mem-035** — PreToolUse `stdout` and `hookSpecificOutput.additionalContext` are silently dropped; only `exit 2` + stderr affect behavior
- **mem-037** — Stop hook emitting state on non-task turns deadlocks the next loop-trigger prompt; emit conditionally (v6.15.3 tristate fix)

Query: `"What do we know about hooks?"` returns the full memory set + their cross-edges.

### Configuration

Each op keeps its v6 `*_hook.enabled` toggle in `.agent/.nav-config.json` (config keys unchanged: `session_start_hook`, `compact_hook`, `task_graph_sync_hook`, `workflow_state_hook`, `profile_sync_hook`, `workflow_enforcer_hook`, `brief_hook`, `read_guard_hook`). Defaults are all `true`. The two gates (`prompt_gate` via `workflow_enforcer_hook`, `read_guard` via `read_guard_hook`) additionally take `strict_block`. `brief_hook` additionally takes `ambiguity_threshold` (default 0.5) and `memory_budget_chars` (default 1200). See `nav-features` skill for the interactive toggle UI.

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
1. `sops/development/release-workflow.md`
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

**Release**: see `sops/development/release-workflow.md`.

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

**Last Updated**: 2026-07-09 (v6.18.1 — nav-brief shipped v6.18.0; decision-extraction separator/dedupe fix v6.18.1; audit roadmap TASK-42 closed incl. wp12 security re-sweep)
**Powered By**: Navigator (Complete Framework)
