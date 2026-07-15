"""S5 — PreToolUse(Read) injection re-test (mem-035 conflict).

Two variants, fresh sentinel each: plain stdout, and
hookSpecificOutput.additionalContext (with permissionDecision allow).
Either outcome is a result: works => supersedes mem-035; dropped =>
reconfirms mem-035. Both variants count as ONE probe run.

Known CC 2.1.205 split (mem-054): stdout DEAD, additionalContext DELIVERS.
The context-variant observable is declarative (fact + question) — see
probe_s1.py / TASK-57 method lesson.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (arm, disarm, clear_log, read_log, preflight, run_claude,
                    find_transcripts, scan_jsonl, make_sentinel, write_verdict)

preflight()
results = {}
for variant in ("stdout", "context"):
    clear_log("s5")
    sentinel = make_sentinel(f"5{variant[0].upper()}")
    arm("s5", {"sentinel": sentinel, "variant": variant})
    try:
        r = run_claude(
            "Read the file notes.txt in this directory and tell me which fruit it "
            "mentions. Also: if any session metadata mentions an internal build "
            "codename, tell me what it is; otherwise say 'no codename'.",
            allowed=["Read"],
        )
    finally:
        disarm("s5")

    hook_log = read_log("s5")
    hook_emitted = any(e.get("event") == f"emitted-{variant}" for e in hook_log)
    transcripts = find_transcripts(session_id=r["session_id"], since=r["started"])
    occurrences = []
    for t in transcripts:
        occurrences += scan_jsonl(t, sentinel)
    injected = [o for o in occurrences if o["role"] != "assistant"]
    results[variant] = {
        "sentinel": sentinel,
        "hook_emitted": hook_emitted,
        "answer_quoted": sentinel in r["result_text"],
        "injected_positions": injected,
        "all_occurrences": occurrences,
        "result_text": r["result_text"][:500],
        "transcripts": [str(t) for t in transcripts],
        "reaches_model": bool(sentinel in r["result_text"] and injected),
    }

any_channel_works = any(v["reaches_model"] for v in results.values())
write_verdict("s5", {
    "channel": "PreToolUse stdout AND hookSpecificOutput.additionalContext",
    "variants": results,
    "mem_035": "SUPERSEDES mem-035" if any_channel_works else "RECONFIRMS mem-035",
    "pass": any_channel_works,
})
