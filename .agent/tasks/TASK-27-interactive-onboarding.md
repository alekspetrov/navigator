# TASK-27: Interactive Onboarding Flow

**Status**: ✅ Completed
**Created**: 2025-12-09
**Completed**: 2025-12-09
**Target Version**: v4.7.0

## Implementation Summary

Created `nav-onboard` skill with:
- **Two learning flows**: Quick Start (~15 min) and Full Education (~45 min)
- **Hands-on learning**: Users complete actual tasks, not just read docs
- **Auto-detection**: Project analyzer detects tech stack automatically
- **Skill recommendations**: Maps project type to relevant skills
- **Progress tracking**: Validates task completion, tracks progress
- **Personalized workflow**: Generates MY-WORKFLOW.md with project-specific guidance

### Files Created

```
skills/nav-onboard/
├── SKILL.md                           # Main skill definition
├── functions/
│   ├── project_analyzer.py            # Extended project detection
│   ├── skill_recommender.py           # Skill recommendation engine
│   ├── progress_tracker.py            # Track learning progress
│   ├── task_validator.py              # Validate completed tasks
│   └── workflow_generator.py          # Generate MY-WORKFLOW.md
├── templates/
│   ├── workflow-template.md           # Personalized guide template
│   └── progress-template.md           # Progress tracking template
└── learning-tasks/
    ├── 01-nav-start.md                # Practice task
    ├── 02-nav-marker.md               # Practice task
    ├── 03-nav-task.md                 # Practice task
    ├── 04-nav-sop.md                  # Practice task
    ├── 05-nav-compact.md              # Practice task
    └── 06-dev-skill.md                # Project-specific task
```

### Triggers

- "onboard me"
- "teach me Navigator"
- "how do I use Navigator"
- "Navigator tutorial"
- "learn Navigator"
- "new to Navigator"
- "what skills should I use"

---

## Problem Statement

Users install Navigator but don't know which skills are relevant to their workflow. Currently:
- All 19 skills listed equally in plugin.json
- No guidance on workflow order (design → component → test)
- Users discover skills randomly or not at all
- No personalization based on project type (frontend, backend, fullstack)

## Solution: Interactive Onboarding

Create an interactive onboarding experience during `nav-init` or first `nav-start` that:
1. Asks about user's project type and tech stack
2. Discovers use cases through guided questions
3. Recommends skill workflow order based on answers
4. Generates personalized skill guide in `.agent/onboarding/`

## User Experience

### Flow

```
"Initialize Navigator in this project"

Navigator: I'll set up Navigator for your project. Let me ask a few questions
to personalize your experience.

Q1: What type of project is this?
[ ] Frontend (React, Vue, Angular)
[ ] Backend (Node, Python, Go)
[ ] Fullstack
[ ] Library/Package
[ ] Other

Q2: What's your primary workflow?
[ ] Feature development (design → code → test)
[ ] Bug fixing and maintenance
[ ] Greenfield development
[ ] Legacy modernization

Q3: Do you use design tools?
[ ] Figma (with MCP)
[ ] Figma (manual export)
[ ] Other design tool
[ ] No design tool

Q4: What's your testing approach?
[ ] Unit + Integration + E2E
[ ] Unit only
[ ] E2E only
[ ] No formal testing yet

Based on your answers, here's your recommended skill workflow:

┌─────────────────────────────────────────────────────────┐
│ Your Navigator Workflow                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. nav-start ──────────────────────────────────────►  │
│     "Start my Navigator session"                        │
│                                                         │
│  2. product-design ─────────────────────────────────►  │
│     "Review this Figma design"                          │
│     (You have Figma MCP - unlocks 95% time savings)     │
│                                                         │
│  3. frontend-component ─────────────────────────────►  │
│     "Create component [name]"                           │
│     (React detected - uses your patterns)               │
│                                                         │
│  4. frontend-test ──────────────────────────────────►  │
│     "Test this component"                               │
│     (RTL + Jest configured)                             │
│                                                         │
│  5. visual-regression ──────────────────────────────►  │
│     "Set up visual regression"                          │
│     (Chromatic recommended for React)                   │
│                                                         │
│  6. nav-compact ────────────────────────────────────►  │
│     "Clear context and preserve markers"                │
│     (Keep sessions efficient)                           │
│                                                         │
└─────────────────────────────────────────────────────────┘

Saved to: .agent/onboarding/MY-WORKFLOW.md
```

## Implementation Plan

### Phase 1: Onboarding Questions Framework
**Effort**: Medium (3-4 hours)

1. Create `onboarding_questionnaire.py` predefined function
   - Question definitions with options
   - Branching logic (skip Figma questions if backend-only)
   - Answer validation

2. Create question templates
   - `templates/onboarding/questions.json` - Question definitions
   - Support for multi-select and single-select

### Phase 2: Skill Recommendation Engine
**Effort**: Medium (3-4 hours)

1. Create `skill_recommender.py` predefined function
   - Maps answers to relevant skills
   - Determines workflow order
   - Calculates potential time savings

2. Skill metadata enhancement
   - Add `project_types` to each skill
   - Add `workflow_position` (design=1, code=2, test=3, etc.)
   - Add `dependencies` (visual-regression needs frontend-component)

### Phase 3: Personalized Guide Generation
**Effort**: Medium (2-3 hours)

1. Create `workflow_generator.py` predefined function
   - Generates `.agent/onboarding/MY-WORKFLOW.md`
   - Includes natural language triggers for each skill
   - Shows workflow diagram

2. Template for workflow guide
   - `templates/onboarding/workflow-template.md`

### Phase 4: nav-onboard Skill Integration
**Effort**: Low (1-2 hours)

1. Create new `nav-onboard` skill
   - Auto-invokes: "onboard me", "what skills should I use", "personalize navigator"
   - Integrates with nav-init (optional onboarding step)

2. Update nav-start
   - Detect first run (no `.agent/onboarding/`)
   - Offer to run onboarding

### Phase 5: Re-Onboarding Support
**Effort**: Low (1 hour)

1. Allow re-running onboarding
   - "Update my Navigator workflow"
   - Preserves previous answers as defaults

## Technical Design

### Question Schema

```json
{
  "questions": [
    {
      "id": "project_type",
      "question": "What type of project is this?",
      "type": "single",
      "options": [
        {"id": "frontend", "label": "Frontend (React, Vue, Angular)"},
        {"id": "backend", "label": "Backend (Node, Python, Go)"},
        {"id": "fullstack", "label": "Fullstack"},
        {"id": "library", "label": "Library/Package"},
        {"id": "other", "label": "Other"}
      ],
      "skip_if": null
    },
    {
      "id": "design_tool",
      "question": "Do you use design tools?",
      "type": "single",
      "options": [...],
      "skip_if": {"project_type": ["backend", "library"]}
    }
  ]
}
```

### Skill Metadata Schema

```json
{
  "skill_id": "product-design",
  "project_types": ["frontend", "fullstack"],
  "workflow_position": 1,
  "dependencies": [],
  "time_savings": "95%",
  "triggers": ["Review this Figma design", "design handoff"]
}
```

### Workflow Output

`.agent/onboarding/MY-WORKFLOW.md`:
```markdown
# My Navigator Workflow

Generated: 2025-12-09
Project Type: Frontend (React)
Stack: React, TypeScript, Jest

## Recommended Skill Order

### 1. Session Management
- **nav-start**: "Start my Navigator session"
- **nav-marker**: "Create checkpoint [name]"
- **nav-compact**: "Clear context and preserve markers"

### 2. Design → Code (Your Primary Flow)
- **product-design**: "Review this Figma design"
  - You have Figma MCP configured
  - Expected savings: 95% on design handoff

- **frontend-component**: "Create component [name]"
  - Uses your React patterns
  - Auto-generates TypeScript + tests

### 3. Testing
- **frontend-test**: "Test this component"
- **visual-regression**: "Set up visual regression"

## Skills Not Recommended for Your Workflow
- backend-endpoint (no backend in project)
- database-migration (no database detected)
```

## Success Metrics

1. **Adoption**: 80%+ of new users complete onboarding
2. **Relevance**: Users report workflow matches their needs
3. **Skill Discovery**: 3x increase in skill usage after onboarding
4. **Time to Value**: Users invoke first relevant skill within 5 minutes

## Files to Create/Modify

### New Files
- `.claude-plugin/skills/nav-onboard/SKILL.md`
- `.claude-plugin/skills/nav-onboard/functions/onboarding_questionnaire.py`
- `.claude-plugin/skills/nav-onboard/functions/skill_recommender.py`
- `.claude-plugin/skills/nav-onboard/functions/workflow_generator.py`
- `templates/onboarding/questions.json`
- `templates/onboarding/workflow-template.md`
- `templates/onboarding/skill-metadata.json`

### Modified Files
- `.claude-plugin/skills/nav-start/SKILL.md` - Add onboarding detection
- `.claude-plugin/skills/nav-init/SKILL.md` - Add optional onboarding step
- `.claude-plugin/plugin.json` - Register nav-onboard skill

## Open Questions

1. Should onboarding be mandatory on first init or optional?
2. Store answers in `.nav-config.json` or separate file?
3. Should we detect tech stack automatically (package.json, etc.)?

---

**Next Step**: Implement Phase 1 - Onboarding Questions Framework
