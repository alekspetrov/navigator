#!/usr/bin/env python3
"""Golden parity suite — v6 hook scripts vs the v7 dispatcher (TASK-61 Phase 0).

For every corpus case (goldens/<surface>.json) this suite runs, in a FRESH tmp project
built from fixtures/ (TASK-45 subprocess-against-tmp-project template):

  1. the v6 hook script  — regression lock proving the golden still reflects v6 truth
     (auto-skipped once Phase 7 deletes the v6 sources; the golden files stay frozen), and
  2. python3 hooks/nav_dispatch.py <event>  — asserting dispatcher stdout + exit code
     BYTE-MATCH the recorded golden.

Env variants (mem-036: an unset env var once made every hook silently no-op for two
releases): every dispatcher case runs TWICE — CLAUDE_PLUGIN_ROOT set to the repo root AND
unset — and both must byte-match the same golden. Under the new sh-guard manifest, unset
only changes WHICH dispatcher file the manifest `sh -c` line executes (the installed-
marketplace fallback path; a missing file no-ops at the sh level, before python runs).
Once nav_dispatch.py is invoked, its output must not depend on the variable; ops resolve
the plugin dir by file-relative fallback. HOME is isolated so the ~/.claude fallbacks
cannot resolve to a machine-local install.

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LOUD COMMENT — READ BEFORE TOUCHING THE DECORATORS                                  │
│                                                                                     │
│ The @unittest.expectedFailure decorators below mark surfaces whose op has NOT been  │
│ ported yet (the dispatcher currently emits nothing for them). They flip to real     │
│ assertions as each port lands; port agents remove the decorator for their surfaces  │
│ in the SAME commit as the op. Never "fix" a failure by editing a golden — goldens   │
│ are recorded v6 truth. The only sanctioned dispatcher/v6 difference is internal     │
│ state-file paths (schema-2 runtime state vs v6 per-hook files).                     │
│                                                                                     │
│ Three dispatcher cases (prompt_gate, prompt_brief, read_guard) are NOT decorated:   │
│ their goldens are silent (v6 emitted nothing on the common path), so the assertion  │
│ already holds pre-port and must KEEP holding after the port.                        │
│                                                                                     │
│ Note for the five `{}` goldens (graph_sync, profile_sync, stop_state, pre_compact,  │
│ post_compact): v6 side-effect hooks print a bare `{}` JSON doc; the TASK-60 runtime │
│ prints nothing for silent ops. Ports must reproduce the `{}` doc (or get that delta │
│ explicitly sanctioned in the task doc and re-record) — do not silently accept it.   │
└─────────────────────────────────────────────────────────────────────────────────────┘

Run:  cd tests/golden && python3 -m unittest discover -p "test_*.py" -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import (  # noqa: E402
    HOOKS_DIR, REPO_ROOT, SURFACES, build_env, build_project, load_golden,
    run_dispatcher, run_v6,
)


class _CorpusCase(unittest.TestCase):
    """Shared harness: fresh project + isolated HOME per run (TASK-45 template)."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        project = build_project(base)
        home = base / "home"
        home.mkdir()
        return project, home

    def assert_v6_matches_golden(self, surface: str) -> None:
        script = HOOKS_DIR / SURFACES[surface]["script"]
        if not script.is_file():
            self.skipTest(f"{script.name} deleted (Phase 7); golden is frozen v6 truth")
        golden = load_golden(surface)
        project, home = self._fresh()
        proc = run_v6(surface, golden["payload"], project, build_env(home, str(REPO_ROOT)))
        self.assertEqual(proc.stdout, golden["stdout"],
                         f"v6 {script.name} stdout drifted from recorded golden")
        self.assertEqual(proc.returncode, golden["exit_code"],
                         f"v6 {script.name} exit code drifted from recorded golden")

    def assert_dispatcher_matches_golden(self, surface: str) -> None:
        golden = load_golden(surface)
        event = SURFACES[surface]["event"]
        for label, plugin_root in (("set", str(REPO_ROOT)), ("unset", None)):
            project, home = self._fresh()
            proc = run_dispatcher(event, golden["payload"], project,
                                  build_env(home, plugin_root))
            self.assertEqual(
                proc.stdout, golden["stdout"],
                f"dispatcher stdout != golden for {surface} (CLAUDE_PLUGIN_ROOT {label})")
            self.assertEqual(
                proc.returncode, golden["exit_code"],
                f"dispatcher exit != golden for {surface} (CLAUDE_PLUGIN_ROOT {label})")


class V6GoldenRegressionTest(_CorpusCase):
    """Leg 1 — the v6 scripts still produce the recorded goldens (recording sanity)."""

    def test_session_start(self):
        self.assert_v6_matches_golden("session_start")

    def test_prompt_gate(self):
        self.assert_v6_matches_golden("prompt_gate")

    def test_prompt_brief(self):
        self.assert_v6_matches_golden("prompt_brief")

    def test_read_guard(self):
        self.assert_v6_matches_golden("read_guard")

    def test_graph_sync(self):
        self.assert_v6_matches_golden("graph_sync")

    def test_profile_sync(self):
        self.assert_v6_matches_golden("profile_sync")

    def test_stop_state(self):
        self.assert_v6_matches_golden("stop_state")

    def test_pre_compact(self):
        self.assert_v6_matches_golden("pre_compact")

    def test_post_compact(self):
        self.assert_v6_matches_golden("post_compact")


class DispatcherParityTest(_CorpusCase):
    """Leg 2 — nav_dispatch.py byte-matches the goldens (the TASK-61 gate)."""

    # Phase 1 port landed (ops/session_start.py) — real assertion.
    def test_session_start(self):
        self.assert_dispatcher_matches_golden("session_start")

    # Silent golden — already-green parity lock, NOT pre-port slack. Keep green.
    def test_prompt_gate(self):
        self.assert_dispatcher_matches_golden("prompt_gate")

    # Silent golden — already-green parity lock, NOT pre-port slack. Keep green.
    def test_prompt_brief(self):
        self.assert_dispatcher_matches_golden("prompt_brief")

    # Silent golden — already-green parity lock, NOT pre-port slack. Keep green.
    def test_read_guard(self):
        self.assert_dispatcher_matches_golden("read_guard")

    # Phase 3 port landed (ops/graph_sync.py) — real assertion.
    def test_graph_sync(self):
        self.assert_dispatcher_matches_golden("graph_sync")

    # Phase 3 port landed (ops/profile_sync.py) — real assertion.
    def test_profile_sync(self):
        self.assert_dispatcher_matches_golden("profile_sync")

    # Phase 5 port landed (ops/stop_state.py) — real assertion.
    def test_stop_state(self):
        self.assert_dispatcher_matches_golden("stop_state")

    # Phase 2 port landed (ops/compact_marker.py) — real assertion.
    def test_pre_compact(self):
        self.assert_dispatcher_matches_golden("pre_compact")

    # Phase 2 port landed (ops/compact_marker.py) — real assertion.
    def test_post_compact(self):
        self.assert_dispatcher_matches_golden("post_compact")


class CorpusCoherenceTest(unittest.TestCase):
    """Surfaces sharing one (event, payload) must record identical stdout + exit.

    The dispatcher emits ONE document per event, but the corpus asserts per surface;
    if two same-event same-payload goldens disagreed, their dispatcher assertions
    would be unsatisfiable simultaneously. This meta-test keeps the corpus coherent
    (guards future re-recordings and payload edits).
    """

    def test_shared_payload_goldens_agree(self):
        groups: dict[tuple, list] = {}
        for surface, spec in SURFACES.items():
            golden = load_golden(surface)
            key = (spec["event"], repr(sorted(golden["payload"].items())))
            groups.setdefault(key, []).append((surface, golden))
        for (event, _), members in groups.items():
            first_surface, first = members[0]
            for surface, golden in members[1:]:
                self.assertEqual(
                    golden["stdout"], first["stdout"],
                    f"{event}: {surface} and {first_surface} share a payload but "
                    f"recorded different stdout — corpus is incoherent")
                self.assertEqual(
                    golden["exit_code"], first["exit_code"],
                    f"{event}: {surface} and {first_surface} share a payload but "
                    f"recorded different exit codes — corpus is incoherent")

    def test_every_surface_has_a_golden(self):
        for surface in SURFACES:
            golden = load_golden(surface)
            for key in ("surface", "event", "payload", "stdout", "exit_code", "env_notes"):
                self.assertIn(key, golden, f"{surface}.json missing key {key!r}")
            self.assertEqual(golden["surface"], surface)


if __name__ == "__main__":
    unittest.main()
