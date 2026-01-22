# TASK-33: Workflow Enforcement Mechanism

**Status**: ✅ Completed
**Created**: 2025-01-22
**Version**: 5.9.0
**Priority**: CRITICAL

---

## Context

**Problem**:
Navigator has comprehensive workflow documentation (Task Mode, Loop Mode, autonomous completion) but **zero enforcement**. Claude can ignore all of it.

**Evidence**:
- User said "do all it's needed" (Loop Mode trigger) → I ignored it
- Task was substantial (complexity > 0.5) → No Task Mode activated
- NAVIGATOR_STATUS blocks never shown
- Workflow completely bypassed

**Root Cause**:
```
Layer 1: Documentation (CLAUDE.md, SKILL.md)     ✓ EXISTS
Layer 2: Configuration (.nav-config.json)         ✓ EXISTS
Layer 3: Enforcement mechanism                    ✗ MISSING
```

**Goal**:
Make workflow enforcement automatic, not voluntary.

**Success Criteria**:
- [ ] Trigger phrases ("run until done", "do all it's needed") auto-invoke Loop Mode
- [ ] Substantial tasks auto-trigger Task Mode complexity check
- [ ] NAVIGATOR_STATUS blocks shown when Loop Mode active
- [ ] Workflow compliance is validated, not hoped for

---

## Implementation Options

### Option A: CLAUDE.md Enforcement Section (Simplest)

Add to CLAUDE.md a **hard requirement** section that's read at session start:

```markdown
## WORKFLOW ENFORCEMENT (MANDATORY)

Before responding to ANY task request, you MUST:

1. **Check for Loop Mode triggers**:
   - "run until done", "do all it's needed", "keep going", "iterate until"
   - If found → Invoke nav-loop skill, show NAVIGATOR_STATUS

2. **Check task complexity**:
   - Multi-file changes, refactoring, new features → complexity > 0.5
   - If substantial → Invoke nav-task-mode, show phase tracking

3. **Never skip these checks**
   - This is NOT optional
   - Failure to follow = workflow violation
```

**Pros**: Simple, no code changes
**Cons**: Still relies on Claude reading and following

### Option B: nav-start Enforcement Gate

Modify nav-start to install an "enforcement context" that Claude must follow:

```python
# In nav-start session output, add:
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW ENFORCEMENT ACTIVE

Before responding to tasks, CHECK:
□ Loop trigger? → nav-loop
□ Substantial? → nav-task-mode
□ Neither? → Direct execution OK

Show this check in your response.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
```

**Pros**: Shown every session, hard to miss
**Cons**: Adds tokens, still voluntary

### Option C: Skill Auto-Invocation via Plugin Hooks (Best)

Use Claude Code's hook system to intercept user messages:

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [{
          "type": "command",
          "command": "python3 workflow_enforcer.py \"$USER_MESSAGE\""
        }]
      }
    ]
  }
}
```

**workflow_enforcer.py**:
```python
def check_workflow(user_message):
    # Check Loop Mode triggers
    loop_triggers = ["run until done", "do all it's needed", "keep going", "iterate until"]
    if any(trigger in user_message.lower() for trigger in loop_triggers):
        return {"action": "invoke_skill", "skill": "nav-loop"}

    # Check complexity indicators
    complexity_indicators = ["refactor", "implement", "add feature", "fix all", "update all"]
    if any(ind in user_message.lower() for ind in complexity_indicators):
        return {"action": "invoke_skill", "skill": "nav-task-mode"}

    return {"action": "proceed"}
```

**Pros**: Automatic, no Claude cooperation needed
**Cons**: Requires hook support, adds latency

### Option D: Mandatory Workflow Block in Response (Pragmatic)

Require Claude to show a workflow decision block at the start of every task response:

```markdown
Add to CLAUDE.md:

Every task response MUST start with:

┌─────────────────────────────────────┐
│ WORKFLOW CHECK                      │
├─────────────────────────────────────┤
│ Loop trigger: [YES/NO] → [action]   │
│ Complexity: [0.X] → [action]        │
│ Mode: [LOOP/TASK/DIRECT]            │
└─────────────────────────────────────┘

If you don't show this block, you're violating workflow.
```

**Pros**: Visible enforcement, self-documenting
**Cons**: Adds tokens to every response

---

## Recommended Approach

**Phase 1**: Option D (Mandatory Workflow Block)
- Immediate, no code changes
- Forces visible compliance
- Easy to verify

**Phase 2**: Option A (CLAUDE.md Enforcement Section)
- Reinforce in documentation
- Add to Forbidden Actions

**Phase 3**: Option C (Plugin Hooks)
- Long-term automation
- Remove reliance on Claude cooperation

---

## Implementation Plan

### Phase 1: Mandatory Workflow Block

**Tasks**:
- [ ] Add WORKFLOW CHECK requirement to CLAUDE.md
- [ ] Add workflow violation to Forbidden Actions
- [ ] Update nav-start to remind about workflow check

**Files**:
- `CLAUDE.md` - Add enforcement section
- `skills/nav-start/SKILL.md` - Add reminder in session output

### Phase 2: Trigger Detection

**Tasks**:
- [ ] Create `workflow_detector.py` with trigger phrase matching
- [ ] Create `complexity_scorer.py` for quick complexity assessment
- [ ] Integrate into nav-start session initialization

**Files**:
- `skills/nav-start/functions/workflow_detector.py` (new)
- `skills/nav-start/functions/complexity_scorer.py` (new)
- `skills/nav-start/SKILL.md` - Call detector on start

### Phase 3: Hook-Based Enforcement (Future)

**Tasks**:
- [ ] Investigate Claude Code hook capabilities
- [ ] Create PreToolUse hook for workflow enforcement
- [ ] Test latency impact

**Files**:
- `.claude/settings.json` - Add hooks
- `hooks/workflow_enforcer.py` (new)

---

## Technical Decisions

| Decision | Options | Chosen | Reasoning |
|----------|---------|--------|-----------|
| Enforcement level | Soft/Hard | Hard | Soft doesn't work (proven) |
| Implementation | Code/Docs | Docs first | Faster, validates approach |
| Visibility | Hidden/Visible | Visible | Forces accountability |

---

## Verify

```bash
# Test trigger detection
echo "run until done: fix the bug" | python3 workflow_detector.py
# Expected: {"loop_mode": true, "trigger": "run until done"}

# Test complexity scoring
echo "refactor auth to use JWT" | python3 complexity_scorer.py
# Expected: {"score": 0.8, "task_mode": true}
```

---

## Done

- [ ] WORKFLOW CHECK block required in CLAUDE.md
- [ ] Workflow violation added to Forbidden Actions
- [ ] nav-start shows enforcement reminder
- [ ] Trigger phrases are detected (manual or automated)
- [ ] Claude actually follows the workflow (tested)

---

## Anti-Patterns to Prevent

1. **Direct response without check** - Claude just answers without workflow evaluation
2. **Ignoring trigger phrases** - "do all it's needed" bypassed
3. **Skipping complexity assessment** - Substantial tasks done ad-hoc
4. **Missing NAVIGATOR_STATUS** - Loop Mode active but no status blocks

---

**Last Updated**: 2025-01-22
