#!/usr/bin/env python3
"""Tests for TASK-37 ROI scoring (code_analyzer + cost_analyzer)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from code_analyzer import (
    compute_benefit_score,
    compute_roi_score,
    roi_gate_action,
    DEFAULT_SCORING_THRESHOLDS,
)
from cost_analyzer import (
    estimate_touch_lines,
    compute_cost_score,
    FIX_SIZE_BY_TYPE,
)


class TestEstimateTouchLines(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(estimate_touch_lines([]), 0)

    def test_known_types(self):
        issues = [
            {"type": "deep_nesting"},
            {"type": "unclear_naming"},
        ]
        expected = FIX_SIZE_BY_TYPE["deep_nesting"] + FIX_SIZE_BY_TYPE["unclear_naming"]
        self.assertEqual(estimate_touch_lines(issues), expected)

    def test_unknown_type_uses_default(self):
        issues = [{"type": "mystery_type"}]
        self.assertEqual(estimate_touch_lines(issues), 3)


class TestComputeBenefitScore(unittest.TestCase):
    def test_no_issues_returns_zero(self):
        score, explain = compute_benefit_score([], 100, in_diff=False)
        self.assertEqual(score, 0.0)
        self.assertEqual(explain["issue_density"], 0.0)

    def test_in_diff_increases_benefit(self):
        issues = [{"type": "deep_nesting", "severity": "high"}]
        no_diff, _ = compute_benefit_score(issues, 200, in_diff=False)
        in_diff, _ = compute_benefit_score(issues, 200, in_diff=True)
        self.assertGreater(in_diff, no_diff)

    def test_more_severe_issues_score_higher(self):
        low = [{"type": "redundant_comparison", "severity": "low"}]
        high = [{"type": "deep_nesting", "severity": "high"}]
        low_score, _ = compute_benefit_score(low, 100, in_diff=False)
        high_score, _ = compute_benefit_score(high, 100, in_diff=False)
        self.assertGreater(high_score, low_score)

    def test_caps_at_ten(self):
        issues = [{"type": "deep_nesting", "severity": "high"}] * 100
        score, _ = compute_benefit_score(issues, 50, in_diff=True)
        self.assertLessEqual(score, 10.0)


class TestComputeCostScore(unittest.TestCase):
    def test_returns_score_and_explanation(self):
        issues = [{"type": "deep_nesting", "severity": "high"}]
        score, explain = compute_cost_score(issues, loc=100, path="nonexistent.py")
        self.assertIsInstance(score, float)
        self.assertIn("estimated_touch_lines", explain)
        self.assertIn("file_loc", explain)
        self.assertIn("days_since_modified", explain)
        self.assertIn("import_references", explain)

    def test_larger_file_costs_more(self):
        issues = [{"type": "deep_nesting", "severity": "high"}]
        small, _ = compute_cost_score(issues, loc=50, path="nonexistent.py")
        large, _ = compute_cost_score(issues, loc=5000, path="nonexistent.py")
        self.assertGreater(large, small)

    def test_more_touch_lines_costs_more(self):
        few = [{"type": "redundant_comparison", "severity": "low"}]
        many = [{"type": "deep_nesting", "severity": "high"}] * 10
        few_cost, _ = compute_cost_score(few, loc=200, path="nonexistent.py")
        many_cost, _ = compute_cost_score(many, loc=200, path="nonexistent.py")
        self.assertGreater(many_cost, few_cost)


class TestROIScore(unittest.TestCase):
    def test_basic_ratio(self):
        self.assertEqual(compute_roi_score(6.0, 3.0), 2.0)

    def test_cost_floor_prevents_explosion(self):
        # cost 0.1 floored to 0.5 → ROI = 5/0.5 = 10
        self.assertEqual(compute_roi_score(5.0, 0.1, cost_floor=0.5), 10.0)

    def test_custom_floor(self):
        self.assertEqual(compute_roi_score(2.0, 0.0, cost_floor=1.0), 2.0)


class TestROIGateAction(unittest.TestCase):
    def setUp(self):
        self.thresholds = DEFAULT_SCORING_THRESHOLDS

    def test_low_roi_skips(self):
        self.assertEqual(roi_gate_action(0.3, self.thresholds), "skip")

    def test_middle_roi_suggests(self):
        self.assertEqual(roi_gate_action(1.0, self.thresholds), "suggest")

    def test_high_roi_applies(self):
        self.assertEqual(roi_gate_action(2.5, self.thresholds), "apply")

    def test_boundary_skip_below(self):
        # skip_below = 0.5 → 0.5 should NOT skip
        self.assertNotEqual(roi_gate_action(0.5, self.thresholds), "skip")

    def test_boundary_auto_apply(self):
        # auto_apply_at = 1.5 → 1.5 should apply
        self.assertEqual(roi_gate_action(1.5, self.thresholds), "apply")

    def test_custom_thresholds(self):
        custom = {"skip_below": 1.0, "auto_apply_at": 3.0}
        self.assertEqual(roi_gate_action(0.5, custom), "skip")
        self.assertEqual(roi_gate_action(2.0, custom), "suggest")
        self.assertEqual(roi_gate_action(3.0, custom), "apply")


class TestIntegrationOrdering(unittest.TestCase):
    """ROI should rank active-diff messy files above stable clean files."""

    def test_high_benefit_low_cost_wins(self):
        messy = [{"type": "deep_nesting", "severity": "high"}] * 5
        benefit_a, _ = compute_benefit_score(messy, 100, in_diff=True)
        cost_a, _ = compute_cost_score(messy, loc=100, path="nonexistent_a.py")
        roi_a = compute_roi_score(benefit_a, cost_a)

        clean = [{"type": "unclear_naming", "severity": "low"}]
        benefit_b, _ = compute_benefit_score(clean, 5000, in_diff=False)
        cost_b, _ = compute_cost_score(clean, loc=5000, path="nonexistent_b.py")
        roi_b = compute_roi_score(benefit_b, cost_b)

        self.assertGreater(roi_a, roi_b)


if __name__ == "__main__":
    unittest.main()
