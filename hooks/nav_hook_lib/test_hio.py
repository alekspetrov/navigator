#!/usr/bin/env python3
"""Unit tests for nav_hook_lib/hio.py (TASK-59 Phase 1).

stdlib unittest only. Contract under test (inter-module API):

  - read_stdin_payload(): tolerant — empty/TTY/closed/bad stdin -> {}.
  - safe_read()/safe_json(): None on missing/unreadable/corrupt, no raise.
  - atomic_write_text()/atomic_write_json(): tmp + os.replace, parents
    created, no tmp litter, False (never raise) on failure.
  - resolve_cwd(): payload cwd wins, ALWAYS .resolve()'d — mem-055: macOS
    realpaths /tmp in hook payloads while $PWD may stay logical. Un-Path-able
    candidates (non-string, embedded NUL) fall through, never raise (FIX 5).
  - project_root(): nearest ancestor containing .agent/, else resolved cwd.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hio  # noqa: E402  (sibling import; path pinned above for package-mode discovery)


class _RaisingStdin(io.StringIO):
    def read(self, *args, **kwargs):
        raise OSError("stdin exploded")


class _TtyStdin(io.StringIO):
    def isatty(self):
        return True


class ReadStdinPayloadTest(unittest.TestCase):
    def _payload_from(self, stdin_obj):
        with mock.patch.object(sys, "stdin", stdin_obj):
            return hio.read_stdin_payload()

    def test_valid_json_object(self):
        payload = self._payload_from(io.StringIO('{"prompt": "hi", "cwd": "/x"}'))
        self.assertEqual(payload, {"prompt": "hi", "cwd": "/x"})

    def test_empty_stdin_returns_empty_dict(self):
        self.assertEqual(self._payload_from(io.StringIO("")), {})

    def test_whitespace_stdin_returns_empty_dict(self):
        self.assertEqual(self._payload_from(io.StringIO("  \n\t ")), {})

    def test_non_json_stdin_returns_empty_dict(self):
        self.assertEqual(self._payload_from(io.StringIO("just do it")), {})

    def test_json_non_object_returns_empty_dict(self):
        self.assertEqual(self._payload_from(io.StringIO('[1, 2, 3]')), {})
        self.assertEqual(self._payload_from(io.StringIO('"a string"')), {})
        self.assertEqual(self._payload_from(io.StringIO("42")), {})
        self.assertEqual(self._payload_from(io.StringIO("null")), {})

    def test_tty_stdin_returns_empty_dict(self):
        self.assertEqual(self._payload_from(_TtyStdin('{"prompt": "x"}')), {})

    def test_none_stdin_returns_empty_dict(self):
        self.assertEqual(self._payload_from(None), {})

    def test_closed_stdin_returns_empty_dict(self):
        closed = io.StringIO("{}")
        closed.close()
        self.assertEqual(self._payload_from(closed), {})

    def test_raising_stdin_returns_empty_dict(self):
        self.assertEqual(self._payload_from(_RaisingStdin()), {})


class SafeReadTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_reads_existing_file(self):
        p = self.root / "a.txt"
        p.write_text("hello\nworld", encoding="utf-8")
        self.assertEqual(hio.safe_read(p), "hello\nworld")

    def test_missing_file_returns_none(self):
        self.assertIsNone(hio.safe_read(self.root / "nope.txt"))

    def test_directory_returns_none(self):
        self.assertIsNone(hio.safe_read(self.root))

    def test_max_bytes_head_truncates(self):
        p = self.root / "b.txt"
        p.write_text("0123456789", encoding="utf-8")
        self.assertEqual(hio.safe_read(p, max_bytes=4), "0123")

    def test_undecodable_bytes_are_replaced_not_raised(self):
        p = self.root / "c.bin"
        p.write_bytes(b"ok\xff\xfeok")
        text = hio.safe_read(p)
        self.assertIsNotNone(text)
        self.assertIn("ok", text)


class SafeJsonTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, text):
        p = self.root / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_valid_object(self):
        p = self._write("cfg.json", '{"a": 1, "b": {"c": null}}')
        self.assertEqual(hio.safe_json(p), {"a": 1, "b": {"c": None}})

    def test_missing_file_returns_none(self):
        self.assertIsNone(hio.safe_json(self.root / "missing.json"))

    def test_corrupt_json_returns_none(self):
        self.assertIsNone(hio.safe_json(self._write("bad.json", "{not json")))

    def test_empty_file_returns_none(self):
        self.assertIsNone(hio.safe_json(self._write("empty.json", "")))

    def test_non_object_json_returns_none(self):
        self.assertIsNone(hio.safe_json(self._write("list.json", "[1, 2]")))


class AtomicWriteTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_text_roundtrip_and_parents_created(self):
        target = self.root / "deep" / "nested" / "out.txt"
        self.assertTrue(hio.atomic_write_text(target, "payload"))
        self.assertEqual(target.read_text(encoding="utf-8"), "payload")

    def test_text_overwrites_existing(self):
        target = self.root / "out.txt"
        target.write_text("old", encoding="utf-8")
        self.assertTrue(hio.atomic_write_text(target, "new"))
        self.assertEqual(target.read_text(encoding="utf-8"), "new")

    def test_no_tmp_file_litter_on_success(self):
        target = self.root / "out.txt"
        self.assertTrue(hio.atomic_write_text(target, "x"))
        self.assertEqual([p.name for p in self.root.iterdir()], ["out.txt"])

    def test_text_failure_returns_false(self):
        blocker = self.root / "file"
        blocker.write_text("i am a file", encoding="utf-8")
        # parent path is a file -> mkdir fails -> False, no raise
        self.assertFalse(hio.atomic_write_text(blocker / "child.txt", "x"))

    def test_json_roundtrip_via_safe_json(self):
        target = self.root / "state" / "s.json"
        obj = {"a": 1, "tristate": None, "flag": False, "nested": {"k": [1, "two"]}}
        self.assertTrue(hio.atomic_write_json(target, obj))
        self.assertEqual(hio.safe_json(target), obj)

    def test_json_preserves_null_false_true_distinction(self):
        # mem-037: check_shown tristate True/False/None must survive unmodified.
        target = self.root / "s.json"
        self.assertTrue(hio.atomic_write_json(target, {"check_shown": None}))
        self.assertIn('"check_shown": null', target.read_text(encoding="utf-8"))
        loaded = hio.safe_json(target)
        self.assertIn("check_shown", loaded)
        self.assertIsNone(loaded["check_shown"])

    def test_json_circular_reference_returns_false(self):
        target = self.root / "s.json"
        circular = {}
        circular["self"] = circular
        self.assertFalse(hio.atomic_write_json(target, circular))
        self.assertFalse(target.exists())


class ResolveCwdTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # keep the LOGICAL name: on macOS this is /var/... which resolves to
        # /private/var/... — exactly the mem-055 mismatch we must normalize.
        self.logical = Path(self._tmp.name)
        self.physical = self.logical.resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def _clean_env(self):
        return mock.patch.dict(os.environ, {}, clear=False)

    def test_payload_cwd_wins_and_is_resolved(self):
        with self._clean_env():
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            got = hio.resolve_cwd({"cwd": str(self.logical)})
        self.assertEqual(got, self.physical)

    def test_symlinked_cwd_is_realpathed(self):
        real = self.physical / "real"
        real.mkdir()
        link = self.physical / "link"
        os.symlink(real, link)
        got = hio.resolve_cwd({"cwd": str(link)})
        self.assertEqual(got, real)

    def test_payload_cwd_beats_project_dir_env(self):
        with self._clean_env():
            os.environ["CLAUDE_PROJECT_DIR"] = "/somewhere/else"
            got = hio.resolve_cwd({"cwd": str(self.logical)})
        self.assertEqual(got, self.physical)

    def test_project_dir_env_beats_getcwd(self):
        with self._clean_env():
            os.environ["CLAUDE_PROJECT_DIR"] = str(self.logical)
            got = hio.resolve_cwd({})
        self.assertEqual(got, self.physical)

    def test_falls_back_to_getcwd(self):
        with self._clean_env():
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            got = hio.resolve_cwd()
        self.assertEqual(got, Path(os.getcwd()).resolve())

    def test_empty_cwd_value_falls_through(self):
        with self._clean_env():
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            got = hio.resolve_cwd({"cwd": ""})
        self.assertEqual(got, Path(os.getcwd()).resolve())

    def test_non_dict_payload_tolerated(self):
        with self._clean_env():
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            got = hio.resolve_cwd("not a dict")
        self.assertEqual(got, Path(os.getcwd()).resolve())

    # FIX 5 (TASK-59 adversarial review): un-Path-able payload cwd values must
    # fall through to the next candidate, never raise out of a hook.
    def test_non_string_cwd_falls_through_to_env(self):
        with self._clean_env():
            os.environ["CLAUDE_PROJECT_DIR"] = str(self.logical)
            got = hio.resolve_cwd({"cwd": 123})
        self.assertEqual(got, self.physical)

    def test_non_string_cwd_falls_through_to_getcwd(self):
        with self._clean_env():
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            got = hio.resolve_cwd({"cwd": 123})
        self.assertEqual(got, Path(os.getcwd()).resolve())

    def test_embedded_nul_cwd_falls_through(self):
        with self._clean_env():
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            got = hio.resolve_cwd({"cwd": "a\x00b"})
        self.assertEqual(got, Path(os.getcwd()).resolve())

    def test_bad_env_candidate_also_falls_through(self):
        # os.environ itself rejects NUL bytes, so substitute a plain mapping
        # to simulate an unusable CLAUDE_PROJECT_DIR value reaching hio.
        with mock.patch.object(hio.os, "environ", {"CLAUDE_PROJECT_DIR": "a\x00b"}):
            got = hio.resolve_cwd({})
        self.assertEqual(got, Path(os.getcwd()).resolve())


class ProjectRootTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self._tmp.name))
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def test_cwd_itself_is_project_root(self):
        (self.root / ".agent").mkdir()
        self.assertEqual(hio.project_root({"cwd": str(self.root)}), self.root)

    def test_walks_up_to_nearest_agent_dir(self):
        (self.root / ".agent").mkdir()
        deep = self.root / "src" / "sub" / "deeper"
        deep.mkdir(parents=True)
        self.assertEqual(hio.project_root({"cwd": str(deep)}), self.root)

    def test_nearest_ancestor_wins_over_outer(self):
        (self.root / ".agent").mkdir()
        inner = self.root / "pkg"
        (inner / ".agent").mkdir(parents=True)
        leaf = inner / "src"
        leaf.mkdir()
        self.assertEqual(hio.project_root({"cwd": str(leaf)}), inner)

    def test_no_agent_dir_falls_back_to_cwd(self):
        lonely = self.root / "lonely"
        lonely.mkdir()
        self.assertEqual(hio.project_root({"cwd": str(lonely)}), lonely)

    def test_result_is_resolved(self):
        (self.root / ".agent").mkdir()
        logical = Path(self._tmp.name)  # unresolved (macOS: /var vs /private/var)
        self.assertEqual(hio.project_root({"cwd": str(logical)}), self.root)

    def test_bad_payload_cwd_values_do_not_raise(self):
        # FIX 5: project_root inherits resolve_cwd's candidate fall-through.
        for bad in (123, "a\x00b"):
            with self.subTest(cwd=bad):
                got = hio.project_root({"cwd": bad})
                self.assertIsInstance(got, Path)
                self.assertTrue(got.is_absolute())


if __name__ == "__main__":
    unittest.main()
