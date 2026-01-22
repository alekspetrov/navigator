#!/usr/bin/env python3
"""
Complexity Detector - Analyze task complexity to determine execution mode.

Determines if a request should use:
- Direct execution (low complexity)
- Task Mode (medium-high complexity, no skill match)
- Skill deferral (matches specific skill)

Usage:
    python3 complexity_detector.py \
        --request "Refactor the auth system to use JWT" \
        --context "Working on user management" \
        --threshold 0.5

Output:
    JSON with complexity score and recommendation
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ComplexityResult:
    complexity_score: float
    signals: Dict[str, bool]
    signal_weights: Dict[str, float]
    recommendation: str
    reason: str
    is_substantial: bool


# Complexity-increasing signals (positive weight)
COMPLEXITY_SIGNALS = {
    # Multi-file indicators
    "multi_file": {
        "patterns": [
            r'\b(multiple|several|all|across|throughout)\s+(file|module|component)s?\b',
            r'\brefactor(ing)?\b',
            r'\bmigrat(e|ion)\b',
            r'\bupgrade\b',
            r'\boverhaul\b',
        ],
        "weight": 0.3,
        "description": "Multi-file changes expected"
    },

    # Planning/feature language
    "planning_language": {
        "patterns": [
            r'\bimplement(ation)?\b',
            r'\b(add|create|build)\s+(new\s+)?(feature|system|module)\b',
            r'\bdesign\b',
            r'\barchitect(ure)?\b',
            r'\bintegrat(e|ion)\b',
        ],
        "weight": 0.2,
        "description": "Feature implementation language"
    },

    # Cross-system changes
    "cross_system": {
        "patterns": [
            r'\b(frontend|backend|database|api)\s+and\s+(frontend|backend|database|api)\b',
            r'\bfull.?stack\b',
            r'\bend.?to.?end\b',
            r'\bclient\s+and\s+server\b',
        ],
        "weight": 0.3,
        "description": "Cross-system changes"
    },

    # Research/exploration needed
    "needs_research": {
        "patterns": [
            r'\bhow\s+(do|does|should|would)\b',
            r'\bunderstand\b',
            r'\bexplore\b',
            r'\binvestigate\b',
            r'\bfigure\s+out\b',
            r'\bbest\s+(way|approach|practice)\b',
        ],
        "weight": 0.2,
        "description": "Research/exploration required"
    },

    # Testing requirements
    "testing_mentioned": {
        "patterns": [
            r'\bwith\s+tests?\b',
            r'\btest(ing)?\s+(coverage|suite)\b',
            r'\bunit\s+tests?\b',
            r'\bintegration\s+tests?\b',
        ],
        "weight": 0.1,
        "description": "Testing requirements mentioned"
    },

    # Security/auth work
    "security_work": {
        "patterns": [
            r'\bauth(entication|orization)?\b',
            r'\bsecur(e|ity)\b',
            r'\bpermission(s)?\b',
            r'\baccess\s+control\b',
            r'\bencrypt(ion)?\b',
        ],
        "weight": 0.15,
        "description": "Security-sensitive changes"
    },

    # Data/state management
    "data_changes": {
        "patterns": [
            r'\bdatabase\b',
            r'\bschema\b',
            r'\bdata\s+(model|structure)\b',
            r'\bstate\s+management\b',
            r'\bcache\b',
        ],
        "weight": 0.15,
        "description": "Data/state management changes"
    },
}

# Simplicity-indicating signals (negative weight)
SIMPLICITY_SIGNALS = {
    # Single file/location
    "single_file": {
        "patterns": [
            r'\bin\s+(the\s+)?[a-zA-Z0-9_./]+\.(ts|js|py|tsx|jsx|css|md)\b',
            r'\bjust\s+(this|that|the)\s+(file|function|line)\b',
            r'\bonly\s+(in|the)\b',
        ],
        "weight": -0.3,
        "description": "Single file scope"
    },

    # Fix/typo language
    "fix_language": {
        "patterns": [
            r'\b(fix|correct)\s+(a\s+)?(typo|bug|error|issue)\b',
            r'\btypo\b',
            r'\bsmall\s+(fix|change|update)\b',
            r'\bminor\b',
        ],
        "weight": -0.2,
        "description": "Bug fix language"
    },

    # Quick/simple modifiers
    "quick_modifier": {
        "patterns": [
            r'\bquick(ly)?\b',
            r'\bsimple\b',
            r'\bjust\b',
            r'\bonly\b',
            r'\bsmall\b',
        ],
        "weight": -0.2,
        "description": "Simplicity modifier"
    },

    # Specific location given
    "specific_location": {
        "patterns": [
            r'\b(line|row)\s+\d+\b',
            r'\bfunction\s+[a-zA-Z_][a-zA-Z0-9_]*\b',
            r'\bclass\s+[A-Z][a-zA-Z0-9_]*\b',
            r'at\s+[a-zA-Z0-9_./]+:\d+',
        ],
        "weight": -0.15,
        "description": "Specific location provided"
    },

    # Update/change existing
    "update_existing": {
        "patterns": [
            r'\bupdate\s+(the\s+)?\w+\b',
            r'\bchange\s+(the\s+)?\w+\s+to\b',
            r'\brename\b',
            r'\breplace\b',
        ],
        "weight": -0.1,
        "description": "Simple update/change"
    },
}


def detect_signals(text: str) -> Tuple[Dict[str, bool], Dict[str, float]]:
    """Detect complexity and simplicity signals in text."""
    text_lower = text.lower()

    signals = {}
    weights = {}

    # Check complexity signals
    for signal_name, signal_config in COMPLEXITY_SIGNALS.items():
        matched = any(
            re.search(pattern, text_lower)
            for pattern in signal_config["patterns"]
        )
        signals[signal_name] = matched
        if matched:
            weights[signal_name] = signal_config["weight"]

    # Check simplicity signals
    for signal_name, signal_config in SIMPLICITY_SIGNALS.items():
        matched = any(
            re.search(pattern, text_lower)
            for pattern in signal_config["patterns"]
        )
        signals[signal_name] = matched
        if matched:
            weights[signal_name] = signal_config["weight"]

    return signals, weights


def calculate_complexity(signals: Dict[str, bool], weights: Dict[str, float]) -> float:
    """Calculate overall complexity score (0-1)."""
    # Start at neutral 0.5
    base_score = 0.5

    # Add/subtract weights
    total_adjustment = sum(weights.values())

    # Calculate final score, clamped to 0-1
    final_score = max(0.0, min(1.0, base_score + total_adjustment))

    return round(final_score, 2)


def get_recommendation(score: float, threshold: float) -> Tuple[str, str]:
    """Get recommendation based on score."""
    if score < 0.3:
        return "direct_execution", "Simple task - direct execution without overhead"
    elif score < threshold:
        return "direct_execution", f"Below threshold ({score:.2f} < {threshold:.2f})"
    elif score < 0.7:
        return "task_mode", "Substantial task - Task Mode recommended"
    else:
        return "task_mode", "Complex task - Task Mode with full phase tracking"


def detect_complexity(
    request: str,
    context: str = "",
    threshold: float = 0.5
) -> ComplexityResult:
    """
    Analyze request complexity and return recommendation.

    Args:
        request: User's request/task description
        context: Additional context (recent conversation, etc.)
        threshold: Complexity threshold for Task Mode activation

    Returns:
        ComplexityResult with score, signals, and recommendation
    """
    # Combine request and context for analysis
    full_text = f"{request} {context}".strip()

    # Detect signals
    signals, weights = detect_signals(full_text)

    # Calculate score
    score = calculate_complexity(signals, weights)

    # Get recommendation
    recommendation, reason = get_recommendation(score, threshold)

    return ComplexityResult(
        complexity_score=score,
        signals=signals,
        signal_weights=weights,
        recommendation=recommendation,
        reason=reason,
        is_substantial=score >= threshold
    )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze task complexity"
    )
    parser.add_argument(
        "--request",
        required=True,
        help="User's request/task description"
    )
    parser.add_argument(
        "--context",
        default="",
        help="Additional context"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Complexity threshold (0-1)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="Output format"
    )

    args = parser.parse_args()

    result = detect_complexity(
        request=args.request,
        context=args.context,
        threshold=args.threshold
    )

    if args.output == "json":
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"Complexity Score: {result.complexity_score:.2f}")
        print(f"Threshold: {args.threshold:.2f}")
        print(f"Substantial: {'Yes' if result.is_substantial else 'No'}")
        print(f"Recommendation: {result.recommendation}")
        print(f"Reason: {result.reason}")
        print()
        print("Signals detected:")
        for signal, active in result.signals.items():
            if active:
                weight = result.signal_weights.get(signal, 0)
                sign = "+" if weight > 0 else ""
                print(f"  {signal}: {sign}{weight}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
