# TASK-37: nav-simplify Complexity-Cost Scoring

**Status**: 📐 Design (not yet implemented)
**Created**: 2026-05-11
**Priority**: Medium
**Deferred from**: v6.3.0, v6.5.0, v6.6.0 (cited 3x in markers)

---

## Summary

Move `nav-simplify` from a one-dimensional "how messy is this?" complexity score to a two-dimensional **cost/benefit ROI score** so it can answer "should I simplify this file, and if so, what?" — not just "is there mess here?".

Current scoring (`skills/nav-simplify/scripts/code_analyzer.py:197`):

```python
severity_weights = {"high": 3.0, "medium": 2.0, "low": 1.0}
total_weight = sum(weights.get(issue["severity"], 1.0) for issue in issues)
score = min(total_weight / 2, 10.0)
```

Tells us the file has issues. Doesn't tell us if fixing them is worth the refactor risk.

---

## Problem Statement

### What's wrong with the current score

| Problem | Example |
|---|---|
| **No file-size normalization** | 5 issues in 50 LOC ≠ 5 issues in 500 LOC |
| **No cost dimension** | Renaming `x` is cheap. Extracting a 5-deep nest into helpers is expensive. Both currently weight the same. |
| **No staleness signal** | Recently-written code is cheap to touch (author still has it in head). Stable code from 18 months ago is expensive (regression risk). |
| **No blast-radius signal** | Public/widely-imported files are higher-cost than private helpers. |
| **No "skip-it" threshold** | Score of 3.2 in a low-stakes file vs 3.2 in a hot path — both get the same treatment. |

### Why it matters

`nav-simplify` runs autonomously (`auto_apply: true` in autonomous flows). Without ROI gating, it can produce churn-for-churn's-sake: 30 trivial renames on a stable file, no real readability gain, but a noisy diff and a fresh chance for regressions.

The autoresearch-style "ship value, not motion" principle from v6.3.0 applies here too. The simplifier should *decline* to simplify when the math doesn't favor it.

---

## Design

### Dimensions

#### Benefit (B) — what clarity gains we get

Composed of:

| Signal | How to measure | Weight |
|---|---|---|
| Issue density | `total_issues / max(LOC, 1)` | 0.4 |
| Severity-weighted impact | sum of (severity × type_weight) | 0.4 |
| Forward-touch likelihood | Is the file in the current diff? `git diff --name-only HEAD~1` | 0.2 |

`type_weight` lets different issue types contribute differently to benefit:
- `deep_nesting`: 3.0 (high readability gain)
- `nested_ternary`: 2.5
- `long_function`: 2.0
- `unclear_naming`: 1.0
- `redundant_comparison`: 0.5 (cosmetic)

#### Cost (C) — what the fix risks

Composed of:

| Signal | How to measure | Weight |
|---|---|---|
| Change surface | Estimated lines touched per fix (per issue type table) | 0.3 |
| File LOC | `log10(max(LOC, 10))` — bigger files = bigger blast radius | 0.2 |
| Recency penalty | Days since last `git log -1 --format=%ct <file>` — older = higher cost | 0.3 |
| Public-API proxy | Count of `import` / `from` references to this file from elsewhere in the repo | 0.2 |

Both B and C normalize to a 0–10 scale.

#### ROI

```
ROI = B / max(C, 0.5)   # floor avoids divide-by-zero churn
```

Single number per file. Higher = more worth simplifying.

### Per-issue vs per-file

**Decision: per-file initially.** Per-issue ROI is more granular but multiplies the surface area (need to estimate cost per fix individually). Per-file is enough to answer the gating question — "should we touch this file at all?" — and avoids over-engineering for v1.

Future: per-issue ROI inside files above the gate, to pick *which* fixes to apply when not all are worth it.

### Thresholds

Configurable in `.agent/.nav-config.json` under `simplification.scoring`:

```json
{
  "simplification": {
    "scoring": {
      "mode": "roi",
      "skip_below": 0.5,
      "suggest_below": 1.5,
      "auto_apply_at": 1.5
    }
  }
}
```

| ROI | Action |
|---|---|
| `< skip_below` | Skip entirely, emit `"low ROI"` reason |
| `skip_below ≤ ROI < auto_apply_at` | Suggest only, never auto-apply |
| `≥ auto_apply_at` | Auto-apply if `auto_apply: true` |

### Backward compatibility

Don't remove the existing `complexity_score`. Add three new fields to the analyzer output:

```json
{
  "complexity_score": 7.2,
  "benefit_score": 6.1,
  "cost_score": 4.3,
  "roi_score": 1.4,
  "scoring_explanation": {
    "benefit": {
      "issue_density": 0.4,
      "severity_impact": 5.2,
      "in_active_diff": true
    },
    "cost": {
      "estimated_touch_lines": 32,
      "file_loc": 287,
      "days_since_modified": 12,
      "import_references": 3
    }
  }
}
```

`scoring_explanation` makes ROI auditable — when the simplifier skips a file, the user can see *why*.

### Mode flag for migration

```json
{ "simplification": { "scoring": { "mode": "complexity" | "roi" } } }
```

- `"complexity"` (default): legacy behavior, ignore ROI
- `"roi"`: gate decisions on ROI

Lets users opt in. Eventually flip default to `"roi"` in a minor release.

---

## Implementation Plan (when picked up)

### Phase 1: Cost signals
1. Add `cost_analyzer.py` to `skills/nav-simplify/scripts/`
2. Functions:
   - `estimate_touch_lines(issues)` → int (uses per-type fix-size table)
   - `file_recency_days(path)` → int (via `git log -1 --format=%ct`)
   - `import_reference_count(path, repo_root)` → int (grep for relative imports of this file's stem; language-agnostic heuristic)
   - `compute_cost_score(...)` → float

### Phase 2: Benefit signals
1. Extend `code_analyzer.py` with:
   - `compute_benefit_score(issues, loc, in_diff)` → float
   - Read `type_weights` table (configurable in nav-config)

### Phase 3: Wire into `code_analyzer.analyze_file()`
1. Compute B, C, ROI
2. Add `scoring_explanation` to output JSON
3. Honor `scoring.mode` from config

### Phase 4: Wire into SKILL.md flow
1. Step 4.5 (new): "Check ROI gate"
   - If ROI < `skip_below`: emit skip reason, continue to next file
   - If ROI in suggest range: force interactive mode regardless of `auto_apply`
   - If ROI ≥ `auto_apply_at`: proceed with current behavior

### Phase 5: Tests
1. Unit tests for cost signals (synthetic git repo fixture for recency / imports)
2. Snapshot tests on real `.py` files in this repo: verify reasonable ROI ordering

### Phase 6: Docs
1. Update `skills/nav-simplify/SKILL.md` Step 4 and 7
2. Add example outputs showing skip-with-reason
3. CHANGELOG note: opt-in ROI mode in vX.X.X

---

## Open Questions

1. **`import_reference_count` portability** — Python / JS / TS imports look very different. Initial heuristic: grep for filename stem appearing in `import` or `from` statements anywhere under repo root. Crude but language-agnostic. Refine per-language later if signal is poor.

2. **`type_weights` source** — config file or hardcoded with override? Suggest: hardcoded defaults in `code_analyzer.py`, overridable via `simplification.scoring.type_weights` in nav-config.

3. **Floor on cost** — `max(C, 0.5)` prevents ROI explosions on near-zero-cost files. Is 0.5 right? Probably needs tuning on real data.

4. **"In active diff" definition** — `git diff --name-only HEAD~1` vs `git diff --name-only main...HEAD` vs `git diff --name-only --cached`. The autonomous-completion flow runs *before commit*, so cached + unstaged is probably right. Worth testing.

5. **What about test files?** Tests are already skipped via `skip_patterns`. ROI doesn't apply.

6. **Per-issue ROI as v2?** If per-file ROI passes but only 2/10 issues in the file are individually worth fixing, do we apply all 10 or just 2? Probably out of scope for v1 — apply all when file passes.

---

## Done (when implemented)

- [ ] `code_analyzer.py` outputs `benefit_score`, `cost_score`, `roi_score`, `scoring_explanation`
- [ ] `scoring.mode` config flag honored (`complexity` default, `roi` opt-in)
- [ ] `simplification.scoring.{skip_below, suggest_below, auto_apply_at}` configurable
- [ ] SKILL.md Step 4.5 implements the gate
- [ ] Skip emits a reason explaining the ROI math
- [ ] Tests cover cost signals and gate logic
- [ ] Existing `complexity_score` unchanged (no regression for users on default mode)

---

## Why this is a design, not an implementation

Three reasons we deferred this three times:

1. **The ROI math needs real-data calibration.** The weight tables (0.4/0.4/0.2 for benefit, 0.3/0.2/0.3/0.2 for cost) are educated guesses. We should pick them after running the analyzer on a sample of files and confirming the ordering matches intuition.

2. **Type-weight table is opinion.** Whether `deep_nesting` is "worth" 3.0 and `unclear_naming` is worth 1.0 is a project-aesthetics call. Worth a discussion / one-pager review before locking in.

3. **The cost signals are heuristics.** Especially `import_reference_count` — language-specific implementations would be more accurate but slower to build. The minimum-viable grep-based version may produce noise we'd want to evaluate before shipping.

Next session can pick this up by tuning weights on this repo's actual files and confirming the ROI ordering matches the "yeah, I'd touch that one but not that one" gut check.
