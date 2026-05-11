#!/usr/bin/env python3
"""
Navigator Workflow Enforcer Hook

Claude Code hook that runs on UserPromptSubmit to detect workflow requirements.

Behavior (v6.11.1+):
  - Soft warn (exit 0) by default: prints WORKFLOW CHECK reminder to stdout.
  - Hard block (exit 2) when ALL of:
      1. Loop Mode trigger detected in current prompt
      2. .agent/.nav-workflow-state.json shows prior turn check_shown=false
      3. workflow_enforcer_hook.strict_block = true (default true)
  - Always exits 0 (soft warn) when state file missing — keeps Phase 1 projects unaffected.

This is the first blocking hook in Navigator (TASK-38 Phase 2). Gating on the
state file written by hooks/nav_workflow_state.py keeps false-positives near zero:
the block only fires when prior turn empirically skipped the CHECK block.

Input (from Claude Code):
    stdin JSON: {"prompt": "..."} for UserPromptSubmit
    Fallback: CLAUDE_USER_MESSAGE env var (legacy)

Output:
    stdout: WORKFLOW CHECK reminder block.
    stderr (on block): explanation surfaced to Claude per Claude Code hooks spec.
    exit 0 (warn) or exit 2 (block).
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
    """Get user message from stdin JSON (UserPromptSubmit) or env (legacy)."""
    # Try stdin JSON first (Claude Code UserPromptSubmit format)
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            raw = sys.stdin.read().strip()
            if raw:
                try:
                    data = json.loads(raw)
                    prompt = data.get("prompt") or data.get("user_message") or ""
                    if prompt:
                        return prompt
                except json.JSONDecodeError:
                    return raw
    except Exception:
        pass

    # Fallback to legacy env var
    return os.environ.get("CLAUDE_USER_MESSAGE", "")


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


def read_prior_turn_state() -> dict:
    """Read .agent/.nav-workflow-state.json — written by hooks/nav_workflow_state.py.

    Returns {} when the file is missing or unreadable; callers must treat this
    as "no signal" and never block on it.
    """
    state_path = Path(".agent/.nav-workflow-state.json")
    if not state_path.exists():
        return {}
    try:
        with open(state_path) as f:
            return json.load(f) or {}
    except Exception:
        return {}


def main():
    """Main hook logic."""
    message = get_user_message()
    if not message:
        sys.exit(0)

    config = check_config()
    enforcer_cfg = config.get("workflow_enforcer_hook", {})
    if enforcer_cfg.get("enabled", True) is False:
        sys.exit(0)
    strict_block = enforcer_cfg.get("strict_block", True)

    result = detect_workflow(message)
    task_mode_enabled = config.get("task_mode", {}).get("enabled", True)

    warnings = []
    if result["loop_mode"]:
        trigger = result.get("loop_trigger", "unknown")
        warnings.append(f"⚠️  LOOP MODE TRIGGER DETECTED: '{trigger}'")
        warnings.append("   Show NAVIGATOR_STATUS blocks and use EXIT_SIGNAL.")

    if result["task_mode"] and task_mode_enabled:
        score = result.get("complexity", 0)
        warnings.append(f"⚠️  TASK MODE RECOMMENDED: complexity={score}")
        warnings.append("   Show phase tracking (RESEARCH → IMPL → VERIFY → COMPLETE).")

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

    # Hard-block gate (TASK-38 Phase 2). Only fires when:
    #   - strict_block enabled
    #   - current prompt has a Loop trigger
    #   - prior turn state file confirms WORKFLOW CHECK was NOT shown
    if strict_block and result["loop_mode"]:
        state = read_prior_turn_state()
        last_turn = state.get("last_turn") or {}
        check_shown = last_turn.get("check_shown")
        # Only block when we have a definitive prior-turn signal saying "missed".
        # Missing state file or unset value → soft warn (Phase 1 projects unaffected).
        if check_shown is False:
            trigger = result.get("loop_trigger", "unknown")
            sys.stderr.write(
                "Navigator workflow_enforcer: blocked.\n"
                f"  Reason: loop trigger '{trigger}' detected, but the prior "
                "assistant turn did not show a WORKFLOW CHECK block "
                "(.agent/.nav-workflow-state.json: check_shown=false).\n"
                "  Action: emit the WORKFLOW CHECK block at the top of the next "
                "response, then continue with NAVIGATOR_STATUS for Loop Mode.\n"
                "  Opt-out: set workflow_enforcer_hook.strict_block=false in "
                ".agent/.nav-config.json.\n"
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
