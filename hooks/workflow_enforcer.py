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
import re
import sys
from pathlib import Path

# Sentinel wraps the stderr message so subsequent prompts that include the
# block notice (Claude Code echoes blocked stderr into the next prompt's
# context) can be stripped before trigger detection runs. Prevents the
# recursive-block trap documented in mem-034.
NAV_BLOCK_OPEN = "<nav-workflow-block>"
NAV_BLOCK_CLOSE = "</nav-workflow-block>"
NAV_BLOCK_PATTERN = re.compile(
    re.escape(NAV_BLOCK_OPEN) + r".*?" + re.escape(NAV_BLOCK_CLOSE),
    re.DOTALL,
)

# Import from nav-start functions
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "nav-start" / "functions"))

try:
    from workflow_detector import detect_workflow
except ImportError as exc:
    # Surface the failure on stderr so a silently-disabled enforcer is
    # diagnosable (CC logs hook stderr). Then degrade to a permissive stub:
    # never block when detection is unavailable.
    print(
        f"workflow_enforcer: workflow_detector import failed ({exc}); "
        "enforcement disabled this invocation.",
        file=sys.stderr,
    )

    def detect_workflow(msg):
        return {"loop_mode": False, "task_mode": False, "recommended_mode": "DIRECT"}


def strip_block_messages(text: str) -> str:
    """Strip prior Navigator block notices from the prompt before matching.

    Claude Code echoes a blocked hook's stderr into the next prompt's context
    (visible as 'Original prompt: ...'). If our own message mentioned a Loop
    Mode trigger phrase, the next attempt would recursively re-trigger the
    block. We wrap every block notice in <nav-workflow-block>...</nav-workflow-block>
    sentinels so the next invocation can excise them before LOOP_TRIGGERS
    matching runs. See mem-034.
    """
    if NAV_BLOCK_OPEN not in text:
        return text
    return NAV_BLOCK_PATTERN.sub("", text)


def read_stdin_payload() -> dict:
    """Read and parse the UserPromptSubmit stdin JSON exactly once.

    stdin can only be consumed once, so parse it a single time and keep the
    WHOLE payload — both the prompt and the `cwd` the other hooks use for
    project-root resolution. Returns {} when stdin is absent/empty, or
    {"prompt": raw} when the body is non-JSON text (legacy raw-prompt form).
    """
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            raw = sys.stdin.read().strip()
            if raw:
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"prompt": raw}
    except Exception:
        pass
    return {}


def get_user_message(stdin_data: dict) -> str:
    """Extract the user message from the parsed stdin payload or legacy env."""
    prompt = stdin_data.get("prompt") or stdin_data.get("user_message") or ""
    if prompt:
        return strip_block_messages(prompt)
    # Fallback to legacy env var
    return strip_block_messages(os.environ.get("CLAUDE_USER_MESSAGE", ""))


def _project_root(stdin_data: dict) -> Path:
    """Resolve the project root the same way every other Navigator hook does.

    Mirrors nav_workflow_state._project_root so the enforcer reads config and
    state from the SAME absolute location the state writer uses. The previous
    cwd-relative Path(".agent/...") disagreed with the writer's
    stdin-cwd-derived absolute path whenever Claude Code's cwd != project root.
    """
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def check_config(root: Path) -> dict:
    """Load Navigator config from the project root."""
    config_path = root / ".agent" / ".nav-config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except:
            pass
    return {}


def read_prior_turn_state(root: Path) -> dict:
    """Read .agent/.nav-workflow-state.json — written by hooks/nav_workflow_state.py.

    Returns {} when the file is missing or unreadable; callers must treat this
    as "no signal" and never block on it.
    """
    state_path = root / ".agent" / ".nav-workflow-state.json"
    if not state_path.exists():
        return {}
    try:
        with open(state_path) as f:
            return json.load(f) or {}
    except Exception:
        return {}


def main():
    """Main hook logic."""
    # Escape hatch for autonomous executors (e.g. PILOT) that drive Claude
    # programmatically and should bypass interactive workflow gating.
    if os.environ.get("PILOT_EXECUTOR"):
        sys.exit(0)

    stdin_data = read_stdin_payload()
    message = get_user_message(stdin_data)
    if not message:
        sys.exit(0)

    root = _project_root(stdin_data)
    config = check_config(root)
    enforcer_cfg = config.get("workflow_enforcer_hook", {})
    if enforcer_cfg.get("enabled", True) is False:
        sys.exit(0)
    strict_block = enforcer_cfg.get("strict_block", True)

    result = detect_workflow(message)
    task_mode_enabled = config.get("task_mode", {}).get("enabled", True)

    # Decide block first; soft-warn output is suppressed when blocking so the
    # only echoed text is the sentinel-wrapped stderr (avoids leaking trigger
    # substrings back into the next prompt). See mem-034.
    will_block = False
    if strict_block and result["loop_mode"]:
        state = read_prior_turn_state(root)
        last_turn = state.get("last_turn") or {}
        check_shown = last_turn.get("check_shown")
        will_block = check_shown is False

    if not will_block:
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

    # Hard-block gate (TASK-38 Phase 2). Fires only when state file confirms
    # the prior assistant turn skipped the WORKFLOW CHECK block.
    if will_block:
        # Important: this message addresses the USER, not the assistant.
        # UserPromptSubmit exit-2 blocks the prompt before the model runs,
        # so any instruction here that asks Claude to "do X" is dead text.
        # Avoid quoting any LOOP_TRIGGERS substring verbatim — Claude Code
        # echoes blocked stderr into the next prompt context, which would
        # recursively re-trigger the block. The sentinel below lets the
        # next invocation strip this message before matching. See mem-034.
        sys.stderr.write(
            NAV_BLOCK_OPEN + "\n"
            "Navigator workflow_enforcer: blocked.\n"
            "  Why: the prior assistant turn skipped its required workflow "
            "check block, but your prompt requests autonomous iteration.\n"
            "  State: .agent/.nav-workflow-state.json check_shown=false\n"
            "  How to proceed (your choice):\n"
            "    1. Send any different prompt that does not request "
            "autonomous iteration. The next assistant response will "
            "restore state; then retry your original prompt.\n"
            "    2. Edit .agent/.nav-workflow-state.json and set "
            "last_turn.check_shown=true.\n"
            "    3. Disable strict enforcement: set "
            "workflow_enforcer_hook.strict_block=false in "
            ".agent/.nav-config.json.\n"
            + NAV_BLOCK_CLOSE + "\n"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
