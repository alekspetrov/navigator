#!/usr/bin/env python3
"""
Unit tests for migrate_hooks_out_of_settings.py.

Covers:
- Removes Navigator hook entries (matched by command path containing hooks/
  AND a known Navigator hook basename).
- Leaves user entries with unrelated commands untouched.
- Idempotent: re-running on a migrated file is a no-op.

Run: python3 -m unittest \
        skills/nav-upgrade/functions/test_migrate_hooks_out_of_settings
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import migrate_hooks_out_of_settings as mig  # noqa: E402


def _nav_entry(cmd: str, matcher: str | None = None) -> dict:
    entry: dict = {"hooks": [{"type": "command", "command": cmd, "timeout": 5}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return entry


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "settings.json"

    def _write(self, payload: dict) -> None:
        self.target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read(self) -> dict:
        return json.loads(self.target.read_text(encoding="utf-8"))

    # ---------- behavior tests ----------

    def test_removes_navigator_entries(self):
        self._write({
            "hooks": {
                "SessionStart": [
                    _nav_entry(
                        "python3 ${CLAUDE_PLUGIN_DIR}/hooks/nav_session_start.py"
                    ),
                ],
                "PostToolUse": [
                    _nav_entry(
                        "python3 ${CLAUDE_PROJECT_DIR}/hooks/token_monitor.py",
                        matcher="Edit|Write|Bash",
                    ),
                ],
            }
        })
        summary = mig.migrate(self.target)
        self.assertTrue(summary["modified"])
        self.assertEqual(len(summary["removed"]), 2)
        # Both events were emptied → hooks key dropped entirely
        self.assertNotIn("hooks", self._read())
        # Backup exists
        self.assertIsNotNone(summary["backup_path"])
        self.assertTrue(Path(summary["backup_path"]).is_file())

    def test_leaves_user_entries_untouched(self):
        user_cmd = "echo hello-from-user"
        self._write({
            "hooks": {
                "SessionStart": [
                    _nav_entry(
                        "python3 ${CLAUDE_PLUGIN_DIR}/hooks/nav_session_start.py"
                    ),
                    _nav_entry(user_cmd),
                ],
                "Stop": [
                    _nav_entry("/usr/local/bin/notify-on-stop"),
                ],
            },
            "permissions": {"allow": ["Bash(*)"]},
        })
        summary = mig.migrate(self.target)
        self.assertTrue(summary["modified"])
        result = self._read()
        # Top-level non-hooks keys preserved
        self.assertEqual(result["permissions"], {"allow": ["Bash(*)"]})
        # User SessionStart entry survives
        ss = result["hooks"]["SessionStart"]
        self.assertEqual(len(ss), 1)
        self.assertEqual(ss[0]["hooks"][0]["command"], user_cmd)
        # User Stop entry survives
        self.assertEqual(result["hooks"]["Stop"][0]["hooks"][0]["command"],
                         "/usr/local/bin/notify-on-stop")
        # Only the nav_session_start command was removed
        self.assertEqual(len(summary["removed"]), 1)
        self.assertIn("nav_session_start", summary["removed"][0][1])

    def test_idempotent_on_rerun(self):
        self._write({
            "hooks": {
                "SessionStart": [
                    _nav_entry(
                        "python3 ${CLAUDE_PLUGIN_DIR}/hooks/nav_session_start.py"
                    ),
                ],
            }
        })
        first = mig.migrate(self.target)
        self.assertTrue(first["modified"])
        after_first = self.target.read_text(encoding="utf-8")
        second = mig.migrate(self.target)
        self.assertFalse(second["modified"])
        self.assertIsNone(second["backup_path"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), after_first)

    def test_does_not_match_unrelated_command_with_substring(self):
        # User has a script that happens to mention "token_monitor" but is
        # NOT in a hooks/ directory — must be preserved.
        self._write({
            "hooks": {
                "PostToolUse": [
                    _nav_entry("/opt/me/scripts/token_monitor.sh"),
                    _nav_entry(
                        "python3 ${CLAUDE_PLUGIN_DIR}/hooks/token_monitor.py",
                        matcher="Edit|Write|Bash",
                    ),
                ],
            }
        })
        summary = mig.migrate(self.target)
        self.assertTrue(summary["modified"])
        result = self._read()
        post = result["hooks"]["PostToolUse"]
        # Only the hooks/token_monitor.py one was removed
        self.assertEqual(len(post), 1)
        self.assertEqual(
            post[0]["hooks"][0]["command"], "/opt/me/scripts/token_monitor.sh"
        )

    def test_missing_file_is_noop(self):
        # Target does not exist
        self.assertFalse(self.target.exists())
        summary = mig.migrate(self.target)
        self.assertFalse(summary["modified"])
        self.assertFalse(self.target.exists())

    def test_dry_run_does_not_write(self):
        self._write({
            "hooks": {
                "SessionStart": [
                    _nav_entry(
                        "python3 ${CLAUDE_PLUGIN_DIR}/hooks/nav_session_start.py"
                    ),
                ],
            }
        })
        before = self.target.read_text(encoding="utf-8")
        summary = mig.migrate(self.target, dry_run=True)
        self.assertTrue(summary["modified"])
        # Nothing written to disk
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)
        # No backup written either
        self.assertIsNone(summary["backup_path"])

    def test_all_navigator_basenames_caught(self):
        # Build one entry per known basename and confirm all are removed.
        cmds = [
            f"python3 ${{CLAUDE_PLUGIN_DIR}}/hooks/{name}.py"
            for name in mig.NAV_HOOK_NAMES
        ]
        self._write({
            "hooks": {
                "PostToolUse": [_nav_entry(c) for c in cmds],
            }
        })
        summary = mig.migrate(self.target)
        self.assertEqual(len(summary["removed"]), len(mig.NAV_HOOK_NAMES))
        self.assertNotIn("hooks", self._read())


if __name__ == "__main__":
    unittest.main()
