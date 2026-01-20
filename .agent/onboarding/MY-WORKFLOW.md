# My Navigator Workflow

**Generated**: 2025-12-09 11:39
**Project**: navigator
**Type**: Library
**Stack**: Not detected

---

## Workflow Diagram

```
SESSION START
     │
     ▼
┌─────────────┐
│  nav-start  │  "Start my Navigator session"
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Load task doc      │  (if continuing work)
└──────┬──────────────┘
       │
       ├────────────────────────┐
       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐
│frontend-component│   │ backend-endpoint │
└───────┬──────────┘   └────────┬─────────┘
        │                       │
        ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│  frontend-test   │   │   backend-test   │
└───────┬──────────┘   └────────┬─────────┘
        │                       │
        └───────────┬───────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │     nav-task        │  "Archive TASK-XX"
          └──────┬──────────────┘
                 │
                 ▼
          ┌─────────────────────┐
          │    nav-marker       │  "Create checkpoint"
          └──────┬──────────────┘
                 │
                 ▼
          ┌─────────────────────┐
          │   nav-compact       │  (when switching)
          └─────────────────────┘
```

---

## Daily Workflow

### Morning Routine

1. **Start session**: "Start my Navigator session"
2. **Check tasks**: Review `.agent/tasks/` index for current work
3. **Load context**: Read relevant task documentation

### During Development

4. **Use dev skills**: development skills
5. **Create checkpoints**: Before breaks or risky changes
6. **Document decisions**: Update task doc with technical choices

### After Completing Work

7. **Archive task**: "Archive TASK-XX documentation"
8. **Capture solutions**: "Create SOP for [solved issue]"
9. **Final checkpoint**: "Create checkpoint [feature-name]-complete"

### End of Session

10. **Clear context**: "Clear context and preserve markers" (if switching tasks)
11. **Or keep context**: If continuing same work tomorrow

---

## Skills Reference

### Essential Skills (Use Daily)

| Skill | Description | Trigger |
|-------|-------------|---------|
| nav-start | Start sessions efficiently | "Start my Navigator session" |
| nav-task | Document what you build | "Create task doc for [feature]" |
| nav-sop | Capture solutions for reuse | "Create SOP for [issue]" |
| nav-marker | Save progress checkpoints | "Create checkpoint [name]" |
| nav-compact | Clear context without losing work | "Clear context and preserve markers" |

### Optional Skills (Advanced)

| Skill | Description | Trigger |
|-------|-------------|---------|
| nav-skill-creator | Create custom skills | "Create a skill for [workflow]" |

---

## Quick Reference

| Action | Say This |
|--------|----------|
| Start session | "Start my Navigator session" |
| Save progress | "Create checkpoint [name]" |
| Document feature | "Create task doc for [feature]" |
| Archive feature | "Archive TASK-XX documentation" |
| Capture solution | "Create SOP for [issue]" |
| Clear context | "Clear context and preserve markers" |

---

## Tips for Library Projects

- Use task docs to capture library/package decisions
- SOPs for build and publish workflows
- Markers before major refactors

---

## Next Steps

1. **Start every session** with: "Start my Navigator session"
2. **Create checkpoints** before breaks: "Create checkpoint [name]"
3. **Document features** when complete: "Archive TASK-XX"
4. **Capture solutions** after debugging: "Create SOP for [issue]"
5. **Clear context** when switching tasks: "Clear context and preserve"

---

*This workflow was personalized for your library project.*
*Update as your needs evolve.*

**Navigator Version**: 4.6.0
