# Navigator v5.7.0 Release Notes

**Release Date**: 2025-01-22
**Type**: Minor Release (Feature Management)

---

## Summary

Navigator v5.7.0 introduces **nav-features**—a skill for viewing and toggling Navigator features. On first session after install or update, users see a feature table showing what's enabled.

---

## New Skill: nav-features

### Feature Table Display

```
v5.7.0 Features Now Enabled:

┌─────────────────┬────────┬─────────────────────────────────────────────────┐
│ Feature         │ Status │ Description                                     │
├─────────────────┼────────┼─────────────────────────────────────────────────┤
│ task_mode       │ ✅      │ Auto-detects task complexity, defers to skills  │
│ tom_features    │ ✅      │ Verification checkpoints, user profile, diag... │
│ loop_mode       │ ⏸ Off  │ Autonomous loop execution (enable when needed)  │
│ simplification  │ ✅      │ Post-implementation code cleanup with Opus      │
│ auto_update     │ ✅      │ Auto-updates on session start                   │
└─────────────────┴────────┴─────────────────────────────────────────────────┘
```

### Commands

```bash
# Show all features
"show my features"

# Enable a feature
"enable loop_mode"

# Disable a feature
"disable simplification"

# Get feature details
"tell me about task_mode"
```

---

## First-Session Display

On first session after install or version update:
1. Feature table automatically displayed
2. Hint shown: "Toggle features: 'show my features'"
3. Uses version-specific marker (won't repeat same version)

**Benefits**:
- Users discover available features
- Can disable unused features to save tokens
- Clear visibility into what's enabled

---

## Files Changed

| File | Change |
|------|--------|
| `skills/nav-features/SKILL.md` | New skill |
| `skills/nav-features/functions/feature_manager.py` | Feature management logic |
| `skills/nav-start/SKILL.md` | First-session trigger |
| `.claude-plugin/plugin.json` | Registered skill, v5.7.0 |
| `.claude-plugin/marketplace.json` | v5.7.0 |
| `README.md` | 27 skills, v5.7.0 |
| `CLAUDE.md` | v5.7.0 notes |

---

## Upgrade Path

**From v5.6.0**: No breaking changes.

1. Update plugin: `/plugin update navigator`
2. First session will show feature table
3. Toggle features as needed

---

## Skills Count

Navigator now includes **27 skills**:
- nav-features (new)
- nav-task-mode, nav-simplify, nav-onboard, nav-init, nav-start
- nav-stats, nav-profile, nav-diagnose, nav-loop, nav-update-claude
- nav-upgrade, nav-install-multi-claude, nav-marker, nav-compact
- nav-task, nav-sop, nav-skill-creator, nav-release
- plugin-slash-command, product-design, visual-regression
- frontend-component, backend-endpoint, database-migration
- backend-test, frontend-test

---

## Version History

### v5.7.0 (This Release)
- **NEW**: nav-features skill
- **NEW**: First-session feature display
- **NEW**: Feature enable/disable commands

### v5.6.0
- Task Mode - unified workflow orchestration
- nav-task-mode skill

### v5.5.0
- Auto-Update on Session Start

### v5.4.0
- Code Simplification (nav-simplify)

---

**Full Changelog**: https://github.com/alekspetrov/navigator/compare/v5.6.0...v5.7.0
