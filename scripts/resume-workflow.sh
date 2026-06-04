#!/bin/bash
# Resume Multi-Claude Workflow
# Resumes interrupted workflows from saved state
#
# ⚠️ DEPRECATED (2026-06, TASK-25): the multi-Claude scripts are superseded by
# native Claude Code Dynamic Workflows (/workflows), which resume in-session.
# Kept for reference only.

set -euo pipefail

if [ "${NAV_MULTI_CLAUDE_FORCE:-0}" != "1" ]; then
  cat <<'DEPRECATED'
⚠️  resume-workflow.sh is DEPRECATED (TASK-25).
Native Dynamic Workflows (/workflows) resume in-session; no marker state needed.
To run anyway: NAV_MULTI_CLAUDE_FORCE=1 resume-workflow.sh ...
DEPRECATED
  exit 0
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
  echo -e "${BLUE}[Resume]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[Resume] ✅${NC} $1"
}

log_error() {
  echo -e "${RED}[Resume] ❌${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[Resume] ⚠️${NC} $1"
}

# Parse arguments
SESSION_ID="${1:-}"

if [ -z "$SESSION_ID" ]; then
  log_error "Usage: $0 SESSION_ID"
  echo ""
  echo "Example: $0 task-21-1730561234"
  echo ""
  echo "Available sessions:"
  for state_file in .agent/tasks/*-state.json; do
    if [ -f "$state_file" ]; then
      session=$(basename "$state_file" | sed 's/-state.json//')
      echo "  - $session"
    fi
  done
  exit 1
fi

STATE_FILE=".agent/tasks/${SESSION_ID}-state.json"

# Check if state file exists
if [ ! -f "$STATE_FILE" ]; then
  log_error "State file not found: $STATE_FILE"
  exit 1
fi

# Check dependencies
if ! command -v jq &> /dev/null; then
  log_error "jq not found. Install with: brew install jq"
  exit 1
fi

# Read state
log_info "Reading workflow state from: $STATE_FILE"

TASK_ID=$(jq -r '.task' "$STATE_FILE")
CURRENT_PHASE=$(jq -r '.current_phase' "$STATE_FILE")
STATUS=$(jq -r '.status' "$STATE_FILE")
PHASES_COMPLETED=$(jq -r '.phases_completed | join(", ")' "$STATE_FILE")
LAST_UPDATE=$(jq -r '.last_update' "$STATE_FILE")

# Display state
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Workflow State${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Session ID:       ${BLUE}$SESSION_ID${NC}"
echo -e "Task:             ${BLUE}$TASK_ID${NC}"
echo -e "Current Phase:    ${YELLOW}$CURRENT_PHASE${NC}"
echo -e "Status:           ${RED}$STATUS${NC}"
echo -e "Completed Phases: ${GREEN}$PHASES_COMPLETED${NC}"
echo -e "Last Update:      $LAST_UPDATE"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if already complete
if [ "$STATUS" == "complete" ]; then
  log_success "Workflow already complete!"
  exit 0
fi

# Confirm resume
read -p "Resume workflow from phase '$CURRENT_PHASE'? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [ -n "$REPLY" ]; then
  log_info "Resume cancelled"
  exit 0
fi

log_info "Resuming workflow..."

# Determine which script to use (POC vs production)
PLAN_FILE=".agent/tasks/${SESSION_ID}-plan.md"

if [ ! -f "$PLAN_FILE" ]; then
  log_error "Plan file not found: $PLAN_FILE"
  exit 1
fi

# Map phase names to resume actions
resume_phase() {
  local phase="$1"

  case "$phase" in
    "planning"|"phase0")
      log_info "Resuming from planning phase..."
      log_warning "Planning phase needs manual intervention"
      log_info "Suggested action: Re-run orchestrator or fix plan file"
      exit 1
      ;;

    "implementation"|"phase1"|"phase2")
      log_info "Resuming implementation phase..."
      local impl_done_file=".agent/tasks/${SESSION_ID}-done"

      claude -p \
        "Read the plan from ${PLAN_FILE}. Continue implementation. When done, create marker: touch ${impl_done_file}" \
        --output-format json \
        --dangerously-skip-permissions

      log_success "Implementation phase resumed"
      ;;

    "testing"|"phase3")
      log_info "Resuming testing phase..."
      local test_done_file=".agent/tasks/${SESSION_ID}-tests-done"

      claude -p \
        "Read the plan from ${PLAN_FILE}. Generate and run tests. When done, create marker: touch ${test_done_file}" \
        --output-format json \
        --dangerously-skip-permissions

      log_success "Testing phase resumed"
      ;;

    "documentation"|"phase4")
      log_info "Resuming documentation phase..."
      local docs_done_file=".agent/tasks/${SESSION_ID}-docs-done"

      claude -p \
        "Read the plan from ${PLAN_FILE}. Generate documentation. When done, create marker: touch ${docs_done_file}" \
        --output-format json \
        --dangerously-skip-permissions

      log_success "Documentation phase resumed"
      ;;

    "review"|"phase5")
      log_info "Resuming review phase..."
      local review_done_file=".agent/tasks/${SESSION_ID}-review-done"
      local review_report_file=".agent/tasks/${SESSION_ID}-review-report.md"

      claude -p \
        "Read the plan from ${PLAN_FILE}. Review implementation and create report at ${review_report_file}. When done, create marker: touch ${review_done_file}" \
        --output-format json \
        --dangerously-skip-permissions

      log_success "Review phase resumed"
      ;;

    *)
      log_error "Unknown phase: $phase"
      exit 1
      ;;
  esac
}

# Resume the current phase
resume_phase "$CURRENT_PHASE"

# Update state to complete
jq '.status = "resumed"' "$STATE_FILE" > "${STATE_FILE}.tmp"
mv "${STATE_FILE}.tmp" "$STATE_FILE"

log_success "Workflow resumed successfully!"
echo ""
echo "Next steps:"
echo "1. Verify phase completion"
echo "2. Continue with next phase or re-run full workflow"
echo "3. Check state: cat $STATE_FILE"
echo ""
