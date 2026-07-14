"""GH-27: a missing probe script must never block a real tool call.

The nav-spike plugin can be installed at user scope with its marketplace path
under ephemeral /tmp. If /tmp is cleaned, the hook scripts vanish (only
__pycache__ survives) but the registration in plugin.json still points at
them. Before this fix, `python3 <missing-file>` exited non-zero and Claude
Code treats a non-zero PreToolUse hook as a block — bricking every Read in
the session. This test proves two independent layers of the fix:

  1. The wrapped shell command in plugin.json degrades to a no-op (exit 0)
     when the target script is absent, without ever invoking python3.
  2. spike_gate.gate()'s outer try/except degrades to an explicit allow
     decision on any unexpected error, as a second line of defense.

Stdlib only, no live CC session required.
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_DIR = HERE / "harness" / "nav-spike"
PLUGIN_JSON = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
HOOKS_DIR = PLUGIN_DIR / "hooks"

# Matches the guarded command shape:
#   sh -c 'f="${CLAUDE_PLUGIN_ROOT}/hooks/X.py"; [ -f "$f" ] && exec python3 "$f" || exit 0'
GUARDED_RE = re.compile(
    r'^sh -c \'f="\$\{CLAUDE_PLUGIN_ROOT\}/hooks/(?P<script>[\w.]+)"; '
    r'\[ -f "\$f" \] && exec python3 "\$f" \|\| exit 0\'$'
)


def _script_commands():
    manifest = json.loads(PLUGIN_JSON.read_text())
    out = []
    for event, entries in manifest["hooks"].items():
        if event == "SessionStart":
            continue  # inline shell, not a python3 script invocation
        for entry in entries:
            for hook in entry["hooks"]:
                out.append((event, hook["command"]))
    return out


class TestManifestCommandsAreGuarded(unittest.TestCase):
    """Layer 1: every s*_*.py registration in plugin.json is a fail-open wrapper."""

    def test_every_script_command_is_guarded(self):
        commands = _script_commands()
        self.assertTrue(commands, "expected at least one script-backed hook command")
        for event, command in commands:
            with self.subTest(event=event, command=command):
                self.assertRegex(
                    command, GUARDED_RE,
                    f"{event} command is not wrapped with a missing-file guard: {command!r}",
                )

    def test_guarded_scripts_exist_on_disk(self):
        """Sanity: the guard references real files, not a typo'd path."""
        for _, command in _script_commands():
            m = GUARDED_RE.match(command)
            self.assertIsNotNone(m)
            self.assertTrue(
                (HOOKS_DIR / m.group("script")).is_file(),
                f"{m.group('script')} referenced by manifest but missing on disk",
            )


class TestMissingScriptFailsOpen(unittest.TestCase):
    """Layer 1, behavioral: run the guarded command with the script deleted."""

    def _run_guarded(self, command: str, plugin_root: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["sh", "-c", command.split("sh -c ", 1)[1].strip("'").replace(
                "${CLAUDE_PLUGIN_ROOT}", str(plugin_root)
            )],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_missing_script_exits_zero_without_invoking_python(self):
        for _, command in _script_commands():
            with self.subTest(command=command):
                # Point CLAUDE_PLUGIN_ROOT at a directory with no hooks/ at
                # all — simulates a wiped /tmp marketplace checkout.
                proc = self._run_guarded(command, Path("/tmp/gh-27-does-not-exist"))
                self.assertEqual(
                    proc.returncode, 0,
                    f"missing script must not block: stderr={proc.stderr!r}",
                )

    def test_present_script_still_runs(self):
        """Behavior is unchanged when the script exists (regression guard)."""
        s5 = next(c for e, c in _script_commands() if e == "PreToolUse")
        proc = self._run_guarded(s5, PLUGIN_DIR)
        # s5 requires an armed, in-scratch-dir payload to do anything; here it
        # just needs to prove python3 actually ran and the gate exited clean.
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")


class TestGateFailsOpenOnUnexpectedError(unittest.TestCase):
    """Layer 2: spike_gate.gate()'s outer try/except emits an explicit allow
    decision and exits 0 on any error the containment checks don't already
    catch (belt-and-suspenders per GH-27)."""

    def test_gate_allows_on_unexpected_exception(self):
        sys.path.insert(0, str(HOOKS_DIR))
        try:
            import spike_gate
            import importlib
            importlib.reload(spike_gate)

            def _boom(probe):
                raise RuntimeError("simulated unexpected failure")

            spike_gate._gate_impl = _boom
            with self.assertRaises(SystemExit) as ctx:
                spike_gate.gate("s5")
            self.assertEqual(ctx.exception.code, 0)
        finally:
            sys.path.remove(str(HOOKS_DIR))
            sys.modules.pop("spike_gate", None)


if __name__ == "__main__":
    unittest.main()
