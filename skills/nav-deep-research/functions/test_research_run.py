#!/usr/bin/env python3
"""Tests for research_run.py (TASK-74) — slug, init, steps, resume, CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from research_run import (ARTIFACTS, STEPS, init_run, list_runs, make_slug, read_query,
                          resume, set_meta, set_step, status)

SCRIPT = Path(__file__).parent / "research_run.py"


class TestSlug(unittest.TestCase):
    def test_drops_stopwords_and_caps_words(self):
        slug = make_slug("What is the state of the art in ion trap quantum error correction?")
        self.assertEqual(slug, "state-art-ion-trap-quantum-error")

    def test_collision_suffix(self):
        self.assertEqual(make_slug("rust async", {"rust-async"}), "rust-async-2")
        self.assertEqual(make_slug("rust async", {"rust-async", "rust-async-2"}), "rust-async-3")

    def test_all_stopwords_falls_back(self):
        self.assertEqual(make_slug("what is the"), "what-is-the")
        self.assertEqual(make_slug("???"), "research")


class TestRunLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agent = str(self.root / ".agent")

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_writes_query_and_manifest(self):
        out = init_run("Compare Rust async runtimes", self.agent, str(self.root))
        directory = Path(out["dir"])
        self.assertEqual(out["backend"], "native")
        self.assertTrue((directory / "query.md").exists())
        self.assertTrue((directory / "sources").is_dir())
        self.assertEqual(read_query(out["slug"], self.agent), "Compare Rust async runtimes")
        manifest = json.loads((directory / "run.json").read_text())
        self.assertEqual(set(manifest["steps"]), {str(n) for n, _ in STEPS})
        self.assertTrue(all(s["status"] == "pending" for s in manifest["steps"].values()))

    def test_init_detects_hyperresearch_backend(self):
        (self.root / ".hyperresearch").mkdir()
        out = init_run("anything", self.agent, str(self.root))
        self.assertEqual(out["backend"], "hyperresearch")

    def test_init_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            init_run("   ", self.agent, str(self.root))

    def test_second_init_same_query_gets_suffix(self):
        first = init_run("same query", self.agent, str(self.root))
        second = init_run("same query", self.agent, str(self.root))
        self.assertEqual(second["slug"], first["slug"] + "-2")

    def test_step_and_resume_follow_manifest(self):
        slug = init_run("resume me", self.agent, str(self.root))["slug"]
        self.assertEqual(resume(slug, self.agent)["next_step"], 1)
        set_step(slug, 1, "running", agent_dir=self.agent)
        self.assertEqual(resume(slug, self.agent)["next_step"], 1)
        set_step(slug, 1, "done", agent_dir=self.agent)
        set_step(slug, 2, "done", agent_dir=self.agent)
        self.assertEqual(resume(slug, self.agent)["next_step"], 3)
        self.assertEqual(resume(slug, self.agent)["reason"], "manifest")

    def test_resume_trusts_disk_when_manifest_stale(self):
        out = init_run("stale manifest", self.agent, str(self.root))
        directory = Path(out["dir"])
        (directory / ARTIFACTS[1]).write_text("| item | query |\n")
        (directory / "sources" / "001.md").write_text("---\nid: 001\nstatus: ok\n---\n")
        (directory / ARTIFACTS[3]).write_text("# report\n")
        result = resume(out["slug"], self.agent)
        self.assertEqual(result["next_step"], 4)
        self.assertIn("artifacts", result["reason"])
        self.assertTrue(result["artifacts"]["2"])

    def test_resume_all_done(self):
        slug = init_run("finished", self.agent, str(self.root))["slug"]
        for n, _ in STEPS:
            set_step(slug, n, "done", agent_dir=self.agent)
        self.assertIsNone(resume(slug, self.agent)["next_step"])

    def test_skipped_steps_do_not_block_resume(self):
        slug = init_run("no critic", self.agent, str(self.root))["slug"]
        for n in (1, 2, 3):
            set_step(slug, n, "done", agent_dir=self.agent)
        set_step(slug, 4, "skipped", "critic disabled", agent_dir=self.agent)
        set_step(slug, 5, "skipped", "critic disabled", agent_dir=self.agent)
        self.assertEqual(resume(slug, self.agent)["next_step"], 6)

    def test_blocked_reported(self):
        slug = init_run("blocked run", self.agent, str(self.root))["slug"]
        set_step(slug, 2, "blocked", "captcha wall", agent_dir=self.agent)
        self.assertEqual(resume(slug, self.agent)["blocked_steps"], [2])

    def test_set_meta_and_status_counts(self):
        out = init_run("meta run", self.agent, str(self.root))
        set_meta(out["slug"], "sources_rows_before_patch", 9, self.agent)
        sources = Path(out["dir"]) / "sources"
        (sources / "001.md").write_text("---\nid: 001\nstatus: ok\n---\n")
        (sources / "002.md").write_text("---\nid: 002\nstatus: blocked\n---\n")
        result = status(out["slug"], self.agent)
        self.assertEqual(result["meta"]["sources_rows_before_patch"], 9)
        self.assertEqual(result["source_counts"]["ok"], 1)
        self.assertEqual(result["source_counts"]["blocked"], 1)

    def test_list_runs_newest_first(self):
        init_run("older", self.agent, str(self.root))
        init_run("newer", self.agent, str(self.root))
        slugs = [r["slug"] for r in list_runs(self.agent)]
        self.assertEqual(set(slugs), {"older", "newer"})

    def test_unknown_step_or_status_rejected(self):
        slug = init_run("bad", self.agent, str(self.root))["slug"]
        with self.assertRaises(ValueError):
            set_step(slug, 9, "done", agent_dir=self.agent)
        with self.assertRaises(ValueError):
            set_step(slug, 1, "weird", agent_dir=self.agent)


class TestCLI(unittest.TestCase):
    def test_init_then_resume_via_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = str(Path(tmp) / ".agent")
            proc = subprocess.run([sys.executable, str(SCRIPT), "--agent-dir", agent,
                                   "--project-root", tmp, "init", "--query", "cli query"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            slug = json.loads(proc.stdout)["slug"]
            proc = subprocess.run([sys.executable, str(SCRIPT), "--agent-dir", agent,
                                   "step", "--run", slug, "--done", "1"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            proc = subprocess.run([sys.executable, str(SCRIPT), "--agent-dir", agent,
                                   "resume", "--run", slug], capture_output=True, text=True)
            self.assertEqual(json.loads(proc.stdout)["next_step"], 2)

    def test_missing_run_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(SCRIPT), "--agent-dir",
                                   str(Path(tmp) / ".agent"), "resume", "--run", "nope"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("error", json.loads(proc.stdout))


if __name__ == "__main__":
    unittest.main()
