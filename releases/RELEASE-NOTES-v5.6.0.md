# Navigator v5.6.0 Release Notes

**Release Date**: 2025-01-22
**Type**: Minor Release (Unified Workflow Architecture)

---

## Summary

Navigator v5.6.0 introduces **Task Mode**—unified workflow orchestration that resolves conflicts between skills, loop mode, and CLAUDE.md workflows. Task Mode auto-detects complexity and routes requests to the appropriate handler.

---

## The Problem Solved

Navigator had three disconnected workflow systems:
1. **Skills** (frontend-component, etc.) - have mini-workflows (Step 1 → Step 7)
2. **Loop Mode** - separate phase system (INIT → COMPLETE)
3. **CLAUDE.md** - documents workflow nobody enforces

**Result**: Conflicts when multiple systems tried to run simultaneously.

---

## Task Mode Architecture

```
User Request
    ↓
TASK MODE (auto-detect)
    ├─ Simple task? → Direct execution (no overhead)
    ├─ Skill matches? → Let skill run (it has workflow)
    └─ Substantial, no skill? → Task Mode phases
```

### Complexity Detection

Task Mode analyzes requests and calculates a complexity score (0-1):

| Signal | Weight | Example |
|--------|--------|---------|
| Multi-file changes | +0.3 | "refactor", "migrate", "across files" |
| Planning language | +0.2 | "implement", "add feature" |
| Cross-system | +0.3 | "frontend and backend" |
| Fix/typo language | -0.2 | "fix typo", "small change" |
| Quick modifier | -0.2 | "just", "quick", "simple" |

### Skill Deferral

When a skill matches the request (confidence ≥ 50%), Task Mode defers:

```
User: "Create a UserProfile component"
→ Skill match: frontend-component (95% confidence)
→ Task Mode defers: "frontend-component skill will handle this"
```

### Phase Guidance

For substantial tasks without skill matches, Task Mode provides phase tracking:

```
RESEARCH → PLAN → IMPL → VERIFY → COMPLETE
```

---

## New Skill: nav-task-mode

### Files Created

| File | Purpose |
|------|---------|
| `skills/nav-task-mode/SKILL.md` | Skill documentation |
| `skills/nav-task-mode/functions/complexity_detector.py` | Analyzes task complexity |
| `skills/nav-task-mode/functions/skill_detector.py` | Matches requests to skills |
| `skills/nav-task-mode/functions/phase_indicator.py` | Visual phase indicators |

### Configuration

```json
{
  "task_mode": {
    "enabled": true,
    "auto_detect": true,
    "defer_to_skills": true,
    "complexity_threshold": 0.5,
    "show_phase_indicator": true
  }
}
```

---

## Verification Results

```
Test 1: "Fix typo in README"
→ Complexity: 0.30
→ Result: Direct execution (below threshold)

Test 2: "Create a LoginButton component"
→ Skill match: frontend-component (55%)
→ Result: Defers to skill

Test 3: "Refactor auth to use JWT"
→ Complexity: 0.95, No skill match
→ Result: Task Mode activates
```

---

## Task Mode vs Loop Mode

| Aspect | Task Mode | Loop Mode |
|--------|-----------|-----------|
| Activation | Auto-detect | Explicit trigger |
| Iteration | None | EXIT_SIGNAL required |
| Skill coordination | Defers to skills | Independent |
| Best for | Features | Autonomous work |

**Can coexist**: Loop Mode wraps Task Mode phases if both active.

---

## Files Changed

| File | Change |
|------|--------|
| `skills/nav-task-mode/` | New skill directory |
| `.agent/.nav-config.json` | Added task_mode config, version 5.6.0 |
| `CLAUDE.md` | Added Task Mode section, version 5.6.0 |
| `.claude-plugin/plugin.json` | Registered skill, version 5.6.0 |
| `.claude-plugin/marketplace.json` | Version 5.6.0 |
| `README.md` | Updated version badge |

---

## Upgrade Path

**From v5.5.0**: No breaking changes.

1. Update plugin: `/plugin update navigator`
2. Task Mode activates automatically based on config defaults
3. Optional: Adjust `complexity_threshold` in `.nav-config.json`

**Backward compatible**: All v5.5.0 features continue unchanged.

---

## Version History

### v5.6.0 (This Release)
- **NEW**: Task Mode - unified workflow orchestration
- **NEW**: nav-task-mode skill with complexity/skill detection
- **NEW**: Phase indicators for substantial tasks
- **FIXED**: Workflow conflicts between skills and loop mode

### v5.5.0
- Auto-Update on Session Start
- Automatic plugin updates when newer version detected

### v5.4.0
- Code Simplification (nav-simplify)
- Clarity over brevity improvements

### v5.3.0
- Task Verification Enhancement
- Verify/Done sections in task docs

### v5.2.0
- "Finish What You Start" positioning
- README rewrite

### v5.1.0
- Loop Mode with structured completion signals
- Dual-condition exit gate

### v5.0.0
- Theory of Mind integration
- nav-profile, nav-diagnose skills

---

## Skills Count

Navigator now includes **26 skills** (up from 25):
- nav-task-mode (new)
- nav-simplify, nav-onboard, nav-init, nav-start, nav-stats
- nav-profile, nav-diagnose, nav-loop, nav-update-claude, nav-upgrade
- nav-install-multi-claude, nav-marker, nav-compact, nav-task, nav-sop
- nav-skill-creator, nav-release, plugin-slash-command
- product-design, visual-regression
- frontend-component, backend-endpoint, database-migration
- backend-test, frontend-test

---

**Full Changelog**: https://github.com/alekspetrov/navigator/compare/v5.5.0...v5.6.0
