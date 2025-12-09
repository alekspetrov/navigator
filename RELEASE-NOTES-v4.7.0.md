# Navigator v4.7.0 Release Notes

**Release Date**: 2025-12-09
**Type**: Feature Release - Interactive Onboarding
**Focus**: Hands-on learning, skill discovery, personalized workflows

---

## Overview

Version 4.7.0 introduces the `nav-onboard` skill - an interactive onboarding experience that teaches Navigator through hands-on practice. Users complete actual tasks (creating markers, task docs, SOPs) to learn the workflow, rather than just reading documentation.

---

## Key Features

### 1. Interactive Onboarding Skill (nav-onboard)

**What's New**: Two learning flows that teach Navigator by doing.

**Quick Start (~15 min)**:
- 3 essential skills with hands-on practice
- Get productive immediately
- Minimal philosophy, maximum doing

**Full Education (~25 min)**:
- Philosophy primer (why context efficiency matters)
- All 5 essential skills with practice tasks
- Complete workflow mastery

**Triggers**:
```
"onboard me"
"teach me Navigator"
"how do I use Navigator"
"Navigator tutorial"
"learn Navigator"
```

**Impact**: Users understand Navigator through experience, not just reading.

---

### 2. Project Auto-Detection

**What's New**: Automatic tech stack detection to recommend relevant skills.

**Detects**:
- Frontend frameworks (React, Next.js, Vue, Angular, Svelte)
- Backend frameworks (Express, FastAPI, Django, Go, Rust)
- Databases (PostgreSQL, MySQL, MongoDB)
- ORMs (Prisma, SQLAlchemy, GORM)
- Testing frameworks (Jest, Pytest, etc.)
- Storybook presence
- Figma MCP configuration

**Output**:
```json
{
  "project_type": "fullstack",
  "frontend_framework": "Next.js",
  "backend_framework": "Express",
  "database": "PostgreSQL",
  "orm": "Prisma"
}
```

**Impact**: Personalized skill recommendations based on actual project.

---

### 3. Skill Recommendation Engine

**What's New**: Maps project analysis to relevant skills.

**Categories**:
- **Essential** (all projects): nav-start, nav-marker, nav-task, nav-sop, nav-compact
- **Recommended** (project-specific): frontend-component, backend-endpoint, etc.
- **Optional** (advanced): nav-skill-creator, visual-regression, product-design

**Workflow Order**: Skills presented in logical sequence (start → develop → document → checkpoint → compact)

---

### 4. Hands-On Learning Tasks

**What's New**: 6 practice tasks that create real files.

| Task | What User Does | Creates |
|------|----------------|---------|
| 01-nav-start | "Start my Navigator session" | Loads DEVELOPMENT-README.md |
| 02-nav-marker | "Create checkpoint learning-test" | .context-markers/*.md |
| 03-nav-task | "Create task doc for learning-feature" | .agent/tasks/TASK-XX.md |
| 04-nav-sop | "Create SOP for debugging test-failures" | .agent/sops/debugging/*.md |
| 05-nav-compact | "Clear context and preserve markers" | .active marker file |
| 06-dev-skill | Project-specific skill | Component or endpoint |

**Impact**: Learning by doing creates muscle memory and real understanding.

---

### 5. Progress Tracking & Validation

**What's New**: Automatic task completion validation.

**Progress File** (`.agent/onboarding/PROGRESS.md`):
```markdown
# Navigator Onboarding Progress

| # | Skill | Status | Completed | Notes |
|---|-------|--------|-----------|-------|
| 1 | nav-start | completed | 2025-12-09 | Session started |
| 2 | nav-marker | completed | 2025-12-09 | Created learning-test |
| 3 | nav-task | in_progress | - | - |

Progress: 2/5 (40%)
Next Task: nav-task
```

**Validation Methods**:
- File existence checks (markers, task docs, SOPs)
- Content validation
- User confirmation for conversational tasks

---

### 6. Personalized Workflow Guide

**What's New**: Auto-generated workflow based on project type.

**Output** (`.agent/onboarding/MY-WORKFLOW.md`):
- Project-specific workflow diagram
- Daily workflow checklist
- Skills reference table with triggers
- Quick reference card
- Tips for project type

**Example for Fullstack**:
```
SESSION START
     │
     ▼
 nav-start ────────────────────────────────┐
     │                                     │
     ▼                                     │
 [Load task doc]                           │
     │                                     │
     ├────────────────────┐                │
     ▼                    ▼                │
 frontend-component   backend-endpoint     │
     │                    │                │
     └────────┬───────────┘                │
              ▼                            │
          nav-task ────────────────────────┤
              ▼                            │
          nav-marker ──────────────────────┤
              ▼                            │
          nav-compact ─────────────────────┘
```

---

## Files Added

```
skills/nav-onboard/
├── SKILL.md                           # Main skill definition (450+ lines)
├── functions/
│   ├── project_analyzer.py            # Extended project detection
│   ├── skill_recommender.py           # Skill recommendation engine
│   ├── progress_tracker.py            # Track learning progress
│   ├── task_validator.py              # Validate task completion
│   └── workflow_generator.py          # Generate MY-WORKFLOW.md
├── learning-tasks/
│   ├── 01-nav-start.md
│   ├── 02-nav-marker.md
│   ├── 03-nav-task.md
│   ├── 04-nav-sop.md
│   ├── 05-nav-compact.md
│   └── 06-dev-skill.md
└── templates/
    ├── workflow-template.md
    └── progress-template.md
```

---

## Files Modified

- `.claude-plugin/plugin.json` - Added nav-onboard skill, version bump
- `.claude-plugin/marketplace.json` - Version bump, changelog entry

---

## Breaking Changes

None. All changes are backward compatible.

---

## Migration Guide

### For New Users

```
"onboard me"
```

Choose Quick Start (~15 min) or Full Education (~25 min).

### For Existing Users

Onboarding is optional. If you want to refresh:

```
"teach me Navigator"
```

---

## Metrics

| Metric | Value |
|--------|-------|
| Skills count | 20 (was 19) |
| Learning tasks | 6 |
| Python functions | 5 |
| Lines of code | 3,373 |

---

## What's Next (v4.8.0)

- Onboarding analytics (track completion rates)
- Team onboarding mode (shared progress)
- Skill certification badges
- Project-specific skill generation from onboarding

---

**Full Changelog**: https://github.com/alekspetrov/navigator/compare/v4.6.0...v4.7.0
