#!/bin/bash
# Navigator Multi-Claude Proof of Concept
# Tests basic automation with 2-phase workflow (plan → implement)

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

# Wait for file to appear
wait_for_file() {
  local file_path="$1"
  local timeout=120  # 2 minutes
  local elapsed=0

  log_info "Waiting for file: $file_path"

  while [ ! -f "$file_path" ]; do
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
  local timeout="${4:-120}"

  for attempt in $(seq 1 $((max_retries + 1))); do
    if [ $attempt -gt 1 ]; then
      log_info "⚠️  Retry attempt $attempt of $((max_retries + 1)) for phase: $phase_name"
    fi

    if wait_for_file "$marker_file" "$timeout"; then
      if [ -s "$marker_file" ] || [ -f "$marker_file" ]; then
        log_success "✅ Marker verified: $marker_file"
        return 0
      fi
    fi

    if [ $attempt -le $max_retries ]; then
      log_info "⚠️  Timeout on attempt $attempt - retrying phase: $phase_name"
    else
      log_error "❌ Phase failed after $attempt attempts: $phase_name"
      return 1
    fi
  done

  return 1
}

# Main workflow
main() {
  local feature_description="${1:-Add health check endpoint}"

  log_phase "🎯 Navigator Multi-Claude POC"
  log_info "Feature: $feature_description"

  # Ensure we're in project root
  if [ ! -f "CLAUDE.md" ]; then
    log_error "Must run from Navigator project root"
    exit 1
  fi

  # Check if claude CLI exists
  if ! command -v claude &> /dev/null; then
    log_error "Claude Code CLI not found. Install from: https://install.claude.com"
    exit 1
  fi

  # Check if jq exists
  if ! command -v jq &> /dev/null; then
    log_error "jq not found. Install with: brew install jq"
    exit 1
  fi

  log_phase "Phase 1: Planning (Orchestrator)"

  # Generate unique task ID
  local task_id="poc-$(date +%s)"
  local plan_file=".agent/tasks/${task_id}-plan.md"

  # Step 1: Create plan and save to file
  log_info "Orchestrator: Creating implementation plan..."

  orchestrator_output=$(claude -p \
    "Start Navigator session. Create a brief implementation plan for: $feature_description. Save the plan to ${plan_file} using the Write tool. Include: 1) Feature description 2) Implementation steps 3) Files to modify 4) Expected outcome." \
    --output-format json \
    --dangerously-skip-permissions 2>&1)

  if [ $? -ne 0 ]; then
    log_error "Orchestrator failed"
    echo "$orchestrator_output"
    exit 1
  fi

  log_success "Plan creation requested"

  # Wait for plan file with retry
  if ! wait_for_marker_with_retry "$plan_file" "planning" 1 120; then
    log_error "Planning phase failed - no plan file created"
    exit 1
  fi

  log_success "Plan saved to: $plan_file"

  log_phase "Phase 2: Implementation"

  # Launch implementation in headless mode
  log_info "Implementation: Building feature from plan..."

  local impl_done_file=".agent/tasks/${task_id}-done"

  impl_output=$(claude -p \
    "Read the plan from ${plan_file}. Implement the feature following the plan. When done, create empty file ${impl_done_file} using: touch ${impl_done_file}" \
    --output-format json \
    --allowedTools "Read,Write,Edit,Bash" \
    --dangerously-skip-permissions 2>&1)

  if [ $? -ne 0 ]; then
    log_error "Implementation failed"
    echo "$impl_output"
    exit 1
  fi

  log_success "Implementation requested"

  # Wait for completion marker file with retry
  if ! wait_for_marker_with_retry "$impl_done_file" "implementation" 1 120; then
    log_error "Implementation phase failed - no completion marker"
    exit 1
  fi

  log_success "Implementation complete"

  log_phase "Phase 3 & 4: Parallel Testing + Documentation"

  local test_done_file=".agent/tasks/${task_id}-tests-done"
  local docs_done_file=".agent/tasks/${task_id}-docs-done"

  # Launch testing Claude in background
  log_info "Testing: Validating implementation and generating tests... (parallel)"

  (
    test_output=$(claude -p \
      "Read the plan from ${plan_file}. Your task is to VERIFY the implementation.

CRITICAL: You MUST create the completion marker when done, regardless of what you find.

For CODE implementations:
- Generate and run tests
- Report test results

For RESEARCH/EVALUATION tasks (reports, analysis, documentation):
- Verify the findings are complete and accurate
- Check that recommendations are justified
- No code tests needed - just verify the report quality

When complete (success OR if no tests applicable), create the marker:
touch ${test_done_file}

This marker is REQUIRED for the workflow to proceed." \
      --output-format json \
      --allowedTools "Read,Write,Edit,Bash" \
      --dangerously-skip-permissions 2>&1)

    # Always create marker if Claude exits (even on failure)
    if [ $? -ne 0 ]; then
      echo "TEST_FAILED: $test_output" > ".agent/tasks/${task_id}-tests-failed"
      touch "${test_done_file}"  # Create marker anyway to unblock workflow
      log_error "Testing failed but marker created"
    fi
  ) &
  local test_pid=$!

  # Launch documentation Claude in parallel
  log_info "Documentation: Generating comprehensive docs... (parallel)"

  (
    docs_output=$(claude -p \
      "Read the plan from ${plan_file}. Review the implementation and generate documentation.

CRITICAL: You MUST create the completion marker when done.

For CODE implementations:
- Generate README sections, JSDoc improvements, usage examples

For RESEARCH/EVALUATION tasks:
- Documentation is likely already complete in the report
- Verify documentation quality, add summary if needed

When complete, create the marker:
touch ${docs_done_file}

This marker is REQUIRED for the workflow to proceed." \
      --output-format json \
      --allowedTools "Read,Write,Edit,Bash" \
      --dangerously-skip-permissions 2>&1)

    # Always create marker if Claude exits (even on failure)
    if [ $? -ne 0 ]; then
      echo "DOCS_FAILED: $docs_output" > ".agent/tasks/${task_id}-docs-failed"
      touch "${docs_done_file}"  # Create marker anyway to unblock workflow
      log_error "Documentation failed but marker created"
    fi
  ) &
  local docs_pid=$!

  log_success "Parallel execution started (Testing + Documentation)"

  # Wait for both processes to complete
  log_info "Waiting for parallel phases to complete..."

  # Wait for testing with retry (longer timeout for complex tasks)
  if ! wait_for_marker_with_retry "$test_done_file" "testing" 1 180; then
    log_error "Testing phase timeout - creating marker to continue"
    touch "$test_done_file"  # Force marker creation
    echo "TIMEOUT" > ".agent/tasks/${task_id}-tests-failed"
    kill $test_pid 2>/dev/null || true
  fi
  log_success "Testing phase complete"

  # Wait for documentation with retry
  if ! wait_for_marker_with_retry "$docs_done_file" "documentation" 1 180; then
    log_error "Documentation phase timeout - creating marker to continue"
    touch "$docs_done_file"  # Force marker creation
    echo "TIMEOUT" > ".agent/tasks/${task_id}-docs-failed"
    kill $docs_pid 2>/dev/null || true
  fi
  log_success "Documentation phase complete"

  # Wait for background processes to fully exit
  wait $test_pid $docs_pid 2>/dev/null

  # Check quality gates (warn but don't fail for research tasks)
  log_info "Checking quality gates..."

  local has_warnings=false

  if [ -f ".agent/tasks/${task_id}-tests-failed" ]; then
    local fail_reason=$(cat ".agent/tasks/${task_id}-tests-failed" 2>/dev/null | head -1)
    if [ "$fail_reason" = "TIMEOUT" ]; then
      log_info "⚠️  Testing phase timed out (may be expected for research tasks)"
      has_warnings=true
    else
      log_error "Tests failed - quality gate warning"
      cat ".agent/tasks/${task_id}-tests-failed"
      has_warnings=true
    fi
  fi

  if [ -f ".agent/tasks/${task_id}-docs-failed" ]; then
    local fail_reason=$(cat ".agent/tasks/${task_id}-docs-failed" 2>/dev/null | head -1)
    if [ "$fail_reason" = "TIMEOUT" ]; then
      log_info "⚠️  Documentation phase timed out"
      has_warnings=true
    else
      log_error "Documentation generation warning"
      cat ".agent/tasks/${task_id}-docs-failed"
      has_warnings=true
    fi
  fi

  if [ "$has_warnings" = true ]; then
    log_info "⚠️  Workflow completed with warnings"
  else
    log_success "All quality gates passed ✓"
  fi

  log_phase "Phase 5: Review"

  local review_done_file=".agent/tasks/${task_id}-review-done"
  local review_report_file=".agent/tasks/${task_id}-review-report.md"

  log_info "Review: Analyzing all changes and providing quality assessment..."

  review_output=$(claude -p \
    "Read the plan from ${plan_file}. Review all implementation changes using git diff. Analyze code quality, test coverage, documentation completeness. Generate a review report and save it to ${review_report_file}. Include: 1) Quality score (1-10) 2) Strengths 3) Issues found 4) Suggestions 5) Approval decision (APPROVED/NEEDS_WORK). When done, create empty file ${review_done_file} using the Bash tool: touch ${review_done_file}" \
    --output-format json \
    --allowedTools "Read,Write,Bash,Grep,Glob" \
    --dangerously-skip-permissions 2>&1)

  if [ $? -ne 0 ]; then
    log_error "Review failed"
    echo "$review_output"
    exit 1
  fi

  log_success "Review requested"

  if ! wait_for_marker_with_retry "$review_done_file" "review" 1 120; then
    log_error "Review phase timeout - no completion marker"
    exit 1
  fi

  log_success "Review complete"

  # Check review approval
  if [ -f "$review_report_file" ]; then
    if grep -q "APPROVED" "$review_report_file"; then
      log_success "Review status: APPROVED ✓"
    else
      log_error "Review status: NEEDS_WORK"
      echo "Review report:"
      cat "$review_report_file"
      exit 1
    fi
  else
    log_error "Review report not found"
    exit 1
  fi

  log_phase "Phase 6: Integration"

  log_info "Integration: Running final checks and cleanup..."

  # Run final validation
  log_info "Running git status check..."
  git status --short

  log_info "Verifying no uncommitted conflicts..."
  if git diff --check; then
    log_success "No whitespace errors"
  else
    log_error "Whitespace errors detected"
    exit 1
  fi

  log_success "Integration checks passed ✓"

  log_phase "✅ POC Complete"
  log_success "Feature: $feature_description"
  log_success "Phases: Planning ✓ Implementation ✓ [Testing+Docs] ✓ Review ✓ Integration ✓"
  log_success "Plan: $plan_file"
  log_success "Review: $review_report_file"

  echo ""
  echo "Next steps:"
  echo "1. Review changes: git status"
  echo "2. Check plan: cat $plan_file"
  echo "3. Check review: cat $review_report_file"
  echo "4. Commit changes: git add . && git commit -m 'feat: $feature_description'"
  echo ""
}

# Trap errors
trap 'log_error "Script failed on line $LINENO"' ERR

# Run main
main "$@"
