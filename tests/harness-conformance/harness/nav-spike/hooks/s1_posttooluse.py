"""S1 — PostToolUse(Read) additionalContext injection probe (TASK-57).

Emits hookSpecificOutput.additionalContext carrying the per-run sentinel plus
an instruction to quote it. Pass = sentinel quoted in the visible answer AND
transcript grep finds it positioned at/after the tool_result (injected), not
merely echoed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spike_gate import gate, log

payload, arm = gate("s1")
sentinel = arm["sentinel"]

# Declarative fact, no imperative: the model's injection defense flags
# "you MUST quote X" from tool-adjacent hooks as prompt injection (observed
# 2/2 on CC 2.1.205), which conflates delivery with compliance. The driving
# prompt asks a question only answerable from this fact.
out = {
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"Session metadata: the internal build codename for this "
            f"session is {sentinel}."
        ),
    }
}
print(json.dumps(out))
log("s1", {"event": "emitted-additionalContext", "sentinel": sentinel,
           "tool_name": payload.get("tool_name")})
sys.exit(0)
