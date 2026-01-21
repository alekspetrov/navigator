#!/usr/bin/env python3
"""
Extract Verify commands and Done criteria from task markdown.

Usage:
    python3 verify_extractor.py <task-file>
    python3 verify_extractor.py --json <task-file>

Output:
    Default: Human-readable format
    --json: JSON format for programmatic use
"""

import re
import sys
import json
import argparse


def extract_verify_commands(content: str) -> list[str]:
    """
    Extract commands from ## Verify section.

    Looks for bash/sh code blocks within the Verify section and
    extracts non-comment lines as commands.

    Args:
        content: Full markdown content of task file

    Returns:
        List of command strings (excluding comments)
    """
    # Find ## Verify section (stops at next ## or end of file)
    match = re.search(r'## Verify\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not match:
        return []

    verify_section = match.group(1)

    # Extract code blocks (bash or sh or no language specified)
    blocks = re.findall(r'```(?:bash|sh)?\n(.*?)```', verify_section, re.DOTALL)

    commands = []
    for block in blocks:
        for line in block.strip().split('\n'):
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                commands.append(line)

    return commands


def extract_done_criteria(content: str) -> list[dict]:
    """
    Extract criteria from ## Done section.

    Looks for checkbox items (- [ ] or - [x]) and extracts:
    - The text description
    - Whether it's checked (completed)

    Args:
        content: Full markdown content of task file

    Returns:
        List of dicts with 'text' and 'completed' keys
    """
    # Find ## Done section (stops at next ## or end of file)
    match = re.search(r'## Done\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not match:
        return []

    done_section = match.group(1)

    criteria = []
    # Match checkbox items: - [ ] text or - [x] text
    for checkbox_match in re.finditer(r'- \[([ x])\] (.+)', done_section):
        is_checked = checkbox_match.group(1) == 'x'
        text = checkbox_match.group(2).strip()
        criteria.append({
            'text': text,
            'completed': is_checked
        })

    return criteria


def get_completion_status(criteria: list[dict]) -> dict:
    """
    Calculate completion status from criteria.

    Args:
        criteria: List of criteria dicts from extract_done_criteria

    Returns:
        Dict with 'total', 'completed', 'pending', 'percent' keys
    """
    total = len(criteria)
    completed = sum(1 for c in criteria if c['completed'])

    return {
        'total': total,
        'completed': completed,
        'pending': total - completed,
        'percent': round((completed / total * 100) if total > 0 else 0)
    }


def extract_all(content: str) -> dict:
    """
    Extract all verification data from task file.

    Args:
        content: Full markdown content of task file

    Returns:
        Dict with 'verify_commands', 'done_criteria', 'status' keys
    """
    commands = extract_verify_commands(content)
    criteria = extract_done_criteria(content)
    status = get_completion_status(criteria)

    return {
        'verify_commands': commands,
        'done_criteria': criteria,
        'status': status
    }


def format_human_readable(data: dict) -> str:
    """Format extraction results for human reading."""
    lines = []

    lines.append("Verify Commands:")
    if data['verify_commands']:
        for cmd in data['verify_commands']:
            lines.append(f"  $ {cmd}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Done Criteria:")
    if data['done_criteria']:
        for criterion in data['done_criteria']:
            check = "[x]" if criterion['completed'] else "[ ]"
            lines.append(f"  {check} {criterion['text']}")
    else:
        lines.append("  (none)")

    lines.append("")
    status = data['status']
    lines.append(f"Status: {status['completed']}/{status['total']} ({status['percent']}%)")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract Verify commands and Done criteria from task markdown"
    )
    parser.add_argument("file", help="Path to task markdown file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--commands-only", action="store_true",
                        help="Output only verify commands, one per line")
    parser.add_argument("--criteria-only", action="store_true",
                        help="Output only done criteria text, one per line")

    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    data = extract_all(content)

    if args.commands_only:
        for cmd in data['verify_commands']:
            print(cmd)
    elif args.criteria_only:
        for criterion in data['done_criteria']:
            print(criterion['text'])
    elif args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_human_readable(data))


if __name__ == "__main__":
    main()
