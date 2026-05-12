#!/usr/bin/env python3
"""
Tests for config_migrator.

Focus areas (regression coverage for issue #7):
- CURRENT_VERSION is loaded from .claude-plugin/plugin.json (not hardcoded).
- Migration is direction-aware: configs newer than CURRENT_VERSION are NOT
  downgraded.
- Older configs still receive missing sections and a version bump.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Make sibling module importable when run via `python3 -m unittest`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config_migrator  # noqa: E402
from config_migrator import (  # noqa: E402
    _read_plugin_version,
    migrate_config,
    version_less_than,
)


def _write_config(tmpdir: Path, payload: dict) -> Path:
    path = tmpdir / ".nav-config.json"
    path.write_text(json.dumps(payload))
    return path


class ReadPluginVersionTests(unittest.TestCase):
    def test_reads_version_from_plugin_json(self):
        repo_root = Path(__file__).resolve().parents[3]
        plugin_json = repo_root / ".claude-plugin" / "plugin.json"
        self.assertTrue(plugin_json.is_file(), f"missing {plugin_json}")

        expected = json.loads(plugin_json.read_text())["version"]
        self.assertEqual(_read_plugin_version(), expected)

    def test_module_current_version_matches_plugin_json(self):
        repo_root = Path(__file__).resolve().parents[3]
        plugin_json = repo_root / ".claude-plugin" / "plugin.json"
        expected = json.loads(plugin_json.read_text())["version"]
        self.assertEqual(config_migrator.CURRENT_VERSION, expected)


class MigrateConfigDirectionTests(unittest.TestCase):
    def test_newer_config_is_not_downgraded(self):
        # Simulate a user whose installed config is ahead of the plugin's
        # CURRENT_VERSION. This is the bug from issue #7: previously the
        # `!=` comparison rewrote `version` to the (stale) CURRENT_VERSION.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            future = "999.0.0"
            cfg_path = _write_config(tmp, {"version": future})

            result = migrate_config(str(cfg_path))

            self.assertTrue(result["success"])
            # No version-update change should have been recorded.
            version_updates = [
                c for c in result["changes"]
                if c.get("action") == "updated" and c.get("key") == "version"
            ]
            self.assertEqual(version_updates, [])

            # On-disk file must still record the newer version.
            on_disk = json.loads(cfg_path.read_text())
            self.assertEqual(on_disk["version"], future)
            self.assertEqual(result["new_version"], future)

    def test_equal_version_is_noop_for_version_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(
                tmp, {"version": config_migrator.CURRENT_VERSION}
            )

            result = migrate_config(str(cfg_path))

            self.assertTrue(result["success"])
            version_updates = [
                c for c in result["changes"]
                if c.get("action") == "updated" and c.get("key") == "version"
            ]
            self.assertEqual(version_updates, [])

    def test_older_config_is_upgraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(tmp, {"version": "1.0.0"})

            result = migrate_config(str(cfg_path))

            self.assertTrue(result["success"])
            version_updates = [
                c for c in result["changes"]
                if c.get("action") == "updated" and c.get("key") == "version"
            ]
            self.assertEqual(len(version_updates), 1)
            self.assertEqual(version_updates[0]["old"], "1.0.0")
            self.assertEqual(
                version_updates[0]["new"], config_migrator.CURRENT_VERSION
            )

            on_disk = json.loads(cfg_path.read_text())
            self.assertEqual(
                on_disk["version"], config_migrator.CURRENT_VERSION
            )

    def test_older_config_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(tmp, {"version": "1.0.0"})

            result = migrate_config(str(cfg_path), dry_run=True)

            self.assertTrue(result["success"])
            self.assertTrue(any(
                c.get("action") == "updated" and c.get("key") == "version"
                for c in result["changes"]
            ))
            # File untouched.
            on_disk = json.loads(cfg_path.read_text())
            self.assertEqual(on_disk, {"version": "1.0.0"})


class VersionLessThanSanityTests(unittest.TestCase):
    def test_basic_orderings(self):
        self.assertTrue(version_less_than("1.0.0", "2.0.0"))
        self.assertTrue(version_less_than("5.7.0", "6.12.0"))
        self.assertFalse(version_less_than("6.12.0", "5.7.0"))
        self.assertFalse(version_less_than("6.12.0", "6.12.0"))


if __name__ == "__main__":
    unittest.main()
