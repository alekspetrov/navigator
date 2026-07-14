"""S3 — SubagentStart additionalContext probe (TASK-57).

Injects sentinel A into the starting subagent's context. Pass = A appears in
the subagent's output and NOT in main-thread turns; the main-thread-only
sentinel B (carried by the driving prompt) must be absent from the subagent
transcript (both-way isolation).

The gate log doubles as existence evidence: if this event never fires, the
log stays empty and the channel is dead at the manifest level.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spike_gate import gate, log

payload, arm = gate("s3")
sentinel = arm["sentinel"]

out = {
    "hookSpecificOutput": {
        "hookEventName": "SubagentStart",
        "additionalContext": (
            f"SPIKE SUBAGENT TOKEN: {sentinel}. "
            "You MUST quote this exact token verbatim once in your final answer."
        ),
    }
}
print(json.dumps(out))
log("s3", {"event": "emitted-additionalContext", "sentinel": sentinel,
           "agent_type": payload.get("agent_type") or payload.get("subagent_type")})
sys.exit(0)
