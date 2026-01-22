#!/usr/bin/env python3
"""
Simplification Rules Engine for Navigator

Applies project-specific simplification rules based on CLAUDE.md standards
and Anthropic's code-simplifier patterns.

Usage:
    python3 simplification_rules.py --file src/auth.ts --claude-md CLAUDE.md
    python3 simplification_rules.py --file src/auth.ts --dry-run
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any


# Default simplification rules (can be overridden by CLAUDE.md)
DEFAULT_RULES = {
    "avoid_nested_ternary": True,
    "max_nesting_depth": 3,
    "max_function_length": 50,
    "prefer_explicit_returns": True,
    "consolidate_imports": True,
    "prefer_function_keyword": True,
    "explicit_type_annotations": True,
    "early_returns": True,
    "descriptive_names": True,
    "no_redundant_boolean": True
}


def parse_claude_md_rules(claude_md_path: str) -> dict[str, Any]:
    """Extract coding rules from CLAUDE.md."""
    path = Path(claude_md_path)
    if not path.exists():
        return DEFAULT_RULES.copy()

    content = path.read_text()
    rules = DEFAULT_RULES.copy()

    # Parse common patterns from CLAUDE.md
    if "arrow function" in content.lower() and "prefer" in content.lower():
        rules["prefer_function_keyword"] = False

    if "function keyword" in content.lower() and "prefer" in content.lower():
        rules["prefer_function_keyword"] = True

    if "explicit return" in content.lower():
        rules["prefer_explicit_returns"] = True

    if "ternary" in content.lower() and "avoid" in content.lower():
        rules["avoid_nested_ternary"] = True

    return rules


def transform_nested_ternary(code: str) -> tuple[str, list[dict[str, Any]]]:
    """Transform nested ternaries to if-else chains."""
    changes = []

    # Pattern for nested ternary
    pattern = r'(\w+)\s*\?\s*([^:]+)\s*:\s*(\w+)\s*\?\s*([^:]+)\s*:\s*(.+)'

    def replace_nested_ternary(match):
        cond1 = match.group(1)
        val1 = match.group(2).strip()
        cond2 = match.group(3)
        val2 = match.group(4).strip()
        val3 = match.group(5).strip().rstrip(';')

        replacement = f"""
if ({cond1}) {{
  return {val1};
}} else if ({cond2}) {{
  return {val2};
}} else {{
  return {val3};
}}""".strip()

        changes.append({
            "type": "nested_ternary_transform",
            "original": match.group(0),
            "replacement": replacement
        })

        return replacement

    new_code = re.sub(pattern, replace_nested_ternary, code)
    return new_code, changes


def transform_deep_nesting(code: str, max_depth: int = 3) -> tuple[str, list[dict[str, Any]]]:
    """Suggest early returns for deeply nested code."""
    changes = []
    lines = code.split('\n')

    # This is a simplified version - full implementation would use AST
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        depth = indent // 2

        if depth > max_depth and 'if' in stripped:
            changes.append({
                "type": "deep_nesting_warning",
                "line": i + 1,
                "depth": depth,
                "suggestion": "Consider using early return pattern"
            })

    return code, changes


def transform_unclear_names(code: str) -> tuple[str, list[dict[str, Any]]]:
    """Identify unclear variable names."""
    changes = []

    # Find single-letter variables
    pattern = r'\b(const|let|var)\s+([a-hln-z])\s*='

    for match in re.finditer(pattern, code):
        changes.append({
            "type": "unclear_name",
            "variable": match.group(2),
            "position": match.start(),
            "suggestion": f"Rename '{match.group(2)}' to a descriptive name"
        })

    return code, changes


def transform_redundant_boolean(code: str) -> tuple[str, list[dict[str, Any]]]:
    """Remove redundant boolean comparisons."""
    changes = []

    # Pattern: === true or === false
    pattern = r'(\w+)\s*===?\s*(true|false)'

    def replace_redundant(match):
        var = match.group(1)
        val = match.group(2)

        if val == 'true':
            replacement = var
        else:
            replacement = f'!{var}'

        changes.append({
            "type": "redundant_boolean",
            "original": match.group(0),
            "replacement": replacement
        })

        return replacement

    new_code = re.sub(pattern, replace_redundant, code)
    return new_code, changes


def apply_simplification_rules(
    file_path: str,
    rules: dict[str, Any],
    dry_run: bool = True
) -> dict[str, Any]:
    """Apply all simplification rules to a file."""
    path = Path(file_path)

    if not path.exists():
        return {
            "file": file_path,
            "error": "File not found",
            "changes": []
        }

    original_code = path.read_text()
    current_code = original_code
    all_changes = []

    # Apply transformations based on rules
    if rules.get("avoid_nested_ternary", True):
        current_code, changes = transform_nested_ternary(current_code)
        all_changes.extend(changes)

    if rules.get("max_nesting_depth"):
        _, changes = transform_deep_nesting(
            current_code,
            rules.get("max_nesting_depth", 3)
        )
        all_changes.extend(changes)

    if rules.get("descriptive_names", True):
        _, changes = transform_unclear_names(current_code)
        all_changes.extend(changes)

    if rules.get("no_redundant_boolean", True):
        current_code, changes = transform_redundant_boolean(current_code)
        all_changes.extend(changes)

    result = {
        "file": file_path,
        "original_size": len(original_code),
        "simplified_size": len(current_code),
        "changes": all_changes,
        "changes_count": len(all_changes),
        "dry_run": dry_run
    }

    if not dry_run and all_changes:
        path.write_text(current_code)
        result["applied"] = True
    else:
        result["applied"] = False
        result["simplified_code"] = current_code if current_code != original_code else None

    return result


def format_output(result: dict[str, Any]) -> str:
    """Format result as human-readable output."""
    output = []
    output.append(f"\n🔧 Simplification: {result['file']}")
    output.append("=" * 50)

    if result.get("error"):
        output.append(f"❌ Error: {result['error']}")
        return "\n".join(output)

    output.append(f"Changes found: {result['changes_count']}")
    output.append(f"Dry run: {result['dry_run']}")
    output.append(f"Applied: {result.get('applied', False)}")
    output.append("")

    if not result['changes']:
        output.append("✅ No simplifications needed")
        return "\n".join(output)

    output.append("Changes:")
    output.append("-" * 40)

    for change in result['changes']:
        change_type = change.get('type', 'unknown')
        output.append(f"  • {change_type}")

        if 'original' in change and 'replacement' in change:
            output.append(f"    Before: {change['original'][:50]}...")
            output.append(f"    After:  {change['replacement'][:50]}...")
        elif 'suggestion' in change:
            output.append(f"    Suggestion: {change['suggestion']}")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Apply simplification rules to code")
    parser.add_argument("--file", required=True, help="Path to file to simplify")
    parser.add_argument("--claude-md", help="Path to CLAUDE.md for project standards")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to file")
    parser.add_argument("--output", choices=["json", "text"], default="text")

    args = parser.parse_args()

    # Parse rules from CLAUDE.md if provided
    rules = DEFAULT_RULES.copy()
    if args.claude_md:
        rules.update(parse_claude_md_rules(args.claude_md))

    # Apply simplifications
    result = apply_simplification_rules(
        args.file,
        rules,
        dry_run=not args.apply
    )

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_output(result))


if __name__ == "__main__":
    main()
