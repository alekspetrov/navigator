#!/bin/bash
# Multi-Claude Workflow Dashboard
# Real-time terminal visualization of parallel agent progress
# Part of Navigator v6.1.0
#
# ⚠️ DEPRECATED (2026-06, TASK-25): the multi-Claude scripts are superseded by
# native Claude Code orchestration; use `/workflows` (live progress) or the
# Agent view to monitor native subagents. Kept for reference only.

set -e

if [ "${NAV_MULTI_CLAUDE_FORCE:-0}" != "1" ]; then
  cat <<'DEPRECATED'
⚠️  multi-claude-dashboard.sh is DEPRECATED (TASK-25).
Monitor native orchestration with /workflows or the Agent view instead.
To run anyway: NAV_MULTI_CLAUDE_FORCE=1 multi-claude-dashboard.sh ...
DEPRECATED
  exit 0
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Progress bar characters
FILLED='█'
EMPTY='░'

# Configuration
REFRESH_INTERVAL=${REFRESH_INTERVAL:-2}
TASKS_DIR=".agent/tasks"
MARKER_LOG=".agent/.marker-log"

# Session to monitor (passed as argument or auto-detect)
SESSION_ID="${1:-}"

# Find latest session if not specified
find_latest_session() {
    if [ -z "$SESSION_ID" ]; then
        local state_file=$(ls -t "$TASKS_DIR"/*-state.json 2>/dev/null | head -1)
        if [ -n "$state_file" ]; then
            SESSION_ID=$(basename "$state_file" | sed 's/-state.json//')
        fi
    fi
}

# Get phase status from markers
get_phase_status() {
    local phase=$1
    local marker_base="$TASKS_DIR/$SESSION_ID"

    case $phase in
        planning)
            [ -f "${marker_base}-plan.md" ] && echo "DONE" || echo "WAIT"
            ;;
        impl)
            if [ -f "${marker_base}-impl-done.failed" ]; then
                echo "FAIL"
            elif [ -f "${marker_base}-impl-done" ]; then
                echo "DONE"
            elif [ -f "${marker_base}-plan.md" ]; then
                echo "RUN"
            else
                echo "WAIT"
            fi
            ;;
        test)
            if [ -f "${marker_base}-tests-done.failed" ]; then
                echo "FAIL"
            elif [ -f "${marker_base}-tests-done" ]; then
                echo "DONE"
            elif [ -f "${marker_base}-impl-done" ]; then
                echo "RUN"
            else
                echo "WAIT"
            fi
            ;;
        docs)
            if [ -f "${marker_base}-docs-done.failed" ]; then
                echo "FAIL"
            elif [ -f "${marker_base}-docs-done" ]; then
                echo "DONE"
            elif [ -f "${marker_base}-impl-done" ]; then
                echo "RUN"
            else
                echo "WAIT"
            fi
            ;;
        review)
            if [ -f "${marker_base}-review-done.failed" ]; then
                echo "FAIL"
            elif [ -f "${marker_base}-review-done" ]; then
                echo "DONE"
            elif [ -f "${marker_base}-tests-done" ] && [ -f "${marker_base}-docs-done" ]; then
                echo "RUN"
            else
                echo "WAIT"
            fi
            ;;
        complete)
            [ -f "${marker_base}-complete" ] && echo "DONE" || echo "WAIT"
            ;;
    esac
}

# Calculate progress percentage
get_progress() {
    local phase=$1
    local status=$(get_phase_status "$phase")

    case $status in
        DONE) echo 100 ;;
        RUN)  echo 50 ;;
        FAIL) echo 0 ;;
        WAIT) echo 0 ;;
    esac
}

# Get status color
get_status_color() {
    local status=$1
    case $status in
        DONE) echo "$GREEN" ;;
        RUN)  echo "$YELLOW" ;;
        FAIL) echo "$RED" ;;
        WAIT) echo "$DIM" ;;
    esac
}

# Draw progress bar
draw_progress_bar() {
    local percent=$1
    local width=20
    local filled=$((percent * width / 100))
    local empty=$((width - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="$FILLED"; done
    for ((i=0; i<empty; i++)); do bar+="$EMPTY"; done

    echo "$bar"
}

# Get elapsed time
get_elapsed_time() {
    local state_file="$TASKS_DIR/$SESSION_ID-state.json"
    if [ -f "$state_file" ]; then
        local started=$(jq -r '.started_at // empty' "$state_file" 2>/dev/null)
        if [ -n "$started" ]; then
            local start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$started" +%s 2>/dev/null || date -d "$started" +%s 2>/dev/null || echo 0)
            local now_epoch=$(date +%s)
            local elapsed=$((now_epoch - start_epoch))
            printf "%d:%02d" $((elapsed / 60)) $((elapsed % 60))
            return
        fi
    fi
    echo "0:00"
}

# Get task description
get_task_description() {
    local state_file="$TASKS_DIR/$SESSION_ID-state.json"
    if [ -f "$state_file" ]; then
        jq -r '.task // "Unknown task"' "$state_file" 2>/dev/null | head -c 45
    else
        echo "Unknown task"
    fi
}

# Calculate total progress
get_total_progress() {
    local phases=("planning" "impl" "test" "docs" "review")
    local total=0
    local count=${#phases[@]}

    for phase in "${phases[@]}"; do
        local status=$(get_phase_status "$phase")
        case $status in
            DONE) total=$((total + 100)) ;;
            RUN)  total=$((total + 50)) ;;
        esac
    done

    echo $((total / count))
}

# Draw dashboard
draw_dashboard() {
    clear

    local task_desc=$(get_task_description)
    local elapsed=$(get_elapsed_time)
    local total_progress=$(get_total_progress)

    # Header
    echo -e "${WHITE}┌─────────────────────────────────────────────────────┐${NC}"
    echo -e "${WHITE}│${NC} ${CYAN}Multi-Agent Workflow${NC}: ${WHITE}$SESSION_ID${NC}"
    echo -e "${WHITE}├─────────────────────────────────────────────────────┤${NC}"
    echo -e "${WHITE}│${NC} Task: ${task_desc}..."
    echo -e "${WHITE}├─────────────────────────────────────────────────────┤${NC}"

    # Agent status rows
    local agents=("orchestrator:planning" "implementer:impl" "tester:test" "reviewer:review" "documenter:docs")

    for agent_phase in "${agents[@]}"; do
        local agent="${agent_phase%%:*}"
        local phase="${agent_phase##*:}"
        local status=$(get_phase_status "$phase")
        local progress=$(get_progress "$phase")
        local color=$(get_status_color "$status")
        local bar=$(draw_progress_bar "$progress")

        printf "${WHITE}│${NC} %-12s ${color}%s${NC} %3d%%  ${color}%-4s${NC}   ${WHITE}│${NC}\n" \
            "$agent" "$bar" "$progress" "$status"
    done

    # Footer
    echo -e "${WHITE}├─────────────────────────────────────────────────────┤${NC}"
    echo -e "${WHITE}│${NC} Progress: ${CYAN}${total_progress}%${NC} │ Time: ${CYAN}${elapsed}${NC} elapsed"
    echo -e "${WHITE}└─────────────────────────────────────────────────────┘${NC}"

    # Status legend
    echo ""
    echo -e "${DIM}Status: ${GREEN}DONE${NC}${DIM}=complete ${YELLOW}RUN${NC}${DIM}=running ${RED}FAIL${NC}${DIM}=failed ${DIM}WAIT${NC}${DIM}=waiting${NC}"
    echo -e "${DIM}Press Ctrl+C to exit${NC}"

    # Recent log entries
    if [ -f "$MARKER_LOG" ]; then
        echo ""
        echo -e "${WHITE}Recent Activity:${NC}"
        tail -5 "$MARKER_LOG" 2>/dev/null | while read line; do
            echo -e "${DIM}  $line${NC}"
        done
    fi
}

# Check if workflow is complete
is_workflow_complete() {
    local status=$(get_phase_status "complete")
    [ "$status" = "DONE" ]
}

# Main loop
main() {
    find_latest_session

    if [ -z "$SESSION_ID" ]; then
        echo -e "${RED}Error: No active workflow found${NC}"
        echo "Usage: $0 [session_id]"
        echo ""
        echo "Start a workflow first with:"
        echo '  "Run multi-agent workflow for TASK-XX"'
        exit 1
    fi

    echo -e "${CYAN}Monitoring workflow: $SESSION_ID${NC}"
    echo -e "${DIM}Refreshing every ${REFRESH_INTERVAL}s...${NC}"
    sleep 1

    # Trap Ctrl+C for graceful exit
    trap 'echo -e "\n${YELLOW}Dashboard stopped${NC}"; exit 0' INT

    while true; do
        draw_dashboard

        if is_workflow_complete; then
            echo ""
            echo -e "${GREEN}✓ Workflow complete!${NC}"
            exit 0
        fi

        sleep "$REFRESH_INTERVAL"
    done
}

# Run
main "$@"
