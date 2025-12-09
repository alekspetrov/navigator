# Learning Task 5: Managing Context Efficiently

**Skill**: nav-compact
**Time**: 3-5 minutes
**Difficulty**: Beginner

## Why This Matters

Context windows fill up. When they do, AI starts forgetting, hallucinating, or crashes. Compact clears context while preserving progress via markers. This is how you maintain efficiency across long sessions.

## The Task

### Step 1: Initiate Compact

**DO THIS NOW:**
```
Type: "Clear context and preserve markers"
```

### Step 2: Observe What Happens

**WHAT SHOULD HAPPEN:**

1. Automatic marker created (preserves current state)
2. `.active` file set (for auto-restore next session)
3. Instructions for manual clear provided

You should see:
```
✅ Ready to compact!

Marker created: before-compact-[timestamp]
Location: .agent/.context-markers/
Active marker set: ✅ (will auto-restore next session)

To complete compact:
1. Start a new conversation (or use /clear)
2. Say "Start my Navigator session"
3. Marker will auto-restore your context

Your progress is preserved in the marker.
```

### Step 3: Understand the Process

**IMPORTANT**: Claude cannot clear conversation programmatically.

The compact workflow:
1. `nav-compact` creates marker + sets `.active`
2. YOU start new conversation (or /clear)
3. Next `nav-start` detects `.active` marker
4. Offers to restore your context

### Step 4: (Optional) Complete the Compact

If you want to practice the full cycle:

1. Start a new conversation
2. Type: "Start my Navigator session"
3. See the auto-restore offer
4. Confirm to load your marker

## Validation

This task is complete when:
- [ ] Compact initiated with "Clear context and preserve markers"
- [ ] Marker created automatically
- [ ] `.active` file set for auto-restore

**Automatic check**: File `.agent/.context-markers/.active` exists.

## Pro Tip

**When to compact:**
- After completing isolated feature (switch to new work)
- When context feels "heavy" (many files loaded)
- After debugging session (clear noise)
- Before major topic change

**When NOT to compact:**
- Mid-feature implementation
- While debugging (need context)
- When files from current work are still needed

**The flow:**
```
Start session → Work → Marker → Compact → New session → Auto-restore → Continue
```

## What You Learned

1. Compact clears context while preserving progress
2. Markers auto-restore on next session
3. Use after completing work units, not mid-work

---

**When done, say "done" to continue to the next task.**
