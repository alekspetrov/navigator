#!/usr/bin/env python3
"""
Navigator Workflow Detector

Detects Loop Mode triggers and Task Mode complexity from user input.
Used to enforce workflow compliance.

Usage:
    python workflow_detector.py "user message here"
    python workflow_detector.py --check-loop "run until done: fix the bug"
    python workflow_detector.py --check-complexity "refactor auth system"

Returns JSON:
    {
        "loop_mode": true/false,
        "loop_trigger": "matched phrase" or null,
        "task_mode": true/false,
        "complexity": 0.0-1.0,
        "complexity_indicators": [...],
        "recommended_mode": "LOOP" | "TASK" | "DIRECT"
    }
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Optional, Tuple


# Loop Mode trigger phrases (case-insensitive)
LOOP_TRIGGERS = [
    "run until done",
    "do all",
    "do it all",
    "keep going",
    "iterate until",
    "finish this",
    "complete everything",
    "don't stop",
    "dont stop",
    "until complete",
    "until finished",
    "until done",
    "all of it",
    "everything",
    "loop mode",
    "autonomous mode",
]

# Task Mode complexity indicators (case-insensitive)
COMPLEXITY_INDICATORS = {
    # High complexity (0.3 each, max contributes 0.9)
    "high": [
        "refactor",
        "implement",
        "add feature",
        "new feature",
        "architecture",
        "redesign",
        "migrate",
        "overhaul",
    ],
    # Medium complexity (0.2 each)
    "medium": [
        "fix all",
        "update all",
        "change all",
        "modify",
        "enhance",
        "improve",
        "extend",
        "integrate",
    ],
    # Low complexity (0.1 each)
    "low": [
        "add",
        "create",
        "update",
        "fix",
        "change",
        "remove",
        "delete",
    ],
}

# Multi-file indicators (adds 0.2)
MULTI_FILE_INDICATORS = [
    "multiple files",
    "several files",
    "across",
    "all files",
    "everywhere",
    "throughout",
    "project-wide",
    "codebase",
]


def detect_loop_trigger(message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if message contains Loop Mode trigger phrases.

    Returns:
        (is_triggered, matched_phrase)
    """
    message_lower = message.lower()

    for trigger in LOOP_TRIGGERS:
        if trigger in message_lower:
            return True, trigger

    return False, None


def calculate_complexity(message: str) -> Tuple[float, List[str]]:
    """
    Calculate task complexity score from message.

    Returns:
        (score 0.0-1.0, list of matched indicators)
    """
    message_lower = message.lower()
    score = 0.0
    matched = []

    # Check high complexity indicators
    for indicator in COMPLEXITY_INDICATORS["high"]:
        if indicator in message_lower:
            score += 0.3
            matched.append(f"high:{indicator}")

    # Check medium complexity indicators
    for indicator in COMPLEXITY_INDICATORS["medium"]:
        if indicator in message_lower:
            score += 0.2
            matched.append(f"medium:{indicator}")

    # Check low complexity indicators
    for indicator in COMPLEXITY_INDICATORS["low"]:
        if indicator in message_lower:
            score += 0.1
            matched.append(f"low:{indicator}")

    # Check multi-file indicators
    for indicator in MULTI_FILE_INDICATORS:
        if indicator in message_lower:
            score += 0.2
            matched.append(f"multi-file:{indicator}")
            break  # Only count once

    # Cap at 1.0
    score = min(score, 1.0)

    return score, matched


def detect_workflow(message: str) -> Dict:
    """
    Full workflow detection - Loop Mode and Task Mode.

    Returns:
        Complete detection result as dict
    """
    # Check Loop Mode
    loop_triggered, loop_phrase = detect_loop_trigger(message)

    # Check Task Mode complexity
    complexity, indicators = calculate_complexity(message)
    task_mode = complexity >= 0.5

    # Determine recommended mode
    if loop_triggered:
        mode = "LOOP"
    elif task_mode:
        mode = "TASK"
    else:
        mode = "DIRECT"

    return {
        "loop_mode": loop_triggered,
        "loop_trigger": loop_phrase,
        "task_mode": task_mode,
        "complexity": round(complexity, 2),
        "complexity_indicators": indicators,
        "recommended_mode": mode,
    }


def main():
    parser = argparse.ArgumentParser(description="Navigator Workflow Detector")
    parser.add_argument("message", nargs="?", help="User message to analyze")
    parser.add_argument("--check-loop", action="store_true", help="Only check Loop Mode")
    parser.add_argument("--check-complexity", action="store_true", help="Only check complexity")

    args = parser.parse_args()

    # Read from stdin if no message provided
    if args.message:
        message = args.message
    else:
        message = sys.stdin.read().strip()

    if not message:
        print(json.dumps({"error": "No message provided"}))
        sys.exit(1)

    if args.check_loop:
        triggered, phrase = detect_loop_trigger(message)
        result = {"loop_mode": triggered, "loop_trigger": phrase}
    elif args.check_complexity:
        score, indicators = calculate_complexity(message)
        result = {
            "task_mode": score >= 0.5,
            "complexity": round(score, 2),
            "complexity_indicators": indicators,
        }
    else:
        result = detect_workflow(message)

    print(json.dumps(result, indent=2))

    # Exit code: 0 if workflow mode detected, 1 if direct
    if result.get("recommended_mode") == "DIRECT" and not result.get("loop_mode"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
