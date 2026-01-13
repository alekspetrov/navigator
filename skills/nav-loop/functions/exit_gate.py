#!/usr/bin/env python3
"""
Dual-condition exit gate for Navigator loop mode.

Evaluates whether loop should exit based on:
1. Heuristics: At least N completion indicators met
2. Explicit signal: EXIT_SIGNAL must be true

Usage:
    python3 exit_gate.py \
        --indicators '{"code_committed": true, "tests_passing": true}' \
        --exit-signal \
        --min-heuristics 2

Output:
    JSON with exit decision and reasoning
"""

import argparse
import json
import sys
from typing import Tuple


def count_indicators(indicators: dict) -> Tuple[int, int]:
    """Count met indicators vs total."""
    if not indicators:
        return 0, 5

    met = sum(1 for v in indicators.values() if v)
    total = len(indicators)
    return met, total


def evaluate_exit(
    indicators: dict,
    exit_signal: bool,
    min_heuristics: int = 2,
    require_explicit: bool = True
) -> dict:
    """
    Evaluate dual-condition exit gate.

    Returns dict with:
        - should_exit: bool
        - reason: str
        - heuristics_met: int
        - heuristics_total: int
        - exit_signal: bool
        - blocked_reason: str or None
    """
    met, total = count_indicators(indicators)
    heuristics_satisfied = met >= min_heuristics

    result = {
        "heuristics_met": met,
        "heuristics_total": total,
        "heuristics_satisfied": heuristics_satisfied,
        "exit_signal": exit_signal,
        "min_required": min_heuristics,
        "require_explicit": require_explicit
    }

    # Dual-condition evaluation
    if heuristics_satisfied and exit_signal:
        result["should_exit"] = True
        result["reason"] = f"EXIT: {met}/{total} heuristics + explicit signal"
        result["blocked_reason"] = None

    elif exit_signal and not heuristics_satisfied:
        result["should_exit"] = False
        result["reason"] = f"BLOCKED: Exit signal but only {met}/{total} heuristics"
        result["blocked_reason"] = "Insufficient completion indicators"

    elif heuristics_satisfied and not exit_signal:
        if require_explicit:
            result["should_exit"] = False
            result["reason"] = f"CONTINUE: {met}/{total} heuristics, awaiting EXIT_SIGNAL"
            result["blocked_reason"] = "Awaiting explicit completion signal"
        else:
            # Legacy mode: exit on heuristics alone
            result["should_exit"] = True
            result["reason"] = f"EXIT: {met}/{total} heuristics (explicit signal not required)"
            result["blocked_reason"] = None

    else:
        result["should_exit"] = False
        result["reason"] = f"CONTINUE: {met}/{total} heuristics, no exit signal"
        result["blocked_reason"] = "More work needed"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate dual-condition exit gate"
    )
    parser.add_argument("--indicators", default="{}",
                        help="JSON object of indicator states")
    parser.add_argument("--exit-signal", action="store_true",
                        help="Whether EXIT_SIGNAL was explicitly set")
    parser.add_argument("--min-heuristics", type=int, default=2,
                        help="Minimum indicators required (default: 2)")
    parser.add_argument("--no-require-explicit", action="store_true",
                        help="Don't require explicit EXIT_SIGNAL")
    parser.add_argument("--output", choices=["json", "text"], default="json",
                        help="Output format")

    args = parser.parse_args()

    try:
        indicators = json.loads(args.indicators)
    except json.JSONDecodeError:
        print("Error: Invalid JSON for indicators", file=sys.stderr)
        return 1

    result = evaluate_exit(
        indicators=indicators,
        exit_signal=args.exit_signal,
        min_heuristics=args.min_heuristics,
        require_explicit=not args.no_require_explicit
    )

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Decision: {'EXIT' if result['should_exit'] else 'CONTINUE'}")
        print(f"Reason: {result['reason']}")
        if result['blocked_reason']:
            print(f"Blocked: {result['blocked_reason']}")

    # Exit code: 0 = should exit, 1 = should continue
    return 0 if result["should_exit"] else 1


if __name__ == "__main__":
    sys.exit(main())
