"""S1 — PostToolUse(Read) additionalContext reaches the model?

Pass: sentinel quoted verbatim in the visible answer AND transcript grep finds
it in a non-assistant (injected) position at/after the tool_result — not
merely echoed by the model.

Observable is DECLARATIVE (fact + question), never "quote this token" —
the model's injection defense refuses imperative compliance on tool-adjacent
channels while delivery succeeds (TASK-57 method lesson).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (arm, disarm, clear_log, read_log, preflight, run_claude,
                    find_transcripts, scan_jsonl, entry_lines, make_sentinel,
                    write_verdict)

preflight()
clear_log("s1")
sentinel = make_sentinel("1")
arm("s1", {"sentinel": sentinel})
try:
    r = run_claude(
        "Read the file notes.txt in this directory and tell me which fruit it "
        "mentions. Also: if any session metadata mentions an internal build "
        "codename, tell me what it is; otherwise say 'no codename'.",
        allowed=["Read"],
    )
finally:
    disarm("s1")

hook_log = read_log("s1")
hook_emitted = any(e.get("event") == "emitted-additionalContext" for e in hook_log)
answer_quoted = sentinel in r["result_text"]

transcripts = find_transcripts(session_id=r["session_id"], since=r["started"])
occurrences = []
tool_result_lines = []
for t in transcripts:
    occurrences += scan_jsonl(t, sentinel)
    tool_result_lines += [
        {"file": str(t), "line": n}
        for n in entry_lines(t, lambda e: isinstance((e.get("message") or {}).get("content"), list)
                             and any(b.get("type") == "tool_result"
                                     for b in e["message"]["content"]))
    ]

injected = [o for o in occurrences if o["role"] != "assistant"]
quoted = [o for o in occurrences if o["role"] == "assistant"]

write_verdict("s1", {
    "channel": "PostToolUse hookSpecificOutput.additionalContext",
    "sentinel": sentinel,
    "hook_emitted": hook_emitted,
    "answer_quoted": answer_quoted,
    "injected_positions": injected,
    "assistant_positions": quoted,
    "tool_result_lines": tool_result_lines,
    "transcripts": [str(t) for t in transcripts],
    "result_text": r["result_text"][:500],
    "exit_code": r["exit_code"],
    "pass": bool(hook_emitted and answer_quoted and injected),
})
