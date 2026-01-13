#!/usr/bin/env python3
"""
Generate NAVIGATOR_STATUS block for loop mode.

Usage:
    python3 status_generator.py \
        --phase "IMPL" \
        --iteration 2 \
        --max-iterations 5 \
        --indicators '{"code_committed": true, "tests_passing": true}' \
        --state-hash "a7b3c9" \
        --prev-hash "a7b3c9" \
        --stagnation-count 1 \
        --next-action "Run tests"
"""

import argparse
import json
import sys


def calculate_progress(phase: str, indicators: dict) -> int:
    """Calculate progress percentage based on phase and indicators."""
    phase_weights = {
        "INIT": 10,
        "RESEARCH": 25,
        "IMPL": 50,
        "VERIFY": 75,
        "COMPLETE": 100
    }

    base = phase_weights.get(phase, 0)
    indicator_count = sum(1 for v in indicators.values() if v)
    indicator_bonus = (indicator_count / max(len(indicators), 1)) * 25

    return min(100, int(base + indicator_bonus))


def format_indicators(indicators: dict) -> str:
    """Format completion indicators with checkboxes."""
    indicator_labels = {
        "code_committed": "Code changes committed",
        "tests_passing": "Tests passing",
        "docs_updated": "Documentation updated",
        "ticket_closed": "Ticket closed",
        "marker_created": "Marker created"
    }

    lines = []
    for key, label in indicator_labels.items():
        checked = indicators.get(key, False)
        mark = "x" if checked else " "
        lines.append(f"  [{mark}] {label}")

    return "\n".join(lines)


def count_met_indicators(indicators: dict) -> tuple:
    """Count met vs total indicators."""
    met = sum(1 for v in indicators.values() if v)
    total = len(indicators) if indicators else 5
    return met, total


def generate_status_block(
    phase: str,
    iteration: int,
    max_iterations: int,
    indicators: dict,
    state_hash: str,
    prev_hash: str,
    stagnation_count: int,
    stagnation_threshold: int = 3,
    exit_signal: bool = False,
    next_action: str = "Continue working"
) -> str:
    """Generate formatted NAVIGATOR_STATUS block."""

    progress = calculate_progress(phase, indicators)
    indicator_display = format_indicators(indicators)
    met, total = count_met_indicators(indicators)

    status = f"""
NAVIGATOR_STATUS
{'=' * 50}
Phase: {phase}
Iteration: {iteration}/{max_iterations}
Progress: {progress}%

Completion Indicators:
{indicator_display}

Exit Conditions:
  Heuristics: {met}/{total} (need 2+)
  EXIT_SIGNAL: {str(exit_signal).lower()}

State Hash: {state_hash}
Previous Hash: {prev_hash}
Stagnation: {stagnation_count}/{stagnation_threshold}

Next Action: {next_action}
{'=' * 50}
"""
    return status.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Generate NAVIGATOR_STATUS block"
    )
    parser.add_argument("--phase", default="INIT",
                        choices=["INIT", "RESEARCH", "IMPL", "VERIFY", "COMPLETE"])
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--indicators", default="{}")
    parser.add_argument("--state-hash", default="000000")
    parser.add_argument("--prev-hash", default="000000")
    parser.add_argument("--stagnation-count", type=int, default=0)
    parser.add_argument("--stagnation-threshold", type=int, default=3)
    parser.add_argument("--exit-signal", action="store_true")
    parser.add_argument("--next-action", default="Continue working")

    args = parser.parse_args()

    try:
        indicators = json.loads(args.indicators)
    except json.JSONDecodeError:
        indicators = {}

    status = generate_status_block(
        phase=args.phase,
        iteration=args.iteration,
        max_iterations=args.max_iterations,
        indicators=indicators,
        state_hash=args.state_hash,
        prev_hash=args.prev_hash,
        stagnation_count=args.stagnation_count,
        stagnation_threshold=args.stagnation_threshold,
        exit_signal=args.exit_signal,
        next_action=args.next_action
    )

    print(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
