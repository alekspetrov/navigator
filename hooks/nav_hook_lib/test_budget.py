#!/usr/bin/env python3
"""Tests for nav_hook_lib/budget.py (TASK-59, Phase 5). stdlib unittest only."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import budget


class BudgetTableTest(unittest.TestCase):
    def test_budgets_match_routing_matrix(self):
        self.assertEqual(budget.BUDGETS["SessionStart"], 9500)
        self.assertEqual(budget.BUDGETS["SubagentStart"], 2000)

    def test_marker_text(self):
        self.assertEqual(budget.TRUNCATION_MARKER, "\n[truncated by nav budget]")


class ClampTest(unittest.TestCase):
    def test_under_budget_passthrough(self):
        text = "short payload\nsecond line"
        self.assertIs(budget.clamp(text, "SubagentStart"), text)

    def test_exact_budget_passthrough(self):
        text = "x" * budget.BUDGETS["SubagentStart"]
        self.assertIs(budget.clamp(text, "SubagentStart"), text)

    def test_unknown_event_never_clamped(self):
        text = "y" * 50_000
        self.assertIs(budget.clamp(text, "PreToolUse"), text)

    def test_none_becomes_empty(self):
        self.assertEqual(budget.clamp(None, "SessionStart"), "")

    def test_over_budget_cuts_on_line_boundary(self):
        lines = [f"line {i:04d} " + "-" * 40 for i in range(100)]
        text = "\n".join(lines)  # ~5200 chars, over the 2000 budget
        out = budget.clamp(text, "SubagentStart")
        self.assertLessEqual(len(out), budget.BUDGETS["SubagentStart"])
        self.assertTrue(out.endswith(budget.TRUNCATION_MARKER))
        head = out[: -len(budget.TRUNCATION_MARKER)]
        self.assertTrue(text.startswith(head))
        # Never mid-line: the char after the kept head is the newline we
        # cut at, i.e. every kept line is complete.
        self.assertEqual(text[len(head)], "\n")

    def test_session_start_budget_applies(self):
        text = "\n".join("row " + "z" * 60 for _ in range(300))  # ~19k chars
        out = budget.clamp(text, "SessionStart")
        self.assertLessEqual(len(out), budget.BUDGETS["SessionStart"])
        self.assertTrue(out.endswith(budget.TRUNCATION_MARKER))

    def test_single_giant_line_hard_cut(self):
        text = "q" * 3000
        out = budget.clamp(text, "SubagentStart")
        self.assertLessEqual(len(out), budget.BUDGETS["SubagentStart"])
        self.assertTrue(out.endswith(budget.TRUNCATION_MARKER))
        head = out[: -len(budget.TRUNCATION_MARKER)]
        self.assertEqual(head, "q" * len(head))
        self.assertGreater(len(head), 0)

    def test_result_never_exceeds_budget(self):
        cases = [
            "",
            "\n" * 5000,
            "a\n" * 3000,
            "word " * 1000,
            ("para\n" * 10 + "x" * 500) * 8,
        ]
        for event in budget.BUDGETS:
            for text in cases:
                out = budget.clamp(text, event)
                self.assertLessEqual(
                    len(out), max(budget.BUDGETS[event], len(text)),
                    f"grew past input: event={event}")
                if len(text) > budget.BUDGETS[event]:
                    self.assertLessEqual(len(out), budget.BUDGETS[event])


if __name__ == "__main__":
    unittest.main()
