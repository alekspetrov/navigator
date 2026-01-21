#!/bin/bash
# Navigator Multi-Claude Production Workflow
# Implements full automation: ticket → implementation → PR → status updates

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging helpers
log_info() {
  echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[$(date '+%H:%M:%S')] ✅${NC} $1"
}

log_error() {
  echo -e "${RED}[$(date '+%H:%M:%S')] ❌${NC} $1"
}

log_phase() {
  echo ""
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${YELLOW}$1${NC}"
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
}

# Generate error handling instructions for sub-Claude
error_handling_instructions() {
  local done_file="$1"
  cat <<EOF

CRITICAL: If you encounter ANY error or cannot complete this task:
1. Create failure marker: ${done_file}.failed
2. Write error details to the file (error message, what went wrong)
3. Exit immediately

Only create ${done_file} on success.
EOF
}

# Wait for file to appear
wait_for_file() {
  local file_path="$1"
  local timeout=300  # 5 minutes (increased for review phase)
  local elapsed=0
  local failure_marker="${file_path}.failed"

  log_info "Waiting for file: $file_path"

  while [ ! -f "$file_path" ]; do
    # Check for failure marker
    if [ -f "$failure_marker" ]; then
      log_error "Sub-Claude reported failure:"
      cat "$failure_marker" >&2
      return 1
    fi

    if [ $elapsed -ge $timeout ]; then
      log_error "Timeout waiting for file: $file_path"
      return 1
    fi
    sleep 1
    ((elapsed++))
  done

  log_success "File created: $file_path"
  return 0
}

# Wait for marker with retry capability
wait_for_marker_with_retry() {
  local marker_file="$1"
  local phase_name="$2"
  local max_retries="${3:-1}"
  local timeout="${4:-180}"
  local attempt=1

  for attempt in $(seq 1 $((max_retries + 1))); do
    if [ $attempt -gt 1 ]; then
      log_info "⚠️  Retry attempt $attempt of $((max_retries + 1)) for phase: $phase_name"
    fi

    if wait_for_file "$marker_file" "$timeout"; then
      # Verify marker is valid (non-empty or exists)
      if [ -s "$marker_file" ] || [ -f "$marker_file" ]; then
        log_success "✅ Marker verified: $marker_file"
        return 0
      else
        log_error "❌ Marker exists but is invalid"
      fi
    fi

    if [ $attempt -le $max_retries ]; then
      log_info "⚠️  Timeout on attempt $attempt - retrying phase: $phase_name"
      # Save state before retry
      save_phase_state "$phase_name" "$attempt"
    else
      log_error "❌ Phase failed after $attempt attempts: $phase_name"
      save_phase_state "$phase_name" "$attempt" "failed"
      return 1
    fi
  done

  return 1
}

# Save phase state for recovery
save_phase_state() {
  local phase_name="$1"
  local attempt="$2"
  local status="${3:-retry}"

  if [ -z "$STATE_FILE" ]; then
    return 0
  fi

  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local temp_file="${STATE_FILE}.tmp.$$"

  # Atomic state file write: write to temp, then move
  cat > "$temp_file" <<EOF
{
  "session_id": "${session_id}",
  "task": "${task_id}",
  "phases_completed": [${PHASES_COMPLETED}],
  "current_phase": "${phase_name}",
  "phase_attempts": {
    "${phase_name}": ${attempt}
  },
  "status": "${status}",
  "last_update": "${timestamp}"
}
EOF

  # Atomic move (prevents partial writes)
  mv "$temp_file" "$STATE_FILE"

  log_info "💾 State saved: ${STATE_FILE}"
}

# Read task file and extract metadata
read_task() {
  local task_id="$1"
  local task_file=".agent/tasks/${task_id}.md"

  if [ ! -f "$task_file" ]; then
    log_error "Task file not found: $task_file"
    exit 1
  fi

  # Extract title (first heading)
  TASK_TITLE=$(grep -m1 "^# " "$task_file" | sed 's/^# //')

  # Extract description from Context section
  TASK_DESCRIPTION=$(sed -n '/^## Context/,/^##/p' "$task_file" | grep -v "^##" | head -10)

  log_success "Task loaded: $TASK_TITLE" >&2
  echo "$task_file"
}

# Update task status
update_task_status() {
  local task_file="$1"
  local status="$2"

  # Backup original if not already backed up
  if [ ! -f "${task_file}.bak" ]; then
    cp "$task_file" "${task_file}.bak"
  fi

  # Update status line
  sed -i.tmp "s/^\*\*Status\*\*:.*/**Status**: $status/" "$task_file"
  rm "${task_file}.tmp" 2>/dev/null || true

  log_info "Task status updated: $status"
}

# Create feature branch
create_feature_branch() {
  local task_id="$1"
  local branch_name="feature/$(echo "$task_id" | tr '[:upper:]' '[:lower:]')"

  # Check if branch exists
  if git rev-parse --verify "$branch_name" >/dev/null 2>&1; then
    log_info "Branch $branch_name already exists, switching to it"
    git checkout "$branch_name"
  else
    log_info "Creating branch: $branch_name"
    git checkout -b "$branch_name"
  fi

  echo "$branch_name"
}

# Main workflow
main() {
  local task_id="${1:-}"

  if [ -z "$task_id" ]; then
    log_error "Usage: $0 TASK-XX"
    echo ""
    echo "Example: $0 TASK-19"
    echo ""
    exit 1
  fi

  log_phase "🎯 Navigator Multi-Claude Workflow"
  log_info "Task: $task_id"

  # Ensure we're in project root
  if [ ! -f "CLAUDE.md" ]; then
    log_error "Must run from Navigator project root"
    exit 1
  fi

  # Check dependencies
  if ! command -v claude &> /dev/null; then
    log_error "Claude Code CLI not found. Install from: https://install.claude.com"
    exit 1
  fi

  if ! command -v jq &> /dev/null; then
    log_error "jq not found. Install with: brew install jq"
    exit 1
  fi

  # Read task file
  log_phase "Phase 0: Task Loading"
  task_file=$(read_task "$task_id")

  # Extract task title from task file
  TASK_TITLE=$(grep -m1 "^# " "$task_file" | sed 's/^# //')

  update_task_status "$task_file" "🚧 In Progress"

  # Create feature branch
  branch_name=$(create_feature_branch "$task_id")
  log_success "Branch: $branch_name" >&2

  # Generate unique session ID
  local session_id="$(echo "$task_id" | tr '[:upper:]' '[:lower:]')-$(date +%s)"
  local plan_file=".agent/tasks/${session_id}-plan.md"

  # Initialize state tracking
  STATE_FILE=".agent/tasks/${session_id}-state.json"
  PHASES_COMPLETED=""
  export STATE_FILE PHASES_COMPLETED session_id task_id

  # Create marker log if not exists
  mkdir -p .agent
  touch .agent/.marker-log

  log_phase "Phase 1: Planning (Orchestrator)"
  update_task_status "$task_file" "🚧 In Progress (Planning)"

  log_info "Orchestrator: Creating implementation plan..."

  orchestrator_output=$(claude -p \
    "You are the Planning Claude in a multi-Claude workflow.

TASK: Read task from ${task_file}. Create implementation plan and save to ${plan_file}.

EFFICIENCY TIPS:
- Use Task agent (subagent_type=Explore) for codebase exploration instead of manual file reading
- Task agents return summaries, saving 60-80% tokens
- For unfamiliar codebases: Launch Explore agent with 'medium' thoroughness

PLAN REQUIREMENTS:
1) Feature description
2) Implementation steps (detailed, actionable)
3) Files to create/modify
4) Expected outcome
5) Test strategy

CRITICAL: You MUST create a completion marker when done.

After saving the plan to ${plan_file}:
1. Verify file was written successfully
2. The plan file itself serves as the completion marker

The orchestrator will wait for ${plan_file} to exist before proceeding.

$(error_handling_instructions "$plan_file")" \
    --output-format json \
    --dangerously-skip-permissions 2>&1)

  if [ $? -ne 0 ]; then
    log_error "Orchestrator failed"
    echo "$orchestrator_output"
    update_task_status "$task_file" "❌ Failed (Planning)"
    exit 1
  fi

  log_success "Plan creation requested"

  if ! wait_for_marker_with_retry "$plan_file" "planning" 1 180; then
    log_error "Planning phase failed - no plan file created"
    log_info "💾 Workflow state saved to: $STATE_FILE"
    log_info "Resume with: ./scripts/resume-workflow.sh $session_id"
    update_task_status "$task_file" "❌ Failed (Planning)"
    exit 1
  fi

  log_success "Plan saved to: $plan_file"
  PHASES_COMPLETED='"phase0"'
  save_phase_state "phase1" 1 "complete"
  update_task_status "$task_file" "🚧 In Progress (Planning complete)"

  log_phase "Phase 2: Implementation"
  update_task_status "$task_file" "🚧 In Progress (Implementation)"

  log_info "Implementation: Building feature from plan..."

  local impl_done_file=".agent/tasks/${session_id}-done"

  impl_output=$(claude -p \
    "You are the Implementation Claude in a multi-Claude workflow.

TASK: Read the plan from ${plan_file}. Implement the feature following the plan.

EFFICIENCY TIPS:
- For multi-file searches: Use Task agent (subagent_type=Explore) instead of manual Grep/Glob
- For understanding existing patterns: Launch Explore agent to analyze similar code
- Task agents save 60-80% tokens on exploration tasks

IMPLEMENTATION RULES:
- Follow the plan exactly
- Write clean, well-documented code
- Use project conventions (check existing files for patterns)

CRITICAL: You MUST create a completion marker when done.

Steps:
1. Implement all features from the plan
2. Test your changes work correctly
3. FINAL STEP (MANDATORY): Create completion marker using Bash tool:

   touch ${impl_done_file} && echo 'Marker created'

Marker file: ${impl_done_file}

⚠️  WARNING: The orchestrator is BLOCKED until this marker exists.
If you don't create it, the entire workflow fails.
Create the marker IMMEDIATELY after implementation, before any other action.

$(error_handling_instructions "$impl_done_file")" \
    --output-format json \
    --dangerously-skip-permissions 2>&1)

  if [ $? -ne 0 ]; then
    log_error "Implementation failed"
    echo "$impl_output"
    update_task_status "$task_file" "❌ Failed (Implementation)"
    exit 1
  fi

  log_success "Implementation requested"

  if ! wait_for_marker_with_retry "$impl_done_file" "implementation" 1 180; then
    log_error "Implementation phase failed - no completion marker"
    log_info "💾 Workflow state saved to: $STATE_FILE"
    log_info "Resume with: ./scripts/resume-workflow.sh $session_id"
    update_task_status "$task_file" "❌ Failed (Implementation)"
    exit 1
  fi

  log_success "Implementation complete"
  PHASES_COMPLETED='"phase0", "phase1"'
  save_phase_state "phase2" 1 "complete"
  update_task_status "$task_file" "🚧 In Progress (Implementation complete)"

  log_phase "Phase 3 & 4: Parallel Testing + Documentation"
  update_task_status "$task_file" "🚧 In Progress (Testing & Documentation)"

  local test_done_file=".agent/tasks/${session_id}-tests-done"
  local docs_done_file=".agent/tasks/${session_id}-docs-done"

  log_info "Testing: Validating implementation... (parallel)"
  log_info "Documentation: Generating docs... (parallel)"

  # Launch testing Claude in background
  (
    test_output=$(claude -p \
      "You are the Testing Claude in a multi-Claude workflow.

TASK: Read the plan from ${plan_file}. Review implementation and generate comprehensive tests. Run tests to validate.

EFFICIENCY TIPS:
- Use Task agent (subagent_type=Explore) to find existing test patterns
- Analyze similar test files to match project conventions

TEST REQUIREMENTS:
- Unit tests for all functions
- Edge cases and error handling
- Run tests and verify they pass

CRITICAL: You MUST create a completion marker when done.

Steps:
1. Generate comprehensive tests
2. Run tests and verify they pass
3. FINAL STEP (MANDATORY): Create completion marker using Bash tool:

   touch ${test_done_file} && echo 'Marker created'

Marker file: ${test_done_file}

⚠️  WARNING: The orchestrator is BLOCKED until this marker exists.
If you don't create it, the entire workflow fails.
Create the marker IMMEDIATELY after testing completes.

$(error_handling_instructions "$test_done_file")" \
      --output-format json \
      --dangerously-skip-permissions 2>&1)

    if [ $? -ne 0 ]; then
      echo "TEST_FAILED" > ".agent/tasks/${session_id}-tests-failed"
      log_error "Testing failed"
    fi
  ) &
  local test_pid=$!

  # Launch documentation Claude in parallel
  (
    docs_output=$(claude -p \
      "You are the Documentation Claude in a multi-Claude workflow.

TASK: Read the plan from ${plan_file}. Review implementation and generate comprehensive documentation.

EFFICIENCY TIPS:
- Use Task agent (subagent_type=Explore) to find existing documentation patterns
- Match project documentation style

DOCUMENTATION REQUIREMENTS:
- README sections (installation, usage, examples)
- JSDoc/TSDoc for all public APIs
- Usage examples with code snippets

CRITICAL: You MUST create a completion marker when done.

Steps:
1. Generate comprehensive documentation
2. Verify documentation is complete
3. FINAL STEP (MANDATORY): Create completion marker using Bash tool:

   touch ${docs_done_file} && echo 'Marker created'

Marker file: ${docs_done_file}

⚠️  WARNING: The orchestrator is BLOCKED until this marker exists.
If you don't create it, the entire workflow fails.
Create the marker IMMEDIATELY after documentation completes.

$(error_handling_instructions "$docs_done_file")" \
      --output-format json \
      --dangerously-skip-permissions 2>&1)

    if [ $? -ne 0 ]; then
      echo "DOCS_FAILED" > ".agent/tasks/${session_id}-docs-failed"
      log_error "Documentation failed"
    fi
  ) &
  local docs_pid=$!

  log_success "Parallel execution started"
  log_info "Waiting for parallel phases to complete..."

  # Wait for testing
  if ! wait_for_marker_with_retry "$test_done_file" "testing" 1 180; then
    log_error "Testing phase timeout"
    kill $test_pid $docs_pid 2>/dev/null
    log_info "💾 Workflow state saved to: $STATE_FILE"
    log_info "Resume with: ./scripts/resume-workflow.sh $session_id"
    update_task_status "$task_file" "❌ Failed (Testing timeout)"
    exit 1
  fi
  log_success "Testing complete"

  # Wait for documentation
  if ! wait_for_marker_with_retry "$docs_done_file" "documentation" 1 180; then
    log_error "Documentation phase timeout"
    kill $docs_pid 2>/dev/null
    log_info "💾 Workflow state saved to: $STATE_FILE"
    log_info "Resume with: ./scripts/resume-workflow.sh $session_id"
    update_task_status "$task_file" "❌ Failed (Documentation timeout)"
    exit 1
  fi
  log_success "Documentation complete"

  wait $test_pid $docs_pid 2>/dev/null

  # Check quality gates
  log_info "Checking quality gates..."

  if [ -f ".agent/tasks/${session_id}-tests-failed" ]; then
    log_error "Tests failed - quality gate not met"
    cat ".agent/tasks/${session_id}-tests-failed"
    update_task_status "$task_file" "❌ Failed (Tests failed)"
    exit 1
  fi

  if [ -f ".agent/tasks/${session_id}-docs-failed" ]; then
    log_error "Documentation generation failed"
    cat ".agent/tasks/${session_id}-docs-failed"
    update_task_status "$task_file" "❌ Failed (Documentation failed)"
    exit 1
  fi

  log_success "All quality gates passed ✓"
  PHASES_COMPLETED='"phase0", "phase1", "phase2", "phase3"'
  save_phase_state "phase4" 1 "complete"
  update_task_status "$task_file" "🚧 In Progress (Testing & docs complete)"

  log_phase "Phase 5: Review"
  update_task_status "$task_file" "🚧 In Progress (Review)"

  local review_done_file=".agent/tasks/${session_id}-review-done"
  local review_report_file=".agent/tasks/${session_id}-review-report.md"

  log_info "Review: Analyzing all changes..."

  # Check if task file has Verify/Done sections for structured verification
  local verify_instructions=""
  if [ -f "$task_file" ]; then
    if grep -q "## Verify" "$task_file"; then
      verify_instructions="
VERIFICATION (IMPORTANT - Task has ## Verify section):
1. Extract commands from ## Verify section in ${task_file}
2. Execute each command using Bash tool
3. Report pass/fail for each command in the review report
4. If verify_extractor.py exists, use it:
   python3 skills/nav-task/functions/verify_extractor.py ${task_file} --commands-only

DONE CRITERIA (if ## Done section exists):
1. Check each item in ## Done section
2. Verify each criterion is met
3. Mark verified/failed in review report
4. Block approval if critical items fail
"
    fi
  fi

  review_output=$(claude -p \
    "You are the Review Claude in a multi-Claude workflow.

TASK: Read the plan from ${plan_file}. Review all implementation changes using git diff. Analyze code quality, test coverage, documentation. Generate review report and save to ${review_report_file}.

EFFICIENCY TIPS:
- Use Task agent (subagent_type=Explore) to analyze patterns across multiple files
- For large changesets: Use Task agent to summarize changes before detailed review
${verify_instructions}
REVIEW REQUIREMENTS:
Include in ${review_report_file}:
1) Quality score (1-10)
2) Strengths
3) Issues found
4) Suggestions for improvement
5) Verification Results (if Verify section exists):
   - Command: [command]
   - Result: PASS/FAIL
   - Output: [summary]
6) Done Criteria Status (if Done section exists):
   - [x] Criterion 1: verified
   - [ ] Criterion 2: not met (reason)
7) Approval decision (APPROVED/NEEDS_WORK)

CRITICAL: You MUST create a completion marker when done.

Steps:
1. Review all changes thoroughly
2. Run verification commands (if Verify section exists)
3. Check done criteria (if Done section exists)
4. Save review report to ${review_report_file}
5. Create completion marker using Bash tool:

   touch ${review_done_file}

Marker file: ${review_done_file}
This is REQUIRED for orchestrator to proceed.

$(error_handling_instructions "$review_done_file")" \
    --output-format json \
    --dangerously-skip-permissions 2>&1)

  if [ $? -ne 0 ]; then
    log_error "Review failed"
    echo "$review_output"
    update_task_status "$task_file" "❌ Failed (Review)"
    exit 1
  fi

  log_success "Review requested"

  # Increased timeout to 300s for comprehensive review with verification
  if ! wait_for_marker_with_retry "$review_done_file" "review" 1 300; then
    log_error "Review phase timeout"
    log_info "💾 Workflow state saved to: $STATE_FILE"
    log_info "Resume with: ./scripts/resume-workflow.sh $session_id"
    update_task_status "$task_file" "❌ Failed (Review timeout)"
    exit 1
  fi

  log_success "Review complete"
  PHASES_COMPLETED='"phase0", "phase1", "phase2", "phase3", "phase4"'
  save_phase_state "phase5" 1 "complete"

  # Check review approval
  if [ -f "$review_report_file" ]; then
    if grep -q "APPROVED" "$review_report_file"; then
      log_success "Review status: APPROVED ✓"
      update_task_status "$task_file" "🚧 In Progress (Review approved)"
    else
      log_error "Review status: NEEDS_WORK"
      echo "Review report:"
      cat "$review_report_file"
      update_task_status "$task_file" "⚠️ Needs Work (Review feedback)"
      exit 1
    fi
  else
    log_error "Review report not found"
    update_task_status "$task_file" "❌ Failed (No review report)"
    exit 1
  fi

  log_phase "Phase 6: Integration"
  update_task_status "$task_file" "🚧 In Progress (Integration)"

  log_info "Integration: Running final checks..."

  # Run final validation
  log_info "Running git status check..."
  git status --short

  log_info "Verifying no uncommitted conflicts..."
  if git diff --check; then
    log_success "No whitespace errors"
  else
    log_error "Whitespace errors detected"
    update_task_status "$task_file" "❌ Failed (Whitespace errors)"
    exit 1
  fi

  log_success "Integration checks passed ✓"

  # Commit changes
  log_info "Committing changes..."

  git add .

  commit_message=$(cat <<EOF
feat($task_id): ${TASK_TITLE:-Feature implementation}

Automated implementation via Navigator Multi-Claude workflow.

See plan: $plan_file
See review: $review_report_file

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)

  git commit -m "$commit_message" || {
    log_error "Commit failed"
    update_task_status "$task_file" "❌ Failed (Commit)"
    exit 1
  }

  log_success "Changes committed"

  # Create PR if gh CLI available
  if command -v gh &> /dev/null; then
    log_info "Creating pull request..."

    pr_body=$(cat <<EOF
## Summary
Automated implementation of $task_id.

## Changes
$(git diff --stat main..HEAD)

## Review Report
See: $review_report_file

## Multi-Claude Workflow
- ✅ Planning complete
- ✅ Implementation complete
- ✅ Tests passing
- ✅ Documentation generated
- ✅ Review approved
- ✅ Integration validated

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)

    pr_url=$(gh pr create \
      --title "feat($task_id): ${TASK_TITLE:-Feature implementation}" \
      --body "$pr_body" \
      --base main \
      --head "$branch_name" 2>&1) || {
      log_error "PR creation failed (may already exist)"
      echo "$pr_url"
    }

    if [[ "$pr_url" =~ ^https:// ]]; then
      log_success "PR created: $pr_url"
      echo "$pr_url" > ".agent/tasks/${session_id}-pr-url.txt"
    fi
  else
    log_info "gh CLI not found - skipping PR creation"
  fi

  log_phase "Phase 7: PM Integration"
  update_task_status "$task_file" "🚧 In Progress (PM Integration)"

  # Close ticket in PM system if available
  if command -v gh &> /dev/null; then
    # Extract issue number from task_id (TASK-21 -> 21)
    # Only process if task_id matches TASK-<number> format
    if [[ "$task_id" =~ ^TASK-([0-9]+)$ ]]; then
      issue_num="${BASH_REMATCH[1]}"
      log_info "Closing ticket in PM system..."

      # Close issue and add comment
      gh issue close "$issue_num" --comment "✅ Implementation complete via Multi-Claude workflow

**Branch**: $branch_name
**Plan**: $plan_file
**Review**: $review_report_file

All phases completed:
- ✅ Planning
- ✅ Implementation
- ✅ Testing
- ✅ Documentation
- ✅ Review (APPROVED)
- ✅ Integration

🤖 Generated with [Claude Code](https://claude.com/claude-code)" 2>&1 || {
        log_error "Failed to close ticket (may not exist or already closed)"
      }

      log_success "Ticket closed in PM system"
    else
      log_info "PM integration skipped (non-standard task ID format)"
    fi
  else
    log_info "PM integration skipped (gh CLI not found)"
  fi

  # Mark task complete
  update_task_status "$task_file" "✅ Complete"

  log_phase "✅ Multi-Claude Workflow Complete"
  log_success "Task: $task_id"
  log_success "Branch: $branch_name"
  log_success "Status: Complete"
  log_success "Plan: $plan_file"
  log_success "Review: $review_report_file"

  echo ""
  echo "Next steps:"
  echo "1. Review changes: git diff main..HEAD"
  echo "2. Check review: cat $review_report_file"
  echo "3. Push branch: git push -u origin $branch_name"
  if command -v gh &> /dev/null; then
    echo "4. View PR: gh pr view"
  fi
  echo ""

  # Cleanup temporary files
  log_info "Cleaning up temporary files..."
  rm -f "${task_file}.bak"
  rm -f ".agent/tasks/${session_id}-"*.{done,failed} 2>/dev/null || true
  log_success "Cleanup complete"
}

# Trap errors
trap 'log_error "Script failed on line $LINENO"' ERR

# Run main
main "$@"
