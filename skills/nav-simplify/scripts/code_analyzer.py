#!/usr/bin/env python3
"""
Code Analyzer for Navigator Simplification Skill

Analyzes code files for simplification opportunities based on Anthropic's
code-simplifier patterns.

Usage:
    python3 code_analyzer.py --file src/utils/auth.ts
    python3 code_analyzer.py --file src/utils/auth.ts --output json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def analyze_nesting_depth(content: str) -> list[dict[str, Any]]:
    """Detect deeply nested code blocks."""
    issues = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Count indentation level (assuming 2 or 4 space indent)
        stripped = line.lstrip()
        if not stripped:
            continue

        indent = len(line) - len(stripped)
        depth = indent // 2  # Assuming 2-space indent

        if depth > 3:
            issues.append({
                "line": i,
                "type": "deep_nesting",
                "severity": "high" if depth > 4 else "medium",
                "depth": depth,
                "suggestion": "Extract to helper function or use early returns"
            })

    return issues


def analyze_nested_ternaries(content: str) -> list[dict[str, Any]]:
    """Detect nested ternary operators."""
    issues = []
    lines = content.split('\n')

    # Pattern: condition ? (another_condition ? x : y) : z
    nested_ternary_pattern = r'\?[^?:]*\?'

    for i, line in enumerate(lines, 1):
        if re.search(nested_ternary_pattern, line):
            issues.append({
                "line": i,
                "type": "nested_ternary",
                "severity": "medium",
                "suggestion": "Convert to switch statement or if-else chain"
            })

    return issues


def analyze_function_length(content: str) -> list[dict[str, Any]]:
    """Detect overly long functions."""
    issues = []

    # Simple pattern for function detection
    function_patterns = [
        r'function\s+(\w+)\s*\([^)]*\)\s*{',
        r'(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{',
        r'(\w+)\s*:\s*(?:async\s*)?\([^)]*\)\s*=>\s*{',
    ]

    lines = content.split('\n')

    for pattern in function_patterns:
        for match in re.finditer(pattern, content):
            start_pos = match.start()
            start_line = content[:start_pos].count('\n') + 1

            # Find matching closing brace (simplified)
            brace_count = 0
            end_line = start_line
            in_function = False

            for i, line in enumerate(lines[start_line - 1:], start_line):
                brace_count += line.count('{') - line.count('}')
                if '{' in line:
                    in_function = True
                if in_function and brace_count == 0:
                    end_line = i
                    break

            length = end_line - start_line + 1
            if length > 50:
                issues.append({
                    "line": start_line,
                    "type": "long_function",
                    "severity": "medium",
                    "length": length,
                    "function_name": match.group(1) if match.lastindex else "anonymous",
                    "suggestion": f"Function is {length} lines. Consider breaking into smaller functions."
                })

    return issues


def analyze_unclear_names(content: str) -> list[dict[str, Any]]:
    """Detect single-letter or unclear variable names."""
    issues = []
    lines = content.split('\n')

    # Pattern for single-letter variables (excluding common loop vars i, j, k)
    single_letter_pattern = r'\b(const|let|var)\s+([a-hln-z])\s*='

    for i, line in enumerate(lines, 1):
        matches = re.findall(single_letter_pattern, line)
        for match in matches:
            issues.append({
                "line": i,
                "type": "unclear_naming",
                "severity": "low",
                "variable": match[1],
                "suggestion": f"Rename '{match[1]}' to a descriptive name"
            })

    return issues


def analyze_redundant_code(content: str) -> list[dict[str, Any]]:
    """Detect potentially redundant patterns."""
    issues = []
    lines = content.split('\n')

    # Detect redundant boolean comparisons
    redundant_bool_pattern = r'===?\s*(true|false)\b'

    for i, line in enumerate(lines, 1):
        if re.search(redundant_bool_pattern, line):
            issues.append({
                "line": i,
                "type": "redundant_comparison",
                "severity": "low",
                "suggestion": "Remove explicit boolean comparison (use truthy/falsy)"
            })

    return issues


def calculate_complexity_score(issues: list[dict[str, Any]]) -> float:
    """Calculate overall complexity score (0-10)."""
    if not issues:
        return 0.0

    severity_weights = {
        "high": 3.0,
        "medium": 2.0,
        "low": 1.0
    }

    total_weight = sum(severity_weights.get(issue.get("severity", "low"), 1.0) for issue in issues)

    # Normalize to 0-10 scale (cap at 10)
    score = min(total_weight / 2, 10.0)
    return round(score, 1)


def analyze_file(file_path: str) -> dict[str, Any]:
    """Analyze a single file for simplification opportunities."""
    path = Path(file_path)

    if not path.exists():
        return {
            "file": file_path,
            "error": "File not found",
            "issues": [],
            "complexity_score": 0,
            "recommended_actions": 0
        }

    content = path.read_text()

    issues = []
    issues.extend(analyze_nesting_depth(content))
    issues.extend(analyze_nested_ternaries(content))
    issues.extend(analyze_function_length(content))
    issues.extend(analyze_unclear_names(content))
    issues.extend(analyze_redundant_code(content))

    # Sort by line number
    issues.sort(key=lambda x: x.get("line", 0))

    complexity_score = calculate_complexity_score(issues)

    # Count high and medium severity issues as recommended actions
    recommended_actions = sum(
        1 for issue in issues
        if issue.get("severity") in ("high", "medium")
    )

    return {
        "file": file_path,
        "issues": issues,
        "complexity_score": complexity_score,
        "recommended_actions": recommended_actions,
        "total_issues": len(issues)
    }


def format_text_output(result: dict[str, Any]) -> str:
    """Format analysis result as human-readable text."""
    output = []
    output.append(f"\n📊 Analysis: {result['file']}")
    output.append("=" * 50)

    if result.get("error"):
        output.append(f"❌ Error: {result['error']}")
        return "\n".join(output)

    output.append(f"Complexity Score: {result['complexity_score']}/10")
    output.append(f"Total Issues: {result['total_issues']}")
    output.append(f"Recommended Actions: {result['recommended_actions']}")
    output.append("")

    if not result['issues']:
        output.append("✅ No simplification opportunities found")
        return "\n".join(output)

    output.append("Issues Found:")
    output.append("-" * 40)

    for issue in result['issues']:
        severity_icon = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }.get(issue.get("severity", "low"), "⚪")

        output.append(f"  {severity_icon} Line {issue.get('line', '?')}: {issue.get('type', 'unknown')}")
        output.append(f"     └─ {issue.get('suggestion', 'No suggestion')}")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Analyze code for simplification opportunities")
    parser.add_argument("--file", required=True, help="Path to file to analyze")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="Output format")
    parser.add_argument("--standards", help="Path to CLAUDE.md for project standards (optional)")

    args = parser.parse_args()

    result = analyze_file(args.file)

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_text_output(result))


if __name__ == "__main__":
    main()
