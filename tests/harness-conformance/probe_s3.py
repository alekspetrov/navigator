"""S3 — SubagentStart additionalContext + both-way isolation.

Sentinel A injected via SubagentStart hook; sentinel B lives only in the main
thread's driving prompt. Pass: A visible on the subagent side (sidechain
context + quoted in the subagent's answer), NOT injected into main-thread
context before the Task result; B absent from sidechain entries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (arm, disarm, clear_log, read_log, preflight, run_claude,
                    find_transcripts, scan_jsonl, make_sentinel, write_verdict)

preflight()
clear_log("s3")
a = make_sentinel("3A")
b = make_sentinel("3B")
arm("s3", {"sentinel": a})
try:
    r = run_claude(
        "Use the Task tool to launch one subagent (subagent_type: general-purpose) "
        "with exactly this prompt: 'What is the capital of France? Answer in one word.' "
        "Then report the subagent's final answer verbatim. "
        f"Main-thread-only marker (do NOT include it in the subagent prompt): {b}",
        allowed=["Task"],
        timeout=420,
    )
finally:
    disarm("s3")

hook_log = read_log("s3")
event_fired = any(e.get("event") == "emitted-additionalContext" for e in hook_log)

transcripts = find_transcripts(session_id=r["session_id"], since=r["started"])
occ_a, occ_b = [], []
for t in transcripts:
    occ_a += scan_jsonl(t, a)
    occ_b += scan_jsonl(t, b)

a_sidechain = [o for o in occ_a if o["is_sidechain"] or "subagents" in o["file"]]
a_main = [o for o in occ_a if not (o["is_sidechain"] or "subagents" in o["file"])]
# A relayed back inside the Task tool_result is expected; a leak means A in
# main-thread entries whose blocks are NOT tool_result relays.
a_main_leak = [o for o in a_main
               if not any(bt in ("tool_result", "toolUseResult", "entry.toolUseResult")
                          for bt in o["block_types"])
               and o["role"] == "user"]
b_sidechain = [o for o in occ_b if o["is_sidechain"] or "subagents" in o["file"]]

write_verdict("s3", {
    "channel": "SubagentStart hookSpecificOutput.additionalContext",
    "sentinel_a": a, "sentinel_b": b,
    "event_fired": event_fired,
    "hook_log": hook_log,
    "a_sidechain_positions": a_sidechain,
    "a_main_positions": a_main,
    "a_main_leaks": a_main_leak,
    "b_sidechain_positions": b_sidechain,
    "result_text": r["result_text"][:500],
    "transcripts": [str(t) for t in transcripts],
    "pass": bool(event_fired and a_sidechain and not a_main_leak and not b_sidechain),
})
