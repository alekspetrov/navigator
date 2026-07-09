#!/usr/bin/env python3
"""Subprocess tests for hooks/nav_brief.py (UserPromptSubmit, TASK-56).

stdlib unittest only. Each test builds a throwaway project dir with its own
.agent/ and drives the hook via subprocess with a JSON prompt on stdin,
mirroring test_workflow_enforcer.py. Contract under test:

  - ALWAYS exit 0 (the hook must never block — mem-034: exit 2 on
    UserPromptSubmit stops the model from running at all).
  - High-ambiguity task prompt -> NAV-BRIEF block on stdout.
  - Questions / confirmations / file-scoped prompts / disabled config
    -> empty stdout.
  - Memory recall degrades silently: missing graph, broken or oversized
    recall helper never break the brief and never leak to stderr loudly.
"""

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

HOOK = str(Path(__file__).resolve().parent / "nav_brief.py")
SENTINEL = "NAV-BRIEF"

AMBIGUOUS_PROMPT = "refactor the API"
SPECIFIC_PROMPT = "fix the typo in README.md"


def run_hook(project_dir, prompt=None, raw_stdin=None, env_extra=None):
    if raw_stdin is None:
        raw_stdin = json.dumps({"prompt": prompt if prompt is not None else ""})
    env = os.environ.copy()
    env.pop("PILOT_EXECUTOR", None)
    env.pop("CLAUDE_USER_MESSAGE", None)
    # Isolate plugin-dir resolution unless a test injects its own fake.
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    env.pop("CLAUDE_PLUGIN_DIR", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["python3", HOOK],
        input=raw_stdin,
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
    )


def make_fake_plugin(root: Path, recall_body: str) -> str:
    """Create a fake plugin dir whose memory_recall.py runs recall_body."""
    functions = root / "skills" / "nav-graph" / "functions"
    functions.mkdir(parents=True)
    (functions / "memory_recall.py").write_text(
        "#!/usr/bin/env python3\n" + textwrap.dedent(recall_body)
    )
    return str(root)


class NavBriefHookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # realpath so macOS /var -> /private/var resolution stays consistent
        self.project = os.path.realpath(self._tmp.name)
        self.agent = Path(self.project) / ".agent"
        self.agent.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write_config(self, brief_hook):
        (self.agent / ".nav-config.json").write_text(
            json.dumps({"brief_hook": brief_hook})
        )

    def write_graph(self):
        knowledge = self.agent / "knowledge"
        knowledge.mkdir(parents=True, exist_ok=True)
        (knowledge / "graph.json").write_text("{}")

    # --- trigger / passthrough ---

    def test_ambiguous_prompt_emits_brief(self):
        result = run_hook(self.project, prompt=AMBIGUOUS_PROMPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)
        self.assertIn("score=", result.stdout)
        self.assertIn("scope", result.stdout)  # undefined dimensions listed

    def test_specific_prompt_stays_silent(self):
        result = run_hook(self.project, prompt=SPECIFIC_PROMPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_question_stays_silent(self):
        result = run_hook(self.project, prompt="why does the build fail?")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_confirmation_stays_silent(self):
        result = run_hook(self.project, prompt="yes, go ahead")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_empty_prompt_stays_silent(self):
        result = run_hook(self.project, prompt="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_malformed_stdin_treated_as_raw_prompt(self):
        result = run_hook(self.project, raw_stdin=AMBIGUOUS_PROMPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)

    # --- config ---

    def test_disabled_stays_silent(self):
        self.write_config({"enabled": False})
        result = run_hook(self.project, prompt=AMBIGUOUS_PROMPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_config_uses_defaults(self):
        self.assertFalse((self.agent / ".nav-config.json").exists())
        result = run_hook(self.project, prompt=AMBIGUOUS_PROMPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)

    def test_high_threshold_suppresses(self):
        self.write_config({"ambiguity_threshold": 0.9})
        result = run_hook(self.project, prompt=AMBIGUOUS_PROMPT)  # scores 0.7
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_pilot_executor_bypasses(self):
        result = run_hook(
            self.project,
            prompt=AMBIGUOUS_PROMPT,
            env_extra={"PILOT_EXECUTOR": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_resolves_config_from_stdin_cwd(self):
        # Config disabling the hook lives under the stdin cwd; process cwd is
        # a neutral dir. TASK-49 contract: stdin cwd wins.
        self.write_config({"enabled": False})
        with tempfile.TemporaryDirectory() as neutral:
            neutral = os.path.realpath(neutral)
            raw = json.dumps({"prompt": AMBIGUOUS_PROMPT, "cwd": self.project})
            result = run_hook(neutral, raw_stdin=raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    # --- memory recall degradation ---

    def test_no_graph_emits_brief_without_memories(self):
        result = run_hook(self.project, prompt=AMBIGUOUS_PROMPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)
        self.assertNotIn("Relevant Memories", result.stdout)

    def test_recall_output_included(self):
        self.write_graph()
        with tempfile.TemporaryDirectory() as fake:
            plugin = make_fake_plugin(
                Path(os.path.realpath(fake)),
                'print(\'- PATTERN: "JWT for stateless auth" (80%)\')\n',
            )
            result = run_hook(
                self.project,
                prompt=AMBIGUOUS_PROMPT,
                env_extra={"CLAUDE_PLUGIN_ROOT": plugin},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)
        self.assertIn("Relevant Memories", result.stdout)
        self.assertIn("JWT for stateless auth", result.stdout)

    def test_recall_failure_degrades_silently(self):
        self.write_graph()
        with tempfile.TemporaryDirectory() as fake:
            plugin = make_fake_plugin(
                Path(os.path.realpath(fake)),
                'import sys\nsys.stderr.write("boom")\nsys.exit(1)\n',
            )
            result = run_hook(
                self.project,
                prompt=AMBIGUOUS_PROMPT,
                env_extra={"CLAUDE_PLUGIN_ROOT": plugin},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)
        self.assertNotIn("Relevant Memories", result.stdout)

    def test_memory_budget_truncates(self):
        self.write_graph()
        self.write_config({"memory_budget_chars": 100})
        with tempfile.TemporaryDirectory() as fake:
            plugin = make_fake_plugin(
                Path(os.path.realpath(fake)),
                'print("M" * 5000)\n',
            )
            result = run_hook(
                self.project,
                prompt=AMBIGUOUS_PROMPT,
                env_extra={"CLAUDE_PLUGIN_ROOT": plugin},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(SENTINEL, result.stdout)
        self.assertLessEqual(result.stdout.count("M"), 110)  # budget + slack

    # --- mem-034 hygiene ---

    def test_enforcer_sentinel_block_is_stripped_before_scoring(self):
        # A prompt whose ONLY task-shaped content lives inside an echoed
        # workflow_enforcer block notice must not trigger a brief.
        echoed = (
            "Original prompt: please summarize the readme\n"
            "<nav-workflow-block>\n"
            "refactor the API until done\n"
            "</nav-workflow-block>\n"
        )
        result = run_hook(self.project, prompt=echoed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
