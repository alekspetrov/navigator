# Navigator - Context Engineering for Your Codebase

**92% token savings. Verified, not estimated.**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.7.0-blue.svg)](https://github.com/alekspetrov/navigator/releases)
[![Status](https://img.shields.io/badge/status-stable-green.svg)](https://github.com/alekspetrov/navigator/releases/tag/v4.7.0)

---

## The Problem

I kept hitting context limits in Claude Code.

Session 5: Claude forgot a function I just wrote.
Session 7: It hallucinated a class that didn't exist.
Session 8: "Context limit reached."

I checked the stats: **150,000 tokens loaded**. I'd used **8,000**.

**I was wasting 94% of my context window on documentation I never needed.**

---

## The Realization

This wasn't a bug. This was my workflow.

**Every AI session, same pattern**:
1. Load all project docs at start ("better to have everything")
2. Context fills with 150k tokens
3. AI gets overwhelmed (signal lost in noise)
4. Forgets recent changes
5. Session crashes
6. Start over

**The default approach—bulk loading—was the problem.**

Then I read Anthropic's context engineering docs. Two insights changed everything:

**Context engineering ≠ Prompt engineering**

```
Prompt engineering: Single query → optimize prompt
Context engineering: Multi-turn agent → curate context
```

**From Anthropic's docs** (literally):
```
Available context:          Curated context:
├── Doc 1                  ├── Doc 1 ✓
├── Doc 2                  ├── Doc 2 ✓
├── Doc 3                  └── Tool 1 ✓
├── Doc 4
└── Tool 1

Load strategically, not everything.
```

**Navigator implements this for your codebase.**

---

## The Solution

**Context engineering: Strategic curation over bulk loading**

### How It Works

**Traditional approach** (bulk loading):
```
Session start → Load all docs (150k) → Context 75% full → Work cramped
Result: Sessions die in 5-7 exchanges
```

**Navigator** (context engineering):
```
Session start:
├── Navigator/index (2k) ✓ Map of what exists
└── Current task (3k) ✓ What you're working on

As you work:
├── Need architecture? Load it (5k)
├── Hit a bug? Load SOP (2k)
└── On-demand, strategic

Result: Sessions last 20+ exchanges
```

**Your project**: 150k tokens available
**Navigator loads**: 12k tokens
**You save**: 138k tokens (92%)

**For actual work. Not documentation overhead.**

---

## The Proof

**Not estimates. Verified via OpenTelemetry.**

```
╔══════════════════════════════════════════════════════╗
║          NAVIGATOR EFFICIENCY REPORT                 ║
╚══════════════════════════════════════════════════════╝

📊 TOKEN USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your project documentation:     150,000 tokens
Loaded this session:             12,000 tokens
Tokens saved:                   138,000 tokens (92% ↓)

📈 SESSION METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context usage:                        35% (excellent)
Efficiency score:                  94/100 (excellent)

⏱️  TIME SAVED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estimated time saved:             ~42 minutes
```

**Check your own: Run `/nav:stats` after installing.**

---

## What Navigator Does

### Context Engineering Implementation

**1. Lazy Loading** - Load what you need, when you need it
```
Always: Navigator (2k) + Current task (3k)
On-demand: System docs (5k), SOPs (2k), Integration guides (3k)
Result: 90%+ context available for work
```

**2. Agent-Optimized Search** - Curated exploration, not bulk reading
```
Traditional: Read 20 files manually (80k tokens)
Navigator: Agent searches → Returns summary (8k tokens)
Savings: 90%
```

**3. Progressive Refinement** - Metadata first, details on-demand
```
Step 1: Load overview (2k)
Step 2: Identify needs
Step 3: Load relevant details (5k)
vs Loading everything: 15k
Savings: 53%
```

**4. Context Markers** - Compress decisions, not raw data
```
Full session: 200k tokens
Context marker: 5k tokens (decisions preserved)
Compression: 97.5%
```

**5. Autonomous Completion** - No manual prompts for predictable workflows
```
Feature complete → Auto-commits, updates docs, closes ticket
Zero "please commit" prompts
```

**These are patterns from Anthropic's context engineering docs, implemented.**

📖 **[Read the Philosophy](.agent/philosophy/CONTEXT-EFFICIENCY.md)** - Why this works
📖 **[See the Patterns](.agent/philosophy/PATTERNS.md)** - How to apply
📖 **[Avoid Anti-Patterns](.agent/philosophy/ANTI-PATTERNS.md)** - Common mistakes

---

## Quick Start

### Installation

```bash
# Claude Code plugin marketplace
/plugin marketplace add alekspetrov/navigator
/plugin install navigator

# Restart Claude Code
```

### Initialize Your Project

```bash
# In your project directory
"Initialize Navigator in this project"
```

Creates documentation structure:
```
your-project/
└── .agent/
    ├── DEVELOPMENT-README.md    # Navigator (your index)
    ├── philosophy/               # Context engineering principles
    ├── tasks/                    # Implementation plans
    ├── system/                   # Architecture docs
    ├── sops/                     # Standard procedures
    └── .nav-config.json         # Configuration
```

**Works with any codebase**: Rust, Python, JavaScript, Go, etc.

### Start Your Session

**Every session begins**:
```
"Start my Navigator session"
```

This loads:
- Navigator/index (2k tokens) - Map of your docs
- Current task (if configured with PM tools) - 3k tokens
- **Nothing else yet** - 195k tokens available for work

### Use Context Engineering

```
# Agent-optimized search (vs reading 15 files)
"Find all authentication implementation files"
→ Agent returns curated summary (8k vs 80k tokens)

# Progressive refinement (vs loading full docs)
"How does the payment system work?"
→ Loads overview → Drills down only if needed

# Lazy loading (vs bulk loading)
"Implement user profile feature"
→ Loads task doc → Adds architecture only when relevant
```

**You'll see the difference in `/nav:stats`**

---

## What's New in v4.7.0 (Latest)

**Interactive Onboarding** - Learn Navigator by doing, not just reading

### nav-onboard Skill

Two learning flows that teach Navigator through hands-on practice:

**Quick Start (~15 min)**:
```
"onboard me"
→ Auto-detect your project type
→ 3 essential skills with practice tasks
→ Get productive immediately
```

**Full Education (~25 min)**:
```
"teach me Navigator"
→ Philosophy primer (why context efficiency matters)
→ All 5 essential skills with practice
→ Generate personalized MY-WORKFLOW.md
```

### What You'll Learn (by doing)

| Task | What You Do | What You Create |
|------|-------------|-----------------|
| nav-start | "Start my Navigator session" | Loaded index |
| nav-marker | "Create checkpoint [name]" | .context-markers/*.md |
| nav-task | "Create task doc for [feature]" | .agent/tasks/TASK-XX.md |
| nav-sop | "Create SOP for [issue]" | .agent/sops/**/*.md |
| nav-compact | "Clear context and preserve" | .active marker |

### Project Auto-Detection

Detects your tech stack and recommends relevant skills:
- Frontend: React, Next.js, Vue, Angular, Svelte
- Backend: Express, FastAPI, Django, Go, Rust
- Database: PostgreSQL, MySQL, MongoDB + ORMs
- Testing: Jest, Pytest, etc.

### Personalized Workflow Guide

Generates `.agent/onboarding/MY-WORKFLOW.md` with:
- Project-specific workflow diagram
- Daily workflow checklist
- Skills reference with triggers

[Full v4.7.0 release notes](RELEASE-NOTES-v4.7.0.md)

---

## What Was in v4.6.0

**Architecture Optimization** - Native agents, token monitoring, cleanup

### Native Claude Code Agents

Two custom agents leveraging Claude Code's subagent system:

**navigator-research** - Codebase exploration with 60-80% token savings
```
"Use the navigator-research agent to explore how authentication works"
→ Samples representative files (not reading everything)
→ Returns concise summary with file references
→ Context isolation prevents pollution
```

**task-planner** - Implementation planning
```
"Use the task-planner agent to create a plan for adding dark mode"
→ Creates structured plans in .agent/tasks/ format
→ Identifies dependencies and critical path
→ Estimates effort realistically
```

### Token Budget Monitoring

Automatic context usage monitoring that warns before you hit limits:

```
[After tool calls when approaching limits]

==================================================
  CONTEXT CRITICAL: 87% used
  156,600 / 180,000 tokens

  Run: 'Clear context and preserve markers'
  Or:  /nav:compact
==================================================
```

- Warns at 70% usage
- Critical alert at 85%
- Auto-installed on init/upgrade

### Skills Cleanup

- Removed unused `auto-invoke: true` field (not used by Claude Code)
- Removed `nav-social-post` skill (misaligned with core purpose)
- Skills: 20 → 19

[Full v4.6.0 release notes](RELEASE-NOTES-v4.6.0.md)

---

## What's in v4.3.0 (Experimental)

**Multi-Claude Agentic Workflow Automation** - Parallel execution while maintaining 92% efficiency

### The Multi-Claude Concept

**Problem**: Single-Claude sequential execution
- One phase at a time (plan → impl → test → docs → review)
- Context fills up during long features
- No parallelism

**Solution**: Automated multi-Claude orchestration
```bash
./scripts/navigator-multi-claude.sh "Implement OAuth authentication"

Behind the scenes:
├── Orchestrator Claude: Creates plan (Phase 1)
├── Implementation Claude: Builds feature (Phase 2)
├── Testing Claude + Docs Claude: Parallel execution (Phase 3-4)
└── Review Claude: Analyzes changes (Phase 5)

Result: 12-21 minutes for complete feature
```

**Each Claude maintains 92% token efficiency** - Navigator principles applied to parallel architecture

### Status: Experimental

**Test results**: 30% full completion rate (3/10 workflows)
- ✅ Works: Simple features (1-2 file changes)
- ⚠️ Issues: Marker coordination timeouts, phase transitions
- 📋 Recommendation: Use with manual fallback readiness

**Try it**:
```bash
# Simple POC
./scripts/navigator-multi-claude-poc.sh "Add email validation"

# Full workflow
./scripts/navigator-multi-claude.sh TASK-42-feature-name
```

[Full v4.3.0 release notes](RELEASE-NOTES-v4.3.0.md) | [Report issues](https://github.com/alekspetrov/navigator/issues)

---

## What's in v4.0.0

**From Tool to Framework** - Philosophy, Metrics, Education

### Philosophy Foundation
- Context Efficiency Manifesto (`.agent/philosophy/CONTEXT-EFFICIENCY.md`)
- Anti-Patterns documentation (what kills sessions)
- Success Patterns (what works and why)

### Real Metrics
- `nav-stats` skill with efficiency scoring (0-100)
- OpenTelemetry-verified token usage
- Actual baseline calculations from your `.agent/` files

### Education Layer
- 4 comprehensive learning guides (69k tokens total)
- 3 interactive hands-on examples
- 3 decision frameworks for quick reference

**Master the principles, not just the patterns.**

---

## What Was New in v3.4.0

**Direct Figma MCP Integration** - Preprocessing pattern proven

**Before v3.4.0**:
```
Claude orchestrates → Call MCP → Save temp files →
Call MCP again → Process files → 15-20 steps, 150k tokens
```

**After v3.4.0**:
```
Python connects to Figma MCP directly →
Preprocesses → Returns clean data → 1 step, 12k tokens
```

**Results**:
- 95% orchestration reduction (20 steps → 1)
- 92% token reduction (150k → 12k)
- 75% faster (15 min → 5 min)
- Deterministic output (no hallucinations)

**This proves**: Python for deterministic, LLM for semantic.

📖 **[v3.4.0 Release Notes](RELEASE-NOTES-v3.4.0.md)** | **[Setup Guide](UPGRADE-v3.4.0.md)**

---

## Built-in Skills (19)

Navigator includes 19 skills that auto-invoke on natural language:

### Navigation & Session Management
```
"Start my Navigator session"              → nav-start
"Initialize Navigator in this project"    → nav-init
"Create context marker: feature-v1"       → nav-marker
```

### Development Workflow
```
"Create a React component for profile"    → frontend-component
"Add an API endpoint for posts"           → backend-endpoint
"Create a database migration for users"   → database-migration
```

### Design & Documentation
```
"Review this Figma design: [URL]"         → product-design
"Archive TASK-05 documentation"           → nav-task
"Create an SOP for debugging auth"        → nav-sop
```

**No commands to memorize** - Skills auto-invoke from natural language.

📖 **[All 19 Skills](.agent/DEVELOPMENT-README.md#available-skills)**

---

## Context Efficiency Score

Navigator tracks how well you're using context engineering:

```bash
/nav:stats
```

**Score calculation** (0-100):
- **Token savings** (40 points): 85%+ = 40 points
- **Cache efficiency** (30 points): 100% = 30 points
- **Context usage** (30 points): <40% = 30 points

**Interpretation**:
- **90-100**: Excellent - Optimal context engineering
- **80-89**: Good - Minor improvements possible
- **70-79**: Fair - Review lazy-loading strategy
- **<70**: Check anti-patterns (wasting context)

**Your metrics. Your project. Your savings.**

---

## Real Workflows

### Feature Implementation
```
Load:
├── Navigator (2k)
├── Task doc (3k)
└── System architecture (5k)

Total: 10k tokens
Session: 15 exchanges to completion
Context at end: 45% (comfortable)
```

### Bug Fix
```
Load:
├── Navigator (2k)
├── Debugging SOP (2k)
└── Agent search results (5k)

Total: 9k tokens
Session: 8 exchanges to fix
Context at end: 30% (plenty of room)
```

### Design Review
```
Load:
├── Navigator (2k)
├── Figma data (12k, preprocessed)
└── Design system docs (5k)

Total: 19k tokens
Session: Complete review in 5 minutes
vs Without preprocessing: 150k tokens, 15 minutes
```

**Efficiency is measurable. Check yours: `/nav:stats`**

---

## Why This Works

### Context Engineering Principles

From Anthropic's docs on context engineering:

**1. Curate, don't bulk load**
```
Available context (left) → Curated context (right)
Select what matters, not everything
```
**Navigator implements**: Lazy loading, agent search, progressive refinement

**2. Right tool for the job**
```
Deterministic tasks → Traditional code (Python, bash)
Semantic tasks → LLM (understanding, generation)
```
**Navigator implements**: Preprocessing (v3.4.0 Figma), autonomous completion

**3. Compress decisions, not data**
```
200k session → Extract decisions → 5k marker
Preserve what matters, not transcripts
```
**Navigator implements**: Context markers (97.5% compression)

📖 **[Context Engineering Philosophy](.agent/philosophy/CONTEXT-EFFICIENCY.md)**

---

## Project Management Integration

**Optional**: Connect Navigator to your PM tool

### Supported
- **Linear** (MCP) - Full integration
- **GitHub Issues** (gh CLI) - Via gh command
- **Jira** (API) - Via API calls
- **Manual** - Documentation-only mode (default)

### With PM Integration
```
"Start my Navigator session"

→ Checks Linear for assigned tasks
→ Loads current task implementation plan
→ Shows task context (3k tokens)
```

When done:
```
→ Auto-closes ticket
→ Archives documentation
→ Creates completion marker
```

**Zero-config works without PM tools.** Integration is enhancement, not requirement.

📖 **[PM Integration Guide](.agent/sops/integrations/linear-setup.md)**

---

## Configuration

Minimal configuration required. Works with defaults.

**Optional** `.agent/.nav-config.json`:
```json
{
  "version": "3.4.0",
  "project_management": "none",
  "task_prefix": "TASK",
  "auto_load_navigator": true,
  "compact_strategy": "conservative"
}
```

**Auto-detected**:
- Project type (JS, Python, Rust, etc.)
- Available integrations
- Documentation structure

**No setup required to start.**

---

## Documentation Structure

Navigator creates organized, discoverable documentation:

```
.agent/
├── DEVELOPMENT-README.md           # Navigator (always load first)
│
├── philosophy/                     # Context engineering principles
│   ├── CONTEXT-EFFICIENCY.md      # Why Navigator exists
│   ├── ANTI-PATTERNS.md            # Common mistakes
│   └── PATTERNS.md                 # Success patterns
│
├── tasks/                          # Implementation plans
│   ├── TASK-01-feature.md
│   └── archive/                    # Completed tasks
│
├── system/                         # Architecture docs
│   ├── architecture.md
│   ├── database.md
│   └── api-design.md
│
└── sops/                           # Standard procedures
    ├── debugging/
    ├── deployment/
    └── integrations/
```

**Strategy**:
- Always load: `DEVELOPMENT-README.md` (2k tokens)
- On-demand: Everything else (as needed)
- Result: 90%+ savings

---

## Examples

### Before Navigator

```bash
# Load all docs
cat .agent/**/*.md  # 150k tokens

# Session
User: "Add auth to API"
AI: "Here's the implementation..."
[5 exchanges]
AI: "What was that function you just wrote?"
[7 exchanges]
Error: Context limit reached

# Restart, start over
```

### With Navigator

```bash
# Strategic loading
"Start my Navigator session"  # 2k tokens

# Work
User: "Add auth to API"
Navigator: Loads task doc (3k) + architecture on-demand (5k)
AI: "Here's the implementation following your patterns..."
[20 exchanges, feature complete]

Context usage: 35%
Efficiency: 94/100
Time saved: 42 minutes
```

**Try it: Install Navigator, check `/nav:stats` after your first session.**

---

## Advanced Features

### Context Markers
```
"Create context marker: auth-implementation-v1"

Saves:
├── Decisions made (what & why)
├── Code written (summary)
├── Next steps

Compression: 200k → 5k (97.5%)

Resume later:
"Resume from marker: auth-implementation-v1"
→ Full context restored in seconds
```

### Agent-Optimized Search
```
"Find all API endpoints and explain routing"

Agent:
├── Searches codebase (50 files found)
├── Reads relevant files
├── Extracts patterns
└── Returns summary (200 tokens)

vs Manual: Read 50 files = 80k tokens
Savings: 99.8%
```

### Skill Generation
```
"Create a skill for adding database indexes"

Navigator:
├── Analyzes your project patterns
├── Generates custom skill
├── Adds functions and templates
└── Auto-invokes on: "Add index for users table"

Result: Automation of repetitive workflows
```

### Real-Time Metrics
```
Session statistics (live):
├── Tokens loaded: 12k / 200k (6%)
├── Cache efficiency: 100%
├── Efficiency score: 94/100
└── Time saved: ~38 minutes
```

---

## Performance

**Token Efficiency**:
- Documentation loading: 150k → 12k (92% ↓)
- Agent searches: 80k → 8k (90% ↓)
- Context markers: 200k → 5k (97.5% ↓)

**Time Savings**:
- Design review: 15 min → 5 min (67% ↓)
- Codebase search: 10 min → 30 sec (95% ↓)
- Context restore: Hours → Seconds (99%+ ↓)

**Session Longevity**:
- Without Navigator: 5-7 exchanges
- With Navigator: 20+ exchanges
- Improvement: 3-4x longer sessions

**Verified via OpenTelemetry** (not file size estimates)

📖 **[Performance Details](PERFORMANCE.md)** | **[Architecture](ARCHITECTURE.md)**

---

## Contributing

Navigator is open source and community-driven.

**Ways to contribute**:
- Share your efficiency scores (`/nav:stats` screenshots)
- Submit patterns you discovered
- Create project-specific skills
- Report issues or request features

📖 **[Contributing Guide](CONTRIBUTING.md)** | **[Skill Creation Guide](.agent/sops/development/creating-skills.md)**

---

## Philosophy

**Navigator isn't about features. It's about principles.**

From Anthropic's context engineering:
- Curate context, don't bulk load
- Right tool for the job (Python + LLM)
- Compress decisions, not data

Navigator implements these patterns for your codebase.

**Result**: 92% token savings. 94/100 efficiency scores. Verified, not claimed.

📖 **[Read the Manifesto](.agent/philosophy/CONTEXT-EFFICIENCY.md)**

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Links

**Documentation**:
- 📖 [Philosophy](.agent/philosophy/CONTEXT-EFFICIENCY.md) - Why Navigator exists
- 📖 [Patterns](.agent/philosophy/PATTERNS.md) - Success patterns
- 📖 [Anti-Patterns](.agent/philosophy/ANTI-PATTERNS.md) - What to avoid
- 📖 [Development Guide](.agent/DEVELOPMENT-README.md) - Complete reference

**Releases**:
- 🚀 [v3.4.0 Release Notes](RELEASE-NOTES-v3.4.0.md) - Direct Figma MCP
- 📋 [All Releases](https://github.com/alekspetrov/navigator/releases)
- 🔄 [Migration Guide](MIGRATION.md) - Upgrade to v3.0+

**Community**:
- 💬 [GitHub Discussions](https://github.com/alekspetrov/navigator/discussions)
- 🐛 [Issues](https://github.com/alekspetrov/navigator/issues)
- ⭐ [Star on GitHub](https://github.com/alekspetrov/navigator)

---

## Multi-Claude Workflow (v4.3.0)

**Automated end-to-end feature implementation using parallel Claude instances.**

### What is it?

Orchestrates multiple specialized Claude sessions to implement features from ticket → tests → PR → ticket closure, fully automated.

```
Orchestrator (Bash)
├─ Planning Claude    → Creates implementation plan
├─ Impl Claude        → Writes code
├─ Testing Claude     → Generates & runs tests (parallel)
├─ Docs Claude        → Creates documentation (parallel)
├─ Review Claude      → Code quality analysis
├─ Integration        → Commits, creates PR
└─ PM Integration     → Closes ticket in PM system
```

### Installation

```bash
# 1. Clone Navigator scripts
curl -o scripts/navigator-multi-claude.sh \
  https://raw.githubusercontent.com/alekspetrov/navigator/main/scripts/navigator-multi-claude.sh

chmod +x scripts/navigator-multi-claude.sh

# 2. Verify installation
./scripts/navigator-multi-claude.sh --help
```

### Prerequisites

- Navigator plugin installed (`claude plugin install navigator`)
- `claude` CLI available
- Git repository
- (Optional) `gh` CLI for PR creation
- (Optional) GitHub Issues for PM integration

### Usage

**Basic workflow**:
```bash
# 1. Create task file
cat > .agent/tasks/TASK-23-add-auth.md << 'EOF'
# TASK-23: Add Authentication

**Status**: 📋 Todo

## Context
Add JWT-based authentication to API endpoints.

## Requirements
- JWT token generation
- Token validation middleware
- Protect /api/* routes
EOF

# 2. Run multi-Claude workflow
./scripts/navigator-multi-claude.sh TASK-23-add-auth

# Workflow executes automatically:
# ✅ Phase 1: Planning (creates implementation plan)
# ✅ Phase 2: Implementation (writes code)
# ✅ Phase 3-4: Testing + Documentation (parallel)
# ✅ Phase 5: Review (code quality analysis)
# ✅ Phase 6: Integration (commit + PR)
# ✅ Phase 7: PM Integration (closes ticket)
```

### Features

**Token Efficiency**:
- Each sub-Claude can spawn Task agents for exploration
- 60-80% token savings vs manual file reading
- Multi-level agent hierarchy: Orchestrator → Sub-Claudes → Task Agents

**Failure Reporting**:
- Sub-Claudes create `.failed` markers with error details
- Instant failure detection (no timeout waits)
- Clear error messages for debugging

**Parallel Execution**:
- Testing and Documentation run simultaneously
- 2x faster than sequential execution

**PM Integration**:
- Automatically closes GitHub Issues when complete
- Creates PR with detailed summary
- Updates task status throughout workflow

### Architecture

```
┌─────────────────────────────────────┐
│ Bash Orchestrator                   │
│ - File-based state management       │
│ - Phase coordination                │
│ - Error handling                    │
└─────────────────────────────────────┘
              │
      ┌───────┼───────┬───────┬───────┐
      ▼       ▼       ▼       ▼       ▼
   Planning  Impl  Testing  Docs  Review
   Claude   Claude  Claude  Claude Claude
      │       │       │       │       │
      └───────┴───────┴───────┴───────┘
              ▼
      Can spawn Task agents
      (Explore, Plan, etc.)
```

### Example Output

```bash
🎯 Navigator Multi-Claude Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: Planning (Orchestrator)
✅ Plan created: .agent/tasks/task-23-plan.md

Phase 2: Implementation
✅ Implementation complete

Phase 3 & 4: Parallel Testing + Documentation
✅ Testing complete (41s)
✅ Documentation complete (53s)
✅ All quality gates passed

Phase 5: Review
✅ Review complete: APPROVED (Quality: 9/10)

Phase 6: Integration
✅ Changes committed
✅ PR created: https://github.com/user/repo/pull/42

Phase 7: PM Integration
✅ Ticket #23 closed

✅ Multi-Claude Workflow Complete
Total time: 7m 14s
```

### Advanced Configuration

**Custom phase timeouts**:
```bash
# Edit wait_for_file() timeout in script
local timeout=300  # 5 minutes default
```

**Enable/disable phases**:
```bash
# Comment out phases in main() function
# Skip documentation phase example:
# docs_output=$(claude -p ...) &  # ← Comment this out
```

**PM Integration**:
- Works with GitHub Issues by default
- Requires `gh` CLI authenticated
- Task ID must match format: `TASK-<number>`

### Troubleshooting

**Timeout errors**:
- Check `.agent/tasks/*-failed` files for error details
- Increase timeout in `wait_for_file()` function
- Sub-Claude logs available in workflow output

**Missing task file**:
```bash
# Ensure task file exists
ls .agent/tasks/TASK-23*.md

# Task file must start with "# TASK-XX: Title"
```

**PM integration fails**:
```bash
# Verify gh CLI auth
gh auth status

# Check task ID format (must be TASK-<number>)
./scripts/navigator-multi-claude.sh TASK-23-feature  # ✅ Good
./scripts/navigator-multi-claude.sh add-feature      # ❌ Bad
```

### Performance Metrics

Real-world example (TASK-22: Simple Console Logger):

| Phase | Duration | Token Savings |
|-------|----------|---------------|
| Planning | 58s | 75% (using Explore agent) |
| Implementation | 1m 44s | 65% (pattern analysis via agent) |
| Testing | 41s | 70% (test pattern discovery) |
| Documentation | 53s | 68% (doc style matching) |
| Review | 2m 45s | 80% (multi-file analysis) |
| **Total** | **7m 14s** | **~70% average** |

### Version History

- **v4.3.0**: Task agent delegation in all phases
- **v4.2.0**: Failure reporting + PM integration (Phase 7)
- **v4.1.0**: Parallel testing + documentation
- **v4.0.0**: Initial multi-Claude POC

---

## Quick Commands

```bash
# Start session
"Start my Navigator session"

# Check efficiency
/nav:stats

# Create marker
"Create context marker: checkpoint-name"

# Initialize project
"Initialize Navigator in this project"

# Get help
"How do I use Navigator?"
```

---

**Transform your AI coding workflow from wasteful to efficient.**

**Install Navigator. Start your first session. Check `/nav:stats`.**

**See the difference: 92% token savings, verified.**
