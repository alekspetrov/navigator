# Navigator v6.8.0 Release Notes

**Release Date**: 2026-05-11
**Type**: Minor Release (TASK-37 — nav-simplify ROI Scoring)

---

## Summary

TASK-37 ships. The `nav-simplify` analyzer gains a cost/benefit ROI score so it can answer "should I simplify this file?" — not just "is there mess here?".

Deferred three times (v6.3.0, v6.5.0, v6.6.0) and captured as a design doc in v6.7.0. v6.8.0 implements the design, calibrates the weights against this repo's files, and ships the gate behind an opt-in config flag.

Default behavior is unchanged. `simplification.scoring.mode: "roi"` activates the gate.

---

## What's New

### Cost analyzer (`skills/nav-simplify/scripts/cost_analyzer.py`)

New module. Four cost signals, each normalized to 0–10 and weighted:

| Signal | Measure | Weight |
|---|---|---|
| Change surface | Estimated lines touched (per-issue-type fix-size table) | 0.3 |
| File LOC | `log10(loc) × 2.5` — bigger files = bigger blast radius | 0.2 |
| Recency penalty | Days since last `git log -1 --format=%ct` — older = higher cost | 0.3 |
| Import references | `git grep` count of `import|from .* <stem>` outside this file | 0.2 |

Per-type fix-size estimates (lines touched):
- `deep_nesting`: 12
- `nested_ternary`: 6
- `long_function`: 20
- `unclear_naming`: 2
- `redundant_comparison`: 1

### Benefit scoring (in `code_analyzer.py`)

Composed of:

| Signal | Measure | Weight |
|---|---|---|
| Issue density | `issues / loc × 100`, capped at 10 | 0.4 |
| Severity-weighted impact | `Σ(severity × type_weight)`, normalized | 0.4 |
| Active diff signal | File appears in `git diff` (uncommitted, cached, or last commit) | 0.2 |

Per-type benefit weights (TYPE_WEIGHTS in `code_analyzer.py:25`):
- `deep_nesting`: 3.0
- `nested_ternary`: 2.5
- `long_function`: 2.0
- `unclear_naming`: 1.0
- `redundant_comparison`: 0.5

### ROI gate

```
ROI = B / max(C, cost_floor)   # default cost_floor = 0.5
```

Three-tier gate based on ROI:

| ROI | Action | Effect |
|---|---|---|
| `< skip_below` (default 0.5) | `skip` | Don't simplify. Emit a one-line skip reason. |
| `skip_below ≤ ROI < auto_apply_at` (default 1.5) | `suggest` | Force interactive mode regardless of `auto_apply`. |
| `≥ auto_apply_at` | `apply` | Proceed with current behavior, honor `auto_apply`. |

### Output shape

When `--scoring roi` is passed (or `mode: "roi"` is set in config), `analyze_file()` adds four fields:

```json
{
  "complexity_score": 7.2,
  "benefit_score": 6.1,
  "cost_score": 4.3,
  "roi_score": 1.42,
  "gate_action": "suggest",
  "scoring_explanation": {
    "benefit": {"issue_density": 0.4, "severity_impact": 5.2, "in_active_diff": true},
    "cost": {"estimated_touch_lines": 32, "file_loc": 287, "days_since_modified": 12, "import_references": 3},
    "thresholds": {"skip_below": 0.5, "suggest_below": 1.5, "auto_apply_at": 1.5},
    "cost_floor": 0.5
  }
}
```

`scoring_explanation` makes the gate decision auditable.

### Config (opt-in)

In `.agent/.nav-config.json`:

```json
{
  "simplification": {
    "scoring": {
      "mode": "roi",
      "skip_below": 0.5,
      "suggest_below": 1.5,
      "auto_apply_at": 1.5,
      "cost_floor": 0.5
    }
  }
}
```

Omitting `scoring` or setting `mode: "complexity"` keeps legacy behavior.

---

## Calibration

ROI ordering validated on this repo's actual files:

| File | Complexity | Benefit | Cost | ROI | Gate |
|---|---|---|---|---|---|
| `code_analyzer.py` (active diff, dense) | 10.0 | 9.92 | 4.29 | **2.31** | apply |
| `stagnation_detector.py` | 10.0 | 6.51 | 4.12 | **1.58** | apply |
| `skill_detector.py` | 10.0 | 6.67 | 4.25 | **1.57** | apply |
| `cost_analyzer.py` (active diff, clean) | 7.0 | 6.12 | 4.06 | **1.51** | apply |
| `exit_gate.py` | 7.5 | 5.71 | 4.03 | **1.42** | suggest |
| `simplification_rules.py` (older) | 10.0 | 8.00 | 6.57 | **1.22** | suggest |
| `change_reporter.py` (older, larger) | 8.0 | 5.70 | 6.53 | **0.87** | suggest |

The ordering matches gut check: active-diff messy files prioritize, older files de-prioritize, clean files get no ROI emission (skipped via existing complexity flow). Default weights ship as designed.

---

## Tests

`skills/nav-simplify/scripts/test_roi_scoring.py` — 20 unit tests covering:

- `estimate_touch_lines`: empty, known types, unknown type fallback
- `compute_benefit_score`: no-issues zero, active-diff lift, severity sensitivity, cap-at-10
- `compute_cost_score`: shape, file-size sensitivity, touch-line sensitivity
- `compute_roi_score`: basic ratio, cost-floor protection, custom floors
- `roi_gate_action`: skip/suggest/apply thresholds, boundaries, custom thresholds
- Integration: ROI ordering on synthetic high-vs-low scenarios

All passing: `python3 test_roi_scoring.py` → 20 OK.

---

## Backward Compatibility

- `complexity_score` unchanged for existing consumers
- Default `scoring.mode` is `"complexity"` — legacy behavior preserved
- No config migration required
- All existing nav-simplify tests continue to pass

---

## Why This Matters

`nav-simplify` runs autonomously when `auto_apply: true`. Without ROI gating, it can produce churn-for-churn's-sake: 30 trivial renames on a stable file, no real readability gain, fresh chance for regressions, noisy diff.

The autoresearch-style "ship value, not motion" principle from v6.3.0 applies here too. The simplifier now *declines* to simplify when:
- File is stable (older = higher regression risk)
- Widely imported (blast-radius cost)
- Issues are cosmetic only (low benefit weight)
- Not in active development

And it *prioritizes* when:
- File is in the current diff (author has it in head, cheap to touch)
- Issues are structural (deep nesting, long functions)
- Issue density is high relative to file size

---

## Files Modified

```
skills/nav-simplify/scripts/cost_analyzer.py        — NEW (cost signals)
skills/nav-simplify/scripts/code_analyzer.py        — benefit + ROI + gate
skills/nav-simplify/scripts/test_roi_scoring.py     — NEW (20 unit tests)
skills/nav-simplify/SKILL.md                        — Step 4.5 gate doc + config
.claude-plugin/{plugin,marketplace}.json            — version 6.8.0
.agent/.nav-config.json                             — version 6.8.0
CHANGELOG.md, CLAUDE.md, README.md                  — version stamps
releases/RELEASE-NOTES-v6.8.0.md                    — these notes
```

---

## Knowledge Graph

Memories worth keeping from this session:

- **Pattern**: ROI ordering on this repo's files matches gut check with default weights (0.4/0.4/0.2 benefit; 0.3/0.2/0.3/0.2 cost; cost_floor 0.5). No tuning needed for current codebase.
- **Pitfall**: `cd` in Bash tool breaks the `monitor-tokens.py` PostToolUse hook (relative path resolves from new cwd). Use absolute paths.

---

## Open Items (still deferred)

- **Per-issue ROI** (TASK-37 v2) — currently per-file only; per-issue would let the gate pick *which* fixes apply when not all are worth it
- **Language-specific import resolution** — current `import_reference_count` is a grep heuristic; per-language parsers would be more accurate but slower to build
- **`database-migration` per-framework template extraction** — still deferred
- **Social card + Threads posts** for v6.3.0 – v6.8.0 — none drafted

---

## Upgrade

```
claude plugin update navigator
# restart Claude Code to load updated config
```

ROI scoring is opt-in. To enable, add to `.agent/.nav-config.json`:

```json
{
  "simplification": {
    "scoring": { "mode": "roi" }
  }
}
```
