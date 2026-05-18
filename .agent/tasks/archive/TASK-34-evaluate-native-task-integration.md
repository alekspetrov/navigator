# TASK-34: Evaluate Native Task Integration

**Status**: ❌ Won't Do
**Created**: 2025-01-22
**Priority**: Low

---

## Context

Claude Code v2.1.16 introduced native task management:
- `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`
- Dependency tracking (blockedBy/blocks)
- Status workflow (pending → in_progress → completed)

**Key Finding**: Native tasks are **session-only** (not persisted). Navigator's `.agent/` documentation system provides persistent tracking.

## Question to Evaluate

Should Navigator use native tasks for **in-session tracking** while keeping `.agent/` for **persistence**?

```
Native Tasks (ephemeral)     Navigator (persistent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TaskCreate/Update            .agent/tasks/TASK-XX.md
Session-only                 Git-tracked
UI integration (maybe)       Documentation system
Dependency tracking          Full implementation plans
```

## Potential Integration

```
Loop Mode:
  - Use TaskCreate for each iteration
  - Use TaskUpdate for phase transitions
  - Native tasks show progress in UI
  - Navigator handles EXIT_SIGNAL logic

Task Mode:
  - TaskCreate for detected substantial task
  - Phase tracking via task updates
  - .agent/ for persistent documentation
```

## Why This May NOT Be Needed

1. Navigator's WORKFLOW CHECK already enforces workflow
2. NAVIGATOR_STATUS blocks are visible in conversation
3. .agent/ provides persistence native tasks lack
4. Additional complexity for marginal benefit

## Decision Criteria

- [ ] Does native task UI provide value over inline status?
- [ ] Is session-only tracking sufficient for loop iterations?
- [ ] Does dependency tracking add value to Navigator workflow?
- [ ] Is the integration complexity worth it?

## Action

**Won't Do** - Native task tools (TaskCreate, TaskUpdate, TaskGet, TaskList) are not available in Claude Code environment. See `poc-1769186747-evaluation-report.md` for full analysis.

## Resolution

- POC poc-1769186747 conducted 2025-01-23
- Native task tools confirmed unavailable
- TodoWrite + NAVIGATOR_STATUS blocks provide equivalent functionality
- No integration path exists

---

**Last Updated**: 2025-01-23
**Closed**: 2025-01-23 (Won't Do - tools unavailable)
