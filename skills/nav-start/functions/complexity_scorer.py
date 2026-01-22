#!/usr/bin/env python3
"""
Navigator Complexity Scorer

Calculates task complexity from user input to determine if Task Mode should activate.
More detailed than workflow_detector - used for precise scoring.

Usage:
    python complexity_scorer.py "refactor auth system to use JWT"
    python complexity_scorer.py --threshold 0.5 "add new button"
    echo "implement user dashboard" | python complexity_scorer.py

Returns JSON:
    {
        "score": 0.0-1.0,
        "task_mode": true/false,
        "category": "trivial" | "simple" | "moderate" | "substantial" | "complex",
        "factors": {
            "action_type": 0.X,
            "scope": 0.X,
            "files_implied": 0.X,
            "planning_needed": 0.X
        },
        "matched": [...]
    }

Scoring:
    0.0-0.2: trivial (typo fix, single line)
    0.2-0.4: simple (small edit, one file)
    0.4-0.6: moderate (feature addition, few files)
    0.6-0.8: substantial (refactor, many files) → TASK MODE
    0.8-1.0: complex (architecture, major changes) → TASK MODE
"""

import argparse
import json
import sys
from typing import Dict, List, Tuple


# Action type scoring (primary factor)
ACTION_SCORES = {
    # Complex actions (0.4)
    "complex": {
        "words": ["refactor", "redesign", "architect", "overhaul", "rewrite", "migrate"],
        "score": 0.4,
    },
    # Substantial actions (0.3)
    "substantial": {
        "words": ["implement", "integrate", "build", "develop", "create feature"],
        "score": 0.3,
    },
    # Moderate actions (0.2)
    "moderate": {
        "words": ["add", "update", "modify", "enhance", "extend", "improve"],
        "score": 0.2,
    },
    # Simple actions (0.1)
    "simple": {
        "words": ["fix", "change", "rename", "move", "delete", "remove"],
        "score": 0.1,
    },
    # Trivial actions (0.05)
    "trivial": {
        "words": ["typo", "comment", "format", "lint", "whitespace"],
        "score": 0.05,
    },
}

# Scope modifiers (adds to score)
SCOPE_MODIFIERS = {
    # Project-wide (0.3)
    "project": {
        "words": ["all", "every", "entire", "whole", "across", "throughout", "project-wide", "codebase"],
        "score": 0.3,
    },
    # Multiple items (0.2)
    "multiple": {
        "words": ["multiple", "several", "many", "various", "different"],
        "score": 0.2,
    },
    # Single/specific (0.0)
    "single": {
        "words": ["this", "the", "single", "one", "specific"],
        "score": 0.0,
    },
}

# File count indicators (adds to score)
FILE_INDICATORS = {
    "many": {
        "words": ["files", "components", "modules", "services", "endpoints"],
        "score": 0.2,
    },
    "few": {
        "words": ["file", "component", "module", "function", "method"],
        "score": 0.1,
    },
}

# Planning indicators (adds to score)
PLANNING_INDICATORS = {
    "needs_planning": {
        "words": ["plan", "design", "strategy", "approach", "architecture", "structure"],
        "score": 0.2,
    },
    "needs_research": {
        "words": ["investigate", "explore", "understand", "analyze", "figure out"],
        "score": 0.15,
    },
}


def find_matches(message: str, word_list: List[str]) -> List[str]:
    """Find all matching words in message."""
    message_lower = message.lower()
    return [word for word in word_list if word in message_lower]


def calculate_score(message: str) -> Dict:
    """
    Calculate complexity score with detailed breakdown.

    Returns complete scoring result.
    """
    message_lower = message.lower()
    factors = {
        "action_type": 0.0,
        "scope": 0.0,
        "files_implied": 0.0,
        "planning_needed": 0.0,
    }
    matched = []

    # Score action type (take highest match)
    for level, data in ACTION_SCORES.items():
        matches = find_matches(message, data["words"])
        if matches:
            if data["score"] > factors["action_type"]:
                factors["action_type"] = data["score"]
                matched.extend([f"action:{m}" for m in matches])

    # Score scope (take highest match)
    for level, data in SCOPE_MODIFIERS.items():
        matches = find_matches(message, data["words"])
        if matches:
            if data["score"] > factors["scope"]:
                factors["scope"] = data["score"]
                matched.extend([f"scope:{m}" for m in matches])

    # Score file indicators
    for level, data in FILE_INDICATORS.items():
        matches = find_matches(message, data["words"])
        if matches:
            factors["files_implied"] = max(factors["files_implied"], data["score"])
            matched.extend([f"files:{m}" for m in matches])

    # Score planning indicators
    for level, data in PLANNING_INDICATORS.items():
        matches = find_matches(message, data["words"])
        if matches:
            factors["planning_needed"] = max(factors["planning_needed"], data["score"])
            matched.extend([f"planning:{m}" for m in matches])

    # Calculate total (capped at 1.0)
    total = sum(factors.values())
    total = min(total, 1.0)

    # Determine category
    if total < 0.2:
        category = "trivial"
    elif total < 0.4:
        category = "simple"
    elif total < 0.6:
        category = "moderate"
    elif total < 0.8:
        category = "substantial"
    else:
        category = "complex"

    return {
        "score": round(total, 2),
        "task_mode": total >= 0.5,
        "category": category,
        "factors": {k: round(v, 2) for k, v in factors.items()},
        "matched": matched,
    }


def main():
    parser = argparse.ArgumentParser(description="Navigator Complexity Scorer")
    parser.add_argument("message", nargs="?", help="User message to analyze")
    parser.add_argument("--threshold", type=float, default=0.5, help="Task Mode threshold (default: 0.5)")

    args = parser.parse_args()

    # Read from stdin if no message provided
    if args.message:
        message = args.message
    else:
        message = sys.stdin.read().strip()

    if not message:
        print(json.dumps({"error": "No message provided"}))
        sys.exit(1)

    result = calculate_score(message)

    # Override task_mode based on custom threshold
    result["task_mode"] = result["score"] >= args.threshold
    result["threshold"] = args.threshold

    print(json.dumps(result, indent=2))

    # Exit code: 0 if task mode, 1 if not
    sys.exit(0 if result["task_mode"] else 1)


if __name__ == "__main__":
    main()
