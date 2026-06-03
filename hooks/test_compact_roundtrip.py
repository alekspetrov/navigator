#!/usr/bin/env python3
"""
Round-trip tests for Navigator's compact lifecycle hooks.

Exercises the PreCompact → PostCompact → SessionStart chain end-to-end
against a throwaway temp project. NEVER touches the real .agent/.

Covered:
  1. nav_pre_compact.py writes a `before-compact-<trigger>-*.md` marker
     plus the `.active` pointer under `.agent/.context-markers/`.
  2. nav_post_compact.py appends the `## Compact Summary (Claude Code)`
     section (containing the supplied summary) to the active marker.
  3. nav_session_start's active-marker section surfaces the marker name.
  4. nav_post_compact.py is a no-op (exit 0) when no `.active` exists.

stdlib unittest only (pytest is NOT installed). Run with:
  cd hooks && python3 -m unittest test_compact_roundtrip -v
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
PRE_COMPACT = HOOKS_DIR / "nav_pre_compact.py"
POST_COMPACT = HOOKS_DIR / "nav_post_compact.py"
SESSION_START = HOOKS_DIR / "nav_session_start.py"


def _run_hook(hook_path: Path, stdin_obj: dict, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(stdin_obj),
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _load_session_start_module():
    """Import nav_session_start.py as a module to call helpers directly."""
    spec = importlib.util.spec_from_file_location("nav_session_start", SESSION_START)
    assert spec and spec.loader, "could not load nav_session_start spec"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompactRoundTripTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.agent = self.root / ".agent"
        self.agent.mkdir(parents=True)
        # Minimal nav-config so the compact hooks are enabled.
        (self.agent / ".nav-config.json").write_text(
            json.dumps(
                {
                    "version": "test",
                    "compact_hook": {
                        "enabled": True,
                        "include_transcript_summary": True,
                        "include_git_state": True,
                        "char_budget": 8000,
                        "append_post_compact_summary": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        # Synthetic JSONL transcript (Claude Code shape).
        self.transcript = self.root / "transcript.jsonl"
        lines = [
            {"message": {"role": "user", "content": "fix the bug in foo.py"}},
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Editing foo.py to handle the error case."},
                    ],
                }
            },
        ]
        self.transcript.write_text(
            "\n".join(json.dumps(obj) for obj in lines) + "\n", encoding="utf-8"
        )
        self.markers_dir = self.agent / ".context-markers"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── Step 1: PreCompact writes marker + .active ──────────────────────────
    def _run_pre_compact(self, trigger: str = "manual") -> subprocess.CompletedProcess:
        return _run_hook(
            PRE_COMPACT,
            {
                "cwd": str(self.root),
                "transcript_path": str(self.transcript),
                "session_id": "test",
                "trigger": trigger,
            },
            cwd=self.root,
        )

    def _active_marker_name(self) -> str:
        active = self.markers_dir / ".active"
        self.assertTrue(active.is_file(), ".active pointer was not written")
        return active.read_text(encoding="utf-8").strip()

    def test_pre_compact_writes_marker_and_active(self) -> None:
        proc = self._run_pre_compact(trigger="manual")
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        # stdout must be valid JSON (empty object).
        self.assertEqual(json.loads(proc.stdout.strip()), {})

        markers = list(self.markers_dir.glob("before-compact-manual-*.md"))
        self.assertEqual(
            len(markers), 1, f"expected exactly one marker, found: {markers}"
        )
        name = self._active_marker_name()
        self.assertEqual(name, markers[0].name)
        self.assertTrue(name.startswith("before-compact-manual-"))
        self.assertTrue(name.endswith(".md"))

    # ── Step 2: PostCompact appends the summary section ─────────────────────
    def test_post_compact_appends_summary(self) -> None:
        pre = self._run_pre_compact(trigger="manual")
        self.assertEqual(pre.returncode, 0, f"pre stderr: {pre.stderr}")
        marker_name = self._active_marker_name()
        marker_path = self.markers_dir / marker_name

        # Summary section must not exist yet.
        before = marker_path.read_text(encoding="utf-8")
        self.assertNotIn("## Compact Summary (Claude Code)", before)

        post = _run_hook(
            POST_COMPACT,
            {"cwd": str(self.root), "compact_summary": "SUMMARY-SENTINEL-12345"},
            cwd=self.root,
        )
        self.assertEqual(post.returncode, 0, f"post stderr: {post.stderr}")
        self.assertEqual(json.loads(post.stdout.strip()), {})

        after = marker_path.read_text(encoding="utf-8")
        self.assertIn("## Compact Summary (Claude Code)", after)
        self.assertIn("SUMMARY-SENTINEL-12345", after)

    # ── Step 3: SessionStart surfaces the active marker ─────────────────────
    def test_session_start_surfaces_active_marker(self) -> None:
        pre = self._run_pre_compact(trigger="manual")
        self.assertEqual(pre.returncode, 0, f"pre stderr: {pre.stderr}")
        marker_name = self._active_marker_name()

        module = _load_session_start_module()
        section = module._section_active_marker(self.root)
        self.assertIsNotNone(section, "active-marker section returned None")
        self.assertIn(marker_name, section)
        self.assertIn("## Active Marker", section)

    # ── Step 4: PostCompact is a no-op without .active ──────────────────────
    def test_post_compact_no_active_is_noop(self) -> None:
        # Fresh temp project: .agent/ exists but no .context-markers/.active.
        with tempfile.TemporaryDirectory() as fresh:
            fresh_root = Path(fresh)
            fresh_agent = fresh_root / ".agent"
            fresh_agent.mkdir(parents=True)
            (fresh_agent / ".nav-config.json").write_text(
                json.dumps({"compact_hook": {"enabled": True}}), encoding="utf-8"
            )

            post = _run_hook(
                POST_COMPACT,
                {"cwd": str(fresh_root), "compact_summary": "should-not-be-written"},
                cwd=fresh_root,
            )
            self.assertEqual(post.returncode, 0, f"stderr: {post.stderr}")
            self.assertEqual(json.loads(post.stdout.strip()), {})
            # No marker dir / no marker file should have been created.
            markers_dir = fresh_agent / ".context-markers"
            created = list(markers_dir.glob("*.md")) if markers_dir.is_dir() else []
            self.assertEqual(created, [], f"unexpected markers written: {created}")


if __name__ == "__main__":
    unittest.main()
