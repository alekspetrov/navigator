#!/usr/bin/env python3
"""
PostToolUse output-channel probe (v6.12.1).

Purpose: empirically determine whether stderr OR stdout from a PostToolUse
Bash hook surfaces to the model's visible context. mem-035 confirmed that
both channels are silent on PreToolUse; PostToolUse is the open question
that gates Opp 5 (commit archival reminder) design.

Probe behavior: on any Bash PostToolUse event, emit a distinct sentinel
string to BOTH stderr and stdout. Observer checks which (if either) appears
in the assistant's context on the next exchange.

This is a probe, not the final Opp 5 implementation. After the probe channel
is confirmed, this file will be replaced with the full commit-reminder logic
in v6.12.2.

Exit: 0 always (never blocks). PostToolUse fires AFTER the command runs;
blocking is semantically wrong.
"""
from __future__ import annotations

import json
import sys

SENTINEL_STDERR = "NAV-PROBE-POSTTOOLUSE-STDERR-VISIBLE"
SENTINEL_STDOUT = "NAV-PROBE-POSTTOOLUSE-STDOUT-VISIBLE"


def main() -> int:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    # Only probe on Bash events to avoid noise on Edit/Write.
    if data.get("tool_name") != "Bash":
        return 0

    sys.stderr.write(SENTINEL_STDERR + "\n")
    print(SENTINEL_STDOUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
