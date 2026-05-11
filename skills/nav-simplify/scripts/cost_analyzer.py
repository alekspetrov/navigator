#!/usr/bin/env python3
"""
Cost Analyzer for Navigator Simplification Skill (TASK-37)

Estimates the cost of simplifying a file across four signals:
    1. Change surface   — estimated lines touched per issue type
    2. File LOC         — bigger files = larger blast radius
    3. Recency penalty  — older code = higher regression risk
    4. Import refs      — public/widely-used files = higher cost

All signals normalize into a single 0–10 cost score, weighted per the
TASK-37 design (0.3 / 0.2 / 0.3 / 0.2).

Used by ``code_analyzer.py`` when ``simplification.scoring.mode == "roi"``.
"""

from __future__ import annotations

import math
import re
import subprocess
import time
from pathlib import Path
from typing import Any

# Per-issue-type fix-size estimates (lines touched). Educated guesses;
# calibrate via TASK-37 Phase 5 on real files.
FIX_SIZE_BY_TYPE: dict[str, int] = {
    "deep_nesting": 12,
    "nested_ternary": 6,
    "long_function": 20,
    "unclear_naming": 2,
    "redundant_comparison": 1,
}

# Default weights for the cost components (sum to 1.0).
DEFAULT_COST_WEIGHTS: dict[str, float] = {
    "touch_lines": 0.3,
    "file_loc": 0.2,
    "recency": 0.3,
    "imports": 0.2,
}


def estimate_touch_lines(issues: list[dict[str, Any]]) -> int:
    """Estimate the number of source lines a fix would touch."""
    return sum(FIX_SIZE_BY_TYPE.get(issue.get("type", ""), 3) for issue in issues)


def file_recency_days(path: str | Path) -> int:
    """Return days since the file's last commit. Returns 0 if not in git or unknown."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        out = result.stdout.strip()
        if not out:
            return 0
        last_commit_ts = int(out)
        days = (time.time() - last_commit_ts) / 86400
        return max(0, int(days))
    except (subprocess.SubprocessError, ValueError, OSError):
        return 0


def import_reference_count(path: str | Path, repo_root: str | Path | None = None) -> int:
    """Count references to this file's stem in ``import``/``from`` statements.

    Language-agnostic heuristic — works reasonably for Python, JS, TS, Go.
    Returns 0 if the search fails or the file has no useful stem.
    """
    path = Path(path)
    stem = path.stem
    if not stem or stem in {"index", "mod", "main"}:
        return 0

    root = Path(repo_root) if repo_root else Path.cwd()

    try:
        result = subprocess.run(
            [
                "git",
                "grep",
                "-l",
                "-E",
                rf"(import|from)\s+.*\b{re.escape(stem)}\b",
                "--",
                ":!{}".format(path.name),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=str(root),
            check=False,
        )
        if result.returncode > 1:
            return 0
        files = [f for f in result.stdout.strip().split("\n") if f]
        return len(files)
    except (subprocess.SubprocessError, OSError):
        return 0


def _normalize_touch_lines(touch_lines: int) -> float:
    """Map touch lines → 0–10 via a soft curve (saturates near 50 lines)."""
    return min(10.0, math.log1p(touch_lines) * 2.5)


def _normalize_file_loc(loc: int) -> float:
    """Map file LOC → 0–10 (log10-scaled, saturates near 10k lines)."""
    if loc <= 10:
        return 0.0
    return min(10.0, math.log10(loc) * 2.5)


def _normalize_recency(days: int) -> float:
    """Map days-since-last-commit → 0–10.

    0 days → 0 (cheap), 30 days → ~3, 180 days → ~7, 365+ days → 10.
    """
    if days <= 0:
        return 0.0
    return min(10.0, math.log1p(days) * 1.7)


def _normalize_imports(refs: int) -> float:
    """Map import-reference count → 0–10."""
    return min(10.0, math.log1p(refs) * 3.0)


def compute_cost_score(
    issues: list[dict[str, Any]],
    loc: int,
    path: str | Path,
    repo_root: str | Path | None = None,
    weights: dict[str, float] | None = None,
) -> tuple[float, dict[str, Any]]:
    """Compute weighted cost score and an audit-friendly explanation."""
    w = weights or DEFAULT_COST_WEIGHTS

    touch_lines = estimate_touch_lines(issues)
    days = file_recency_days(path)
    refs = import_reference_count(path, repo_root)

    score = (
        _normalize_touch_lines(touch_lines) * w["touch_lines"]
        + _normalize_file_loc(loc) * w["file_loc"]
        + _normalize_recency(days) * w["recency"]
        + _normalize_imports(refs) * w["imports"]
    )

    explanation = {
        "estimated_touch_lines": touch_lines,
        "file_loc": loc,
        "days_since_modified": days,
        "import_references": refs,
    }
    return round(score, 2), explanation
