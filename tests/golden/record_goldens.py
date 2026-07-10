#!/usr/bin/env python3
"""Record v6 golden outputs for the TASK-61 parity corpus.

Two modes:

  python3 record_goldens.py --capture-log /tmp/nav-v7-golden/captured/events.jsonl
      Initial recording. Extracts the live-captured payloads (one headless session driven
      per README.md), synthesizes the two compact payloads (Pre/PostCompact cannot be
      driven headlessly — documented deviation), runs each v6 hook script against a fresh
      fixture project, and writes goldens/<surface>.json.

  python3 record_goldens.py
      Re-record. Keeps every stored payload byte-identical and refreshes stdout/exit_code
      from the current v6 scripts. Only legitimate use: a SANCTIONED behavior change was
      approved for the corpus (record the reason in the golden's env_notes / task doc).
      Refuses to run if the v6 scripts are gone (post Phase 7 the goldens are frozen).

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import (  # noqa: E402
    GOLDENS, HOOKS_DIR, REPO_ROOT, SURFACES, build_env, build_project, load_golden, run_v6,
)

SYNTH_NOTE = (
    "SYNTHESIZED payload: Pre/PostCompact cannot be driven headlessly. Fields mirror what "
    "the v6 hook reads (cwd, session_id, transcript_path, plus trigger / compact_summary), "
    "with session identity taken from the live-captured Stop payload. See README.md."
)
CAPTURE_NOTE = "REAL payload captured verbatim from a live headless session (see README.md)."
ENV_NOTES = {
    "CLAUDE_PLUGIN_ROOT": "repo root (parity runner also replays with the var UNSET)",
    "HOME": "isolated empty tmp dir (blocks installed-plugin/version-drift leakage)",
    "stripped": "CLAUDE_PROJECT_DIR, CLAUDE_USER_MESSAGE, CLAUDE_PLUGIN_DIR, PILOT_EXECUTOR",
    "runtime_rewrites": "payload cwd -> fresh tmp project; transcript_path -> "
                        "fixtures/transcript.jsonl (the only sanctioned payload edits)",
    "state": "fresh fixture project, NO pre-existing state files (default no-state branch)",
}


def _payloads_from_capture(log_path: Path) -> dict:
    """Pick one verbatim payload per live-capturable surface from the capture log."""
    events: list[tuple[str, dict]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        events.append((rec["event"], json.loads(rec["raw"])))

    def first(name: str, pred=lambda p: True) -> dict:
        for event_name, payload in events:
            if event_name == name and pred(payload):
                return payload
        raise SystemExit(f"capture log has no matching {name} event")

    session_start = first("SessionStart")
    prompt = first("UserPromptSubmit")
    read_pre = first(
        "PreToolUse",
        lambda p: p.get("tool_name") == "Read"
        and "/.agent/" in (p.get("tool_input") or {}).get("file_path", ""),
    )
    edit_post = first("PostToolUse", lambda p: p.get("tool_name") == "Edit")
    stop = first("Stop")

    base = {k: stop[k] for k in ("session_id", "transcript_path", "cwd")}
    pre_compact = dict(base, hook_event_name="PreCompact", trigger="manual",
                       custom_instructions="")
    post_compact = dict(base, hook_event_name="PostCompact",
                        compact_summary="Synthesized compact summary for golden parity: the "
                                        "session read TASK-01 and appended one line to "
                                        "notes.md.")
    return {
        "session_start": session_start,
        "prompt_gate": prompt,
        "prompt_brief": prompt,
        "read_guard": read_pre,
        "graph_sync": edit_post,
        "profile_sync": edit_post,
        "stop_state": stop,
        "pre_compact": pre_compact,
        "post_compact": post_compact,
    }


def _payloads_from_goldens() -> dict:
    return {surface: load_golden(surface)["payload"] for surface in SURFACES}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-log", type=Path, default=None)
    args = parser.parse_args()

    missing = [s["script"] for s in SURFACES.values()
               if not (HOOKS_DIR / s["script"]).is_file()]
    if missing:
        raise SystemExit(f"v6 scripts deleted ({missing}); goldens are frozen — not recording.")

    if args.capture_log:
        payloads = _payloads_from_capture(args.capture_log)
        payload_notes = {s: (SYNTH_NOTE if s in ("pre_compact", "post_compact")
                             else CAPTURE_NOTE) for s in SURFACES}
    else:
        payloads = _payloads_from_goldens()
        payload_notes = {s: load_golden(s)["payload_note"] for s in SURFACES}

    GOLDENS.mkdir(parents=True, exist_ok=True)
    for surface, spec in SURFACES.items():
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = build_project(base)
            home = base / "home"
            home.mkdir()
            env = build_env(home, str(REPO_ROOT))
            proc = run_v6(surface, payloads[surface], project, env)
        golden = {
            "surface": surface,
            "event": spec["event"],
            "v6_script": f"hooks/{spec['script']}",
            "payload_note": payload_notes[surface],
            "payload": payloads[surface],
            "stdout": proc.stdout,
            "exit_code": proc.returncode,
            "env_notes": ENV_NOTES,
        }
        out = GOLDENS / f"{surface}.json"
        out.write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
        print(f"{surface}: exit={proc.returncode} stdout={proc.stdout!r:.70}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
