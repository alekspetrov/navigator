#!/usr/bin/env python3
"""Tests for triz_suggest.py (TASK-73) — ranking, diversity, fallback, graph priors, CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from triz_suggest import (PRINCIPLES, SEPARATION_ORDER, _tokens, score_principles,
                          suggest, prior_resolutions, render_text)

SCRIPT = Path(__file__).parent / "triz_suggest.py"


class TestCatalog(unittest.TestCase):
    def test_principles_well_formed_and_unique(self):
        nums = [p[0] for p in PRINCIPLES]
        self.assertEqual(len(nums), len(set(nums)))
        for p in PRINCIPLES:
            self.assertIn(p[2], SEPARATION_ORDER, p[1])
            self.assertTrue(p[3] and p[4], p[1])
        self.assertEqual(set(p[2] for p in PRINCIPLES), set(SEPARATION_ORDER))


class TestScoring(unittest.TestCase):
    def test_tokens_drop_stopwords_and_add_singular(self):
        self.assertEqual(_tokens("improving Speed vs worsening rollbacks"),
                         {"speed", "rollbacks", "rollback"})

    def test_rollback_ranks_beforehand_cushioning_first(self):
        top = score_principles("big-bang runtime replacement vs reversibility")[0]
        self.assertEqual(top[1][0], 11)

    def test_diversity_one_per_separation_mode_first(self):
        result = suggest("slow startup vs opt-in regression risk from shared state", 3)
        modes = [c["separation"] for c in result["candidates"]]
        self.assertEqual(len(modes), len(set(modes)), result)
        self.assertFalse(result["generic"])

    def test_pads_to_limit_when_few_hits(self):
        result = suggest("rollback", 3)          # only cushioning matches
        self.assertEqual(len(result["candidates"]), 3)
        self.assertEqual(result["candidates"][0]["number"], 11)
        self.assertFalse(result["generic"])

    def test_keyword_plural_singular_match(self):
        nums = [c["number"] for c in suggest("shim vs token budget", 3)["candidates"]]
        self.assertIn(24, nums)   # "shims" keyword hit by "shim"
        self.assertIn(10, nums)   # "tokens" keyword hit by "token"

    def test_generic_fallback_when_no_keyword_hits(self):
        result = suggest("zzzz vs qqqq", 3)
        self.assertTrue(result["generic"])
        self.assertEqual([c["number"] for c in result["candidates"]], [10, 15, 1])

    def test_limit_respected(self):
        self.assertEqual(len(suggest("slow startup vs enough context", 2)["candidates"]), 2)


class TestPriors(unittest.TestCase):
    def _graph(self, tmp):
        gp = Path(tmp) / "graph.json"
        gp.write_text(json.dumps({"version": "1.0.0", "nodes": {"memories": {
            "mem-001": {"type": "decision", "summary": "shims", "confidence": 0.9,
                        "contradiction": "clean codebase vs rollback safety",
                        "separation": "time", "principle": "temporary shims"},
            "mem-002": {"type": "decision", "summary": "untagged", "confidence": 0.9},
        }}, "edges": [], "concept_index": {}}))
        return str(gp)

    def test_priors_match_by_shared_keyword(self):
        with tempfile.TemporaryDirectory() as tmp:
            priors = prior_resolutions("reversibility vs rollback speed", self._graph(tmp))
        self.assertEqual([m["id"] for m in priors], ["mem-001"])
        self.assertEqual(priors[0]["separation"], "time")

    def test_missing_graph_returns_empty(self):
        self.assertEqual(prior_resolutions("a vs b", "/nonexistent/graph.json"), [])


class TestRenderAndCli(unittest.TestCase):
    def test_render_mentions_generic_when_fallback(self):
        out = render_text(suggest("zzzz vs qqqq"), [])
        self.assertIn("generic fallback", out)
        self.assertIn("this shape of tension is new here", out)

    def test_cli_json_and_exit_zero(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--contradiction", "slow startup vs enough context",
             "--graph-path", "/nonexistent.json", "--format", "json"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["prior_resolutions"], [])
        self.assertEqual(len(data["candidates"]), 3)
        self.assertIn(10, [c["number"] for c in data["candidates"]])  # prior action


if __name__ == "__main__":
    unittest.main(verbosity=2)
