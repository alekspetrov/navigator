# Navigator v5.0.0 - Theory of Mind

**Release Date**: 2025-12-11

## Overview

Navigator v5.0.0 introduces Theory of Mind (ToM) features for better human-AI collaboration. Based on Riedl & Weidmann 2025 research showing 23-29% performance boost from ToM alignment.

## Two-Layer Architecture

```
Navigator = Context Engineering + Human-AI Collaboration

Layer 1: Context Efficiency (v1-v4)
├── 92% token savings (verified via OpenTelemetry)
├── Lazy loading documentation
├── Context markers (97% compression)
├── Agent-optimized search
└── Proven, stable foundation

Layer 2: Theory of Mind (v5.0.0) [NEW]
├── Bilateral modeling (nav-profile)
├── Quality detection (nav-diagnose)
├── Verification checkpoints
├── Auto-learn corrections
└── Intent capture in markers
```

## New Features

### 1. nav-profile Skill

**Purpose**: Claude learns your preferences across sessions

**How it works**:
```
"Remember I prefer concise explanations"
→ Saved to .agent/.user-profile.json
→ Applied in future sessions
→ Survives context clears and compacts
```

**Features**:
- Communication preferences (verbosity, confirmation threshold)
- Technical preferences (frameworks, code style)
- Workflow preferences (autonomous commits, compact threshold)
- Auto-learn from corrections (silent capture)
- Goal tracking across sessions

**Commands**:
- "Save my preferences" → Creates/updates profile
- "Show my profile" → Displays current settings
- "Reset my profile" → Clears all preferences

### 2. nav-diagnose Skill

**Purpose**: Detects when collaboration quality drops and prompts re-anchoring

**Triggers**:
- Same correction given twice
- User says "you're not getting this", "wrong again"
- Context confusion detected
- Frustration signals ("ugh", "sigh")

**Output**:
```
⚠️  QUALITY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detected Issue: Repeated Corrections
Severity: High

What I noticed:
- Same naming convention correction twice
- REST endpoint plural naming

Let me re-anchor:
1. Your goal: Create user API endpoints
2. Current state: 3/5 endpoints complete
3. Rule established: Use plural nouns (/users not /user)

Is this understanding correct? [Y/n]
```

### 3. Verification Checkpoints

**Purpose**: Confirm understanding before generating high-stakes code

**Skills with checkpoints**:
- `backend-endpoint` - Verifies endpoint design before generation
- `frontend-component` - Confirms component structure
- `database-migration` - ALWAYS verifies (database changes are critical)
- `nav-task` - Verifies interpretation when archiving tasks

**Checkpoint format**:
```
I understood you want:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint: POST /api/users
Framework: Express (detected from package.json)
Auth required: yes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Assumptions I'm making:
- Using Joi for validation (detected from existing validators)
- Error handling follows existing pattern in src/middleware/error.ts

Proceed with generation? [Y/n]
```

**Skip conditions** (HIGH-STAKES ONLY mode):
- Simple CRUD operations
- User explicitly says "quick" or "skip confirmation"
- Standard patterns with no customization

### 4. Auto-Learn Corrections

**Purpose**: Silently learn from user corrections to avoid repeating mistakes

**Detection patterns**:
- "No, I meant..." → Direct correction
- "Actually, ..." → Clarification
- "Not X, use Y" → Substitution
- "Always use ..." → Rule establishment
- "Never do ..." → Anti-pattern

**Storage**:
- Saved to `.agent/.user-profile.json`
- Rolling window (last 20 corrections)
- Persists across sessions

**Feedback** (every 5 corrections):
```
📚 I've learned from your corrections:
- REST endpoints should use plural nouns
- You prefer functional components over class components
- TypeScript strict mode is required

These will be applied in future sessions.
```

### 5. Enhanced Context Markers

**Purpose**: Capture user intent and corrections, not just technical state

**New sections in markers**:
```markdown
## User Intent & Goals (ToM) [CAPTURE ACTIVELY]

**Primary goal this session**:
Implement OAuth for user authentication

**Stated preferences**:
- Prefers concise explanations
- Wants functional components

**Corrections made**:
- "Should be /users not /user (plural convention)"
- "Use httpOnly cookies for tokens"

## Belief State [CAPTURE ACTIVELY]

**What user knows**:
- Familiar with Express, new to Passport
- Senior developer, skip basics

**Assumptions I made**:
- Using Redis for sessions (confirmed)
- Auth endpoints at /api/auth/*
```

## Configuration

New ToM configuration in `.agent/.nav-config.json`:

```json
{
  "version": "5.0.0",
  "tom_features": {
    "verification_checkpoints": true,
    "confirmation_threshold": "high-stakes",
    "profile_enabled": true,
    "diagnose_enabled": true,
    "belief_anchors": false
  }
}
```

**Options**:
- `verification_checkpoints`: Enable/disable checkpoints (default: true)
- `confirmation_threshold`: "always" | "high-stakes" | "never" (default: "high-stakes")
- `profile_enabled`: Enable nav-profile skill (default: true)
- `diagnose_enabled`: Enable nav-diagnose skill (default: true)
- `belief_anchors`: Optional explicit assumption declarations (default: false)

## Navigator + Claude Code

Claude Code v2.0.107 has features that appear similar but serve different purposes:

| Feature | Claude Code | Navigator | Why Different |
|---------|-------------|-----------|---------------|
| Session resume | Full replay | Curated markers | Navigator: 97% compression, decisions only |
| @imports | All load at start | On-demand | Navigator: semantic decision tree |
| Auto-compact | Reactive (95%) | Proactive | Navigator: task-switch with intent capture |
| Rules | Config | Knowledge | Complementary domains |

**Use both**: Claude Code handles infrastructure, Navigator handles strategy + collaboration.

## Migration from v4.x

**Automatic**:
- Existing `.agent/` structure preserved
- Skills continue working
- No breaking changes

**New files created on first use**:
- `.agent/.user-profile.json` (when preferences saved)
- Enhanced markers (ToM sections added automatically)

**Configuration update**:
```bash
# Check current version
cat .agent/.nav-config.json | grep version

# Update to v5.0.0 (preserves other settings)
# nav-upgrade skill handles this automatically
```

## Research Foundation

Theory of Mind features based on:

**Riedl & Weidmann 2025** - "Humans are not tokens: Interindividual differences and the human-AI synergy"

Key findings:
- ToM predicts 23-29% collaborative performance boost
- ToM varies dynamically within users (moment-to-moment)
- Bilateral modeling (both human→AI and AI→human) matters

**Navigator implementation**:
- `nav-profile`: AI→human modeling (Claude learns you)
- `nav-diagnose`: Detects when ToM alignment degrades
- Checkpoints: Explicit verification of mutual understanding

## Skills Updated

| Skill | Change |
|-------|--------|
| nav-start | Profile loading at session start |
| nav-marker | Intent/belief state capture sections |
| backend-endpoint | Verification checkpoint (Step 1.5) |
| frontend-component | Verification checkpoint (Step 1.5) |
| database-migration | Verification checkpoint (Step 2.5, always enabled) |
| nav-task | Verification checkpoint (Step 3.5, archive mode) |

## Known Limitations

1. **Auto-learn requires explicit corrections** - Implicit preferences harder to detect
2. **Checkpoints add friction** - Configurable via `confirmation_threshold`
3. **Profile is local** - Not synced across machines (git-ignored)

## Upgrade Path

```bash
# 1. Update plugin
/plugin update navigator

# 2. Run upgrade skill (optional, updates CLAUDE.md)
"Upgrade Navigator to latest version"

# 3. Start session - profile loading automatic
"Start my Navigator session"
```

## Changelog

### v5.0.0 (2025-12-11)
- **NEW**: nav-profile skill for bilateral modeling
- **NEW**: nav-diagnose skill for quality detection
- **NEW**: Verification checkpoints in high-stakes skills
- **NEW**: Auto-learn correction detection
- **ENHANCED**: nav-marker with intent/belief state capture
- **ENHANCED**: nav-start with profile loading
- **ADDED**: "Navigator + Claude Code" comparison section

---

**Navigator v5.0.0**: Context efficiency remains the foundation. Theory of Mind makes collaboration better.
