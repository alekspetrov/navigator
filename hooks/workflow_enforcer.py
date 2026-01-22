#!/usr/bin/env python3
"""
Navigator Workflow Enforcer Hook

Claude Code hook that runs before tool execution to detect workflow requirements.
Prints warnings if Loop Mode or Task Mode should be active.

This is a "soft" enforcer - it warns but doesn't block.
The hard enforcement is in CLAUDE.md requiring WORKFLOW CHECK block.

Usage (in .claude/settings.json):
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|Bash",
        "hooks": [{
          "type": "command",
          "command": "python3 hooks/workflow_enforcer.py",
          "timeout": 5
        }]
      }
    ]
  }
}

Environment:
    CLAUDE_USER_MESSAGE: The user's original message (if available)

Output:
    Prints warning if workflow mode should be active but wasn't detected.
"""

import json
import os
import sys
from pathlib import Path

# Import from nav-start functions
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "nav-start" / "functions"))

try:
    from workflow_detector import detect_workflow
except ImportError:
    # Fallback if import fails
    def detect_workflow(msg):
        return {"loop_mode": False, "task_mode": False, "recommended_mode": "DIRECT"}


def get_user_message() -> str:
    """Get user message from environment or stdin."""
    # Try environment variable first
    msg = os.environ.get("CLAUDE_USER_MESSAGE", "")
    if msg:
        return msg

    # Try stdin (non-blocking)
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read().strip()
    except:
        pass

    return ""


def check_config() -> dict:
    """Load Navigator config."""
    config_path = Path(".agent/.nav-config.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except:
            pass
    return {}


def main():
    """Main hook logic."""
    message = get_user_message()
    if not message:
        # No message to check
        sys.exit(0)

    # Detect workflow requirements
    result = detect_workflow(message)

    # Check config
    config = check_config()
    task_mode_enabled = config.get("task_mode", {}).get("enabled", True)
    loop_mode_enabled = config.get("loop_mode", {}).get("enabled", False)

    warnings = []

    # Warn if Loop Mode should be active
    if result["loop_mode"]:
        trigger = result.get("loop_trigger", "unknown")
        warnings.append(f"⚠️  LOOP MODE TRIGGER DETECTED: '{trigger}'")
        warnings.append("   Show NAVIGATOR_STATUS blocks and use EXIT_SIGNAL.")

    # Warn if Task Mode should be active
    if result["task_mode"] and task_mode_enabled:
        score = result.get("complexity", 0)
        warnings.append(f"⚠️  TASK MODE RECOMMENDED: complexity={score}")
        warnings.append("   Show phase tracking (RESEARCH → IMPL → VERIFY → COMPLETE).")

    # Print warnings if any
    if warnings:
        print("\n".join(warnings))
        print("")
        print("Remember to show WORKFLOW CHECK block!")
        print("┌─────────────────────────────────────┐")
        print("│ WORKFLOW CHECK                      │")
        print("├─────────────────────────────────────┤")
        print(f"│ Loop trigger: {'YES' if result['loop_mode'] else 'NO':17} │")
        print(f"│ Complexity: {result.get('complexity', 0):<19} │")
        print(f"│ Mode: {result['recommended_mode']:<24} │")
        print("└─────────────────────────────────────┘")

    sys.exit(0)


if __name__ == "__main__":
    main()
