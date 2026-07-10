#!/usr/bin/env python3
"""Tests for ops/prompt_brief.py — the intent-brief injector (v6 parity).

Differential layer runs the v6 script (hooks/nav_brief.py) as a subprocess
and asserts the op's context + the shim's trailing newline byte-match its
stdout (auto-skips once Phase 7 deletes the source). Op-level layer pins
the gates (question/confirmation/threshold), PILOT passthrough, mem-034
strip-before-scoring, and the memory-budget truncation with a stubbed
nav_hook_lib.memory.recall.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/

import prompt_brief  # noqa: E402
from nav_hook_lib import config as nav_config  # noqa: E402
from nav_hook_lib import sentinels  # noqa: E402

HOOKS_DIR = Path(__file__).resolve().parent.parent
V6_SCRIPT = HOOKS_DIR / "nav_brief.py"

AMBIGUOUS_PROMPT = "fix the bugs in the app"


def make_ctx(prompt=None, cfg=None, pilot=False):
    payload = {} if prompt is None else {"prompt": prompt}
    return types.SimpleNamespace(
        event="UserPromptSubmit",
        payload=payload,
        config=cfg or copy.deepcopy(nav_config.DEFAULTS),
        state={},
        pilot_executor=pilot,
        now=0.0,
    )


class BriefTestBase(unittest.TestCase):
    def setUp(self):
        self._saved = {
            key: os.environ.pop(key, None)
            for key in ("PILOT_EXECUTOR", "CLAUDE_USER_MESSAGE",
                        "CLAUDE_PROJECT_DIR")
        }
        self.addCleanup(self._restore)

    def _restore(self):
        for key, value in self._saved.items():
            if value is not None:
                os.environ[key] = value

    def stub_recall(self, text):
        original = prompt_brief.memory.recall
        prompt_brief.memory.recall = lambda **kwargs: text
        self.addCleanup(setattr, prompt_brief.memory, "recall", original)


class V6DifferentialTest(BriefTestBase):
    def _v6_stdout(self, prompt: str) -> str:
        if not V6_SCRIPT.is_file():
            self.skipTest("nav_brief.py deleted (Phase 7)")
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(V6_SCRIPT)],
                input=json.dumps({"prompt": prompt, "cwd": tmp}),
                cwd=tmp, env=dict(os.environ), capture_output=True, text=True,
                timeout=30,
            )
        self.assertEqual(proc.returncode, 0)
        return proc.stdout

    def test_brief_instruction_bytes_match_v6(self):
        result = prompt_brief.run(make_ctx(AMBIGUOUS_PROMPT))
        self.assertIsNotNone(result)
        # No knowledge graph in either run -> no memories on both sides; the
        # dispatcher shim print()s the context, adding exactly one newline.
        self.assertEqual(result["additional_context"] + "\n",
                         self._v6_stdout(AMBIGUOUS_PROMPT))

    def test_question_prompt_matches_v6_silence(self):
        prompt = "How does the auth flow work?"
        self.assertEqual(self._v6_stdout(prompt), "")
        self.assertIsNone(prompt_brief.run(make_ctx(prompt)))

    def test_specific_prompt_matches_v6_silence(self):
        # File reference + limiter credits push the score below threshold.
        prompt = "fix only the typo in hooks/nav_brief.py line 12"
        self.assertEqual(self._v6_stdout(prompt), "")
        self.assertIsNone(prompt_brief.run(make_ctx(prompt)))


class GatingTest(BriefTestBase):
    def test_confirmation_prompt_is_silent(self):
        self.assertIsNone(prompt_brief.run(make_ctx("yes, go ahead")))

    def test_threshold_from_config_respected(self):
        cfg = copy.deepcopy(nav_config.DEFAULTS)
        cfg["brief_hook"]["ambiguity_threshold"] = 0.9
        self.assertIsNone(prompt_brief.run(make_ctx(AMBIGUOUS_PROMPT, cfg=cfg)))

    def test_pilot_executor_passthrough(self):
        self.assertIsNone(prompt_brief.run(make_ctx(AMBIGUOUS_PROMPT,
                                                    pilot=True)))

    def test_empty_prompt_is_silent(self):
        self.assertIsNone(prompt_brief.run(make_ctx()))

    def test_echoed_block_message_is_silent(self):
        # mem-034: echoed enforcer stderr must not fake a task-shaped prompt.
        echoed = (
            sentinels.wrap("nav-workflow-block", "fix everything, keep going")
            + "\nOriginal prompt: " + AMBIGUOUS_PROMPT
        )
        self.assertIsNone(prompt_brief.run(make_ctx(echoed)))


class MemoriesTest(BriefTestBase):
    def test_memories_section_appended(self):
        self.stub_recall("- PITFALL: watch the session tests (90%)")
        result = prompt_brief.run(make_ctx(AMBIGUOUS_PROMPT))
        context = result["additional_context"]
        self.assertIn("## Relevant Memories", context)
        self.assertTrue(context.endswith(
            "- PITFALL: watch the session tests (90%)"))

    def test_memory_budget_truncates(self):
        cfg = copy.deepcopy(nav_config.DEFAULTS)
        cfg["brief_hook"]["memory_budget_chars"] = 10
        self.stub_recall("X" * 50)
        result = prompt_brief.run(make_ctx(AMBIGUOUS_PROMPT, cfg=cfg))
        self.assertTrue(result["additional_context"].endswith("X" * 10))
        self.assertNotIn("X" * 11, result["additional_context"])

    def test_recall_failure_degrades_to_no_memories_section(self):
        self.stub_recall("")
        result = prompt_brief.run(make_ctx(AMBIGUOUS_PROMPT))
        self.assertNotIn("## Relevant Memories", result["additional_context"])


class ConceptExtractionTest(unittest.TestCase):
    def test_stopwords_dropped_dedup_and_cap(self):
        message = "please fix this auth auth token flow " \
                  "alpha beta gamma delta epsilon zeta eta theta iota"
        concepts = prompt_brief._extract_concepts(message)
        self.assertNotIn("please", concepts)
        self.assertNotIn("this", concepts)
        self.assertEqual(concepts.count("auth"), 1)
        self.assertLessEqual(len(concepts), prompt_brief.MAX_CONCEPTS)


if __name__ == "__main__":
    unittest.main()
