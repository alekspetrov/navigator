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

### Philosophy & Principles

**New to this approach?** Start with the philosophy:
- [Context Efficiency Manifesto](./philosophy/CONTEXT-EFFICIENCY.md) - Why Navigator exists
- [Anti-Patterns](./philosophy/ANTI-PATTERNS.md) - Common mistakes (upfront loading, etc.)
- [Success Patterns](./philosophy/PATTERNS.md) - What works and why

### Learning Guides (New in v4.0)

**Master the principles** with comprehensive guides:
- [Context Budgets](./learning/CONTEXT-BUDGETS.md) - How to think about token allocation
- [Preprocessing vs LLM](./learning/PREPROCESSING-VS-LLM.md) - When to use which tool
- [Progressive Refinement](./learning/PROGRESSIVE-REFINEMENT.md) - Metadata → details on-demand
- [Token Optimization](./learning/TOKEN-OPTIMIZATION.md) - Complete strategy guide

### Interactive Examples

**Try it yourself** with hands-on exercises:
- [TRY-THIS-LAZY-LOADING.md](./learning/examples/TRY-THIS-LAZY-LOADING.md) - Experience 90%+ token savings
- [TRY-THIS-AGENT-SEARCH.md](./learning/examples/TRY-THIS-AGENT-SEARCH.md) - Agent-assisted exploration
- [TRY-THIS-MARKERS.md](./learning/examples/TRY-THIS-MARKERS.md) - 97% context compression

### Decision Frameworks

**Quick reference** for common decisions:
- [When to Compact](./learning/frameworks/WHEN-TO-COMPACT.md) - Context management flowchart
- [Agent vs Manual Read](./learning/frameworks/AGENT-VS-MANUAL.md) - File reading decisions
- [Preprocessing Decision Tree](./learning/frameworks/PREPROCESSING-DECISION-TREE.md) - Right tool selection

**Quick start?** Jump to [Development Workflow](#-development-workflow)

---

## 🚀 Quick Start for Development

**Project**: Claude Code plugin for Navigator
**Tech Stack**: Markdown templates, JSON configuration, Bash slash commands, Python functions
**Updated**: 2025-10-23

### New to This Project?
**Read in this order:**
1. [Project Architecture](./system/project-architecture.md) - Plugin structure, templates
2. [Plugin Development Patterns](./system/plugin-patterns.md) - Claude Code plugin best practices

### Working on Plugin Features?
1. Check if similar task exists in [`tasks/`](#implementation-plans-tasks)
2. Read relevant system docs from [`system/`](#system-architecture-system)
3. Check for integration SOPs in [`sops/`](#standard-operating-procedures-sops)
4. Test changes in `/Users/aleks.petrov/Projects/tmp/nav-test`

### Fixing a Bug?
1. Check [`sops/debugging/`](#debugging) for known issues
2. Review relevant system docs for context
3. After fixing, create SOP: `/nav:update-doc sop debugging [issue-name]`

---

## 📊 Session Statistics & Grafana Dashboard (New in v3.1)

Navigator uses **OpenTelemetry** for real-time session metrics with visual dashboards.

### Quick Setup (2 minutes)

**1. Enable metrics**:
```bash
# Add to ~/.zshrc or ~/.bashrc
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=prometheus

# Reload shell
source ~/.zshrc  # or source ~/.bashrc
```

**2. Start Grafana dashboard** (optional):
```bash
cd .agent/grafana
docker compose up -d
```

Access at **http://localhost:3333** (admin/admin)

### What You Get

**Console metrics** (terminal output):
- ✅ Real token usage (not file-size estimates)
- ✅ Cache hit rates (CLAUDE.md caching performance)
- ✅ Session costs (actual USD spent)
- ✅ Active time tracking

**Grafana dashboard** (visual monitoring):
- ✅ 10-panel dashboard with all metrics
- ✅ Token usage trends (cumulative & rate)
- ✅ Cache hit rate gauge (validates optimization)
- ✅ Cost tracking (USD/hour, total cost)
- ✅ Model distribution (Haiku vs Sonnet)
- ✅ Auto-refresh every 10 seconds

**See**:
- [OpenTelemetry Setup Guide](./sops/integrations/opentelemetry-setup.md)
- [Grafana Dashboard README](./grafana/README.md)

---

## 🤖 Task Completion Protocol (CRITICAL)

### Autonomous Completion Expected

Navigator projects run in **full autonomy mode**. When task implementation is complete:

✅ **Execute automatically** (no human prompt needed):
1. **Commit changes** with conventional commit message
2. **Archive implementation plan** (`/nav:update-doc feature TASK-XX`)
3. **Close ticket** in PM tool (if configured)
4. **Create completion marker** (`TASK-XX-complete`)
5. **Suggest compact** for next task

❌ **Don't wait for**:
- "Please commit now"
- "Close the ticket"
- "Update documentation"
- "Create a marker"

### Exception Cases (Ask First)

Only interrupt autonomous flow if:
- Uncommitted files contain secrets (.env, credentials, API keys)
- Multiple unrelated tasks modified (unclear which to close)
- No task context loaded (ambiguous TASK-XX)
- Tests failing or implementation incomplete

### Completion Summary Template

```
✅ TASK-XX Complete

Automated actions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Committed: [hash] [message]
✅ Documentation: Implementation plan archived
✅ Ticket: Closed in [PM tool]
✅ Marker: TASK-XX-complete created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next: Run /nav:compact to clear context
```

**For detailed protocol**: See [`sops/development/autonomous-completion.md`](#autonomous-completion)

---

## 📂 Documentation Structure

```
.agent/
├── DEVELOPMENT-README.md     ← You are here (navigator)
│
├── tasks/                    ← Implementation plans
│   └── TASK-01-session-start-pm-integration.md
│
├── system/                   ← Living architecture documentation
│   ├── project-architecture.md
│   └── plugin-patterns.md
│
└── sops/                     ← Standard Operating Procedures
    ├── integrations/         # (Not applicable for this project)
    ├── debugging/            # Plugin issues and solutions (none yet)
    ├── development/          # Development workflows
    │   └── plugin-release-workflow.md
    └── deployment/           # Publishing to GitHub (none yet)
```

---

## 📖 Documentation Index

### Implementation Plans (`tasks/`)

#### [TASK-01: Session Start Command and PM Integration](./tasks/TASK-01-session-start-pm-integration.md)
**Status**: ✅ Completed (v1.3.0)
**Completed**: 2025-10-12

**What was built**:
- New `/nav:start` command for session initialization
- Enhanced `/nav:init` with PM tool auto-configuration (Step 6.5)
- Linear MCP and GitHub CLI detection with setup guidance
- Auto-generated integration SOPs
- Stronger CLAUDE.md enforcement of Navigator workflow

**Impact**: Dramatically improved onboarding UX and consistent Navigator adoption

#### [TASK-02: README Overhaul & Context Markers](./tasks/TASK-02-readme-markers-v1.4.0.md)
**Status**: ✅ Completed (v1.4.0)
**Completed**: 2025-10-12

**What was built**:
- New `/nav:marker` command for on-demand conversation save points
- Updated `/nav:init` with `.context-markers/` setup and .gitignore
- Comprehensive README.md rewrite with clear feature explanations
- Token optimization strategy documented step-by-step
- Context markers explained with examples (97.7% compression)

**Impact**: Crystal-clear plugin value proposition, users understand Navigator in 30 seconds

#### [TASK-03: Interactive Marker Management + Auto-Resume](./tasks/TASK-03-markers-management-auto-resume.md)
**Status**: ✅ Completed (v1.5.0)
**Completed**: 2025-10-12

**What was built**:
- New `/nav:markers` command for interactive marker management (list, load, clean)
- Active marker auto-resume system (.active file + /nav:start detection)
- Performance optimizations (<1s for 50+ markers)
- Updated `/nav:compact` to create active markers
- Updated `/nav:start` to auto-detect and load active markers

**Impact**: One-command resume after compact (vs 3 manual steps), visual marker selection

#### [TASK-04: Version Sync Fix & Release Process](./tasks/TASK-04-version-sync-release-process.md)
**Status**: ✅ Completed (v1.5.0 docs)
**Completed**: 2025-10-13

**What was built**:
- Fixed README.md version references (1.4.0 → 1.5.0)
- Created Version Management SOP with audit script
- Enhanced Plugin Release Workflow with mandatory version sync step
- Created missing GitHub releases (v1.3.0, v1.4.0, v1.5.0)
- Systematic checklist to prevent future version drift

**Impact**: Zero version drift prevention, professional release quality, clear process for contributors

#### [TASK-05: Autonomous Task Completion](./tasks/TASK-05-autonomous-completion.md)
**Status**: ✅ Completed (v1.5.1)
**Completed**: 2025-10-13

**What was built**:
- Updated CLAUDE.md with autonomous completion protocol
- Updated DEVELOPMENT-README.md with Task Completion Protocol
- Created Autonomous Completion SOP (sops/development/)
- Modified Development Workflow to show [AUTONOMOUS] completion
- Enforced "no wait for prompts" behavior via Forbidden Actions

**Impact**: Fully autonomous task completion - no more "please commit" or "close ticket" prompts needed

#### [TASK-06: Real Session Statistics from Claude Code Internals](./tasks/TASK-06-session-statistics.md)
**Status**: ✅ Completed (v1.6.0)
**Completed**: 2025-10-16

**What was built**:
- session_stats.py script to extract real token usage from Claude Code internals
- Proof of Navigator efficiency with actual measurements (not estimates)
- Integration with /nav:start command to show cache performance
- Real-world validation of 92% token reduction claim

**Impact**: Concrete proof of Navigator's token efficiency, verified cache performance metrics

#### [TASK-07: Skills Migration Strategy](./tasks/TASK-07-skills-migration.md)
**Status**: ✅ Completed (v2.0.0)
**Completed**: 2025-10-19

**What was built**:
- 5 core Navigator skills (nav-start, nav-marker, nav-compact, nav-task, nav-sop)
- Skills registered in plugin.json with auto-invocation capability
- Hybrid architecture: Both commands and skills work simultaneously
- Foundation for progressive disclosure (250 token overhead)

**Impact**: Natural language invocation, auto-detection, zero breaking changes for v1.x users

#### [TASK-08: Skills Enhancements & Hybrid Architecture](./tasks/TASK-08-skills-enhancements-v2.1.md)
**Status**: ✅ Completed (v2.1.0)
**Completed**: 2025-10-19

**What was built**:
- Predefined functions for nav-task (task_id_generator.py, task_formatter.py, index_updater.py)
- Predefined functions for nav-sop (sop_formatter.py)
- Predefined functions for nav-marker (marker_compressor.py)
- nav-skill-creator skill (self-improving capability)
- Functions execute with 0 tokens (no context pollution)

**Impact**: Consistent output via templates, self-improving system, foundation for v2.2 project-specific skills

#### [TASK-09: Plugin Update Migration System](./tasks/TASK-09-migration-system.md)
**Status**: ✅ Completed (v2.0.0)
**Completed**: 2025-10-19

**What was built**:
- Backward compatibility commands (_jitd_*.md) for smooth v1→v2 transition
- Post-install script for automatic project migration discovery
- Config migration (.jitd-config.json → .nav-config.json)
- Zero breaking changes for existing users

**Impact**: Smooth migration path, old commands work with warnings, automatic upgrade detection

#### [TASK-10: Project-Specific Skills Generation](./tasks/TASK-10-project-skills-v2.2.md)
**Status**: ✅ Completed (v2.2.0)
**Completed**: 2025-10-19

**What was built**:
- Completed nav-skill-creator implementation (531 lines with comprehensive instructions)
- Generated plugin-slash-command skill (first project-specific skill)
- Predefined functions: command_generator.py, command_validator.py
- Templates and examples for slash command generation
- Self-improving capability validated on Navigator codebase

**Impact**: Self-improving plugin that generates its own tools, 80% token reduction for command creation, repeatable pattern for any project

#### [TASK-11: Project-Specific Skills Generation v2.3](./tasks/TASK-11-project-skills-generation-v2.3.md)
**Status**: ✅ Completed (v2.3.0)
**Completed**: 2025-10-19

**What was built**:
- Generated 5 project-specific skills for common development patterns
- frontend-component skill (React/Vue components with tests and styles)
- backend-endpoint skill (REST/GraphQL APIs with validation)
- database-migration skill (Schema changes with rollbacks)
- backend-test skill (Unit/integration tests with mocks)
- frontend-test skill (Component tests with RTL)
- Total: 12 skills (7 core + 5 project-specific)

**Impact**: 80% token reduction for common dev patterns (15k → 3k tokens), validates self-improving capability at scale, proven repeatable skill generation process

#### [TASK-12: v3.0 Skills-Only Migration](./tasks/TASK-12-v3.0-skills-only.md)
**Status**: ✅ Completed (v3.0.0)
**Completed**: 2025-10-19

**What was built**:
- Removed all slash commands (/nav:* deleted - 13 files)
- Skills-only architecture (natural language interface)
- Breaking change migration (v3.0 major version)
- 11k token reduction (commands overhead eliminated)
- Cleaner architecture (no hybrid complexity)
- Updated all documentation (README, templates, CLAUDE.md)

**Impact**: Natural language only, 50% simpler UX, 97% total token reduction, future-proof architecture

#### [TASK-13: OpenTelemetry Session Statistics](./tasks/archive/TASK-13-otel-session-statistics.md)
**Status**: ✅ Completed (v3.1.0)
**Completed**: 2025-10-20

**What was built**:
- OpenTelemetry integration for real-time session metrics
- Replaced file-size estimation with official Claude Code metrics
- Auto-enablement via post-install hook
- Comprehensive OpenTelemetry setup SOP
- Zero-config upgrade experience

**Impact**: Real token usage validation, cache performance tracking, session cost monitoring, ROI measurement with hard data

#### [TASK-14: CLAUDE.md Updater Skill](./tasks/archive/TASK-14-claude-md-updater.md)
**Status**: ✅ Completed (v3.1.1)
**Completed**: 2025-10-20

**What was built**:
- nav-update-claude skill for automated CLAUDE.md migration
- version_detector.py to identify outdated configurations
- claude_updater.py to extract customizations and generate updated files
- Non-destructive migration (creates backup before changes)
- Preserves project-specific customizations (tech stack, standards, forbidden actions)
- Updated README.md with shorter marketplace installation format
- Added SECURITY.md policy

**Impact**: Users can upgrade to v3.1 natural language without losing customizations, solves "Claude doesn't understand Navigator" issues in migrated projects

#### [TASK-16: Product Design Skill with Figma MCP Integration](./tasks/TASK-16-product-design-skill.md)
**Status**: ✅ Completed (v3.2.0)
**Completed**: 2025-10-21

**What was built**:
- product-design skill for automated design handoff
- 5 predefined functions (design_analyzer, token_extractor, component_mapper, design_system_auditor, implementation_planner)
- DTCG format support for design tokens (W3C standard)
- Figma MCP integration (local and remote server support)
- Component similarity matching for reuse detection
- Design system drift detection and audit reports
- Automated implementation plan generation with phased breakdown
- Templates for design reviews and token diffs

**Impact**: Reduces design handoff time from 6-10 hours to 15-20 minutes (95% reduction), automates token extraction, prevents design system drift, generates Navigator task docs from Figma analysis

#### [TASK-17: Visual Regression Integration Skill](./tasks/TASK-17-visual-regression-skill.md)
**Status**: ✅ Completed (v3.3.0)
**Completed**: 2025-10-21

**What was built**:
- visual-regression skill for automated visual regression testing setup
- 4 predefined functions (vr_setup_validator, story_generator, chromatic_config_generator, ci_workflow_generator)
- Support for Chromatic, Percy, and BackstopJS
- Storybook story generation with component variants
- CI/CD workflow generation (GitHub Actions, GitLab CI, CircleCI)
- Templates for stories, configs, and CI workflows
- Integration with product-design skill for complete design→code→testing workflow
- Visual regression setup SOP

**Impact**: Reduces visual regression setup from 2-3 hours to 5 minutes (96% reduction), automates Storybook story generation, ensures pixel-perfect component implementation, integrates with design workflow for end-to-end validation

#### [TASK-18: Principle to Product - Philosophy, Metrics, Education](./tasks/TASK-18-principle-to-product-v3.5.md)
**Status**: ✅ Completed (v4.0.0)
**Completed**: 2025-01-24

**What was built**:

**Phase 1: Philosophy Foundation (v3.5.0)**
- Context Efficiency Manifesto (`.agent/philosophy/CONTEXT-EFFICIENCY.md`)
- Anti-Patterns documentation (`.agent/philosophy/ANTI-PATTERNS.md`)
- Success Patterns documentation (`.agent/philosophy/PATTERNS.md`)
- Narrative transformation of DEVELOPMENT-README, CLAUDE.md, README.md
- Vulnerability-driven voice and movement positioning

**Phase 2: Metrics & Proof (v3.5.0)**
- nav-stats skill with real efficiency scoring (0-100)
- Actual baseline calculations from `.agent/` markdown
- OpenTelemetry-verified metrics
- 3 real workflow case studies (`.agent/examples/`)
- Shareable ROI reports

**Phase 3: Education Layer (v4.0.0)**
- 4 comprehensive learning guides (69k tokens total):
  - Context Budgets (token allocation strategies)
  - Preprocessing vs LLM (tool selection principles)
  - Progressive Refinement (metadata → details pattern)
  - Token Optimization (complete strategy guide)
- 3 interactive examples (hands-on practice):
  - TRY-THIS-LAZY-LOADING (90%+ savings experience)
  - TRY-THIS-AGENT-SEARCH (60-80% agent savings)
  - TRY-THIS-MARKERS (97% compression experience)
- 3 decision frameworks (quick reference):
  - When to Compact (flowchart)
  - Agent vs Manual Read (decision tree)
  - Preprocessing Decision Tree (tool selection)

**Impact**: Transforms Navigator from "tool with good docs" to "complete framework with philosophy, proof, and education." Users go from copying patterns to mastering principles. Typical learning: 30 min philosophy → 40 min practice → ongoing framework reference → 90%+ efficiency scores in 2-4 weeks.

#### [TASK-25: Multi-Claude Workflow Reliability Fixes](./tasks/TASK-25-fix-multi-claude-reliability.md)
**Status**: ✅ Completed (v4.5.0)
**Completed**: 2025-11-02

**What was built**:
- Automatic retry logic for failed phase markers
- Sub-Claude timeout monitoring (sub-claude-monitor.sh)
- Phase state persistence and recovery
- Workflow resume capability (resume-workflow.sh)
- Enhanced marker verification with central logging
- Improved sub-Claude prompts with explicit marker instructions
- Test suite (test-retry-logic.sh, test-monitor.sh)

**Impact**: Multi-Claude workflow success rate increased from 30% to 90%+ through automatic retry, timeout detection, and recovery mechanisms

#### [TASK-19: Multi-Claude Agentic Workflow Automation](./tasks/TASK-19-multi-claude-agentic-workflow.md)
**Status**: ✅ Completed (v4.3.0 - foundation), 🚧 Ongoing improvements
**Created**: 2025-10-31
**Foundation Complete**: 2025-10-31

**What we're building**:

**Automated multi-Claude orchestration system** leveraging:
- Claude Code's headless mode (`-p` flag) + streaming JSON I/O
- Session management (`--resume`) for multi-turn conversations
- Git worktrees for isolated parallel workspaces
- Navigator's marker system for cross-instance communication
- Role-specific CLAUDE.md templates (5k tokens vs 50k per instance)

**10-Phase Implementation**:
1. **Core Automation Scripts** - Bash orchestrator with marker detection
2. **Role-Specific Templates** - Minimal context CLAUDE.md per worktree (orchestrator, impl, test, docs, review)
3. **Skill Integration** - Natural language setup: "Setup multi-Claude workflow"
4. **Enhanced Markers** - Rich context transfer (2k vs 15k handoffs)
5. **Subagent Patterns** - 8x multiplier per terminal (40x total parallelism)
6. **Status Monitoring** - Real-time dashboard showing all phases
7. **Error Handling** - Recovery paths + automatic retry
8. **CI/CD Integration** - GitHub Actions workflow for automated features
9. **Documentation** - Complete SOP + walkthrough examples
10. **Benchmarking** - Validate 3x speedup + 92% efficiency claims

**Key Innovation**: Parallel execution with Navigator efficiency
- 5 Claude instances (orchestrator, impl, test, docs, review)
- Each maintains 92% token efficiency (role-specific minimal context)
- Subagents per instance (8x research capacity each)
- Total throughput: 32x single Claude baseline

**Expected Impact**:
- **Time**: 3x faster (parallel vs sequential phases)
- **Tokens**: 35k across 5 sessions vs 70k single session crash
- **Quality**: 95% success rate (fresh contexts prevent crashes)
- **Throughput**: 40x parallel research/verification capacity

**Technical Foundation**: Streaming JSON + session persistence enables full automation without manual coordination.

#### [TASK-29: Theory of Mind v5.0.0 Release](./tasks/TASK-29-tom-v5-release.md)
**Status**: 🚧 In Progress
**Created**: 2025-12-11
**Target Version**: v5.0.0

**What we're building**:

**Theory of Mind features** based on Riedl & Weidmann 2025 research:
- **nav-profile**: Bilateral modeling - Claude learns user preferences across sessions
- **nav-diagnose**: Quality detection - catches collaboration drift, prompts re-anchoring
- **Verification checkpoints**: Confirms understanding before generating high-stakes code
- **Auto-learn corrections**: Silently captures correction patterns
- **Enhanced markers**: Intent and belief state capture

**Two-layer positioning**:
```
Navigator = Context Engineering + Human-AI Collaboration

Layer 1: Context Efficiency (v1-v4) - proven, 92% savings
Layer 2: Theory of Mind (v5.0.0) - bilateral modeling, quality detection
```

**Expected Impact**:
- 23-29% performance boost from ToM alignment (per research)
- Fewer repeated corrections (auto-learn)
- Better restoration from markers (intent preserved)
- Clearer Claude Code differentiation (complementary, not competing)

---

### System Architecture (`system/`)

#### [Project Architecture](./system/project-architecture.md)
**When to read**: Starting work on plugin, understanding structure

**Contains**:
- Plugin file structure
- Template system organization
- Slash command implementations
- Configuration schema
- Development workflow

**Updated**: Every major architecture change

#### [Plugin Development Patterns](./system/plugin-patterns.md)
**When to read**: Adding new features or commands

**Contains**:
- Claude Code plugin best practices
- Template design patterns
- Slash command patterns
- Testing strategies

**Updated**: When adding new patterns

---

### Standard Operating Procedures (`sops/`)

#### Development

##### [Version Management](./sops/development/version-management.md)
**When to use**: Before every release, auditing version consistency

**Contains**:
- Single source of truth (marketplace.json)
- Version reference map (9 locations)
- Pre-release checklist with audit script
- Semantic versioning guide
- Troubleshooting version mismatches

**Last Updated**: 2025-10-13

##### [Complete Release Workflow](./sops/development/complete-release-workflow.md)
**When to use**: Releasing new Navigator version (comprehensive guide)

**Contains**:
- Step-by-step release process (10 steps)
- Version file updates (marketplace.json, plugin.json, README.md)
- Release notes creation
- GitHub release automation (via GitHub Actions)
- Pre-release vs stable release handling
- Troubleshooting common issues
- Real example: v4.3.0 release walkthrough

**Created**: 2025-10-31
**Last Updated**: 2025-10-31

##### [Navigator Plugin Release Workflow](./sops/development/navigator-plugin-release-workflow.md)
**When to use**: Legacy release guide (use Complete Release Workflow instead)

**Contains**:
- Preparing release materials (release notes, upgrade guides)
- Updating plugin metadata (.claude-plugin/plugin.json)
- Updating skill versions (SKILL.md)
- Commit and push workflow (feature, version, docs)
- Git tagging and GitHub releases
- Testing upgrade paths
- Release checklist
- Example: v3.4.0 release walkthrough

**Created**: 2025-10-22
**Last Updated**: 2025-10-22
**Status**: Superseded by Complete Release Workflow

##### [Plugin Release Workflow](./sops/development/plugin-release-workflow.md)
**When to use**: Releasing new plugin version

**Contains**:
- **Step 0: Pre-Release Version Sync (MANDATORY)**
- Semantic versioning guide
- Step-by-step release process
- Git tag and GitHub release creation
- Troubleshooting common issues
- Complete release checklist

**Last Used**: v1.5.0 (2025-10-13)

##### [Autonomous Completion](./sops/development/autonomous-completion.md)
**When to use**: Understanding how to complete tasks autonomously

**Contains**:
- Autonomous completion protocol (7 steps)
- Exception handling (secrets, multiple tasks, no context, test failures)
- Completion summary template
- Integration with PM tools and markers
- Best practices for fully autonomous workflow

**Last Updated**: 2025-10-13

#### Integrations

##### [OpenTelemetry Setup](./sops/integrations/opentelemetry-setup.md)
**When to use**: Enabling real-time session statistics, ROI measurement

**Contains**:
- Quick start setup (2 minutes)
- Configuration options (console, OTLP, Prometheus)
- Navigator-specific setup recommendations
- ROI measurement strategies
- Troubleshooting guide
- Enterprise deployment patterns

**Last Updated**: 2025-10-20

#### Debugging
*No SOPs yet - document issues as they're discovered*

#### Deployment

##### [Plugin Release](./sops/deployment/plugin-release.md)
**When to use**: Releasing new plugin version to marketplace

**Contains**:
- Pre-release checklist (verify all skills committed)
- Release process (commit → push → tag → release)
- Post-release verification (cache clearing, test install)
- Emergency tag fixes (update tag after release)
- Common mistakes and prevention

**Created**: 2025-01-13 (after v5.1.0 missing nav-profile incident)

---

## 🔄 When to Read What

### Scenario: Adding New Slash Command

**Read order**:
1. This navigator (DEVELOPMENT-README.md)
2. `system/plugin-patterns.md` → Command structure
3. Check existing commands in `.claude/commands/`
4. Implement new command
5. Test in nav-test project
6. Document: `/nav:update-doc feature TASK-XX`

### Scenario: Adding New Template

**Read order**:
1. This navigator
2. `system/project-architecture.md` → Template location
3. Check existing templates in `templates/`
4. Create new template
5. Update `/nav:init` command to copy it
6. Test in nav-test project
7. Document: `/nav:update-doc feature TASK-XX`

### Scenario: Fixing Plugin Installation Issues

**Read order**:
1. Check `sops/debugging/` → Known installation issues?
2. `system/project-architecture.md` → Plugin manifest
3. Debug issue
4. Create SOP: `/nav:update-doc sop debugging [issue-name]`

### Scenario: Releasing New Plugin Version

**Read order**:
1. This navigator (DEVELOPMENT-README.md)
2. `sops/development/plugin-release-workflow.md` → Complete process
3. Follow checklist step-by-step
4. Document: `/nav:update-doc feature TASK-XX`
5. Update SOP with lessons learned

---

## 🛠️ Development Workflow

### Local Development Setup

```bash
# 1. Clone repo
git clone https://github.com/alekspetrov/navigator.git
cd navigator

# 2. Create test project
mkdir -p ~/Projects/tmp/nav-test
cd ~/Projects/tmp/nav-test

# 3. Point to local plugin (for testing)
# In Claude Code:
/plugin marketplace add file:///Users/aleks.petrov/Projects/startups/navigator
/plugin install navigator
```

### Making Changes

```bash
# 1. Read navigator first
Read .agent/DEVELOPMENT-README.md

# 2. Make changes to plugin files
# - Templates: templates/
# - Commands: .claude/commands/
# - Config: .claude-plugin/marketplace.json

# 3. Test in nav-test project
cd ~/Projects/tmp/nav-test
/nav:init  # or other command you're testing

# 4. Verify changes work
ls .agent/  # Check structure created
cat CLAUDE.md  # Check file generated

# 5. Document changes
/nav:update-doc feature TASK-XX
```

### Release Process

```bash
# 1. Update version in marketplace.json
# - Patch: 1.0.1 (bug fix)
# - Minor: 1.1.0 (new feature)
# - Major: 2.0.0 (breaking change)

# 2. Commit changes
git add -A
git commit -m "feat: description"

# 3. Push to GitHub
git push origin main

# 4. Tag release
git tag -a v1.1.0 -m "Version 1.1.0: Feature X"
git push origin v1.1.0

# 5. Create GitHub release (optional)
gh release create v1.1.0 --title "Navigator v1.1.0" --notes "..."
```

---

## 📊 Token Optimization Strategy

**This repo follows Navigator principles**:

1. **Always load**: `DEVELOPMENT-README.md` (~2k tokens)
2. **Load for current work**: Specific system doc (~3k tokens)
3. **Load if needed**: Specific SOP (~2k tokens)
4. **Never load**: All templates at once (~20k tokens)

**Total**: ~7k tokens vs ~35k (80% savings)

---

## 🎯 Success Metrics

### Plugin Quality
- [ ] All templates follow universal pattern
- [ ] Slash commands work in test project
- [ ] Documentation is accurate
- [ ] Examples provided for common use cases

### Token Efficiency
- [ ] <30k tokens per development session
- [ ] Navigator-first loading practiced
- [ ] `/nav:compact` used between tasks

### User Experience
- [ ] `/nav:init` creates complete structure
- [ ] Templates easy to customize
- [ ] Documentation clear and helpful

---

## 🚀 Quick Natural Language Reference

Navigator v3.1 uses natural language - no commands needed!

**Initialize Navigator**:
```
"Initialize Navigator in this project"
```

**Update documentation**:
```
"Archive TASK-XX documentation"
"Create an SOP for debugging [issue]"
"Update system architecture documentation"
```

**Smart compact**:
```
"Clear context and preserve markers"
```

---

**This documentation system keeps plugin development context-efficient while maintaining comprehensive knowledge.**

**Last Updated**: 2025-01-24 (v4.0.0)
**Powered By**: Navigator (Complete Framework)
