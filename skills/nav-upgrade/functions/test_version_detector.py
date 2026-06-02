#!/usr/bin/env python3
"""Unit tests for version_detector's current-version parsing and cache fallback.

Guards two MED findings from audit wf_0dc1b9ce-7d8:
  - get_current_version() parsed a single line of `claude plugin list`, but the
    name and version live on separate lines, so it never matched.
  - get_plugin_json_version() used static install paths that never matched the
    version-keyed cache layout, so the fallback always returned None.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import version_detector as vd  # noqa: E402


# Real-shape `claude plugin list` output: name and version on separate lines.
PLUGIN_LIST_FIXTURE = """\
Installed plugins:

❯ navigator@navigator-marketplace
  Version: 6.15.6
  Scope: user
  Status: ✔ enabled

❯ some-other-plugin@other-marketplace
  Version: 1.2.3
  Scope: user
  Status: ✔ enabled
"""


class GetCurrentVersionTest(unittest.TestCase):
    def _run_with_stdout(self, stdout):
        fake = mock.Mock(stdout=stdout, returncode=0)
        with mock.patch.object(vd.subprocess, "run", return_value=fake):
            return vd.get_current_version()

    def test_parses_version_from_multiline_block(self):
        self.assertEqual(self._run_with_stdout(PLUGIN_LIST_FIXTURE), "6.15.6")

    def test_does_not_grab_following_plugin_version(self):
        # The navigator block's version must win, not the next plugin's 1.2.3.
        self.assertEqual(self._run_with_stdout(PLUGIN_LIST_FIXTURE), "6.15.6")

    def test_missing_navigator_returns_none(self):
        other = "❯ other-plugin@x\n  Version: 1.0.0\n  Scope: user\n"
        self.assertIsNone(self._run_with_stdout(other))

    def test_claude_not_installed_returns_none(self):
        with mock.patch.object(vd.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIsNone(vd.get_current_version())


class GetPluginJsonVersionTest(unittest.TestCase):
    def _build_cache(self, home: Path, versions):
        base = home / ".claude" / "plugins" / "cache" / "navigator-marketplace" / "navigator"
        for v in versions:
            plugin_dir = base / v / ".claude-plugin"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.json").write_text(json.dumps({"version": v}))

    def test_resolves_highest_version_from_cache(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            # 6.10.0 must beat 6.9.0 numerically (not lexically).
            self._build_cache(home, ["6.9.0", "6.10.0", "6.15.6"])
            with mock.patch.object(vd.Path, "home", lambda: home):
                self.assertEqual(vd.get_plugin_json_version(), "6.15.6")

    def test_returns_none_when_cache_absent(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            with mock.patch.object(vd.Path, "home", lambda: home):
                self.assertIsNone(vd.get_plugin_json_version())


if __name__ == "__main__":
    unittest.main()
