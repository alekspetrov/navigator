#!/usr/bin/env python3
"""
POC-1769187675 Test Suite: Validate Native Task Integration Evaluation

Tests verify:
1. Evaluation report structure and completeness
2. Tool availability claims accuracy
3. Documentation quality and format
4. Decision criteria documentation
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Test configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
TASKS_DIR = PROJECT_ROOT / ".agent" / "tasks"
EVALUATION_REPORT = TASKS_DIR / "poc-1769186747-evaluation-report.md"
VERIFICATION_PLAN = TASKS_DIR / "poc-1769187675-plan.md"


class TestResult:
    """Simple test result container."""

    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message

    def __str__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        msg = f" - {self.message}" if self.message else ""
        return f"{status}: {self.name}{msg}"


def test_evaluation_report_exists() -> TestResult:
    """Test that the evaluation report file exists."""
    exists = EVALUATION_REPORT.exists()
    return TestResult(
        "Evaluation report exists",
        exists,
        f"Path: {EVALUATION_REPORT}" if exists else f"Missing: {EVALUATION_REPORT}"
    )


def test_verification_plan_exists() -> TestResult:
    """Test that the verification plan file exists."""
    exists = VERIFICATION_PLAN.exists()
    return TestResult(
        "Verification plan exists",
        exists,
        f"Path: {VERIFICATION_PLAN}" if exists else f"Missing: {VERIFICATION_PLAN}"
    )


def test_evaluation_report_structure() -> TestResult:
    """Test that evaluation report has required sections."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Evaluation report structure", False, "File not found")

    content = EVALUATION_REPORT.read_text()
    required_sections = [
        "Executive Summary",
        "Native Task Capabilities",
        "TodoWrite Comparison",
        "Navigator Integration Assessment",
        "Recommendation",
        "Future Considerations",
        "Decision Criteria Results",
        "API Documentation",
        "Usage Examples",
        "Decision Tree",
        "Comparison",
        "Re-evaluation Criteria"
    ]

    missing = [section for section in required_sections if section not in content]

    if missing:
        return TestResult(
            "Evaluation report structure",
            False,
            f"Missing sections: {', '.join(missing)}"
        )

    return TestResult(
        "Evaluation report structure",
        True,
        f"All {len(required_sections)} required sections present"
    )


def test_tool_availability_claims() -> TestResult:
    """Test that tool availability claims are documented."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Tool availability claims", False, "File not found")

    content = EVALUATION_REPORT.read_text()

    # Check unavailable tools are listed
    unavailable_tools = ["TaskCreate", "TaskUpdate", "TaskGet", "TaskList"]
    missing_unavailable = [t for t in unavailable_tools if t not in content]

    # Check available tools are listed
    available_tools = ["Task", "TaskOutput", "TodoWrite"]
    missing_available = [t for t in available_tools if t not in content]

    issues = []
    if missing_unavailable:
        issues.append(f"Missing unavailable tool docs: {missing_unavailable}")
    if missing_available:
        issues.append(f"Missing available tool docs: {missing_available}")

    if issues:
        return TestResult("Tool availability claims", False, "; ".join(issues))

    return TestResult(
        "Tool availability claims",
        True,
        f"All {len(unavailable_tools)} unavailable and {len(available_tools)} available tools documented"
    )


def test_decision_recommendation_present() -> TestResult:
    """Test that a clear recommendation is documented."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Decision recommendation", False, "File not found")

    content = EVALUATION_REPORT.read_text()

    # Check for recommendation markers
    has_recommendation = "DO NOT INTEGRATE" in content or "INTEGRATE" in content
    has_rationale = "Rationale" in content
    has_actions = "Actions" in content

    issues = []
    if not has_recommendation:
        issues.append("No clear recommendation found")
    if not has_rationale:
        issues.append("No rationale section found")
    if not has_actions:
        issues.append("No actions section found")

    if issues:
        return TestResult("Decision recommendation", False, "; ".join(issues))

    return TestResult("Decision recommendation", True, "Recommendation, rationale, and actions present")


def test_api_documentation_quality() -> TestResult:
    """Test that API documentation includes TypeScript interfaces."""
    if not EVALUATION_REPORT.exists():
        return TestResult("API documentation quality", False, "File not found")

    content = EVALUATION_REPORT.read_text()

    # Check for TypeScript code blocks
    has_typescript = "```typescript" in content
    has_interfaces = "interface Todo" in content or "interface" in content
    has_jsdoc = "@param" in content or "@returns" in content

    issues = []
    if not has_typescript:
        issues.append("No TypeScript code blocks")
    if not has_interfaces:
        issues.append("No interface definitions")
    if not has_jsdoc:
        issues.append("No JSDoc comments")

    if issues:
        return TestResult("API documentation quality", False, "; ".join(issues))

    return TestResult("API documentation quality", True, "TypeScript, interfaces, and JSDoc present")


def test_comparison_tables_present() -> TestResult:
    """Test that comparison tables exist."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Comparison tables", False, "File not found")

    content = EVALUATION_REPORT.read_text()

    # Count markdown tables (lines starting with |)
    table_rows = [line for line in content.split('\n') if line.strip().startswith('|')]
    table_count = len([r for r in table_rows if '---' in r])  # Header separators indicate tables

    if table_count < 3:
        return TestResult(
            "Comparison tables",
            False,
            f"Found {table_count} tables, expected at least 3"
        )

    return TestResult("Comparison tables", True, f"{table_count} tables found")


def test_decision_tree_present() -> TestResult:
    """Test that decision tree diagram exists."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Decision tree", False, "File not found")

    content = EVALUATION_REPORT.read_text()

    # Check for ASCII diagram indicators
    has_box = "┌" in content or "├" in content or "│" in content
    has_decision_markers = "YES →" in content or "NO →" in content

    if not has_box:
        return TestResult("Decision tree", False, "No ASCII box characters found")
    if not has_decision_markers:
        return TestResult("Decision tree", False, "No decision branch markers found")

    return TestResult("Decision tree", True, "ASCII diagram with decision branches present")


def test_verification_completeness() -> TestResult:
    """Test that verification plan shows 100% completeness."""
    if not VERIFICATION_PLAN.exists():
        return TestResult("Verification completeness", False, "File not found")

    content = VERIFICATION_PLAN.read_text()

    # Check for completeness indicators
    has_complete_status = "✅ Complete" in content
    has_100_score = "100%" in content
    has_all_checkmarks = content.count("[x]") >= 8  # At least 8 verified items

    issues = []
    if not has_complete_status:
        issues.append("No ✅ Complete status found")
    if not has_100_score:
        issues.append("No 100% score found")
    if not has_all_checkmarks:
        issues.append(f"Only {content.count('[x]')} checkmarks, expected 8+")

    if issues:
        return TestResult("Verification completeness", False, "; ".join(issues))

    return TestResult("Verification completeness", True, "All verification criteria passed")


def test_reevaluation_criteria_defined() -> TestResult:
    """Test that re-evaluation criteria are documented."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Re-evaluation criteria", False, "File not found")

    content = EVALUATION_REPORT.read_text()

    # Check for re-evaluation section content
    has_triggers = "Trigger" in content or "trigger" in content
    has_criteria = "Criteria" in content or "criteria" in content
    has_claude_code_mention = "Claude Code release" in content or "release notes" in content

    issues = []
    if not has_triggers:
        issues.append("No re-evaluation triggers defined")
    if not has_criteria:
        issues.append("No criteria section found")
    if not has_claude_code_mention:
        issues.append("No future release monitoring mentioned")

    if issues:
        return TestResult("Re-evaluation criteria", False, "; ".join(issues))

    return TestResult("Re-evaluation criteria", True, "Triggers and criteria documented")


def test_report_word_count() -> TestResult:
    """Test that report has substantial content."""
    if not EVALUATION_REPORT.exists():
        return TestResult("Report word count", False, "File not found")

    content = EVALUATION_REPORT.read_text()
    word_count = len(content.split())
    line_count = len(content.split('\n'))

    if word_count < 500:
        return TestResult("Report word count", False, f"Only {word_count} words, expected 500+")

    return TestResult("Report word count", True, f"{word_count} words, {line_count} lines")


def run_all_tests() -> Tuple[List[TestResult], int, int]:
    """Run all tests and return results."""
    tests = [
        test_evaluation_report_exists,
        test_verification_plan_exists,
        test_evaluation_report_structure,
        test_tool_availability_claims,
        test_decision_recommendation_present,
        test_api_documentation_quality,
        test_comparison_tables_present,
        test_decision_tree_present,
        test_verification_completeness,
        test_reevaluation_criteria_defined,
        test_report_word_count,
    ]

    results = []
    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            results.append(result)
            if result.passed:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            results.append(TestResult(test.__name__, False, f"Exception: {e}"))
            failed += 1

    return results, passed, failed


def main():
    """Main test runner."""
    print("=" * 60)
    print("POC-1769187675 Test Suite")
    print("Native Task Integration Evaluation Verification")
    print("=" * 60)
    print()

    results, passed, failed = run_all_tests()

    print("Test Results:")
    print("-" * 60)
    for result in results:
        print(result)

    print()
    print("-" * 60)
    print(f"Total: {len(results)} tests | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    if failed > 0:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
