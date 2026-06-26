# Multi-Claude Workflow Troubleshooting

**Category**: Development
**Created**: 2025-11-02
**Last Updated**: 2025-11-02
**Applies to**: Navigator v4.5.0+

---

## Context

**When to use this SOP**:
When multi-Claude workflows fail, timeout, or produce unexpected results. This guide helps diagnose and recover from common failure modes.

**Problem it solves**:
Multi-Claude workflows involve multiple headless Claude instances coordinating via markers. Failures can occur at phase boundaries, during marker creation, or due to timeouts. This SOP provides systematic diagnosis and recovery procedures.

**Prerequisites**:
- Navigator v4.5.0+ installed
- Basic understanding of multi-Claude workflow phases
- Terminal access to project directory

---

## Common Failure Modes

### 1. Marker Timeout (Most Common)

**Symptoms**:
```
[15:24:49] Waiting for file: .agent/tasks/poc-XXX-done
[15:26:51] ❌ Timeout waiting for file
[15:26:51] ❌ Implementation phase timeout - no completion marker
```

**Root causes**:
- Sub-Claude didn't invoke marker skill
- Marker skill invoked but creation failed
- Claude process hung/crashed
- File system permissions issue

**Diagnosis steps**:
```bash
# 1. Check if marker file exists (might be created after timeout)
ls -la .agent/tasks/*-done

# 2. Check marker log for events
tail -50 .agent/.marker-log

# 3. Check if Claude process still running
ps aux | grep claude

# 4. Check state file
cat .agent/tasks/{session-id}-state.json | jq .
```

**Recovery**:
```bash
# Option 1: Resume workflow (if state file exists)
./scripts/resume-workflow.sh {session-id}

# Option 2: Manual marker creation (if work completed)
touch .agent/tasks/{session-id}-{phase}-done

# Option 3: Restart from scratch
./scripts/navigator-multi-claude-poc.sh "Your task"
```

---

### 2. Phase Retry Loop

**Symptoms**:
```
[15:27:00] ⚠️  Retry attempt 1 of 2 for phase: implementation
[15:29:05] ⚠️  Retry attempt 2 of 2 for phase: implementation
[15:31:10] ❌ Phase failed after 2 attempts: implementation
```

**Root cause**: Phase consistently failing marker creation (retry logic activated but unsuccessful)

**Diagnosis**:
```bash
# 1. Check marker log for pattern
grep "implementation" .agent/.marker-log

# 2. Check if files were actually modified
git status --short

# 3. Review state file attempts
cat .agent/tasks/{session-id}-state.json | jq '.phase_attempts'
```

**Recovery**:
```bash
# If work was completed (files modified):
touch .agent/tasks/{session-id}-done
./scripts/resume-workflow.sh {session-id}

# If work not started:
# Fix underlying issue, then restart phase manually
```

---

### 3. Monitor False Positive (Process Killed Prematurely)

**Symptoms**:
```
[Monitor] ⚠️  Timeout exceeded (180 > 180)
[Monitor] ❌ No marker, killing stuck process
# But work was actually in progress
```

**Root cause**: Phase took longer than timeout (180s default)

**Diagnosis**:
```bash
# 1. Check monitor log
grep "Monitor" .agent/.marker-log

# 2. Check if partial work exists
git diff

# 3. Verify process was killed
ps aux | grep claude
```

**Recovery**:
```bash
# 1. Increase timeout for complex phases
# Edit navigator-multi-claude.sh, increase timeout:
# wait_for_marker_with_retry "$file" "phase" 1 300  # 5 min instead of 3

# 2. Resume workflow
./scripts/resume-workflow.sh {session-id}
```

---

### 4. State File Corruption

**Symptoms**:
```
cat: .agent/tasks/SESSION-state.json: invalid JSON
```

**Root cause**: Incomplete write or concurrent modification

**Diagnosis**:
```bash
# Try to parse JSON
jq empty .agent/tasks/{session-id}-state.json

# If invalid, check for backup
ls -la .agent/tasks/{session-id}-state.json*
```

**Recovery**:
```bash
# Option 1: Restore from backup (if exists)
cp .agent/tasks/{session-id}-state.json.bak .agent/tasks/{session-id}-state.json

# Option 2: Manually reconstruct state
cat > .agent/tasks/{session-id}-state.json <<EOF
{
  "session_id": "{session-id}",
  "task": "{TASK-XX}",
  "phases_completed": ["phase0", "phase1"],
  "current_phase": "phase2",
  "status": "failed",
  "last_update": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
```

---

### 5. Empty Marker Files

**Symptoms**:
```
[15:30:00] ⚠️  Marker exists but is invalid (empty or corrupted)
```

**Root cause**: Marker created but not written to

**Diagnosis**:
```bash
# Check marker file size
ls -lh .agent/tasks/{session-id}-done

# Check if empty
[ -s .agent/tasks/{session-id}-done ] && echo "Has content" || echo "Empty"
```

**Recovery**:
```bash
# Markers can be empty - this is usually OK
# If workflow complains, recreate with content:
echo "completed" > .agent/tasks/{session-id}-done
```

---

### 6. Parallel Phase Deadlock

**Symptoms**:
```
[15:30:00] Waiting for parallel phases to complete...
# Hangs indefinitely
```

**Root cause**: One parallel phase (testing/docs) completed, other stuck

**Diagnosis**:
```bash
# Check which markers exist
ls -la .agent/tasks/{session-id}-tests-done
ls -la .agent/tasks/{session-id}-docs-done

# Check if processes running
ps aux | grep "claude -p"
```

**Recovery**:
```bash
# Kill hung processes
pkill -f "claude -p"

# Create missing marker manually if work done
touch .agent/tasks/{session-id}-tests-done

# Resume
./scripts/resume-workflow.sh {session-id}
```

---

## Diagnostic Checklist

When a workflow fails, run through this checklist:

```bash
# 1. What phase failed?
tail -20 {workflow-output}  # Check last logs

# 2. Was marker created?
ls -la .agent/tasks/*{session-id}*done

# 3. What does marker log show?
tail -50 .agent/.marker-log

# 4. What's the workflow state?
cat .agent/tasks/{session-id}-state.json | jq .

# 5. Was work actually completed?
git status --short

# 6. Are Claude processes still running?
ps aux | grep claude

# 7. What files were created/modified?
git diff --stat
```

---

## Recovery Decision Tree

```
Workflow failed?
    ├─ Marker exists?
    │   ├─ YES: Work completed, create marker manually → Resume
    │   └─ NO: Work incomplete → Check state file
    │
    ├─ State file exists?
    │   ├─ YES: Resume from last phase
    │   └─ NO: Restart workflow from scratch
    │
    ├─ Work was done (git diff shows changes)?
    │   ├─ YES: Create marker, resume
    │   └─ NO: Retry phase or restart
    │
    └─ Timeout too short?
        ├─ YES: Increase timeout, retry
        └─ NO: Investigate root cause
```

---

## Preventive Measures

### 1. Monitor Marker Logs During Workflow

```bash
# In separate terminal, watch marker creation in real-time
tail -f .agent/.marker-log
```

### 2. Use Longer Timeouts for Complex Tasks

```bash
# For workflows likely to take >3 minutes per phase
# Edit scripts/navigator-multi-claude.sh
# Change: wait_for_marker_with_retry "$file" "phase" 1 180
# To:     wait_for_marker_with_retry "$file" "phase" 1 300
```

### 3. Verify Before Running

```bash
# Ensure clean state
git status --short  # Should be clean or have expected changes

# Check no orphaned processes
ps aux | grep claude | grep -v grep

# Verify marker log accessible
touch .agent/.marker-log && ls -la .agent/.marker-log
```

---

## Advanced Debugging

### Enable Verbose Logging

```bash
# Add debug output to orchestrator
export DEBUG=1
./scripts/navigator-multi-claude-poc.sh "Your task"

# Check Claude Code logs
tail -f ~/.claude/logs/claude.log
```

### Inspect Sub-Claude Prompts

```bash
# View exactly what sub-Claude received
# Look in navigator-multi-claude.sh for prompt construction
grep -A 20 "claude -p" scripts/navigator-multi-claude.sh
```

### Test Monitor Separately

```bash
# Simulate Claude process
sleep 60 &
PID=$!

# Test monitor
./scripts/sub-claude-monitor.sh "test-phase" 30 $PID /tmp/test-marker

# Should timeout and kill process after 30s
```

---

## Real Examples

### Example 1: TASK-25 Implementation Failure

**Scenario**: Multi-Claude implementing TASK-25 failed at Phase 2

**Diagnosis**:
```bash
$ ls -la .agent/tasks/poc-1762086614*
-rw-r--r--  plan.md
# No -done marker found

$ git status --short
M scripts/sub-claude-monitor.sh    # Work WAS done
M scripts/resume-workflow.sh
?? tests/

$ tail .agent/.marker-log
[2025-11-02T12:35:00Z] ❌ implementation: Timeout (no marker after 180s)
```

**Conclusion**: Implementation completed but marker not created

**Fix**:
```bash
# Work done, create marker manually
touch .agent/tasks/poc-1762086614-done

# Resume workflow
./scripts/resume-workflow.sh poc-1762086614
```

### Example 2: Review Phase Success

**Scenario**: Manual review phase invocation worked

**What worked**:
```bash
$ claude -p "Review task..." &
PID=$!

# Monitor showed progress
$ tail -f .agent/.marker-log
[2025-11-02T12:50:00Z] ✅ review: marker created

# Marker file created
$ ls -la .agent/tasks/poc-1762086614-review-done
-rw-r--r--  0 bytes  # Empty is OK
```

**Lesson**: Explicit marker instructions in prompts increased success rate

---

## When to Give Up and Restart

**Restart from scratch if**:
- State file irreparably corrupted
- Multiple phases failed consecutively
- Workflow state doesn't match reality (git diff vs state.json)
- Session ID conflicts (multiple workflows with same ID)

**How to clean restart**:
```bash
# 1. Kill all processes
pkill -f "navigator-multi-claude"

# 2. Clean state files
rm -f .agent/tasks/*-state.json

# 3. Clean marker files (optional, depends on situation)
rm -f .agent/tasks/*-done

# 4. Commit or stash changes
git add . && git stash  # Or commit if good

# 5. Start fresh
./scripts/navigator-multi-claude-poc.sh "Your task"
```

---

## Success Indicators

**Workflow is healthy when**:
- ✅ Each phase creates marker within timeout
- ✅ Marker log shows steady progress
- ✅ State file updates after each phase
- ✅ Git diff shows expected changes
- ✅ No orphaned Claude processes

**Monitor health with**:
```bash
# Success rate over last 10 workflows
grep "✅" .agent/.marker-log | wc -l
grep "❌" .agent/.marker-log | wc -l

# Average phase duration
# (requires timestamp parsing, TBD)
```

---

## Related Documentation

**Navigator SOPs**:
- Release Workflow: `.agent/sops/development/release-workflow.md`
- Multi-Claude Workflow Guide: `scripts/POC-LEARNINGS.md`

**Code References**:
- Orchestrator: `scripts/navigator-multi-claude.sh`
- POC Script: `scripts/navigator-multi-claude-poc.sh`
- Monitor: `scripts/sub-claude-monitor.sh`
- Resume: `scripts/resume-workflow.sh`

**External**:
- Claude Code CLI docs: https://docs.claude.com
- Navigator GitHub: https://github.com/alekspetrov/navigator

---

## Maintenance

**Update this SOP when**:
- New failure mode discovered
- Recovery procedure improved
- Workflow scripts modified
- Timeout defaults changed

**Owner**: Navigator maintainers
**Review frequency**: After major releases or significant workflow failures

---

**Last Updated**: 2025-11-02
**Tested With**: v4.5.0 (TASK-25 implementation, dogfooding)
**Known Issues**: Monitor timeout detection needs refinement for long-running phases
