#!/usr/bin/env python3
"""
Navigator CLAUDE.md Version Detector
Detects if CLAUDE.md is outdated, current (v3.1), or unknown
"""

import sys
import re
from pathlib import Path
from typing import Literal

VersionStatus = Literal["outdated", "current", "unknown"]

def detect_version(claude_md_path: str) -> VersionStatus:
    """Detect CLAUDE.md version status"""

    if not Path(claude_md_path).exists():
        print(f"Error: File not found: {claude_md_path}", file=sys.stderr)
        sys.exit(1)

    with open(claude_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for version marker
    version_match = re.search(r'Navigator Version[:\s]+(\d+\.\d+\.\d+)', content, re.IGNORECASE)

    if version_match:
        version_str = version_match.group(1)
        major, minor, patch = map(int, version_str.split('.'))

        # Version 3.1+ is current
        if major > 3 or (major == 3 and minor >= 1):
            # Double-check for natural language (should have it in v3+)
            if has_natural_language_examples(content):
                return "current"
            else:
                # Has v3.1 marker but no natural language - partial migration
                return "outdated"

        # Version 3.0 - check for natural language
        elif major == 3 and minor == 0:
            if has_natural_language_examples(content) and not has_slash_commands(content):
                return "current"
            else:
                return "outdated"

        # Version < 3.0 is definitely outdated
        else:
            return "outdated"

    # No version marker - use heuristics
    return detect_by_heuristics(content)

def has_slash_commands(content: str) -> bool:
    """Check if content has slash command references"""
    slash_patterns = [
        r'/nav:start',
        r'/nav:init',
        r'/nav:doc',
        r'/nav:marker',
        r'/nav:markers',
        r'/nav:compact',
        r'/jitd:',
    ]

    for pattern in slash_patterns:
        if re.search(pattern, content):
            return True

    return False

def has_natural_language_examples(content: str) -> bool:
    """Check if content has natural language command examples"""
    natural_language_patterns = [
        r'"Start my Navigator session"',
        r'"Initialize Navigator in this project"',
        r'"Archive TASK-\w+ documentation"',
        r'"Create an SOP for',
        r'"Clear context and preserve markers"',
        r'"Start my session"',
        r'"Load the navigator"',
    ]

    matches = 0
    for pattern in natural_language_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            matches += 1

    # Need at least 2 natural language examples to be considered current
    return matches >= 2

def has_skills_explanation(content: str) -> bool:
    """Check if content explains skills architecture"""
    skills_markers = [
        r'skills-only architecture',
        r'skills that auto-invoke',
        r'How Claude Discovers.*Skills',
        r'Progressive disclosure.*skills',
    ]

    for pattern in skills_markers:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return True

    return False

def has_navigator_markers(content: str) -> bool:
    """Check if content has any Navigator-specific markers"""
    navigator_markers = [
        r'Navigator',
        r'\.agent/',
        r'DEVELOPMENT-README\.md',
        r'nav-start',
        r'nav-task',
        r'nav-compact',
        r'context markers',
        r'token optimization',
    ]

    matches = 0
    for pattern in navigator_markers:
        if re.search(pattern, content, re.IGNORECASE):
            matches += 1

    # Need at least 3 Navigator markers to be considered Navigator-related
    return matches >= 3

def detect_by_heuristics(content: str) -> VersionStatus:
    """Detect version using heuristics when no version marker present"""

    # Check if it's Navigator-related at all
    if not has_navigator_markers(content):
        return "unknown"

    # Has slash commands → definitely outdated
    if has_slash_commands(content):
        return "outdated"

    # Has natural language + skills explanation → current
    if has_natural_language_examples(content) and has_skills_explanation(content):
        return "current"

    # Has natural language but no skills explanation → partial migration
    if has_natural_language_examples(content):
        return "outdated"

    # Has Navigator markers but no natural language → old version
    if has_navigator_markers(content):
        return "outdated"

    # Can't determine
    return "unknown"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 version_detector.py CLAUDE.md", file=sys.stderr)
        sys.exit(1)

    claude_md_path = sys.argv[1]

    try:
        status = detect_version(claude_md_path)
        print(status)
    except Exception as e:
        print(f"Error detecting version: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
