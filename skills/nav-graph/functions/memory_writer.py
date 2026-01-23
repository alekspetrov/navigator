#!/usr/bin/env python3
"""
Memory Writer - Creates detailed memory markdown files

Creates .agent/knowledge/memories/{type}/{id}.md files
with rich context for experiential knowledge.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def create_memory_file(
    memory_id: str,
    memory_type: str,
    title: str,
    summary: str,
    context: str = "",
    details: str = "",
    approach: str = "",
    related_tasks: list = None,
    related_sops: list = None,
    related_files: list = None,
    confidence: int = 80,
    concepts: list = None,
    base_dir: str = ".agent/knowledge"
) -> str:
    """Create a detailed memory markdown file."""

    related_tasks = related_tasks or []
    related_sops = related_sops or []
    related_files = related_files or []
    concepts = concepts or []

    # Determine directory
    type_dir = f"{memory_type}s"  # pattern -> patterns
    output_dir = Path(base_dir) / "memories" / type_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{memory_id}.md"

    # Build related section
    related_lines = []
    for task in related_tasks:
        related_lines.append(f"- {task}")
    for sop in related_sops:
        related_lines.append(f"- SOP: {sop}")
    for file in related_files:
        related_lines.append(f"- `{file}`")

    related_str = "\n".join(related_lines) if related_lines else "- None documented"

    # Type display name
    type_display = memory_type.title()

    content = f"""# {type_display}: {title}

## Summary
{summary}

## Context
{context if context else "Discovered during development."}

## Details
{details if details else summary}

## Recommended Approach
{approach if approach else "Apply this knowledge when working on related topics."}

## Related
{related_str}

---
**Captured**: {datetime.now().strftime("%Y-%m-%d")}
**Confidence**: {confidence}%
**Concepts**: {", ".join(concepts) if concepts else "general"}
"""

    output_path.write_text(content)
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='Create memory markdown file')
    parser.add_argument('--memory-id', required=True, help='Memory ID (e.g., mem-001)')
    parser.add_argument('--memory-type', required=True,
                       choices=['pattern', 'pitfall', 'decision', 'learning'],
                       help='Type of memory')
    parser.add_argument('--title', required=True, help='Memory title')
    parser.add_argument('--summary', required=True, help='Short summary')
    parser.add_argument('--context', default='', help='When/how discovered')
    parser.add_argument('--details', default='', help='Detailed explanation')
    parser.add_argument('--approach', default='', help='Recommended approach')
    parser.add_argument('--related-tasks', default='', help='Comma-separated task IDs')
    parser.add_argument('--related-sops', default='', help='Comma-separated SOP names')
    parser.add_argument('--related-files', default='', help='Comma-separated file paths')
    parser.add_argument('--confidence', type=int, default=80, help='Confidence (0-100)')
    parser.add_argument('--concepts', default='', help='Comma-separated concepts')
    parser.add_argument('--base-dir', default='.agent/knowledge', help='Base directory')

    args = parser.parse_args()

    # Parse comma-separated lists
    related_tasks = [t.strip() for t in args.related_tasks.split(',') if t.strip()]
    related_sops = [s.strip() for s in args.related_sops.split(',') if s.strip()]
    related_files = [f.strip() for f in args.related_files.split(',') if f.strip()]
    concepts = [c.strip() for c in args.concepts.split(',') if c.strip()]

    output_path = create_memory_file(
        memory_id=args.memory_id,
        memory_type=args.memory_type,
        title=args.title,
        summary=args.summary,
        context=args.context,
        details=args.details,
        approach=args.approach,
        related_tasks=related_tasks,
        related_sops=related_sops,
        related_files=related_files,
        confidence=args.confidence,
        concepts=concepts,
        base_dir=args.base_dir
    )

    print(f"Memory file created: {output_path}")


if __name__ == '__main__':
    main()
