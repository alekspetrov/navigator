---
name: nav-multi
description: Run multi-Claude parallel workflow for a task. Auto-invokes when user says "run multi-agent workflow", "parallel agents for", "multi-claude for", or "spawn agents for".
allowed-tools: Bash, Read, Write, Glob
version: 1.0.0
---

# Navigator Multi-Agent Workflow

Launch parallel Claude agents to implement a task with orchestration, implementation, testing, review, and documentation phases.

## When to Invoke

Auto-invoke when user says:
- "Run multi-agent workflow for TASK-XX"
- "Use parallel agents for this feature"
- "Multi-claude for implementing X"
- "Spawn agents for this task"
- "Launch multi-agent on TASK-XX"

**DO NOT invoke** if:
- Multi-Claude scripts not installed (use nav-install-multi-claude first)
- User is asking informational questions about multi-agent
- Task is trivial (single file change)

## Prerequisites

Check before running:
1. `navigator-multi-claude.sh` in PATH
2. Git repository clean (no uncommitted changes)
3. Navigator initialized (`.agent/` exists)

## Execution Steps

### Step 1: Validate Prerequisites

```bash
# Check scripts installed
if ! command -v navigator-multi-claude.sh &> /dev/null; then
  echo "❌ Multi-Claude scripts not installed"
  echo ""
  echo "Install first with:"
  echo '  "Install multi-Claude workflows"'
  exit 1
fi

# Check Navigator initialized
if [ ! -d ".agent" ]; then
  echo "❌ Navigator not initialized in this project"
  echo ""
  echo "Initialize first with:"
  echo '  "Initialize Navigator in this project"'
  exit 1
fi

# Check git clean
if [ -n "$(git status --porcelain)" ]; then
  echo "⚠️  Uncommitted changes detected"
  echo ""
  git status --short
  echo ""
  echo "Multi-agent workflows work best with a clean git state."
  echo "Commit or stash changes before proceeding?"
fi

echo "✅ Prerequisites validated"
```

### Step 2: Parse Task Information

Extract from user request:
- **Task ID**: TASK-XX (if mentioned)
- **Task description**: What to implement

If TASK-XX mentioned, read task file:
```bash
if [ -n "$TASK_ID" ]; then
  TASK_FILE=".agent/tasks/${TASK_ID}*.md"
  if ls $TASK_FILE 1> /dev/null 2>&1; then
    TASK_DESC=$(head -1 $TASK_FILE | sed 's/# //')
    echo "📋 Task: $TASK_DESC"
  fi
fi
```

### Step 3: Choose Workflow Type

Present options to user:

```
Which workflow type?

1. **POC (2-phase)** - Quick validation
   - Planning → Implementation
   - ~3 minutes
   - Best for: Simple features, utilities

2. **Standard (4-phase)** - Full quality gates
   - Planning → Implementation → Testing + Docs → Review
   - ~6 minutes
   - Best for: Production features

3. **Full (6-phase)** - With simplification
   - Planning → Implementation → Simplify → Testing + Docs → Review → Integration
   - ~8 minutes
   - Best for: Complex features, refactoring
```

### Step 4: Generate Session ID

```bash
TASK_NUM=$(echo "$TASK_ID" | grep -oE '[0-9]+' || echo "0")
# Append PID to prevent collision when two parallel runs start in the same second
# without a TASK_ID (both would resolve to TASK_NUM=0).
SESSION_ID="task-${TASK_NUM}-$(date +%s)-$$"
echo "📌 Session: $SESSION_ID"
```

### Step 5: Create State File

```bash
cat > ".agent/tasks/${SESSION_ID}-state.json" << EOF
{
  "session_id": "${SESSION_ID}",
  "task": "${TASK_DESC}",
  "task_id": "${TASK_ID}",
  "workflow_type": "${WORKFLOW_TYPE}",
  "phases_completed": [],
  "current_phase": "init",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "in_progress"
}
EOF
```

### Step 5.5: Branch-Per-Run Convention

**Each multi-agent run should use a dedicated git branch.** Two parallel workflows committing to the same branch produces interleaved, hard-to-review history. A per-run branch isolates each workflow's commits and makes PR review possible.

**Convention**:
```bash
BRANCH="nav-multi/${SESSION_ID}"
git checkout -b "$BRANCH"
echo "🌿 Branch: $BRANCH"
```

**Why this matters**:
- **Parallel safety**: Two runs on `main` race on every commit. Each run on its own branch is safe.
- **Reviewable diffs**: One branch = one workflow = one PR.
- **Clean rollback**: Failed workflow? Delete the branch. No `git revert` archaeology.
- **Bisect-friendly**: Mixed-workflow commits on `main` are nearly impossible to bisect.

**When to skip**:
- POC workflow with no commits planned (just exploration).
- User explicitly asks to commit to current branch (rare — confirm intent).

**Cleanup after success**: open a PR from the branch, or merge directly if the workflow declared no review needed (configured via `multi_agent.default_workflow`).

### Step 6: Launch Workflow

```bash
echo "🚀 Launching multi-agent workflow..."
echo ""

case $WORKFLOW_TYPE in
  poc)
    navigator-multi-claude-poc.sh "$TASK_DESC"
    ;;
  standard)
    navigator-multi-claude.sh "$TASK_DESC"
    ;;
  full)
    navigator-multi-claude.sh "$TASK_DESC" --with-simplify
    ;;
esac
```

### Step 7: Offer Dashboard

```bash
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Monitor progress with dashboard?"
echo ""
echo "In another terminal, run:"
echo "  ./scripts/multi-claude-dashboard.sh $SESSION_ID"
echo ""
echo "Or watch marker log:"
echo "  tail -f .agent/.marker-log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Output Format

```
┌─────────────────────────────────────────────────────┐
│ Multi-Agent Workflow: task-36-1705123456           │
├─────────────────────────────────────────────────────┤
│ Task: Implement user authentication                 │
│ Type: standard (4-phase)                           │
├─────────────────────────────────────────────────────┤
│ Phases:                                            │
│   1. Planning      → orchestrator                   │
│   2. Implementation → implementer                   │
│   3. Testing       → tester (parallel)             │
│   3. Documentation → documenter (parallel)         │
│   4. Review        → reviewer                       │
├─────────────────────────────────────────────────────┤
│ Monitor: ./scripts/multi-claude-dashboard.sh       │
│ Logs: tail -f .agent/.marker-log                   │
└─────────────────────────────────────────────────────┘

🚀 Launching workflow...
```

## Error Handling

### Scripts Not Installed
```
❌ Multi-Claude scripts not installed

The multi-agent workflow requires orchestration scripts.

Install with:
  "Install multi-Claude workflows"

Then retry:
  "Run multi-agent workflow for TASK-XX"
```

### Uncommitted Changes
```
⚠️  Uncommitted changes detected

M  src/auth/login.ts
?? src/utils/temp.ts

Multi-agent workflows create branches and parallel changes.
Working with uncommitted changes may cause conflicts.

Options:
1. Commit changes first: git add -A && git commit -m "WIP"
2. Stash changes: git stash
3. Proceed anyway (risky)

Which option? [1/2/3]
```

### Workflow Already Running
```
⚠️  Workflow already in progress

Session: task-35-1705120000
Status: IMPL phase running
Started: 5 minutes ago

Options:
1. Resume existing workflow
2. Cancel existing and start new
3. Wait for completion

Which option? [1/2/3]
```

## Configuration

In `.agent/.nav-config.json`:

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

## Success Criteria

Workflow launch successful when:
- [ ] Prerequisites validated
- [ ] Session ID generated
- [ ] State file created
- [ ] Workflow script launched
- [ ] Dashboard instructions shown

## Workflow Phases

### POC (2-phase)
```
Planning ─────► Implementation ─────► Done
```

### Standard (4-phase)
```
                              ┌─► Testing ────┐
Planning ─► Implementation ───┤               ├─► Review ─► Done
                              └─► Docs ───────┘
```

### Full (6-phase)
```
                                          ┌─► Testing ────┐
Planning ─► Implementation ─► Simplify ───┤               ├─► Review ─► Integration ─► Done
                                          └─► Docs ───────┘
```

## Role Templates

Each phase uses a minimal context CLAUDE.md:
- `templates/multi-claude/orchestrator-claude.md` (~4k tokens)
- `templates/multi-claude/implementer-claude.md` (~5k tokens)
- `templates/multi-claude/tester-claude.md` (~4k tokens)
- `templates/multi-claude/reviewer-claude.md` (~4k tokens)
- `templates/multi-claude/documenter-claude.md` (~4k tokens)
- `templates/multi-claude/simplifier-claude.md` (~5k tokens)

**Total**: ~27k tokens across 6 roles (vs 50k+ loading full project context per role)

## Examples

### Example 1: Quick Feature with POC

User: "Run multi-agent POC for adding a logout button"

```
✅ Prerequisites validated
📋 Task: Add logout button
📌 Session: task-0-1705123456
🚀 Launching POC workflow (2-phase)...

Phase 1: Planning (orchestrator)
Phase 2: Implementation (implementer)

Monitor: ./scripts/multi-claude-dashboard.sh task-0-1705123456
```

### Example 2: Standard Workflow for TASK-XX

User: "Use parallel agents for TASK-36"

```
✅ Prerequisites validated
📋 Task: Multi-Agent Production Polish (from TASK-36)
📌 Session: task-36-1705123456
🚀 Launching standard workflow (4-phase)...

Phase 1: Planning
Phase 2: Implementation
Phase 3: Testing + Documentation (parallel)
Phase 4: Review

Dashboard available in another terminal.
```

### Example 3: Full Workflow with Simplification

User: "Multi-claude full workflow for auth refactor"

```
✅ Prerequisites validated
📋 Task: Auth refactor
📌 Session: task-0-1705123456
🚀 Launching full workflow (6-phase)...

Includes code simplification phase for clarity improvements.
Expected duration: ~8 minutes

Monitor progress:
  ./scripts/multi-claude-dashboard.sh task-0-1705123456
```

## Related Skills

- **nav-install-multi-claude**: Install orchestration scripts
- **nav-task**: Create task documentation
- **nav-marker**: Context preservation between phases
- **nav-simplify**: Code simplification (used in full workflow)

## Notes

- Multi-agent workflows spawn headless Claude instances
- Each role gets fresh context (no cross-contamination)
- Marker files coordinate phase transitions
- Dashboard provides real-time visibility
- State file enables resume after interruption
