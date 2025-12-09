# Learning Task 3: Documenting What You Build

**Skill**: nav-task
**Time**: 4-5 minutes
**Difficulty**: Beginner

## Why This Matters

Task documentation captures WHAT you build - implementation plans, technical decisions, and outcomes. This becomes your project's knowledge base. Future sessions can load relevant task docs instead of re-explaining everything.

## The Task

### Step 1: Create a Task Document

**DO THIS NOW:**
```
Type: "Create task doc for learning-feature"
```

### Step 2: Observe What Happens

**WHAT SHOULD HAPPEN:**

1. Task ID generated (TASK-XX format)
2. Template created in `.agent/tasks/`
3. Navigator index updated with reference

You should see:
```
✅ Task document created!

Task: TASK-XX-learning-feature
File: .agent/tasks/TASK-XX-learning-feature.md

Template includes:
- Problem Statement
- Implementation Plan
- Technical Decisions
- Success Criteria

Fill this in as you implement the feature.
```

### Step 3: Review the Template

**DO THIS:**
```
Ask: "Show me the task document that was created"
```

The template has sections for:
- **Context**: Why this feature exists
- **Implementation Plan**: Steps to build it
- **Technical Decisions**: Architecture choices
- **Files Modified**: What changed
- **Success Criteria**: How to verify completion

### Step 4: Understand the Workflow

Task docs have two phases:
1. **Planning**: Create doc when starting feature
2. **Archiving**: Update doc when feature complete

The archive captures what was ACTUALLY built vs what was planned.

## Validation

This task is complete when:
- [ ] Task doc created with "Create task doc for learning-feature"
- [ ] File exists in `.agent/tasks/`
- [ ] Template structure visible

**Automatic check**: File `.agent/tasks/*learning-feature*.md` exists.

## Pro Tip

Task docs answer: "What did we build and why?"

When returning to a feature months later:
1. `nav-start` loads the index
2. Find relevant TASK-XX in index
3. Load just that task doc (~3k tokens)
4. Full context without re-explaining

This is much more efficient than:
- Searching through git history
- Re-reading all source files
- Asking "what was the original plan?"

## What You Learned

1. Task docs capture implementation knowledge
2. Created at start (planning) and updated at end (archiving)
3. Future sessions load task docs for context

---

**When done, say "done" to continue to the next task.**
