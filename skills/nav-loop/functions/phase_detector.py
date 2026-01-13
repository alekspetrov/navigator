#!/usr/bin/env python3
"""
Auto-detect current task phase for Navigator loop mode.

Phases:
- INIT: Loading context, understanding requirements
- RESEARCH: Exploring codebase, finding patterns
- IMPL: Writing code, making changes
- VERIFY: Running tests, validating functionality
- COMPLETE: All indicators met, ready to exit

Usage:
    python3 phase_detector.py \
        --files-read '["src/auth.ts", "README.md"]' \
        --files-changed '["src/login.ts"]' \
        --tests-running \
        --indicators '{"code_committed": true, "tests_passing": true}'

Output:
    JSON with detected phase and confidence
"""

import argparse
import json
import sys
from typing import List, Optional


def detect_phase(
    files_read: List[str],
    files_changed: List[str],
    tests_running: bool = False,
    test_exit_code: Optional[int] = None,
    indicators: dict = None,
    exit_signal: bool = False
) -> dict:
    """
    Auto-detect current task phase from context.

    Returns dict with:
        - phase: str
        - confidence: float (0-1)
        - reason: str
        - next_expected: str
    """
    indicators = indicators or {}
    met_count = sum(1 for v in indicators.values() if v)

    # COMPLETE: Exit conditions met
    if met_count >= 4 and exit_signal:
        return {
            "phase": "COMPLETE",
            "confidence": 1.0,
            "reason": f"Exit conditions met ({met_count}/5 indicators + EXIT_SIGNAL)",
            "next_expected": "Execute autonomous completion protocol"
        }

    # VERIFY: Tests running or recently run
    if tests_running:
        return {
            "phase": "VERIFY",
            "confidence": 0.95,
            "reason": "Tests currently running",
            "next_expected": "Wait for test results, then evaluate"
        }

    if test_exit_code is not None:
        if test_exit_code == 0:
            return {
                "phase": "VERIFY",
                "confidence": 0.9,
                "reason": f"Tests completed (exit code: {test_exit_code})",
                "next_expected": "Commit changes if tests pass"
            }
        else:
            return {
                "phase": "IMPL",
                "confidence": 0.85,
                "reason": f"Tests failed (exit code: {test_exit_code})",
                "next_expected": "Fix failing tests"
            }

    # IMPL: Files being modified
    if files_changed:
        return {
            "phase": "IMPL",
            "confidence": 0.9,
            "reason": f"Files modified: {len(files_changed)} file(s)",
            "next_expected": "Continue implementation or run tests"
        }

    # RESEARCH: Reading files, no changes yet
    if files_read and not files_changed:
        return {
            "phase": "RESEARCH",
            "confidence": 0.85,
            "reason": f"Files read: {len(files_read)} file(s), no changes yet",
            "next_expected": "Start implementation based on research"
        }

    # INIT: Default starting state
    return {
        "phase": "INIT",
        "confidence": 0.7,
        "reason": "No significant activity detected",
        "next_expected": "Load context and understand requirements"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Detect current task phase"
    )
    parser.add_argument("--files-read", default="[]",
                        help="JSON array of files read this iteration")
    parser.add_argument("--files-changed", default="[]",
                        help="JSON array of files changed this iteration")
    parser.add_argument("--tests-running", action="store_true",
                        help="Whether tests are currently running")
    parser.add_argument("--test-exit-code", type=int, default=None,
                        help="Exit code from last test run")
    parser.add_argument("--indicators", default="{}",
                        help="JSON object of completion indicator states")
    parser.add_argument("--exit-signal", action="store_true",
                        help="Whether EXIT_SIGNAL was set")
    parser.add_argument("--init", action="store_true",
                        help="Initialize fresh phase detection")
    parser.add_argument("--output", choices=["json", "text"], default="json",
                        help="Output format")

    args = parser.parse_args()

    # Handle --init flag
    if args.init:
        result = {
            "phase": "INIT",
            "confidence": 1.0,
            "reason": "Fresh initialization",
            "next_expected": "Load context and understand task"
        }
    else:
        try:
            files_read = json.loads(args.files_read)
            files_changed = json.loads(args.files_changed)
            indicators = json.loads(args.indicators)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON input - {e}", file=sys.stderr)
            return 1

        result = detect_phase(
            files_read=files_read,
            files_changed=files_changed,
            tests_running=args.tests_running,
            test_exit_code=args.test_exit_code,
            indicators=indicators,
            exit_signal=args.exit_signal
        )

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Phase: {result['phase']}")
        print(f"Confidence: {result['confidence']:.0%}")
        print(f"Reason: {result['reason']}")
        print(f"Next: {result['next_expected']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
