#!/usr/bin/env python3
"""
Format task markdown with proper structure and metadata.
"""

import sys
import argparse
from datetime import datetime

def format_task(title, task_id, priority="Medium", complexity="Medium", status="Planning"):
    """
    Generate formatted task markdown.

    Args:
        title: Task title
        task_id: Task ID (e.g., TASK-10)
        priority: Priority level (Low, Medium, High, Critical)
        complexity: Complexity level (Low, Medium, High)
        status: Task status (Planning, In Progress, Completed)

    Returns:
        str: Formatted markdown content
    """
    today = datetime.now().strftime("%Y-%m-%d")

    template = f"""# {task_id}: {title}

**Created**: {today}
**Status**: {status}
**Priority**: {priority}
**Complexity**: {complexity}

---

## Context

[Describe the problem, feature request, or improvement needed]

**Problem**: [What needs to be solved?]

**Goal**: [What should be achieved?]

---

## Implementation Plan

### Phase 1: [Phase Name]

**Tasks**:
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Expected Outcome**: [What this phase delivers]

---

## Success Metrics

**Functionality**:
- [ ] Feature works as expected
- [ ] Edge cases handled
- [ ] Error handling implemented

**Quality**:
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Code reviewed

**Token Efficiency** (if applicable):
- [ ] Token usage measured
- [ ] Optimization targets met
- [ ] No context pollution

---

## Testing Plan

1. **Unit tests**: [What to test]
2. **Integration tests**: [What to test]
3. **Manual testing**: [Steps to verify]

---

## Verify

Run these commands to validate the implementation:

```bash
# Run tests
[test command for this feature]

# Type check
[type check command]

# Build
[build command]
```

---

## Done

Observable outcomes that prove completion:

- [ ] [Specific file/API exists and exports expected interface]
- [ ] [Tests pass - specify count or coverage target]
- [ ] [Build succeeds without errors]
- [ ] [User-observable behavior works as specified]

---

## Related Tasks

- [Link to related tasks]

---

## Notes

- [Additional context, decisions, or considerations]

---

**Task created**: {today}
**Priority**: {priority}
**Effort**: {complexity}
"""
    return template

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Format Navigator task markdown")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--id", required=True, help="Task ID (e.g., TASK-10)")
    parser.add_argument("--priority", default="Medium", choices=["Low", "Medium", "High", "Critical"])
    parser.add_argument("--complexity", default="Medium", choices=["Low", "Medium", "High"])
    parser.add_argument("--status", default="Planning", choices=["Planning", "In Progress", "Completed"])

    args = parser.parse_args()

    output = format_task(
        title=args.title,
        task_id=args.id,
        priority=args.priority,
        complexity=args.complexity,
        status=args.status
    )

    print(output)
