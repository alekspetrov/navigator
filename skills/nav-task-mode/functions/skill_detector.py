#!/usr/bin/env python3
"""
Skill Detector - Check if a request matches an existing Navigator skill.

Determines if a specific skill should handle the request instead of Task Mode.
This enables Task Mode to defer to skills that have their own workflows.

Usage:
    python3 skill_detector.py \
        --request "Add a login component" \
        --available-skills '["frontend-component", "backend-endpoint"]'

Output:
    JSON with matching skill info and defer recommendation
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class SkillMatch:
    matching_skill: Optional[str]
    confidence: float
    triggers: List[str]
    defer: bool
    reason: str
    alternative_skills: List[str]


# Skill trigger patterns
# Each skill has patterns that indicate it should handle the request
SKILL_TRIGGERS = {
    "frontend-component": {
        "patterns": [
            r'\b(create|add|build|make|new)\s+(an?\s+)?(\w+\s+)?component\b',
            r'\bcomponent\s+(for|called|named)\b',
            r'\b(ui|user\s+interface)\s+component\b',
            r'\b(button|modal|form|card|list|table)\s+component\b',
            r'\b\w+component\b',  # PascalCase component names
        ],
        "keywords": ["component", "react", "vue", "ui"],
        "priority": 1,
        "description": "React/Vue component generation"
    },

    "backend-endpoint": {
        "patterns": [
            r'\b(create|add|build|make|new)\s+(an?\s+)?(api\s+)?endpoint\b',
            r'\b(rest|graphql)\s+(api|endpoint)\b',
            r'\b(add|create)\s+(an?\s+)?route\b',
            r'\bapi\s+(for|called|named)\b',
            r'\bendpoint\s+for\b',
        ],
        "keywords": ["endpoint", "api", "route", "rest"],
        "priority": 1,
        "description": "API endpoint generation"
    },

    "database-migration": {
        "patterns": [
            r'\b(create|add|write)\s+(an?\s+)?(database\s+)?migration\b',
            r'\bmigration\s+(for|to)\b',
            r'\b(add|modify|change)\s+(an?\s+)?(database\s+)?(table|column|schema)\b',
            r'\bschema\s+(change|update|migration)\b',
        ],
        "keywords": ["migration", "schema", "table", "column"],
        "priority": 1,
        "description": "Database migration generation"
    },

    "backend-test": {
        "patterns": [
            r'\b(write|create|add)\s+(an?\s+)?(unit\s+)?test(s)?\s+for\s+.*(api|endpoint|service|function)\b',
            r'\bbackend\s+test(s)?\b',
            r'\btest\s+(the\s+)?(api|endpoint|service)\b',
        ],
        "keywords": ["test", "backend", "unit test", "api test"],
        "priority": 2,
        "description": "Backend test generation"
    },

    "frontend-test": {
        "patterns": [
            r'\b(write|create|add)\s+(an?\s+)?(unit\s+)?test(s)?\s+for\s+.*(component|ui)\b',
            r'\bcomponent\s+test(s)?\b',
            r'\btest\s+(the\s+)?component\b',
            r'\bsnapshot\s+test\b',
        ],
        "keywords": ["test", "component", "snapshot", "jest"],
        "priority": 2,
        "description": "Frontend component test generation"
    },

    "nav-task": {
        "patterns": [
            r'\b(create|document|archive)\s+(an?\s+)?task\b',
            r'\btask\s+doc(umentation)?\b',
            r'\bimplementation\s+plan\b',
            r'\bdocument\s+(this|the)\s+feature\b',
        ],
        "keywords": ["task", "documentation", "implementation plan"],
        "priority": 2,
        "description": "Task documentation management"
    },

    "nav-sop": {
        "patterns": [
            r'\b(create|document|write)\s+(an?\s+)?(sop|standard\s+operating\s+procedure)\b',
            r'\bprocedure\s+for\b',
            r'\bdocument\s+(this\s+)?solution\b',
            r'\bsave\s+(this\s+)?for\s+next\s+time\b',
        ],
        "keywords": ["sop", "procedure", "document solution"],
        "priority": 2,
        "description": "Standard Operating Procedure creation"
    },

    "nav-marker": {
        "patterns": [
            r'\b(create|save)\s+(an?\s+)?(context\s+)?marker\b',
            r'\bsave\s+(my\s+)?progress\b',
            r'\b(create|make)\s+(an?\s+)?checkpoint\b',
            r'\bmark\s+this\s+point\b',
        ],
        "keywords": ["marker", "checkpoint", "save progress"],
        "priority": 3,
        "description": "Context marker creation"
    },

    "nav-compact": {
        "patterns": [
            r'\b(clear|compact)\s+(the\s+)?context\b',
            r'\bstart\s+fresh\b',
            r'\bdone\s+with\s+this\s+task\b',
        ],
        "keywords": ["compact", "clear context", "fresh"],
        "priority": 3,
        "description": "Context compaction"
    },

    "nav-simplify": {
        "patterns": [
            r'\bsimplify\s+(this\s+)?code\b',
            r'\breview\s+for\s+clarity\b',
            r'\bcleanup\s+code\b',
            r'\bcode\s+clarity\b',
        ],
        "keywords": ["simplify", "clarity", "cleanup"],
        "priority": 2,
        "description": "Code simplification"
    },

    "nav-diagnose": {
        "patterns": [
            r'\bsomething\s+(seems|is)\s+(off|wrong)\b',
            r'\byou\'?re\s+not\s+getting\s+(this|it)\b',
            r'\bdiagnose\b',
            r'\bre-?anchor\b',
        ],
        "keywords": ["diagnose", "something off", "re-anchor"],
        "priority": 2,
        "description": "Quality diagnosis"
    },

    "nav-loop": {
        "patterns": [
            r'\brun\s+until\s+done\b',
            r'\bkeep\s+going\s+until\s+complete\b',
            r'\biterate\s+until\s+finished\b',
            r'\bloop\s+mode\b',
            r'\bautonomous\s+mode\b',
        ],
        "keywords": ["loop", "until done", "autonomous"],
        "priority": 1,
        "description": "Loop mode activation"
    },

    "product-design": {
        "patterns": [
            r'\bdesign\s+review\b',
            r'\bfigma\s+(mockup|design|file)\b',
            r'\bdesign\s+handoff\b',
            r'\b(review|analyze)\s+design\b',
        ],
        "keywords": ["design", "figma", "mockup"],
        "priority": 1,
        "description": "Design review automation"
    },

    "visual-regression": {
        "patterns": [
            r'\bvisual\s+regression\b',
            r'\bscreenshot\s+test(ing)?\b',
            r'\b(add|set\s+up)\s+(chromatic|percy|backstop)\b',
            r'\bvisual\s+test(ing)?\b',
        ],
        "keywords": ["visual regression", "chromatic", "percy"],
        "priority": 1,
        "description": "Visual regression testing setup"
    },
}


def calculate_match_score(
    text: str,
    patterns: List[str],
    keywords: List[str]
) -> Tuple[float, List[str]]:
    """Calculate how well text matches skill patterns."""
    text_lower = text.lower()
    matched_triggers = []

    # Pattern matches (stronger signal)
    pattern_score = 0
    for pattern in patterns:
        if re.search(pattern, text_lower):
            pattern_score += 0.4
            matched_triggers.append(pattern)

    # Keyword matches (weaker signal)
    keyword_score = 0
    for keyword in keywords:
        if keyword.lower() in text_lower:
            keyword_score += 0.15

    # Cap scores
    pattern_score = min(pattern_score, 0.8)
    keyword_score = min(keyword_score, 0.3)

    total_score = min(pattern_score + keyword_score, 1.0)

    return total_score, matched_triggers


def detect_skill_match(
    request: str,
    available_skills: List[str] = None
) -> SkillMatch:
    """
    Check if a skill should handle this request.

    Args:
        request: User's request text
        available_skills: List of available skill names (filters results)

    Returns:
        SkillMatch with best matching skill or None
    """
    # Default to all known skills if not specified
    if available_skills is None:
        available_skills = list(SKILL_TRIGGERS.keys())

    best_match = None
    best_score = 0
    best_triggers = []
    alternatives = []

    for skill_name, skill_config in SKILL_TRIGGERS.items():
        # Skip skills not in available list
        if skill_name not in available_skills:
            continue

        score, triggers = calculate_match_score(
            request,
            skill_config["patterns"],
            skill_config["keywords"]
        )

        if score > 0.3:  # Minimum threshold for consideration
            if score > best_score:
                # Move previous best to alternatives
                if best_match:
                    alternatives.append(best_match)
                best_match = skill_name
                best_score = score
                best_triggers = triggers
            else:
                alternatives.append(skill_name)

    # Determine if we should defer
    defer = best_score >= 0.5

    if best_match:
        skill_desc = SKILL_TRIGGERS[best_match]["description"]
        reason = f"Request matches {best_match} skill ({skill_desc})"
    else:
        reason = "No skill match found - Task Mode should handle"

    return SkillMatch(
        matching_skill=best_match,
        confidence=round(best_score, 2),
        triggers=best_triggers[:3],  # Limit to top 3 triggers
        defer=defer,
        reason=reason,
        alternative_skills=alternatives[:2]  # Limit to top 2 alternatives
    )


def main():
    parser = argparse.ArgumentParser(
        description="Detect if a skill should handle a request"
    )
    parser.add_argument(
        "--request",
        required=True,
        help="User's request text"
    )
    parser.add_argument(
        "--available-skills",
        default=None,
        help="JSON array of available skill names"
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="Output format"
    )

    args = parser.parse_args()

    # Parse available skills
    available_skills = None
    if args.available_skills:
        try:
            available_skills = json.loads(args.available_skills)
        except json.JSONDecodeError:
            print("Error: --available-skills must be valid JSON array",
                  file=sys.stderr)
            return 1

    result = detect_skill_match(args.request, available_skills)

    if args.output == "json":
        print(json.dumps(asdict(result), indent=2))
    else:
        if result.matching_skill:
            print(f"Matching Skill: {result.matching_skill}")
            print(f"Confidence: {result.confidence:.0%}")
            print(f"Defer: {'Yes' if result.defer else 'No'}")
            print(f"Reason: {result.reason}")
            if result.triggers:
                print(f"Triggers: {', '.join(result.triggers[:2])}")
            if result.alternative_skills:
                print(f"Alternatives: {', '.join(result.alternative_skills)}")
        else:
            print("No skill match found")
            print("Recommendation: Task Mode should orchestrate")

    return 0


if __name__ == "__main__":
    sys.exit(main())
