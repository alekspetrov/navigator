#!/usr/bin/env python3
"""Tests for auto_updater.py"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Import module for direct testing
sys.path.insert(0, str(Path(__file__).parent))
import auto_updater
from auto_updater import (
    compare_versions,
    get_current_version,
    reinstall_plugin,
)


class TestCompareVersions(unittest.TestCase):
    """Tests for semantic version comparison.

    Convention: -1 if current < latest, 0 if equal, 1 if current > latest.
    """

    def test_current_older_negative(self):
        self.assertEqual(compare_versions("6.15.5", "6.15.6"), -1)

    def test_equal_zero(self):
        self.assertEqual(compare_versions("6.15.6", "6.15.6"), 0)

    def test_current_newer_positive(self):
        self.assertEqual(compare_versions("6.16.0", "6.15.6"), 1)

    def test_major_difference(self):
        self.assertEqual(compare_versions("5.0.0", "6.0.0"), -1)
        self.assertEqual(compare_versions("7.0.0", "6.0.0"), 1)

    def test_uneven_length_equal(self):
        """'6.15' is padded to '6.15.0' and equals '6.15.0'."""
        self.assertEqual(compare_versions("6.15", "6.15.0"), 0)

    def test_uneven_length_older(self):
        """'6.15' (-> 6.15.0) is older than '6.15.2'."""
        self.assertEqual(compare_versions("6.15", "6.15.2"), -1)

    def test_uneven_length_newer(self):
        """'6.16' (-> 6.16.0) is newer than '6.15.9'."""
        self.assertEqual(compare_versions("6.16", "6.15.9"), 1)


class TestGetCurrentVersion(unittest.TestCase):
    """Tests for parsing version out of `claude plugin list` output."""

    PLUGIN_LIST_OUTPUT = (
        "Installed plugins:\n"
        "❯ navigator@navigator-marketplace\n"
        "  Version: 6.15.6\n"
        "  Scope: user\n"
        "  Status: ✔ enabled\n"
    )

    NO_NAVIGATOR_OUTPUT = (
        "Installed plugins:\n"
        "❯ other-plugin@some-marketplace\n"
        "  Version: 1.2.3\n"
        "  Scope: user\n"
    )

    @patch("auto_updater.subprocess.run")
    def test_parses_navigator_version(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout=self.PLUGIN_LIST_OUTPUT, returncode=0, stderr=""
        )
        self.assertEqual(get_current_version(), "6.15.6")

    @patch("auto_updater.subprocess.run")
    def test_returns_none_without_navigator(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout=self.NO_NAVIGATOR_OUTPUT, returncode=0, stderr=""
        )
        self.assertIsNone(get_current_version())

    @patch("auto_updater.subprocess.run")
    def test_handles_version_prefix_v(self, mock_run):
        """A leading 'v' on the version is stripped by the regex."""
        out = (
            "❯ navigator@navigator-marketplace\n"
            "  Version: v6.10.1\n"
        )
        mock_run.return_value = SimpleNamespace(stdout=out, returncode=0, stderr="")
        self.assertEqual(get_current_version(), "6.10.1")


class TestReinstallPlugin(unittest.TestCase):
    """Tests for the uninstall/add/install fallback flow.

    A failed uninstall must abort before install runs (no inconsistent
    mid-state where the plugin is removed but never reinstalled).
    """

    @patch("auto_updater.time.sleep", return_value=None)
    @patch("auto_updater.subprocess.run")
    def test_failed_uninstall_aborts_before_install(self, mock_run, _mock_sleep):
        """First call (uninstall) fails -> install is never invoked."""

        def fake_run(cmd, *args, **kwargs):
            # cmd is the argv list, e.g. ['claude', 'plugin', 'uninstall', ...]
            if "uninstall" in cmd:
                return SimpleNamespace(returncode=1, stdout="", stderr="boom")
            # Any other call would indicate the flow wrongly continued.
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_run

        result = reinstall_plugin()

        self.assertFalse(result["success"])
        self.assertIn("Uninstall failed", result["error"])
        self.assertEqual(result["method"], "reinstall")

        # Only the uninstall call should have happened.
        self.assertEqual(mock_run.call_count, 1)
        invoked_cmds = [call.args[0] for call in mock_run.call_args_list]
        # install must NOT appear in any invoked command.
        self.assertFalse(
            any("install" in cmd and "uninstall" not in cmd for cmd in invoked_cmds),
            "install was invoked despite a failed uninstall",
        )

    @patch("auto_updater.time.sleep", return_value=None)
    @patch("auto_updater.subprocess.run")
    def test_failed_install_reported(self, mock_run, _mock_sleep):
        """Uninstall + add succeed but install fails -> success False reported."""

        def fake_run(cmd, *args, **kwargs):
            if "uninstall" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "add" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "install" in cmd:
                return SimpleNamespace(returncode=1, stdout="", stderr="install boom")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run.side_effect = fake_run

        result = reinstall_plugin()

        self.assertFalse(result["success"])
        self.assertEqual(result["method"], "reinstall")
        # All three steps run: uninstall, add, install.
        self.assertEqual(mock_run.call_count, 3)

    @patch("auto_updater.time.sleep", return_value=None)
    @patch("auto_updater.subprocess.run")
    def test_successful_reinstall(self, mock_run, _mock_sleep):
        """All three steps succeed -> success True."""
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")

        result = reinstall_plugin()

        self.assertTrue(result["success"])
        self.assertEqual(result["method"], "reinstall")
        self.assertEqual(mock_run.call_count, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
