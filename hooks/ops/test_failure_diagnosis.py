#!/usr/bin/env python3
"""Tests for ops/failure_diagnosis.py — TASK-62 Phase 3 (PostToolUseFailure).

Covers: the tool-name + error-pattern dual key (no match ⇒ silent, no generic
noise), PITFALL-only line filtering, declarative output that never echoes the
raw error text, recall-failure silence, and the dispatch-level contract for
the PostToolUseFailure event (validate-or-drop KEPT the registration on CC
2.1.205) with CLAUDE_PLUGIN_ROOT set AND unset (mem-036).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # this dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # hooks/ (nav_hook_lib)

import failure_diagnosis
from nav_hook_lib import config

HOOKS_DIR = Path(__file__).resolve().parent.parent
DISPATCH = str(HOOKS_DIR / "nav_dispatch.py")
SESSION_ID = "sess-failure-diagnosis-tests"
NOW = 1_700_000_000.0

RECALL_SUMMARY = (
    '- PITFALL: "Auth changes break session tests" (90%)\n'
    '- PITFALL: "flock lockfile contention wedges peers" (80%)\n'
    '- DECISION: "JWT over sessions for scaling" (95%)'
)

# Stub memory_recall.py used by the subprocess contract tests: prints the
# compact summary above regardless of arguments.
STUB_RECALL = f"""\
print({RECALL_SUMMARY!r})
"""


class FailureDiagnosisBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name)) / "project"
        (self.root / ".agent" / "knowledge").mkdir(parents=True)
        (self.root / ".agent" / "knowledge" / "graph.json").write_text("{}\n")

    def payload(self, tool_name="Bash", error="session tests exploded"):
        return {
            "cwd": str(self.root),
            "session_id": SESSION_ID,
            "tool_name": tool_name,
            "error": error,
        }

    def ctx(self, payload):
        return types.SimpleNamespace(
            event="PostToolUseFailure",
            payload=payload,
            config=config.load(self.root),
            state={},
            pilot_executor=False,
            now=NOW,
        )

    def run_with_recall(self, payload, summary=RECALL_SUMMARY):
        with mock.patch.object(failure_diagnosis.memory, "recall",
                               return_value=summary) as recall:
            result = failure_diagnosis.run(self.ctx(payload))
        return result, recall


class MatchingTest(FailureDiagnosisBase):
    def test_matching_tool_and_error_pattern_surfaces_pitfall(self):
        result, _ = self.run_with_recall(self.payload(error="session tests broke"))
        self.assertIn("Auth changes break session tests", result["additional_context"])
        self.assertIn("Bash failure", result["additional_context"])

    def test_non_matching_error_is_silent(self):
        result, _ = self.run_with_recall(self.payload(error="disk quota exceeded"))
        self.assertIsNone(result)

    def test_non_pitfall_memory_types_never_surface(self):
        # "scaling" matches only the DECISION line — pitfall lookup stays silent.
        result, _ = self.run_with_recall(self.payload(error="scaling problem"))
        self.assertIsNone(result)

    def test_raw_error_text_is_not_echoed_into_context(self):
        error = "session tests broke: SECRET-TOKEN-9f1e"
        result, _ = self.run_with_recall(self.payload(error=error))
        self.assertNotIn("SECRET-TOKEN-9f1e", result["additional_context"])

    def test_tool_name_and_error_tokens_key_the_recall(self):
        _, recall = self.run_with_recall(self.payload(tool_name="Edit",
                                                      error="lockfile contention"))
        concepts = recall.call_args.kwargs["concepts"]
        self.assertEqual(concepts[0], "edit")
        self.assertIn("lockfile", concepts)
        self.assertIn("contention", concepts)


class SilenceTest(FailureDiagnosisBase):
    def test_missing_tool_name_is_silent(self):
        payload = self.payload()
        del payload["tool_name"]
        result, _ = self.run_with_recall(payload)
        self.assertIsNone(result)

    def test_empty_error_text_is_silent_without_recall(self):
        payload = self.payload(error="")
        with mock.patch.object(failure_diagnosis.memory, "recall") as recall:
            result = failure_diagnosis.run(self.ctx(payload))
        self.assertIsNone(result)
        recall.assert_not_called()

    def test_generic_only_error_words_are_silent(self):
        # Every token is failure-vocabulary stopwords: no pattern to match.
        result, _ = self.run_with_recall(self.payload(error="error failed exception"))
        self.assertIsNone(result)

    def test_recall_failure_collapses_to_silence(self):
        result, _ = self.run_with_recall(self.payload(), summary="")
        self.assertIsNone(result)

    def test_error_extracted_from_tool_response_dict(self):
        payload = self.payload()
        del payload["error"]
        payload["tool_response"] = {"error": "session tests broke"}
        result, _ = self.run_with_recall(payload)
        self.assertIn("session tests", result["additional_context"])


class DeclarativeConstraintTest(FailureDiagnosisBase):
    """mem-050 inheritance: tool-adjacent content stays declarative."""

    def test_header_is_declarative(self):
        result, _ = self.run_with_recall(self.payload(error="session tests broke"))
        lowered = result["additional_context"].lower()
        for marker in ("you must", "you should", "make sure", "remember to"):
            self.assertNotIn(marker, lowered)


class DispatchContractTest(FailureDiagnosisBase):
    """TASK-45 subprocess pattern against the live PostToolUseFailure route."""

    def setUp(self):
        super().setUp()
        self.plugin_dir = Path(os.path.realpath(self._tmp.name)) / "plugin"
        functions = self.plugin_dir / "skills" / "nav-graph" / "functions"
        functions.mkdir(parents=True)
        (functions / "memory_recall.py").write_text(STUB_RECALL, encoding="utf-8")

    def enable(self):
        (self.root / ".agent" / ".nav-config.json").write_text(
            json.dumps({"failure_diagnosis": {"enabled": True}}), encoding="utf-8")

    def dispatch(self, payload, plugin_root=None):
        env = os.environ.copy()
        for key in ("PILOT_EXECUTOR", "CLAUDE_PROJECT_DIR", "CLAUDE_USER_MESSAGE",
                    "CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR"):
            env.pop(key, None)
        if plugin_root is not None:
            env["CLAUDE_PLUGIN_ROOT"] = plugin_root
        return subprocess.run(
            [sys.executable, DISPATCH, "PostToolUseFailure"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(self.root),
            env=env,
            timeout=30,
        )

    def test_default_config_keeps_op_off(self):
        proc = self.dispatch(self.payload(), plugin_root=str(self.plugin_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("PITFALL", proc.stdout)

    def test_enabled_match_surfaces_pitfall_env_set(self):
        self.enable()
        proc = self.dispatch(self.payload(error="session tests broke"),
                             plugin_root=str(self.plugin_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        context = doc["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(doc["hookSpecificOutput"]["hookEventName"],
                         "PostToolUseFailure")
        self.assertIn("Auth changes break session tests", context)

    def test_enabled_no_match_is_silent_env_set(self):
        self.enable()
        proc = self.dispatch(self.payload(error="disk quota exceeded"),
                             plugin_root=str(self.plugin_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("PITFALL", proc.stdout)

    def test_enabled_env_unset_fails_open(self):
        # mem-036: CLAUDE_PLUGIN_ROOT unset — recall resolves the real repo
        # checkout (file-relative fallback), whose graph lookup runs against
        # the tmp project graph; whatever recall yields, dispatch exits 0.
        self.enable()
        proc = self.dispatch(self.payload(error="session tests broke"))
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
