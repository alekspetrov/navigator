#!/bin/bash
# Sub-Claude Timeout Monitor
# Monitors headless Claude instances for timeouts and marker creation
#
# ⚠️ DEPRECATED (2026-06, TASK-25): internal helper for the deprecated
# navigator-multi-claude.sh orchestrator. Superseded by native Claude Code
# orchestration (/workflows, the Agent tool). Kept for reference only.

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Parse arguments
PHASE_NAME="${1:-unknown}"
TIMEOUT="${2:-180}"  # 3 minutes default
CLAUDE_PID="${3:-}"
MARKER_FILE="${4:-}"

if [ -z "$CLAUDE_PID" ] || [ -z "$MARKER_FILE" ]; then
  echo -e "${RED}Usage: $0 PHASE_NAME TIMEOUT CLAUDE_PID MARKER_FILE${NC}" >&2
  exit 1
fi

log_monitor() {
  echo -e "${YELLOW}[Monitor]${NC} $1" >&2
}

log_warning() {
  echo -e "${YELLOW}[Monitor] ⚠️${NC} $1" >&2
}

log_error() {
  echo -e "${RED}[Monitor] ❌${NC} $1" >&2
}

log_success() {
  echo -e "${GREEN}[Monitor] ✅${NC} $1" >&2
}

# Main monitoring loop
monitor_claude() {
  local elapsed=0
  local check_interval=5  # Check every 5 seconds
  local last_check=$((TIMEOUT - 30))  # Check for marker 30s before timeout

  log_monitor "Monitoring phase: $PHASE_NAME (timeout: ${TIMEOUT}s)"
  log_monitor "Claude PID: $CLAUDE_PID"
  log_monitor "Marker file: $MARKER_FILE"

  while [ $elapsed -lt $TIMEOUT ]; do
    # Check if Claude process is still running
    if ! kill -0 "$CLAUDE_PID" 2>/dev/null; then
      log_monitor "Claude process $CLAUDE_PID exited naturally"

      # Give it a moment to write the marker
      sleep 2

      if [ -f "$MARKER_FILE" ]; then
        log_success "Marker found after process exit"
        exit 0
      else
        log_warning "Process exited but no marker found"
        exit 1
      fi
    fi

    # Check if marker exists
    if [ -f "$MARKER_FILE" ]; then
      log_success "Marker found: $MARKER_FILE"

      # Log to central marker log
      if [ -f ".agent/.marker-log" ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ✅ $PHASE_NAME: $MARKER_FILE (elapsed: ${elapsed}s)" >> .agent/.marker-log
      fi

      exit 0
    fi

    # Warn when approaching timeout
    if [ $elapsed -eq $last_check ]; then
      log_warning "Approaching timeout (30s remaining) for phase: $PHASE_NAME"

      # Log warning to marker log
      if [ -f ".agent/.marker-log" ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ⚠️  $PHASE_NAME: Timeout approaching (${elapsed}/${TIMEOUT}s)" >> .agent/.marker-log
      fi
    fi

    sleep $check_interval
    elapsed=$((elapsed + check_interval))
  done

  # Timeout reached
  log_error "Timeout reached (${TIMEOUT}s) for phase: $PHASE_NAME"

  # Check one final time for marker (race condition)
  if [ -f "$MARKER_FILE" ]; then
    log_success "Marker found just after timeout - accepting"

    if [ -f ".agent/.marker-log" ]; then
      echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ✅ $PHASE_NAME: $MARKER_FILE (at timeout)" >> .agent/.marker-log
    fi

    exit 0
  fi

  # Log timeout to marker log
  if [ -f ".agent/.marker-log" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ❌ $PHASE_NAME: Timeout (no marker after ${TIMEOUT}s)" >> .agent/.marker-log
  fi

  # Kill Claude process if still running
  if kill -0 "$CLAUDE_PID" 2>/dev/null; then
    log_warning "Killing Claude process $CLAUDE_PID due to timeout"
    kill -TERM "$CLAUDE_PID" 2>/dev/null || true

    # Wait 5 seconds for graceful shutdown
    sleep 5

    # Force kill if still running
    if kill -0 "$CLAUDE_PID" 2>/dev/null; then
      log_warning "Force killing Claude process $CLAUDE_PID"
      kill -KILL "$CLAUDE_PID" 2>/dev/null || true
    fi
  fi

  exit 1
}

# Run monitor
monitor_claude
