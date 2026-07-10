"""Schema validation for harness-conformance results files (TASK-58).

Stdlib unittest (TASK-45 pattern), no live CC needed. Validates EVERY
results/cc-<version>.json: required keys, six probes present, version and
date formats, filename/content consistency. Runs in `make test` via
per-directory discovery:

    cd tests/harness-conformance && python3 -m unittest discover -p "test_*.py"
"""

import datetime
import json
import re
import unittest
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FILENAME_RE = re.compile(r"^cc-(\d+\.\d+\.\d+)\.json$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MEMORY_RE = re.compile(r"^mem-\d{3}$")

REQUIRED_TOP_KEYS = {"cc_version", "date", "recorded_by", "probes"}
REQUIRED_PROBES = {"s1", "s2", "s3", "s4", "s5", "s6"}
REQUIRED_PROBE_KEYS = {"pass", "channel_works", "verdict_file", "memory", "summary"}


def results_files():
    if not RESULTS_DIR.is_dir():
        return []
    return sorted(RESULTS_DIR.glob("*.json"))


class TestResultsSchema(unittest.TestCase):

    def test_results_dir_has_at_least_one_file(self):
        """The suite ships with a checked-in results file; zero files means
        the conformance evidence was deleted, not merely outdated."""
        self.assertTrue(results_files(),
                        f"no results files found under {RESULTS_DIR}")

    def test_every_results_file_matches_schema(self):
        for path in results_files():
            with self.subTest(file=path.name):
                self._validate_file(path)

    def _validate_file(self, path: Path):
        m = FILENAME_RE.match(path.name)
        self.assertIsNotNone(
            m, f"{path.name}: filename must match cc-<major.minor.patch>.json")
        filename_version = m.group(1)

        data = json.loads(path.read_text())
        self.assertIsInstance(data, dict, f"{path.name}: top level must be an object")

        missing = REQUIRED_TOP_KEYS - set(data)
        self.assertFalse(missing, f"{path.name}: missing top-level keys {sorted(missing)}")

        # cc_version: bare version token, consistent with the filename
        # (produced by `claude --version | awk '{print $1}'`).
        cc_version = data["cc_version"]
        self.assertIsInstance(cc_version, str)
        self.assertRegex(cc_version, VERSION_RE,
                         f"{path.name}: cc_version must be major.minor.patch")
        self.assertEqual(cc_version, filename_version,
                         f"{path.name}: cc_version does not match filename")

        # date: YYYY-MM-DD, actually parseable
        self.assertIsInstance(data["date"], str)
        try:
            datetime.datetime.strptime(data["date"], "%Y-%m-%d")
        except ValueError:
            self.fail(f"{path.name}: date {data['date']!r} is not YYYY-MM-DD")

        self.assertIsInstance(data["recorded_by"], str)
        self.assertTrue(data["recorded_by"].strip(),
                        f"{path.name}: recorded_by must be non-empty")

        probes = data["probes"]
        self.assertIsInstance(probes, dict, f"{path.name}: probes must be an object")
        self.assertEqual(set(probes), REQUIRED_PROBES,
                         f"{path.name}: probes must be exactly s1..s6")

        for name, probe in probes.items():
            self._validate_probe(path.name, name, probe)

    def _validate_probe(self, filename: str, name: str, probe):
        ctx = f"{filename}: probes.{name}"
        self.assertIsInstance(probe, dict, f"{ctx} must be an object")
        missing = REQUIRED_PROBE_KEYS - set(probe)
        self.assertFalse(missing, f"{ctx}: missing keys {sorted(missing)}")

        self.assertIsInstance(probe["pass"], bool, f"{ctx}.pass must be a bool")
        self.assertIsInstance(probe["channel_works"], bool,
                              f"{ctx}.channel_works must be a bool")
        self.assertIsInstance(probe["verdict_file"], str,
                              f"{ctx}.verdict_file must be a string")
        self.assertTrue(probe["verdict_file"].strip(),
                        f"{ctx}.verdict_file must be non-empty")
        self.assertIsInstance(probe["memory"], str, f"{ctx}.memory must be a string")
        self.assertRegex(probe["memory"], MEMORY_RE,
                         f"{ctx}.memory must look like mem-0XX")
        self.assertIsInstance(probe["summary"], str, f"{ctx}.summary must be a string")
        self.assertTrue(probe["summary"].strip(),
                        f"{ctx}.summary must be non-empty")


if __name__ == "__main__":
    unittest.main()
