#!/usr/bin/env python3
"""
Quality Detector - Detect quality drops in human-AI collaboration

Analyzes conversation patterns to identify when collaboration quality is degrading.
"""

import json
import sys
import argparse
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(Enum):
    REPEATED_CORRECTION = "repeated_correction"
    HALLUCINATION = "hallucination"
    CONTEXT_CONFUSION = "context_confusion"
    UNADDRESSED_FEEDBACK = "unaddressed_feedback"
    GOAL_DRIFT = "goal_drift"
    FRUSTRATION = "frustration"


@dataclass
class QualityIssue:
    issue_type: str
    severity: str
    description: str
    evidence: List[str]
    suggestion: str


# Frustration signal patterns
FRUSTRATION_PATTERNS = [
    r'\bugh\b',
    r'\bsigh\b',
    r'\bfrustrat(ing|ed)\b',
    r'\bannoying\b',
    r'\bcome on\b',
    r'\bseriously\b',
    r'\bwhy (can\'t|won\'t)\b',
    r'\bstill (not|wrong)\b',
    r'\bagain[,!?]?\s*$',
    r'\bi (already|just) (said|told)\b',
]

# Correction signal patterns
CORRECTION_PATTERNS = [
    r'\bno,?\s',
    r'\bwrong\b',
    r'\bnot (that|what|right)\b',
    r'\bshould (be|have)\b',
    r'\bactually,?\s',
    r'\bi meant\b',
    r'\bnot (\w+),?\s*(use|it\'s)\b',
    r'\bplural\b',
    r'\bsingular\b',
]

# Hallucination report patterns
HALLUCINATION_PATTERNS = [
    r'\b(that|this) (file|function|module|package|class) (doesn\'t|does not) exist\b',
    r'\bthere\'?s no (such|that)\b',
    r'\b(file|function|variable) not found\b',
    r'\bwhere did you get\b',
    r'\bi (don\'t|never) have\b',
    r'\bthat\'?s not (in|from|part of)\b',
]

# Context confusion patterns
CONFUSION_PATTERNS = [
    r'\bthat\'?s (from|for) (the|a) (other|different|wrong)\b',
    r'\bwrong (project|feature|file|context)\b',
    r'\bnot (this|that) (one|project|feature)\b',
    r'\bwe\'?re (talking|working) (on|about)\b',
    r'\bmixing (up|things)\b',
]

# Goal drift patterns
DRIFT_PATTERNS = [
    r'\bgetting off track\b',
    r'\bnot what i asked\b',
    r'\bback to\b',
    r'\blet\'?s focus\b',
    r'\boriginal(ly)?\b',
    r'\bwhat i (actually|really) (want|need)\b',
]


def analyze_message(text: str) -> Dict[str, List[str]]:
    """Analyze a single message for quality signals."""
    text_lower = text.lower()

    signals = {
        'frustration': [],
        'correction': [],
        'hallucination': [],
        'confusion': [],
        'drift': [],
    }

    for pattern in FRUSTRATION_PATTERNS:
        if re.search(pattern, text_lower):
            signals['frustration'].append(pattern)

    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, text_lower):
            signals['correction'].append(pattern)

    for pattern in HALLUCINATION_PATTERNS:
        if re.search(pattern, text_lower):
            signals['hallucination'].append(pattern)

    for pattern in CONFUSION_PATTERNS:
        if re.search(pattern, text_lower):
            signals['confusion'].append(pattern)

    for pattern in DRIFT_PATTERNS:
        if re.search(pattern, text_lower):
            signals['drift'].append(pattern)

    return signals


def extract_correction_topic(text: str) -> Optional[str]:
    """Try to extract what the correction is about."""
    text_lower = text.lower()

    # "should be X" pattern
    match = re.search(r'should be ["\']?(\w+)["\']?', text_lower)
    if match:
        return match.group(1)

    # "not X, use Y" pattern
    match = re.search(r'not (\w+),?\s*(use|it\'s) (\w+)', text_lower)
    if match:
        return f"{match.group(1)}→{match.group(3)}"

    # "plural/singular" pattern
    if 'plural' in text_lower or 'singular' in text_lower:
        return "naming_convention"

    return None


def detect_quality_issues(messages: List[str]) -> List[QualityIssue]:
    """Analyze multiple messages to detect quality issues."""
    issues = []

    # Aggregate signals across messages
    all_signals = {
        'frustration': 0,
        'correction': 0,
        'hallucination': 0,
        'confusion': 0,
        'drift': 0,
    }

    correction_topics = []
    evidence = []

    for msg in messages:
        signals = analyze_message(msg)

        for signal_type, patterns in signals.items():
            if patterns:
                all_signals[signal_type] += 1
                evidence.append(f"{signal_type}: '{msg[:50]}...'")

                if signal_type == 'correction':
                    topic = extract_correction_topic(msg)
                    if topic:
                        correction_topics.append(topic)

    # Detect repeated corrections on same topic
    topic_counts = {}
    for topic in correction_topics:
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

    repeated_topics = [t for t, c in topic_counts.items() if c >= 2]

    # Generate issues based on signals

    # Critical: Repeated same correction
    if repeated_topics:
        issues.append(QualityIssue(
            issue_type=IssueType.REPEATED_CORRECTION.value,
            severity=Severity.CRITICAL.value,
            description=f"Same correction given multiple times: {repeated_topics}",
            evidence=[f"Topic '{t}' corrected {topic_counts[t]} times" for t in repeated_topics],
            suggestion="Explicitly acknowledge the correction and confirm understanding before proceeding"
        ))

    # Critical: Hallucination detected
    if all_signals['hallucination'] >= 1:
        issues.append(QualityIssue(
            issue_type=IssueType.HALLUCINATION.value,
            severity=Severity.CRITICAL.value,
            description="Referenced non-existent file, function, or resource",
            evidence=[e for e in evidence if 'hallucination' in e],
            suggestion="Re-verify file structure and available resources before generating code"
        ))

    # High: Multiple corrections
    if all_signals['correction'] >= 3:
        issues.append(QualityIssue(
            issue_type=IssueType.UNADDRESSED_FEEDBACK.value,
            severity=Severity.HIGH.value,
            description=f"High number of corrections ({all_signals['correction']})",
            evidence=[e for e in evidence if 'correction' in e][:3],
            suggestion="Pause and re-establish understanding of user's requirements"
        ))

    # High: Frustration signals
    if all_signals['frustration'] >= 2:
        issues.append(QualityIssue(
            issue_type=IssueType.FRUSTRATION.value,
            severity=Severity.HIGH.value,
            description="User showing signs of frustration",
            evidence=[e for e in evidence if 'frustration' in e],
            suggestion="Acknowledge the difficulty and ask what would help"
        ))

    # Medium: Context confusion
    if all_signals['confusion'] >= 1:
        issues.append(QualityIssue(
            issue_type=IssueType.CONTEXT_CONFUSION.value,
            severity=Severity.MEDIUM.value,
            description="Mixing up context from different tasks or projects",
            evidence=[e for e in evidence if 'confusion' in e],
            suggestion="Consider using nav-compact to clear old context"
        ))

    # Medium: Goal drift
    if all_signals['drift'] >= 1:
        issues.append(QualityIssue(
            issue_type=IssueType.GOAL_DRIFT.value,
            severity=Severity.MEDIUM.value,
            description="Output diverging from original goal",
            evidence=[e for e in evidence if 'drift' in e],
            suggestion="Re-establish the primary goal before continuing"
        ))

    return issues


def format_diagnostic_report(issues: List[QualityIssue]) -> str:
    """Format issues as a diagnostic report."""
    if not issues:
        return "✅ No quality issues detected"

    # Get highest severity
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    highest_severity = min(issues, key=lambda x: severity_order.get(x.severity, 99)).severity

    report = f"""⚠️  QUALITY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Severity: {highest_severity.upper()}
Issues Detected: {len(issues)}

"""

    for i, issue in enumerate(issues, 1):
        report += f"""Issue {i}: {issue.issue_type.replace('_', ' ').title()}
Severity: {issue.severity}
Description: {issue.description}
Evidence:
"""
        for e in issue.evidence[:3]:
            report += f"  - {e}\n"
        report += f"Suggestion: {issue.suggestion}\n\n"

    return report


def main():
    parser = argparse.ArgumentParser(description='Detect quality issues in conversation')
    parser.add_argument('--messages', required=True, help='JSON array of user messages to analyze')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--threshold', default='medium',
                       choices=['low', 'medium', 'high', 'critical'],
                       help='Minimum severity to report')

    args = parser.parse_args()

    try:
        messages = json.loads(args.messages)
    except json.JSONDecodeError:
        print("Error: --messages must be a valid JSON array", file=sys.stderr)
        sys.exit(1)

    issues = detect_quality_issues(messages)

    # Filter by threshold
    severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
    threshold_value = severity_order[args.threshold]
    issues = [i for i in issues if severity_order.get(i.severity, 0) >= threshold_value]

    if args.json:
        output = {
            'issues_count': len(issues),
            'issues': [asdict(i) for i in issues],
            'needs_reanchor': len(issues) > 0
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_diagnostic_report(issues))

    # Exit code indicates if issues found
    sys.exit(0 if not issues else 1)


if __name__ == '__main__':
    main()
