#!/usr/bin/env python3
"""
Stagnation detection for Navigator loop mode.

Detects when the loop is stuck in the same state by comparing
state hashes across iterations.

Usage:
    python3 stagnation_detector.py \
        --phase "IMPL" \
        --indicators '{"code_committed": false}' \
        --files-changed '["src/auth.ts"]' \
        --history '["abc123", "abc123"]' \
        --threshold 3

Output:
    JSON with stagnation status and hash
"""

import argparse
import hashlib
import json
import sys
from typing import List, Tuple


def calculate_state_hash(
    phase: str,
    indicators: dict,
    files_changed: List[str],
    error_state: str = None
) -> str:
    """
    Generate hash representing current state.

    Same hash = same state = potential stagnation.
    """
    state_components = {
        "phase": phase,
        "indicators": sorted([
            k for k, v in indicators.items() if v
        ]),
        "files_changed": sorted(files_changed) if files_changed else [],
        "error_state": error_state
    }

    state_json = json.dumps(state_components, sort_keys=True)
    return hashlib.md5(state_json.encode()).hexdigest()[:6]


def count_consecutive_same(history: List[str], current_hash: str) -> int:
    """Count consecutive occurrences of current hash in history."""
    consecutive = 1  # Current counts as 1

    for prev_hash in reversed(history):
        if prev_hash == current_hash:
            consecutive += 1
        else:
            break

    return consecutive


def check_stagnation(
    current_hash: str,
    history: List[str],
    threshold: int = 3
) -> Tuple[bool, int]:
    """
    Check if loop is stagnating.

    Returns:
        (is_stagnant, consecutive_count)
    """
    consecutive = count_consecutive_same(history, current_hash)
    is_stagnant = consecutive >= threshold
    return is_stagnant, consecutive


def detect_stagnation(
    phase: str,
    indicators: dict,
    files_changed: List[str],
    history: List[str],
    threshold: int = 3,
    error_state: str = None
) -> dict:
    """
    Full stagnation detection.

    Returns dict with:
        - current_hash: str
        - is_stagnant: bool
        - consecutive_count: int
        - threshold: int
        - recommendation: str
    """
    current_hash = calculate_state_hash(
        phase=phase,
        indicators=indicators,
        files_changed=files_changed,
        error_state=error_state
    )

    is_stagnant, consecutive = check_stagnation(
        current_hash=current_hash,
        history=history,
        threshold=threshold
    )

    # Generate recommendation
    if is_stagnant:
        recommendation = "PAUSE: Same state detected. User intervention needed."
    elif consecutive >= threshold - 1:
        recommendation = "WARNING: Approaching stagnation threshold."
    else:
        recommendation = "OK: State is changing normally."

    return {
        "current_hash": current_hash,
        "previous_hash": history[-1] if history else None,
        "is_stagnant": is_stagnant,
        "consecutive_count": consecutive,
        "threshold": threshold,
        "recommendation": recommendation,
        "state_components": {
            "phase": phase,
            "met_indicators": [k for k, v in indicators.items() if v],
            "files_changed_count": len(files_changed) if files_changed else 0
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Detect loop stagnation"
    )
    parser.add_argument("--phase", default="INIT",
                        help="Current phase")
    parser.add_argument("--indicators", default="{}",
                        help="JSON object of indicator states")
    parser.add_argument("--files-changed", default="[]",
                        help="JSON array of changed files")
    parser.add_argument("--history", default="[]",
                        help="JSON array of previous state hashes")
    parser.add_argument("--threshold", type=int, default=3,
                        help="Stagnation threshold (default: 3)")
    parser.add_argument("--error-state", default=None,
                        help="Current error state if any")
    parser.add_argument("--output", choices=["json", "text"], default="json",
                        help="Output format")

    args = parser.parse_args()

    try:
        indicators = json.loads(args.indicators)
        files_changed = json.loads(args.files_changed)
        history = json.loads(args.history)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input - {e}", file=sys.stderr)
        return 1

    result = detect_stagnation(
        phase=args.phase,
        indicators=indicators,
        files_changed=files_changed,
        history=history,
        threshold=args.threshold,
        error_state=args.error_state
    )

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Hash: {result['current_hash']}")
        print(f"Stagnant: {result['is_stagnant']}")
        print(f"Consecutive: {result['consecutive_count']}/{result['threshold']}")
        print(f"Status: {result['recommendation']}")

    # Exit code: 1 = stagnant, 0 = OK
    return 1 if result["is_stagnant"] else 0


if __name__ == "__main__":
    sys.exit(main())
