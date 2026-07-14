"""S6 — CLAUDE_PLUGIN_ROOT env-binding re-check (mem-036).

Live observable: the SessionStart manifest hook appended ROOT=<path> lines to
state/log-s6.txt during every probe session driven in the scratch project.
Plus the mem-036 three-variant shell test of the exact manifest command shape:
env unset, empty, explicitly bound.

Known CC 2.1.205 behavior (mem-055): ROOT binds to the marketplace SOURCE
path for dir-source installs; unset is a LOUD failure, not a silent no-op.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import SPIKE, STATE, preflight, write_verdict, run_claude

preflight()

log_file = STATE / "log-s6.txt"
if not log_file.exists() or not log_file.read_text().strip():
    # Ensure at least one live session has run in the scratch project.
    run_claude("Say the word ok and nothing else.")

lines = [l for l in log_file.read_text().splitlines() if l.strip()] \
    if log_file.exists() else []
root_values = [l.split("ROOT=", 1)[1].split(" PWD=")[0] for l in lines
               if l.startswith("ROOT=")]
live_bound = [v for v in root_values if v.strip()]
points_into_install = any("plugin" in v or "marketplace" in v.lower()
                          for v in live_bound)

# mem-036 three-variant shell test against the real python-hook command shape.
manifest = json.loads((SPIKE / "marketplace" / "nav-spike" / ".claude-plugin"
                       / "plugin.json").read_text())
cmd = manifest["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
variants = {}
for name, env_extra in (
    ("unset", {"CLAUDE_PLUGIN_ROOT": None}),
    ("empty", {"CLAUDE_PLUGIN_ROOT": ""}),
    ("bound", {"CLAUDE_PLUGIN_ROOT": str(live_bound[-1]) if live_bound else ""}),
):
    env = dict(os.environ)
    for k, v in env_extra.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    proc = subprocess.run(["sh", "-c", cmd], env=env, capture_output=True,
                          text=True, input="{}", timeout=15)
    variants[name] = {"exit_code": proc.returncode,
                      "stdout": proc.stdout[:200], "stderr": proc.stderr[:300],
                      "silent_noop": proc.returncode == 0 and not proc.stdout
                      and not proc.stderr}

write_verdict("s6", {
    "channel": "${CLAUDE_PLUGIN_ROOT} manifest binding",
    "live_log_lines": lines[-10:],
    "live_bound_values": sorted(set(live_bound)),
    "points_into_install": points_into_install,
    "shell_variants": variants,
    "pass": bool(live_bound and points_into_install),
})
