# Learning Task 2: Creating Context Markers

**Skill**: nav-marker
**Time**: 3-5 minutes
**Difficulty**: Beginner

## Why This Matters

Context markers are "save points" for your AI sessions. When you take a break or clear context, the marker preserves what you were working on. A 130k token conversation compresses to ~3k tokens - 97% reduction.

## The Task

### Step 1: Create a Marker

**DO THIS NOW:**
```
Type: "Create checkpoint learning-test"
```

### Step 2: Observe What Happens

**WHAT SHOULD HAPPEN:**

1. System creates marker file in `.agent/.context-markers/`
2. Marker captures:
   - What you were working on
   - Files you modified (if any)
   - Technical decisions made
   - Next steps

You should see:
```
✅ Context marker created!

Marker: learning-test
File: .agent/.context-markers/[timestamp]_learning-test.md
Size: ~2-3 KB

This marker captures:
- Session summary
- Current focus
- Next steps

To restore later: "Load marker learning-test"
```

### Step 3: Verify the Marker

**DO THIS:**
```
Ask: "Show me the marker file that was just created"
```

You should see structured content:
- Conversation Summary
- Files Modified
- Current Focus
- Technical Decisions
- Next Steps

## Validation

This task is complete when:
- [ ] Marker created with "Create checkpoint learning-test"
- [ ] File exists in `.agent/.context-markers/`
- [ ] Marker contains session summary

**Automatic check**: File `.agent/.context-markers/*learning-test*.md` exists.

## Pro Tip

Create markers:
- Before breaks (lunch, EOD)
- Before risky refactors
- At milestones (feature complete)
- Before clearing context

Good names: `before-refactor`, `auth-complete`, `eod-friday`
Bad names: `temp`, `test1`, `asdf`

## What You Learned

1. Markers compress 130k → 3k tokens (97% reduction)
2. They preserve context across sessions
3. Create them before breaks and risky changes

---

**When done, say "done" to continue to the next task.**
