#!/bin/bash
# Test Sub-Claude Monitor
# Simulates stuck Claude processes and verifies timeout detection

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEST_DIR=".agent/tasks/test-monitor-$$"
mkdir -p "$TEST_DIR"

# Portable timeout function for macOS/Linux compatibility
run_with_timeout() {
  local timeout_seconds="$1"
  shift

  # Check if GNU timeout is available
  if command -v timeout &>/dev/null; then
    timeout "$timeout_seconds" "$@"
    return $?
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$timeout_seconds" "$@"
    return $?
  else
    # Portable fallback using background process
    "$@" &
    local cmd_pid=$!

    (sleep "$timeout_seconds" && kill -TERM "$cmd_pid" 2>/dev/null) &
    local watchdog_pid=$!

    wait "$cmd_pid" 2>/dev/null
    local exit_code=$?

    # Kill watchdog if command finished before timeout
    kill "$watchdog_pid" 2>/dev/null || true
    wait "$watchdog_pid" 2>/dev/null || true

    return $exit_code
  fi
}

log_test() {
  echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
  exit 1
}

cleanup() {
  rm -rf "$TEST_DIR"
  # Kill any background processes
  jobs -p | xargs kill 2>/dev/null || true
}

trap cleanup EXIT

# Test 1: Monitor detects marker creation
test_marker_detection() {
  log_test "Test 1: Monitor detects marker creation"

  local marker_file="$TEST_DIR/test1-marker"

  # Start a dummy process
  sleep 30 &
  local test_pid=$!

  # Create marker after 2 seconds
  (sleep 2 && touch "$marker_file") &

  # Start monitor (15 second timeout to allow for 5-second check interval)
  # Monitor checks at t=0, t=5, t=10... marker created at t=2, detected at t=5
  if run_with_timeout 20 ./scripts/sub-claude-monitor.sh "test1" 15 "$test_pid" "$marker_file" 2>/dev/null; then
    log_pass "Monitor detected marker creation"
  else
    log_fail "Monitor failed to detect marker"
  fi

  kill $test_pid 2>/dev/null || true
  rm -f "$marker_file"
}

# Test 2: Monitor times out and kills process
test_timeout_kill() {
  log_test "Test 2: Monitor times out and kills stuck process"

  local marker_file="$TEST_DIR/test2-marker"

  # Start a process that never creates marker
  sleep 30 &
  local test_pid=$!

  # Start monitor with short timeout (3 seconds)
  if ./scripts/sub-claude-monitor.sh "test2" 3 "$test_pid" "$marker_file" 2>/dev/null; then
    log_fail "Monitor should have timed out"
  else
    # Verify process was killed
    if kill -0 "$test_pid" 2>/dev/null; then
      log_fail "Process should have been killed"
    else
      log_pass "Monitor timed out and killed process"
    fi
  fi
}

# Test 3: Process exits naturally with marker
test_natural_exit() {
  log_test "Test 3: Process exits naturally with marker"

  local marker_file="$TEST_DIR/test3-marker"

  # Start a short process that creates marker
  (sleep 1 && touch "$marker_file" && exit 0) &
  local test_pid=$!

  # Start monitor
  if ./scripts/sub-claude-monitor.sh "test3" 10 "$test_pid" "$marker_file" 2>/dev/null; then
    log_pass "Monitor handled natural exit correctly"
  else
    log_fail "Monitor should succeed when process exits with marker"
  fi

  rm -f "$marker_file"
}

# Test 4: Process exits without marker
test_exit_without_marker() {
  log_test "Test 4: Process exits without creating marker"

  local marker_file="$TEST_DIR/test4-marker"

  # Start a short process that doesn't create marker
  (sleep 1 && exit 0) &
  local test_pid=$!

  # Start monitor
  if ./scripts/sub-claude-monitor.sh "test4" 10 "$test_pid" "$marker_file" 2>/dev/null; then
    log_fail "Monitor should fail when no marker created"
  else
    log_pass "Monitor correctly detected missing marker"
  fi
}

# Test 5: Marker log creation
test_marker_log() {
  log_test "Test 5: Marker log creation"

  mkdir -p .agent
  local marker_log=".agent/.marker-log"
  local marker_file="$TEST_DIR/test5-marker"

  # Clear log
  > "$marker_log"

  # Start dummy process
  sleep 10 &
  local test_pid=$!

  # Create marker quickly
  touch "$marker_file"

  # Run monitor
  ./scripts/sub-claude-monitor.sh "test5" 10 "$test_pid" "$marker_file" 2>/dev/null || true

  # Verify log entry
  if grep -q "test5" "$marker_log"; then
    log_pass "Marker log entry created"
  else
    log_fail "Marker log entry missing"
  fi

  kill $test_pid 2>/dev/null || true
  rm -f "$marker_file"
}

# Run all tests
echo ""
echo "======================================"
echo "  Sub-Claude Monitor Tests"
echo "======================================"
echo ""

test_marker_detection
test_timeout_kill
test_natural_exit
test_exit_without_marker
test_marker_log

echo ""
echo -e "${GREEN}All tests passed! ✅${NC}"
echo ""
