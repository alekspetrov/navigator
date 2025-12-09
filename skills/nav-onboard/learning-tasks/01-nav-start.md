# Learning Task 1: Starting Navigator Sessions

**Skill**: nav-start
**Time**: 3-5 minutes
**Difficulty**: Beginner

## Why This Matters

Every Navigator session begins with `nav-start`. It loads the documentation index (~2k tokens) instead of all documentation at once (~150k tokens). This is the foundation of Navigator's 92% token reduction.

## The Task

### Step 1: Start Your Session

**DO THIS NOW:**
```
Type: "Start my Navigator session"
```

### Step 2: Observe What Happens

**WHAT SHOULD HAPPEN:**

1. Navigator loads DEVELOPMENT-README.md (the index)
2. Session summary appears showing:
   - Documentation structure
   - Token usage (should be <15k)
   - Available task context

You should see something like:
```
Navigator Session Started
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: [your-project-name]
Documentation loaded: DEVELOPMENT-README.md
Token usage: ~12k (vs 150k loading everything)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 3: Understand the Index

**NOTICE:**
- The index shows WHAT documentation exists
- It does NOT load all the documentation
- You request specific docs when needed

This is lazy loading - the core of Navigator.

## Validation

This task is complete when:
- [ ] Session started with "Start my Navigator session"
- [ ] DEVELOPMENT-README.md loaded
- [ ] You see the documentation index structure

## Pro Tip

**Always** start sessions with this command. It sets up efficient context loading for everything else you do. Without it, you'll miss Navigator's benefits.

## What You Learned

1. Navigator loads an INDEX, not everything
2. ~2k tokens for index vs ~150k loading all docs
3. Request specific docs as needed (lazy loading)

---

**When done, say "done" to continue to the next task.**
