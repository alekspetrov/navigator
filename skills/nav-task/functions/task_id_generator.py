#!/usr/bin/env python3
"""
Generate next sequential TASK-XX ID by scanning existing task files.
"""

import os
import re
import sys

def get_next_task_id(agent_dir=".agent", prefix="TASK"):
    """
    Scan tasks/ directory and return next available TASK-XX ID.

    Args:
        agent_dir: Path to .agent directory (default: .agent)
        prefix: Task ID prefix (default: TASK)

    Returns:
        str: Next task ID (e.g., "TASK-10")
    """
    tasks_dir = os.path.join(agent_dir, "tasks")

    if not os.path.exists(tasks_dir):
        return f"{prefix}-01"

    # Find all task files matching TASK-XX.md or TASK-XX-name.md
    task_pattern = re.compile(rf"{prefix}-(\d+)(?:-.*)?\.md")
    task_numbers = []

    for filename in os.listdir(tasks_dir):
        if filename == "archive":  # Skip archive directory
            continue

        match = task_pattern.match(filename)
        if match:
            task_numbers.append(int(match.group(1)))

    if not task_numbers:
        return f"{prefix}-01"

    # Get next sequential number
    next_num = max(task_numbers) + 1
    return f"{prefix}-{next_num:02d}"

if __name__ == "__main__":
    # Support optional arguments
    agent_dir = sys.argv[1] if len(sys.argv) > 1 else ".agent"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "TASK"

    next_id = get_next_task_id(agent_dir, prefix)
    print(next_id)
