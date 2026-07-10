"""S4 — UserPromptSubmit block-as-answer probe (Tier-1 candidate; TASK-57, mem-034).

Trigger: the EXACT prompt "nav spike ping". Variants (from arm file):
  "block-json" — print {"decision": "block", "reason": <answer+sentinel>}, exit 0
  "exit-2"     — print answer+sentinel on stderr, exit 2

Echo hygiene (mem-034): the served answer must never contain the trigger
phrase, so a re-echo cannot re-trigger the hook. Non-trigger prompts are
logged (proof the hook ran without blocking) and passed through.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))
from spike_gate import gate, log

payload, arm = gate("s4")
prompt = (payload.get("prompt") or "").strip()

if prompt != "nav spike ping":
    log("s4", {"event": "non-trigger-passthrough", "prompt_head": prompt[:80]})
    sys.exit(0)

sentinel = arm["sentinel"]
variant = arm.get("variant", "block-json")
answer = (
    f"PONG — served deterministically by the S4 hook, zero model tokens. "
    f"Answer token: {sentinel}."
)

log("s4", {"event": "trigger-blocked", "variant": variant, "sentinel": sentinel})

if variant == "block-json":
    print(json.dumps({"decision": "block", "reason": answer}))
    sys.exit(0)
else:
    print(answer, file=sys.stderr)
    sys.exit(2)
