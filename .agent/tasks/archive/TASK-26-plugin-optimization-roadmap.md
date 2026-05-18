# TASK-26: Navigator Plugin Optimization Roadmap

**Status**: ✅ Completed
**Created**: 2025-11-27
**Priority**: High

## Context

Based on Claude Code documentation review, identified optimization opportunities for Navigator plugin architecture.

## Findings Summary

| Aspect | Current | Recommendation |
|--------|---------|----------------|
| `auto-invoke: true` field | Added to all 20 skills | Remove - description quality is actual mechanism |
| Skill descriptions | Varied format | Standardize to structured format |
| nav-social-post | In plugin.json | Remove - misaligned with core purpose |
| Subagents | Not used | Integrate Claude Code's agent system |
| Hooks | Not used | Add token budget monitoring |

---

## Phase 1: Quick Wins (Immediate)

### Task 1.1: Remove `auto-invoke: true` Field
**Impact**: Code cleanup, no functional change
**Effort**: 10 min

The `auto-invoke: true` frontmatter field is likely ignored by Claude Code. Auto-invocation is determined by description quality, not a boolean flag.

**Action**: Remove from all 19 SKILL.md files (nav-init has triggers array which is useful, keep that).

### Task 1.2: Standardize Skill Descriptions
**Impact**: Better auto-invocation reliability
**Effort**: 30 min

Standardize all descriptions to:
```yaml
description: [What it does]. Auto-invoke when user says "[phrase 1]", "[phrase 2]", "[phrase 3]". Do NOT invoke if [condition].
```

### Task 1.3: Remove nav-social-post
**Impact**: Cleaner plugin focus
**Effort**: 5 min

Misaligned with Navigator's core documentation-efficiency mission. Move to separate tool or archive.

---

## Phase 2: Subagent Integration (Medium-term)

### Task 2.1: Research Claude Code Subagent System
**Impact**: Context isolation, better lazy-loading
**Effort**: 1 hour research

Understand:
- How subagents differ from Task tool
- Context isolation mechanics
- Integration with existing skills

### Task 2.2: Create Navigator Research Subagent
**Impact**: Isolated codebase exploration
**Effort**: 2 hours

Purpose: Explore codebases without polluting main context
- Tools: Read, Glob, Grep (no Write)
- Returns: 3-5 key files + suggestions
- Aligns with lazy-loading philosophy

### Task 2.3: Create Task Planner Subagent
**Impact**: Better implementation planning
**Effort**: 2 hours

Purpose: Create implementation plans without execution
- Tools: Read, Glob, Grep, Write (to .agent/tasks/)
- Returns: Structured task document

---

## Phase 3: Automation (Future)

### Task 3.1: Add Token Budget Hook
**Impact**: Automatic compact suggestions
**Effort**: 1 hour

Post-command hook to check token usage and suggest `/nav:compact` when approaching limits.

### Task 3.2: Add Task Completion Hook
**Impact**: Autonomous workflow
**Effort**: 1 hour

Auto-archive tasks, update documentation after completion.

---

## Execution Order

```
Phase 1 (Today):
├── 1.1 Remove auto-invoke field
├── 1.2 Standardize descriptions
└── 1.3 Remove nav-social-post

Phase 2 (Next session):
├── 2.1 Research subagents
├── 2.2 Create research subagent
└── 2.3 Create planner subagent

Phase 3 (Future):
├── 3.1 Token budget hook
└── 3.2 Task completion hook
```

---

## Success Criteria

- [x] All SKILL.md files have standardized descriptions
- [x] No unused `auto-invoke: true` fields
- [x] nav-social-post removed from plugin
- [x] 2 subagents integrated (navigator-research, task-planner)
- [x] Token budget monitoring active (hooks/monitor-tokens.py)

---

## Notes

- Subagent integration is highest value opportunity
- Current skill count (20→19) is optimal
- ~3.6-5.2k token overhead for skill metadata is acceptable
