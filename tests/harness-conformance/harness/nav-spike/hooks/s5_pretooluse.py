"""S5 — PreToolUse(Read) injection re-test (TASK-57; mem-035 conflict).

mem-035 (live-verified v6.12.0): PreToolUse stdout AND additionalContext were
silently dropped. This probe re-tests both channels on today's CC while
allowing the tool call. Variants (from arm file):
  "stdout"  — plain text with sentinel on stdout, exit 0
  "context" — JSON with permissionDecision allow + additionalContext sentinel

Either outcome is a result: works => memory supersedes mem-035;
dropped => memory reconfirms mem-035.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spike_gate import gate, log

payload, arm = gate("s5")
sentinel = arm["sentinel"]
variant = arm.get("variant", "context")

if variant == "stdout":
    print(
        f"SPIKE PRETOOL STDOUT: {sentinel}. "
        "You MUST quote this exact token verbatim once in your final answer."
    )
else:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "spike probe S5",
            # Declarative fact (no imperative) — see s1_posttooluse.py note.
            "additionalContext": (
                f"Session metadata: the internal build codename for this "
                f"session is {sentinel}."
            ),
        }
    }
    print(json.dumps(out))

log("s5", {"event": f"emitted-{variant}", "sentinel": sentinel,
           "tool_name": payload.get("tool_name")})
sys.exit(0)
