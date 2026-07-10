#!/usr/bin/env python3
"""
Unit tests for settings_merger.py — user-hook preservation guarantees.

Run:  python3 -m unittest skills/nav-init/functions/test_settings_merger
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Allow `python3 -m unittest skills/...` to find the module without an
# __init__.py in functions/.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import settings_merger as sm  # noqa: E402


NAV_FRAGMENT = {
    "$schema": "https://example/schema.json",
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 sample_hook_a.py",
                        "timeout": 10,
                    }
                ]
            }
        ],
        "PreCompact": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 sample_hook_b.py",
                        "timeout": 30,
                    }
                ]
            }
        ],
    },
}


class MergerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.target = self.dir / "settings.json"

    # ---------- helpers ----------

    def _write_settings(self, payload: dict) -> None:
        self.target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_target(self) -> dict:
        return json.loads(self.target.read_text(encoding="utf-8"))

    def _commands_for(self, merged: dict, event: str) -> list[str]:
        out = []
        for entry in merged.get("hooks", {}).get(event, []) or []:
            for h in entry.get("hooks", []) or []:
                if isinstance(h, dict) and h.get("type") == "command":
                    out.append(h.get("command"))
        return out

    # ---------- tests ----------

    def test_fresh_install_no_existing_file(self):
        self.assertFalse(self.target.exists())
        sm.merge(self.target, NAV_FRAGMENT)
        result = self._read_target()
        self.assertEqual(
            self._commands_for(result, "SessionStart"),
            ["python3 sample_hook_a.py"],
        )

    def test_preserves_user_hooks_same_event(self):
        self._write_settings(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {"type": "command", "command": "echo user-hello"}
                            ]
                        }
                    ]
                }
            }
        )
        sm.merge(self.target, NAV_FRAGMENT)
        cmds = self._commands_for(self._read_target(), "SessionStart")
        self.assertIn("echo user-hello", cmds)
        self.assertIn("python3 sample_hook_a.py", cmds)

    def test_preserves_user_hooks_different_event(self):
        self._write_settings(
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {"type": "command", "command": "echo on-stop"}
                            ]
                        }
                    ]
                }
            }
        )
        sm.merge(self.target, NAV_FRAGMENT)
        merged = self._read_target()
        self.assertEqual(self._commands_for(merged, "Stop"), ["echo on-stop"])
        self.assertIn(
            "python3 sample_hook_a.py",
            self._commands_for(merged, "SessionStart"),
        )

    def test_idempotent_rerun(self):
        sm.merge(self.target, NAV_FRAGMENT)
        first = self.target.read_text(encoding="utf-8")
        sm.merge(self.target, NAV_FRAGMENT)
        second = self.target.read_text(encoding="utf-8")
        self.assertEqual(first, second)
        # And the SessionStart entry isn't duplicated
        cmds = self._commands_for(self._read_target(), "SessionStart")
        self.assertEqual(cmds.count("python3 sample_hook_a.py"), 1)

    def test_dedupe_by_command_string(self):
        self._write_settings(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 sample_hook_a.py",
                                }
                            ]
                        }
                    ]
                }
            }
        )
        sm.merge(self.target, NAV_FRAGMENT)
        cmds = self._commands_for(self._read_target(), "SessionStart")
        self.assertEqual(cmds, ["python3 sample_hook_a.py"])

    def test_preserves_top_level_keys(self):
        self._write_settings(
            {
                "permissions": {"allow": ["Bash(*)"]},
                "mcpServers": {"foo": {"command": "foo-server"}},
                "model": "claude-opus-4-7",
                "outputStyle": "compact",
            }
        )
        sm.merge(self.target, NAV_FRAGMENT)
        result = self._read_target()
        self.assertEqual(result["permissions"], {"allow": ["Bash(*)"]})
        self.assertEqual(result["mcpServers"], {"foo": {"command": "foo-server"}})
        self.assertEqual(result["model"], "claude-opus-4-7")
        self.assertEqual(result["outputStyle"], "compact")

    def test_invalid_existing_json_aborts(self):
        self.target.write_text("{ this is not valid json", encoding="utf-8")
        original = self.target.read_text(encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            sm.merge(self.target, NAV_FRAGMENT)
        self.assertEqual(ctx.exception.code, 2)
        # File is untouched
        self.assertEqual(self.target.read_text(encoding="utf-8"), original)

    def test_empty_existing_file_aborts(self):
        self.target.write_text("", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            sm.merge(self.target, NAV_FRAGMENT)
        self.assertEqual(ctx.exception.code, 2)
        # File is untouched
        self.assertEqual(self.target.read_text(encoding="utf-8"), "")

    def test_non_list_hooks_skipped_with_warning(self):
        # Preserve user's good `Stop` entry; fragment has a malformed object
        # for `SessionStart`.
        self._write_settings(
            {
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "echo stop"}]}
                    ]
                }
            }
        )
        broken_fragment = {
            "hooks": {
                "SessionStart": {"not": "a list"},  # type: ignore[dict-item]
                "PreCompact": NAV_FRAGMENT["hooks"]["PreCompact"],
            }
        }
        captured_stderr = io.StringIO()
        with mock.patch("sys.stderr", captured_stderr):
            sm.merge(self.target, broken_fragment)
        merged = self._read_target()
        # Existing Stop preserved
        self.assertEqual(self._commands_for(merged, "Stop"), ["echo stop"])
        # PreCompact merged in
        self.assertIn(
            "python3 sample_hook_b.py",
            self._commands_for(merged, "PreCompact"),
        )
        # SessionStart skipped, not corrupted
        self.assertNotIn("SessionStart", merged.get("hooks", {}))
        # And a warning was emitted
        self.assertIn("SessionStart", captured_stderr.getvalue())
        self.assertIn("not a list", captured_stderr.getvalue())

    def test_dry_run_does_not_write(self):
        self._write_settings({"hooks": {"Stop": []}})
        before = self.target.read_text(encoding="utf-8")
        merged = sm.merge(self.target, NAV_FRAGMENT, dry_run=True)
        after = self.target.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        # But the returned dict has the merge applied
        self.assertIn(
            "python3 sample_hook_a.py",
            self._commands_for(merged, "SessionStart"),
        )

    def test_atomic_write_no_partial_state_on_failure(self):
        # Pre-populate so we can assert preservation on failure
        original_content = json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x"}]}]}},
            indent=2,
        )
        self.target.write_text(original_content, encoding="utf-8")

        boom = RuntimeError("simulated power loss")
        with mock.patch.object(sm.os, "replace", side_effect=boom):
            with self.assertRaises(RuntimeError):
                sm.merge(self.target, NAV_FRAGMENT)

        # File untouched
        self.assertEqual(self.target.read_text(encoding="utf-8"), original_content)
        # No leftover tmp files
        leftovers = list(self.dir.glob("settings.json.*.tmp"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
