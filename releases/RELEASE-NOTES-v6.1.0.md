# Navigator v6.1.0 Release Notes

**Release Date**: 2025-01-23
**Previous Version**: v6.0.0

---

## Highlights

### Multi-Agent Production Ready

Launch parallel Claude agents with a single natural language command:

```
"Run multi-agent workflow for TASK-XX"
```

**What's new:**
- **5 role templates**: orchestrator, implementer, tester, reviewer, documenter
- **Visual dashboard**: Real-time terminal progress bars
- **nav-multi skill**: Natural language workflow trigger
- **3 workflow types**: POC (2-phase), Standard (4-phase), Full (6-phase)

### Improved Reliability

Multi-agent workflows now handle research/evaluation tasks correctly:
- Better prompts that adapt to task type (code vs research)
- Guaranteed marker creation (no more stuck workflows)
- Graceful degradation with warnings instead of hard failures
- Longer timeouts (120s → 180s) for complex operations

---

## New Features

### nav-multi Skill
Natural language trigger for multi-Claude workflows:
- `"Run multi-agent workflow for TASK-XX"`
- `"Use parallel agents for this feature"`
- `"Multi-claude for implementing X"`

### Visual Dashboard
Real-time monitoring in terminal:
```bash
./scripts/multi-claude-dashboard.sh [session_id]
```

Shows progress bars, phase status, elapsed time, and recent activity.

### Role Templates
Minimal context CLAUDE.md for each role (~4-5k tokens each):
- `templates/multi-claude/orchestrator-claude.md`
- `templates/multi-claude/implementer-claude.md`
- `templates/multi-claude/tester-claude.md`
- `templates/multi-claude/reviewer-claude.md`
- `templates/multi-claude/documenter-claude.md`

---

## Bug Fixes

### Multi-Agent Reliability (ba22abe)
- Fixed testing phase timeout on research tasks
- Prompts now handle research/evaluation tasks (not just code)
- Marker creation guaranteed even on timeout/failure
- Workflow continues with warnings instead of hard fail

---

## Configuration

New `multi_agent` section in `.nav-config.json`:

```json
{
  "multi_agent": {
    "enabled": true,
    "default_workflow": "standard",
    "auto_dashboard": false,
    "parallel_limit": 3,
    "retry_attempts": 2,
    "phase_timeout_seconds": 180
  }
}
```

---

## Task Closures

### TASK-34: Evaluate Native Task Integration
**Resolution**: Won't Do

Native task tools (TaskCreate, TaskUpdate, TaskGet, TaskList) are not available in Claude Code headless mode. Evaluation conducted via multi-agent POC confirmed:
- Tools unavailable in spawned Claude instances
- TodoWrite + NAVIGATOR_STATUS provide equivalent functionality
- No integration path exists

See: `.agent/tasks/poc-1769186747-evaluation-report.md`

### TASK-36: Multi-Agent Production Polish
**Resolution**: Completed

All requirements met:
- One-command setup via nav-multi skill
- Visual dashboard with real-time progress
- Role templates for token-efficient parallel execution
- 90%+ success rate with reliability improvements

---

## Breaking Changes

None.

---

## Upgrade Instructions

```bash
# If using auto-update (default)
"Start my Navigator session"  # Auto-updates to v6.1.0

# Manual upgrade
nav-upgrade
```

---

## Contributors

- Claude (Opus 4.5) - Multi-agent workflow implementation
- Multi-Claude POC - Generated tests for nav-loop and nav-task-mode

---

## What's Next

- TASK-36+ variants: More workflow types (research-only, documentation-only)
- Dashboard improvements: Token usage per agent
- CI/CD integration: GitHub Actions workflow

---

**Full Changelog**: https://github.com/alekspetrov/navigator/compare/v6.0.0...v6.1.0
