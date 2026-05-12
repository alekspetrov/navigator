#!/usr/bin/env python3
"""
Phase Indicator - Generate Task Mode phase transition displays.

Provides visual feedback for phase transitions in Task Mode,
similar to Loop Mode's NAVIGATOR_STATUS but lighter weight.

Usage:
    python3 phase_indicator.py \
        --phase "IMPL" \
        --status "in_progress" \
        --progress 60 \
        --details '{"files_changed": 3, "tests_written": 2}'

Output:
    Formatted phase indicator block
"""

import argparse
import json
import sys
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class Phase(Enum):
    RESEARCH = "RESEARCH"
    PLAN = "PLAN"
    IMPL = "IMPL"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"


class Status(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SKIPPED = "skipped"


@dataclass
class PhaseState:
    phase: str
    status: str
    progress: int
    details: Dict
    next_phase: Optional[str]


# Phase descriptions
PHASE_INFO = {
    "RESEARCH": {
        "description": "Understanding requirements and exploring codebase",
        "activities": ["File exploration", "Pattern discovery", "Dependency mapping"],
        "icon": "🔍"
    },
    "PLAN": {
        "description": "Creating implementation strategy",
        "activities": ["Task breakdown", "Approach selection", "TodoWrite items"],
        "icon": "📋"
    },
    "IMPL": {
        "description": "Executing planned changes",
        "activities": ["Code writing", "File creation/modification", "Integration"],
        "icon": "🔧"
    },
    "VERIFY": {
        "description": "Testing and validating changes",
        "activities": ["Test execution", "Type checking", "Code simplification"],
        "icon": "✅"
    },
    "COMPLETE": {
        "description": "Finishing and documenting",
        "activities": ["Commit changes", "Update docs", "Close tickets"],
        "icon": "🎉"
    }
}

# Phase order for progress calculation
PHASE_ORDER = ["RESEARCH", "PLAN", "IMPL", "VERIFY", "COMPLETE"]


def get_next_phase(current: str) -> Optional[str]:
    """Get the next phase in sequence."""
    try:
        idx = PHASE_ORDER.index(current.upper())
        if idx < len(PHASE_ORDER) - 1:
            return PHASE_ORDER[idx + 1]
        return None
    except ValueError:
        return None


def calculate_overall_progress(phase: str, phase_progress: int) -> int:
    """Calculate overall task progress based on phase and phase progress."""
    try:
        phase_idx = PHASE_ORDER.index(phase.upper())
        phase_weight = 100 / len(PHASE_ORDER)  # Each phase is equal weight

        # Completed phases
        completed_progress = phase_idx * phase_weight

        # Current phase progress
        current_progress = (phase_progress / 100) * phase_weight

        return int(completed_progress + current_progress)
    except ValueError:
        return phase_progress


def format_activation(task_summary: str, complexity: float, threshold: float) -> str:
    """Format Task Mode activation banner."""
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK MODE ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task: {task_summary}
Complexity: {complexity:.2f} (threshold: {threshold:.2f})
Skills matched: None (Task Mode will orchestrate)

Phases:
  ○ RESEARCH - Understand requirements
  ○ PLAN - Create implementation strategy
  ○ IMPL - Execute changes
  ○ VERIFY - Test and validate
  ○ COMPLETE - Commit and document

Starting RESEARCH phase...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def format_transition(
    from_phase: str,
    to_phase: str,
    completed_details: Dict
) -> str:
    """Format phase transition banner."""
    from_info = PHASE_INFO.get(from_phase.upper(), {})
    to_info = PHASE_INFO.get(to_phase.upper(), {})

    # Build completed summary
    completed_lines = []
    for key, value in completed_details.items():
        if isinstance(value, bool):
            mark = "✓" if value else "○"
            completed_lines.append(f"  {mark} {key.replace('_', ' ').title()}")
        elif isinstance(value, (int, float)):
            completed_lines.append(f"  ✓ {key.replace('_', ' ').title()}: {value}")
        else:
            completed_lines.append(f"  ✓ {key.replace('_', ' ').title()}: {value}")

    completed_section = "\n".join(completed_lines) if completed_lines else "  ✓ Phase complete"

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE: {from_phase} → {to_phase}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{from_phase} completed:
{completed_section}

Moving to {to_phase} phase...
{to_info.get('icon', '')} {to_info.get('description', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def format_progress(
    phase: str,
    status: str,
    progress: int,
    details: Dict
) -> str:
    """Format in-progress phase indicator."""
    info = PHASE_INFO.get(phase.upper(), {})
    overall = calculate_overall_progress(phase, progress)

    # Progress bar
    filled = int(progress / 10)
    bar = "█" * filled + "░" * (10 - filled)

    # Status icon
    status_icon = {
        "pending": "○",
        "in_progress": "◐",
        "complete": "●",
        "skipped": "○"
    }.get(status, "○")

    # Build phases display
    phases_display = []
    for p in PHASE_ORDER:
        p_info = PHASE_INFO.get(p, {})
        if p == phase.upper():
            phases_display.append(f"  {status_icon} {p} ← current")
        elif PHASE_ORDER.index(p) < PHASE_ORDER.index(phase.upper()):
            phases_display.append(f"  ● {p}")
        else:
            phases_display.append(f"  ○ {p}")

    # Details section
    details_lines = []
    for key, value in details.items():
        if isinstance(value, bool):
            mark = "✓" if value else "○"
            details_lines.append(f"  {mark} {key.replace('_', ' ').title()}")
        else:
            details_lines.append(f"  • {key.replace('_', ' ').title()}: {value}")

    details_section = "\n".join(details_lines) if details_lines else "  • In progress..."

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK MODE: {phase}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Progress: [{bar}] {overall}%
Phase Progress: {progress}%

{info.get('icon', '')} {info.get('description', '')}

Phases:
{chr(10).join(phases_display)}

Current Activity:
{details_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def format_completion(
    task_summary: str,
    phases_completed: Dict,
    summary: Dict
) -> str:
    """Format Task Mode completion banner."""
    # Build phases summary
    phases_lines = []
    for phase in PHASE_ORDER:
        duration = phases_completed.get(phase, {}).get("duration", "N/A")
        phases_lines.append(f"  ✓ {phase} - {duration}")

    # Build summary
    summary_lines = []
    for key, value in summary.items():
        summary_lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK MODE COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task: {task_summary}

Phases:
{chr(10).join(phases_lines)}

Summary:
{chr(10).join(summary_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def format_skill_defer(skill_name: str, confidence: float, reason: str) -> str:
    """Format skill deferral message."""
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILL DETECTED: {skill_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confidence: {confidence:.0%}
{reason}

Task Mode deferring to skill workflow.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate Task Mode phase indicators"
    )
    parser.add_argument(
        "--phase",
        required=True,
        help="Current phase (RESEARCH, PLAN, IMPL, VERIFY, COMPLETE)"
    )
    parser.add_argument(
        "--status",
        default="in_progress",
        choices=["pending", "in_progress", "complete", "skipped"],
        help="Phase status"
    )
    parser.add_argument(
        "--progress",
        type=int,
        default=0,
        help="Phase progress (0-100)"
    )
    parser.add_argument(
        "--details",
        default="{}",
        help="JSON object with phase details"
    )
    parser.add_argument(
        "--mode",
        default="progress",
        choices=["activation", "transition", "progress", "completion", "defer"],
        help="Display mode"
    )
    parser.add_argument(
        "--task-summary",
        default="",
        help="Task summary (for activation/completion)"
    )
    parser.add_argument(
        "--from-phase",
        default="",
        help="Previous phase (for transition)"
    )
    parser.add_argument(
        "--skill-name",
        default="",
        help="Skill name (for defer mode)"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.0,
        help="Skill match confidence (for defer mode)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Complexity threshold (for activation)"
    )
    parser.add_argument(
        "--complexity",
        type=float,
        default=0.0,
        help="Complexity score (for activation)"
    )

    args = parser.parse_args()

    try:
        details = json.loads(args.details)
    except json.JSONDecodeError:
        details = {}

    # Generate appropriate display
    if args.mode == "activation":
        output = format_activation(
            args.task_summary or "Unknown task",
            args.complexity,
            args.threshold
        )
    elif args.mode == "transition":
        output = format_transition(
            args.from_phase or "RESEARCH",
            args.phase,
            details
        )
    elif args.mode == "completion":
        output = format_completion(
            args.task_summary or "Unknown task",
            details.get("phases", {}),
            details.get("summary", {})
        )
    elif args.mode == "defer":
        output = format_skill_defer(
            args.skill_name,
            args.confidence,
            details.get("reason", "Skill will handle workflow")
        )
    else:  # progress
        output = format_progress(
            args.phase,
            args.status,
            args.progress,
            details
        )

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
