"""Shared gate for TASK-57 spike hooks.

The spike plugin installs at user scope, so these hooks are registered for
every session. Containment: a hook only acts when BOTH hold —
  (a) the session cwd is inside /tmp/nav-v7-spike (the scratch project), and
  (b) its arm file /tmp/nav-v7-spike/state/arm-<probe>.json exists
      (written by the driving probe script, carrying the per-run sentinel).
Anywhere else it exits 0 silently. Stdlib only.
"""

import json
import os
import sys
from pathlib import Path

# NAV_SPIKE_DIR is honored when the session env carries it; the default is
# the runtime home. The SessionStart command in plugin.json hardcodes the
# default path — keep them in sync if you ever relocate the harness.
SPIKE = Path(os.environ.get("NAV_SPIKE_DIR", "/tmp/nav-v7-spike"))
STATE = SPIKE / "state"


def log(probe: str, obj: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / f"log-{probe}.jsonl", "a") as f:
        f.write(json.dumps(obj) + "\n")


def _allow_and_exit() -> None:
    """Belt-and-suspenders fail-open (GH-27): a probe must never block a real
    tool call. Emitted only for truly unexpected errors — the expected
    containment paths below already exit 0 on their own."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }))
    sys.exit(0)


def gate(probe: str):
    """Return (payload, arm) when armed; exit 0 otherwise."""
    try:
        return _gate_impl(probe)
    except SystemExit:
        raise
    except Exception:
        _allow_and_exit()


def _gate_impl(probe: str):
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cwd = payload.get("cwd") or os.getcwd()
    # macOS: payload cwd arrives realpath'd (/tmp -> /private/tmp), so
    # compare resolved paths instead of raw string prefixes.
    spike_real = SPIKE.resolve()
    try:
        cwd_real = Path(cwd).resolve()
    except Exception:
        sys.exit(0)
    if not (cwd_real == spike_real or spike_real in cwd_real.parents):
        sys.exit(0)
    arm_file = STATE / f"arm-{probe}.json"
    if not arm_file.exists():
        log(probe, {"event": "fired-unarmed",
                    "hook_event": payload.get("hook_event_name")})
        sys.exit(0)
    try:
        arm = json.loads(arm_file.read_text())
    except Exception:
        sys.exit(0)
    log(probe, {"event": "fired-armed",
                "hook_event": payload.get("hook_event_name"),
                "session_id": payload.get("session_id"),
                "transcript_path": payload.get("transcript_path"),
                "arm": arm})
    return payload, arm
