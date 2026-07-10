"""S4 — UserPromptSubmit block-as-answer (Tier-1 candidate; mem-034 hygiene).

Variant A: {"decision":"block","reason":<answer>}; variant B: exit 2 + stderr.
Pass per variant: zero model invocation on the blocked turn; then an unrelated
follow-up in the same session must not re-trigger the hook and must answer
normally. Rendering (stdout/stderr shape) is captured for the winner call.

Both variants count as ONE probe run. Known CC 2.1.205 behavior (mem-053):
CC appends "Original prompt: <trigger>" to block messages — transcript-scanning
hooks must tolerate it; winner is decision:block (exit-2 leaks hook chrome).
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))
from common import (arm, disarm, clear_log, read_log, preflight, run_claude,
                    find_transcripts, scan_jsonl, entry_lines, make_sentinel,
                    write_verdict)

preflight()
results = {}

for variant in ("block-json", "exit-2"):
    clear_log("s4")
    sentinel = make_sentinel(f"4{'A' if variant == 'block-json' else 'B'}")
    arm("s4", {"sentinel": sentinel, "variant": variant})
    try:
        r1 = run_claude("nav spike ping")
        r2 = (run_claude("What is 2+2? Answer with just the number.",
                         resume=r1["session_id"])
              if r1["session_id"] else
              run_claude("What is 2+2? Answer with just the number."))
    finally:
        disarm("s4")

    log = read_log("s4")
    blocked = any(e.get("event") == "trigger-blocked" for e in log)
    followup_passthrough = any(e.get("event") == "non-trigger-passthrough"
                               for e in log)

    transcripts = find_transcripts(session_id=r1["session_id"], since=r1["started"])
    if r2["session_id"]:
        transcripts += [t for t in find_transcripts(session_id=r2["session_id"])
                        if t not in transcripts]
    assistant_lines, occurrences = [], []
    for t in transcripts:
        occurrences += scan_jsonl(t, sentinel)
        assistant_lines += entry_lines(
            t, lambda e: e.get("type") == "assistant")

    results[variant] = {
        "sentinel": sentinel,
        "hook_blocked": blocked,
        "blocked_turn_exit_code": r1["exit_code"],
        "blocked_turn_stdout": r1["stdout"][:800],
        "blocked_turn_stderr": r1["stderr"][:800],
        "sentinel_in_cli_output": sentinel in (r1["stdout"] + r1["stderr"]),
        "followup_hook_passthrough": followup_passthrough,
        "followup_retriggered": sum(1 for e in log
                                    if e.get("event") == "trigger-blocked") > 1,
        "followup_answer": r2["result_text"][:200],
        "followup_answer_contains_block_text": sentinel in (r2["result_text"] or ""),
        "sentinel_occurrences": occurrences,
        "assistant_entry_lines": assistant_lines,
        "transcripts": [str(t) for t in transcripts],
        "hook_log": log,
    }

write_verdict("s4", {
    "channel": "UserPromptSubmit block-as-answer (decision:block vs exit-2)",
    "variants": results,
    "pass": any(
        v["hook_blocked"] and v["sentinel_in_cli_output"]
        and not v["followup_retriggered"]
        and not v["followup_answer_contains_block_text"]
        for v in results.values()),
})
