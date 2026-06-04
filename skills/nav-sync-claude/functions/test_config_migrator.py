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


# Every feature / hook block VERSION_CONFIGS knows how to seed, regardless of
# introduction version. Keep in sync with config_migrator.VERSION_CONFIGS.
ALL_FEATURE_BLOCKS = {
    "tom_features",
    "loop_mode",
    "simplification",
    "auto_update",
    "task_mode",
    "knowledge_graph",
    "multi_agent",
    "session_start_hook",
    "compact_hook",
    "task_graph_sync_hook",
    "workflow_state_hook",
    "profile_sync_hook",
    "workflow_enforcer_hook",
    "read_guard_hook",
}

# Blocks introduced strictly after v5.3.0 — the set a real v5.3.0 user is
# missing and should receive on upgrade. tom_features (5.0.0) and loop_mode
# (5.1.0) predate 5.3.0, so that user already has them and they must NOT be
# re-seeded (introduction-version contract).
POST_5_3_0_BLOCKS = ALL_FEATURE_BLOCKS - {"tom_features", "loop_mode"}


class FeatureBlockSeedingTests(unittest.TestCase):
    """wp9/TASK-52: VERSION_CONFIGS seeds every v5.x/v6.x feature + hook block."""

    def test_version_configs_cover_every_known_block(self):
        # Guards against a block being added to the live config but forgotten
        # in the migrator (the original drift this work-package fixed).
        seeded = {
            key
            for blocks in config_migrator.VERSION_CONFIGS.values()
            for key in blocks
        }
        self.assertEqual(seeded, ALL_FEATURE_BLOCKS)

    def test_pre_feature_config_seeds_all_blocks(self):
        # A config older than every feature block receives all of them.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(tmp, {"version": "4.0.0"})

            result = migrate_config(str(cfg_path))

            self.assertTrue(result["success"])
            added = {
                c["key"] for c in result["changes"] if c.get("action") == "added"
            }
            self.assertEqual(added, ALL_FEATURE_BLOCKS)

            on_disk = json.loads(cfg_path.read_text())
            for block in ALL_FEATURE_BLOCKS:
                self.assertIn(block, on_disk)
            # Default shapes are copied verbatim from the live config.
            self.assertEqual(on_disk["read_guard_hook"]["escalate_threshold"], 5)
            self.assertEqual(on_disk["session_start_hook"]["char_budget"], 9500)
            self.assertFalse(on_disk["loop_mode"]["enabled"])

    def test_v5_3_0_config_seeds_only_newer_blocks(self):
        # Introduction-version contract: a v5.3.0 user keeps their pre-5.3.0
        # blocks untouched and receives everything introduced after 5.3.0.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(tmp, {"version": "5.3.0"})

            result = migrate_config(str(cfg_path))

            self.assertTrue(result["success"])
            added = {
                c["key"] for c in result["changes"] if c.get("action") == "added"
            }
            self.assertEqual(added, POST_5_3_0_BLOCKS)

            on_disk = json.loads(cfg_path.read_text())
            self.assertNotIn("tom_features", on_disk)
            self.assertNotIn("loop_mode", on_disk)

    def test_seeding_is_idempotent_on_second_run(self):
        # First migrate brings the config to CURRENT_VERSION; a second run must
        # add nothing and bump nothing.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(tmp, {"version": "4.0.0"})

            migrate_config(str(cfg_path))
            first_pass = json.loads(cfg_path.read_text())

            second = migrate_config(str(cfg_path))

            self.assertTrue(second["success"])
            self.assertEqual(second["changes"], [])
            self.assertEqual(json.loads(cfg_path.read_text()), first_pass)

    def test_existing_block_is_not_overwritten(self):
        # User customisation of an already-present block survives migration.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = _write_config(
                tmp,
                {
                    "version": "4.0.0",
                    "read_guard_hook": {"enabled": False},
                },
            )

            migrate_config(str(cfg_path))

            on_disk = json.loads(cfg_path.read_text())
            self.assertEqual(on_disk["read_guard_hook"], {"enabled": False})


if __name__ == "__main__":
    unittest.main()
