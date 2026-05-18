# TASK-12: v3.0 Skills-Only Migration

**Status**: 📋 In Progress
**Version**: 3.0.0
**Created**: 2025-10-19
**Type**: Breaking Change (Major Version)

---

## Executive Summary

**Goal**: Remove all slash commands, make Navigator 100% skills-only with natural language interface.

**Impact**:
- 11k token reduction (commands overhead eliminated)
- Natural language only ("Start my session" vs `/nav:start`)
- Cleaner architecture (no hybrid overhead)
- Breaking change (v3.0 major version bump)

**Timeline**: Accelerated (skip v2.5 deprecation phase)

---

## Context

### Current State (v2.3.0)

**Hybrid Architecture**:
- ✅ 12 skills (7 core + 5 project-specific + nav-markers)
- ⚠️ 13 commands (7 main + 6 backward-compatible)
- Both work simultaneously (no conflicts)

**File Structure**:
```
navigator/
├── commands/               # TO BE REMOVED
│   ├── init.md
│   ├── start.md
│   ├── doc.md
│   ├── marker.md
│   ├── markers.md
│   ├── compact.md
│   ├── migrate.md
│   ├── _jitd_init.md       # v1.x compat
│   ├── _jitd_start.md
│   ├── _jitd_marker.md
│   ├── _jitd_markers.md
│   ├── _jitd_compact.md
│   └── _jitd_update_doc.md
│
└── skills/                 # KEEP
    ├── nav-start/
    ├── nav-marker/
    ├── nav-markers/
    ├── nav-compact/
    ├── nav-task/
    ├── nav-sop/
    ├── nav-skill-creator/
    ├── plugin-slash-command/
    ├── frontend-component/
    ├── backend-endpoint/
    ├── database-migration/
    ├── backend-test/
    └── frontend-test/
```

### Why Skip v2.5 Deprecation Phase?

**Original Plan (TASK-07)**:
- v2.5: Add deprecation warnings, 6-month migration
- v3.0: Remove commands after user adoption

**New Plan (Accelerated)**:
- v3.0: Remove commands immediately
- Users already have skills (v2.0-v2.3)
- Natural language works today

**Rationale**:
1. **Skills work perfectly** (proven in v2.0-v2.3)
2. **No user complaints** about natural language
3. **Deprecation overhead** unnecessary (skills auto-invoke)
4. **Cleaner faster** (skip 6-month warning period)

---

## Implementation Plan

### Phase 1: Preparation ✅ (Already Done)

**Status**: Complete (v2.0-v2.3)
- [x] All core skills created (nav-start, nav-marker, etc.)
- [x] Skills tested and working
- [x] Auto-invocation verified
- [x] Natural language interface proven

### Phase 2: Breaking Changes (v3.0)

**Step 1: Remove Commands Directory**
```bash
rm -rf commands/
```

**Step 2: Update plugin.json**
```json
{
  "name": "navigator",
  "version": "3.0.0",
  "commands": [],  // Empty - no commands
  "skills": [
    "./skills/nav-start",
    "./skills/nav-marker",
    "./skills/nav-markers",
    "./skills/nav-compact",
    "./skills/nav-task",
    "./skills/nav-sop",
    "./skills/nav-skill-creator",
    "./skills/plugin-slash-command",
    "./skills/frontend-component",
    "./skills/backend-endpoint",
    "./skills/database-migration",
    "./skills/backend-test",
    "./skills/frontend-test"
  ]
}
```

**Step 3: Update marketplace.json**
```json
{
  "plugins": [
    {
      "id": "navigator",
      "version": "3.0.0",
      "breaking_changes": [
        "Removed all slash commands (/nav:*)",
        "Use natural language instead",
        "Skills auto-invoke based on intent"
      ]
    }
  ]
}
```

**Step 4: Update CLAUDE.md Template**

Remove all command references:
```diff
- /nav:init          # Initialize Navigator
- /nav:start         # Start session
+ "Initialize Navigator in this project"
+ "Start my Navigator session"
```

Update workflow examples to show natural language only.

**Step 5: Update README.md**

Remove slash commands section, add migration guide:
```markdown
## 🚨 Breaking Change: v3.0

Navigator v3.0 removes all slash commands. Use natural language instead.

### Migration Guide

**Before (v2.x)**:
```
/nav:init
/nav:start
/nav:marker checkpoint
```

**After (v3.0)**:
```
"Initialize Navigator in this project"
"Start my Navigator session"
"Create a checkpoint marker"
```

Skills auto-invoke - no manual commands needed.
```

**Step 6: Update Documentation**

Files to update:
- `.agent/DEVELOPMENT-README.md` - Remove command references
- `.agent/system/project-architecture.md` - Skills-only architecture
- `templates/CLAUDE.md` - Natural language examples
- `README.md` - Migration guide + v3.0 announcement

---

## Testing Plan

### Manual Testing

**Test 1: Init without command**
```
User: "Initialize Navigator in this project"
Expected: nav-init skill auto-invokes
Result: [ ]
```

**Test 2: Start without command**
```
User: "Start my Navigator session"
Expected: nav-start skill auto-invokes
Result: [ ]
```

**Test 3: Marker without command**
```
User: "Create a checkpoint marker called feature-complete"
Expected: nav-marker skill auto-invokes
Result: [ ]
```

**Test 4: Task documentation without command**
```
User: "Archive this task documentation"
Expected: nav-task skill auto-invokes
Result: [ ]
```

**Test 5: Compact without command**
```
User: "Clear context but preserve markers"
Expected: nav-compact skill auto-invokes
Result: [ ]
```

### Test in nav-test Project

```bash
cd ~/Projects/tmp/nav-test
rm -rf .agent  # Clean slate

# Test init
"Initialize Navigator in this project"
→ Should create .agent/ structure

# Test start
"Start my Navigator session"
→ Should load navigator, show stats

# Test marker
"Create a marker called test-checkpoint"
→ Should create marker file

# Test compact
"Clear context and preserve markers"
→ Should create active marker
```

---

## Migration Guide for Users

### For Existing Navigator Users (v2.x → v3.0)

**You need to change**: Nothing (if you use natural language)
**You need to stop**: Using `/nav:*` commands (they're gone)

**Command → Natural Language Map**:

| Old Command | Natural Language (v3.0) |
|------------|------------------------|
| `/nav:init` | "Initialize Navigator in this project" |
| `/nav:start` | "Start my Navigator session" / "Load the navigator" |
| `/nav:doc feature TASK-X` | "Archive TASK-X documentation" |
| `/nav:marker name` | "Create a marker called [name]" |
| `/nav:markers` | "Show my markers" / "Load a marker" |
| `/nav:compact` | "Clear context and preserve markers" |
| `/nav:migrate` | Not needed (v3.0 is skills-only) |

**Skills auto-invoke** - just describe what you want.

### For New Users (v3.0)

**No commands to learn!**

Just tell Claude what you want:
- "Initialize Navigator"
- "Start my session"
- "Create a checkpoint"
- "Archive this task"

Skills automatically activate based on your intent.

---

## Version Sync Checklist

**Before v3.0 release, update ALL version references**:

- [ ] `.claude-plugin/plugin.json` → `"version": "3.0.0"`
- [ ] `.claude-plugin/marketplace.json` → `"version": "3.0.0"`
- [ ] `.agent/.nav-config.json` → `"version": "3.0.0"`
- [ ] `README.md` line ~5 → `v3.0.0`
- [ ] `README.md` line ~8 (badge) → `3.0.0`
- [ ] `README.md` footer → `3.0.0`
- [ ] `.agent/DEVELOPMENT-README.md` bottom → `(v3.0.0)`
- [ ] Git tag → `v3.0.0`
- [ ] GitHub release → `v3.0.0`

**Run audit script**:
```bash
./scripts/version-audit.sh 3.0.0
```

---

## Risks & Mitigation

### Risk 1: Users Still Type Commands

**Problem**: Muscle memory - users type `/nav:start`
**Impact**: Command not found error
**Mitigation**:
- Clear error message: "Commands removed in v3.0. Use: 'Start my Navigator session'"
- Migration guide in README
- v3.0 announcement explains change

**Likelihood**: High (first week)
**Severity**: Low (easy fix)

### Risk 2: Skill Auto-Invocation Fails

**Problem**: Natural language doesn't match skill description
**Impact**: Skill doesn't activate
**Mitigation**:
- Comprehensive skill descriptions
- Multiple trigger phrases documented
- Test with various phrasings

**Likelihood**: Low (skills tested in v2.x)
**Severity**: Medium (user confusion)

### Risk 3: Breaking Change Adoption

**Problem**: Users refuse to upgrade to v3.0
**Impact**: Stuck on v2.3 forever
**Mitigation**:
- v2.3 still works (no forced upgrade)
- Migration guide makes it easy
- Natural language is easier than commands

**Likelihood**: Low (upgrade is easier, not harder)
**Severity**: Low (v2.3 is stable)

---

## Success Metrics

### Token Efficiency
- [ ] Commands overhead: 0 tokens (vs 11k in v2.x)
- [ ] Skills overhead: ~250 tokens (12 skills)
- [ ] Total documentation: <6k tokens
- [ ] Available context: >194k tokens (vs 184k in v2.x)

### User Experience
- [ ] Natural language success rate: >90%
- [ ] New user onboarding: -50% time (no commands to learn)
- [ ] User satisfaction: +40% (simpler)

### Code Quality
- [ ] Zero slash command files
- [ ] Clean skills-only architecture
- [ ] No hybrid overhead

---

## Rollout Plan

### Step 1: Development (This Task)
- [ ] Remove commands directory
- [ ] Update plugin.json (commands: [])
- [ ] Update all documentation
- [ ] Test in nav-test project
- [ ] Verify all skills work via natural language

### Step 2: Testing (1 day)
- [ ] Test every skill with natural language
- [ ] Verify auto-invocation works
- [ ] Test in fresh project
- [ ] Confirm no regressions

### Step 3: Documentation (1 day)
- [ ] Update README.md with migration guide
- [ ] Update CLAUDE.md template
- [ ] Update .agent/ docs
- [ ] Create v3.0 announcement

### Step 4: Release (1 day)
- [ ] Run version audit script
- [ ] Commit: "feat!: v3.0 skills-only architecture (breaking)"
- [ ] Push to GitHub
- [ ] Tag: `v3.0.0`
- [ ] Create GitHub release with migration guide
- [ ] Update marketplace.json

### Step 5: Community (Post-Release)
- [ ] Announce on GitHub
- [ ] Share migration guide
- [ ] Monitor for issues
- [ ] Help users migrate

---

## Breaking Changes (v3.0.0)

**BREAKING**: Removed all slash commands (`/nav:*`)

**Migration**:
- Replace `/nav:start` with "Start my Navigator session"
- Replace `/nav:init` with "Initialize Navigator in this project"
- Replace `/nav:marker name` with "Create a marker called [name]"
- All other commands → natural language equivalents

**Skills auto-invoke** based on intent - no manual invocation needed.

---

## Post-v3.0 Roadmap

**What's Next After v3.0**:

### v3.1: Enhanced Skills
- More built-in skills (test-generator, doc-generator, config-generator)
- Improved auto-invocation accuracy
- Multi-skill coordination

### v3.2: Analytics
- session-analytics skill (real-time token tracking)
- Usage metrics dashboard
- ROI proof for teams

### v3.x: Platform Features
- Skill marketplace (share skills)
- Skill versioning
- Cross-project sync
- Skill dependencies

**Framework skills skipped** (not critical, community can generate)

---

## Related Tasks

- **TASK-07**: Skills migration strategy (planning phase)
- **TASK-08**: Skills enhancements v2.1 (foundation)
- **TASK-10**: nav-skill-creator implementation (self-improving)
- **TASK-11**: Project-specific skills v2.3 (5 skills generated)

---

## Notes

### Why This Is the Right Move

1. **Skills proven** (6 months in production: v2.0-v2.3)
2. **Natural language easier** (no syntax to remember)
3. **Cleaner architecture** (no hybrid complexity)
4. **11k token savings** (commands overhead gone)
5. **Future-proof** (skills-first is Claude's direction)

### What We're NOT Doing

❌ **Framework skills** (React, Vue, Express, etc.)
- Reason: Not critical for v3.0
- Community can generate via nav-skill-creator
- Focus on core platform first

❌ **Deprecation phase** (v2.5 with warnings)
- Reason: Unnecessary delay
- Skills already work
- Users already using natural language

❌ **Skill marketplace** (sharing platform)
- Reason: v3.x feature (after v3.0 stable)
- Need user adoption first
- Focus on core migration

---

## Timeline

**Total Effort**: 3 days

- Day 1: Remove commands, update plugin.json, update docs
- Day 2: Test thoroughly, verify auto-invocation
- Day 3: Release v3.0, announce, monitor

**Target Release**: 2025-10-22 (3 days from now)

---

**Task created**: 2025-10-19
**Priority**: High (major version)
**Effort**: Small (3 days - cleanup work)
**Impact**: Very High (breaking change, cleaner architecture, 11k token savings)
