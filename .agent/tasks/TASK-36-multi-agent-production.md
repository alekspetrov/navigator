# TASK-36: Multi-Agent Production Polish

**Status**: 📋 Backlog
**Created**: 2025-01-23
**Version**: TBD (post-6.0)
**Priority**: High
**Builds On**: TASK-19, TASK-25

## Summary

Polish the multi-Claude orchestration system into production-ready feature with one-command setup, visual monitoring, and reliable coordination.

## Context

Foundation exists (TASK-19, TASK-25):
- Basic orchestration scripts
- Role-specific CLAUDE.md templates
- Marker-based coordination
- Retry logic and timeout monitoring
- ~30% → 90% success rate achieved

Gap: Not user-friendly enough for general adoption. Requires manual setup, no visual feedback, coordination is fragile.

## Vision

```bash
# One command to spawn parallel agents
"Run multi-agent workflow for TASK-XX"

# Visual dashboard shows:
┌─────────────────────────────────────────────────┐
│ Multi-Agent Workflow: TASK-XX                   │
├─────────────────────────────────────────────────┤
│ orchestrator  ████████████████░░░░  80%  IMPL   │
│ implementer   ████████████████████  100% DONE   │
│ tester        ██████████░░░░░░░░░░  50%  RUN    │
│ reviewer      ░░░░░░░░░░░░░░░░░░░░  0%   WAIT   │
│ documenter    ░░░░░░░░░░░░░░░░░░░░  0%   WAIT   │
├─────────────────────────────────────────────────┤
│ Tokens: 12k/35k budget │ Time: 4:32 elapsed     │
└─────────────────────────────────────────────────┘
```

## Requirements

### R1: One-Command Setup
- Natural language: "Setup multi-agent for this task"
- Auto-creates worktrees with role-specific CLAUDE.md
- Auto-configures marker directories
- Validates prerequisites (git clean, etc.)

### R2: Visual Dashboard
- Real-time progress for each agent
- Phase tracking (RESEARCH → IMPL → VERIFY → DONE)
- Token usage per agent
- Error/retry status
- Terminal-based (no external dependencies)

### R3: Reliable Coordination
- Marker-based handoffs with verification
- Automatic retry on marker failures
- Timeout detection with recovery
- Dependency graph enforcement (reviewer waits for impl+test)

### R4: Role Templates
- Minimal context per role (~5k tokens each)
- Clear responsibilities and boundaries
- Handoff protocols documented
- Available roles: orchestrator, implementer, tester, reviewer, documenter, simplifier

### R5: Resource Management
- Parallel execution limits (configurable)
- Token budget per agent
- Automatic cleanup of worktrees
- Session persistence for resume

## Technical Design

### Orchestration Flow
```
User Request
    ↓
Orchestrator (main terminal)
    ├─→ Implementer (worktree-impl/)
    ├─→ Tester (worktree-test/) [waits for impl]
    ├─→ Reviewer (worktree-review/) [waits for impl+test]
    └─→ Documenter (worktree-docs/) [waits for review]
```

### Marker Protocol
```
.context-markers/
├── workflow-TASK-XX/
│   ├── phase-research-complete.md
│   ├── phase-impl-complete.md
│   ├── phase-test-complete.md
│   ├── phase-review-complete.md
│   └── workflow-complete.md
```

### Dashboard Implementation
- Shell script with ANSI colors
- Polls marker directory for status
- Shows agent logs on selection
- Ctrl+C graceful shutdown

## Success Criteria

- Single command spawns full workflow
- Visual feedback throughout execution
- 95%+ success rate on standard features
- 3x faster than sequential (measured)
- Token budget respected (35k total vs 70k single session)

## Open Questions

1. **Agent communication**: Markers only, or add direct channel?
2. **Failure handling**: Retry agent, or fail entire workflow?
3. **Customization**: User-defined roles/phases?
4. **CI/CD**: GitHub Actions integration priority?

## References

- TASK-19: Multi-Claude Agentic Workflow (foundation)
- TASK-25: Fix Multi-Claude Reliability (retry/recovery)
- Inspiration: GitHub Copilot Workspace parallel agents
