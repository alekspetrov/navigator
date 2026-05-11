#!/usr/bin/env python3
"""
Navigator Token Monitor Hook

Monitors context usage and suggests /nav:compact when approaching limits.
Runs after each tool use to track session efficiency.

Usage: Configure in .claude/settings.json:
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python3 $CLAUDE_PROJECT_DIR/hooks/monitor-tokens.py",
        "timeout": 5
      }]
    }]
  }
}
"""

import json
import sys
import os
from pathlib import Path

# Configuration
TOKEN_LIMIT = 180000  # Claude's context window
WARN_THRESHOLD = 0.70  # 70% - suggest planning compact
CRITICAL_THRESHOLD = 0.85  # 85% - recommend compact now

# State file to avoid repeated warnings
STATE_FILE = Path.home() / '.claude' / '.nav-token-state.json'


def read_hook_data():
    """Read hook context from stdin"""
    try:
        return json.loads(sys.stdin.read())
    except:
        return {}


def estimate_tokens_from_transcript(transcript_path):
    """Estimate token count from conversation transcript"""
    try:
        if not transcript_path or not Path(transcript_path).exists():
            return 0

        with open(transcript_path, 'r') as f:
            content = f.read()

        # Rough estimate: ~4 characters per token
        # This is conservative - actual tokenization varies
        estimated_tokens = len(content) // 4
        return estimated_tokens
    except Exception:
        return 0


def get_state():
    """Load previous alert state"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'last_warning_level': 0, 'session_id': None}


def save_state(state):
    """Persist alert state"""
    try:
        STATE_FILE.parent.mkdir(exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass


def main():
    try:
        hook_data = read_hook_data()
        transcript_path = hook_data.get('transcript_path')
        session_id = hook_data.get('session_id')

        if not transcript_path:
            sys.exit(0)

        # Estimate current token usage
        tokens = estimate_tokens_from_transcript(transcript_path)
        usage_percent = tokens / TOKEN_LIMIT

        # Load state (reset if new session)
        state = get_state()
        if state.get('session_id') != session_id:
            state = {'last_warning_level': 0, 'session_id': session_id}

        # Determine warning level
        if usage_percent >= CRITICAL_THRESHOLD:
            warning_level = 2
        elif usage_percent >= WARN_THRESHOLD:
            warning_level = 1
        else:
            warning_level = 0

        # Only alert when crossing a new threshold
        if warning_level > state['last_warning_level']:
            percent_display = int(usage_percent * 100)

            if warning_level == 2:
                print(f"\n{'='*50}")
                print(f"  CONTEXT CRITICAL: {percent_display}% used")
                print(f"  {tokens:,} / {TOKEN_LIMIT:,} tokens")
                print(f"")
                print(f"  Run: 'Clear context and preserve markers'")
                print(f"  Or:  /nav:compact")
                print(f"{'='*50}\n")
            elif warning_level == 1:
                print(f"\n  Context at {percent_display}% - plan to compact after current task\n")

            state['last_warning_level'] = warning_level
            save_state(state)

        # Reset warning level if usage drops (after compact)
        elif warning_level < state['last_warning_level']:
            state['last_warning_level'] = warning_level
            save_state(state)

        sys.exit(0)

    except Exception as e:
        # Fail silently - don't block Claude
        sys.exit(0)


if __name__ == '__main__':
    main()
