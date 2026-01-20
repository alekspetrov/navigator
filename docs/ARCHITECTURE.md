# Navigator Architecture

> **Technical deep-dive** into how Navigator combines Skills, Agents, and Documentation for context-efficient development.

**Audience**: Contributors, advanced users, and developers understanding internals.

---

## Table of Contents

- [Core Concepts](#core-concepts)
- [Skills System](#skills-system)
- [Agents Integration](#agents-integration)
- [Documentation Strategy](#documentation-strategy)
- [Progressive Disclosure](#progressive-disclosure)
- [Self-Improving Loop](#self-improving-loop)

---

## Core Concepts

Navigator operates on three architectural pillars:

**1. Skills (Execution)**: Auto-invoking tools with predefined functions and templates
**2. Agents (Research)**: Separate-context exploration with summary returns
**3. Documentation (Knowledge)**: On-demand loading via navigator pattern

Each pillar optimizes a different aspect of context usage:
- **Skills**: Progressive disclosure (3k → 0 tokens via functions)
- **Agents**: Separate context (100k research → 200 token summary)
- **Documentation**: Lazy loading (150k → 12k via navigator)

**Combined result**: 97% context available for actual work

---

## Skills System

### Architecture

Skills consist of four components:

```
navigator/skills/[skill-name]/
├── SKILL.md              # 50-token description (always loaded)
├── functions/            # 0-token execution (run separately)
│   ├── function_1.py
│   └── function_2.py
├── templates/            # Boilerplate generation
│   └── template.tsx
└── examples/             # Usage patterns
    └── example.md
```

**Token optimization**:
- **Description** (SKILL.md): 50 tokens, always loaded
- **Instructions**: 3k tokens, loaded only when skill invokes
- **Functions**: 0 tokens (execute in separate process)
- **Templates**: 0 tokens (file contents, not in context)

**Progressive disclosure in action**:
```
Upfront: 7 skills × 50 tokens = 350 tokens
On invoke: +3k tokens (one skill's instructions)
Functions: 0 tokens (execute separately)
Total: 3,350 tokens vs 50k (loading all instructions)
```

### Built-in Skills

**Core Skills (7)**:

1. **nav-skill-creator** 🔄
   - Self-improving capability
   - Analyzes codebase patterns
   - Generates project-specific skills
   - Output: Complete skill with functions, templates, examples

2. **plugin-slash-command**
   - Navigator plugin development
   - Generates slash commands following conventions
   - Functions: `command_generator.py`, `command_validator.py`

3. **nav-start**
   - Session initialization
   - Loads `.agent/DEVELOPMENT-README.md` navigator
   - Checks PM tool for assigned tasks
   - Functions: `otel_session_stats.py` (OpenTelemetry metrics)

4. **nav-marker**
   - Context compression (130k → 3k)
   - Saves conversation state like git commits
   - Functions: `marker_compressor.py`

5. **nav-compact**
   - Smart context clearing
   - Preserves markers, clears history
   - Reloads navigator automatically

6. **nav-task**
   - Implementation plan generation
   - Task documentation management
   - Functions: `task_id_generator.py`, `task_formatter.py`, `index_updater.py`

7. **nav-sop**
   - Standard Operating Procedure capture
   - Converts solutions into reusable docs
   - Functions: `sop_formatter.py`

**Project-Specific Skills (Generated)**:

Generated via `nav-skill-creator` based on codebase analysis:

- **frontend-component**: React/Vue component generation
- **backend-endpoint**: REST/GraphQL API endpoint creation
- **database-migration**: Schema change management
- **backend-test**: Test generation for APIs
- **frontend-test**: Component test generation

### Predefined Functions

Functions execute outside Claude's context:

```python
# navigator/skills/nav-task/functions/task_id_generator.py
def generate_task_id(prefix: str = "TASK") -> str:
    """Generate next sequential task ID"""
    tasks = glob.glob(f".agent/tasks/{prefix}-*.md")
    if not tasks:
        return f"{prefix}-01"
    numbers = [int(t.split("-")[-1].split(".")[0]) for t in tasks]
    return f"{prefix}-{max(numbers) + 1:02d}"
```

**Advantages**:
- **0 tokens**: Executes in separate process
- **Consistency**: Same logic every time
- **Speed**: No LLM inference needed
- **Reliability**: No hallucination risk

### Templates

Templates ensure consistent code generation:

```typescript
// navigator/skills/frontend-component/templates/component-template.tsx
import React from 'react';
import styles from './{{COMPONENT_NAME}}.module.css';

interface {{COMPONENT_NAME}}Props {
  // Props here
}

export const {{COMPONENT_NAME}}: React.FC<{{COMPONENT_NAME}}Props> = (props) => {
  return (
    <div className={styles.container}>
      {/* Implementation */}
    </div>
  );
};
```

**Token cost**: 0 (file read, not in context)
**Consistency**: Enforces project patterns
**Customization**: Templating variables for flexibility

---

## Agents Integration

### Separate Context Architecture

Agents run in isolated context:

```
Main Conversation Context (200k token limit)
├── System prompts: 50k
├── CLAUDE.md: 15k
├── Skills: 350 tokens
├── Navigator: 2k
├── Message history: 60k
└── Available: 73k (36%)

Agent Context (separate 200k token limit)
├── Agent instructions: 5k
├── Tool calls: variable
├── File reads: 50-100k
└── Summary generation: 5k
→ Returns: 200 tokens to main conversation
```

**Key insight**: Agent's 100k token consumption doesn't impact main conversation.

### When Agents Save Tokens

**Scenario: "Find all API endpoints"**

**Manual approach** (100k+ tokens):
```
1. Grep for "endpoint" → 50 files
2. Read api/users.ts → 5k tokens
3. Read api/posts.ts → 5k tokens
4. Read api/comments.ts → 5k tokens
... (47 more files)
= 100k+ tokens in main context
```

**Agent approach** (200 tokens):
```
1. Task agent invokes in separate context
2. Agent reads 50 files (doesn't count against main)
3. Agent summarizes patterns
4. Returns: "18 endpoints across 3 files: routes.ts, middleware.ts, handlers.ts"
= 200 tokens in main context
= 99.8% savings
```

### CLAUDE.md Integration

CLAUDE.md includes agent usage instructions:

```markdown
## Agents vs Skills - Token Optimization Strategy

✅ **Use Agents for**:
- Multi-file codebase searches (60-80% savings)
- Pattern discovery (75% savings)
- Code exploration (65% savings)

❌ **Don't use Agents for**:
- Reading specific known file
- Working with 1-2 already loaded files
```

Claude automatically considers agent usage before manual file reading.

---

## Documentation Strategy

### Navigator-First Pattern

Traditional approach:
```
Load all docs → 150k tokens → No context left → Session restart
```

Navigator approach:
```
Load navigator → 2k tokens → Navigator guides to relevant docs → Load only what's needed
```

### Structure

```
.agent/
├── DEVELOPMENT-README.md      # Navigator (2k tokens, ALWAYS load first)
│   ├── Documentation index
│   ├── "When to read what" decision tree
│   ├── Current task context
│   └── Quick start guides
│
├── tasks/                     # Implementation plans (3k each, load when working on task)
│   ├── TASK-01-oauth.md
│   ├── TASK-02-api.md
│   └── archive/               # Completed tasks
│
├── system/                    # Architecture docs (5k each, load as needed)
│   ├── project-architecture.md
│   └── integration-patterns.md
│
└── sops/                      # Procedures (2k each, load when relevant)
    ├── integrations/          # Tool integration guides
    ├── debugging/             # Common issue solutions
    ├── development/           # Development workflows
    └── deployment/            # Deployment procedures
```

### Token Budget

**Typical session**:
```
Always loaded:
  DEVELOPMENT-README.md       2k tokens

Current work:
  TASK-XX.md                  3k tokens

As needed:
  system/[doc].md             5k tokens (if required)

If helpful:
  sops/[sop].md               2k tokens (if relevant)

Total: ~12k tokens vs ~150k (92% reduction)
```

### Living Documentation

Documentation updates automatically:

```
After feature completion:
  "Archive TASK-XX documentation"
  → Moves TASK-XX.md to tasks/archive/
  → Updates task index
  → Updates navigator roadmap

After solving novel issue:
  "Create an SOP for debugging [issue]"
  → Generates SOP in .agent/sops/debugging/
  → Adds to SOP index
  → Links from navigator

After architecture change:
  "Update system architecture documentation"
  → Updates .agent/system/project-architecture.md
  → Reflects in navigator
```

---

## Progressive Disclosure

Navigator implements progressive disclosure at multiple levels:

### Level 1: Skill Descriptions (Always Loaded)

```
7 skills × 50 tokens = 350 tokens always loaded
```

User sees capabilities, doesn't pay for implementation.

### Level 2: Skill Instructions (Load on Invoke)

```
Skill invokes → Load 3k token instruction set → Use once → Remains in context
```

Instructions loaded only when needed.

### Level 3: Functions (0 Tokens)

```
Function call → Execute in separate process → Return result → 0 context impact
```

Logic executes outside Claude's context.

### Level 4: Templates (0 Tokens)

```
Template needed → Read file → Apply variables → Insert into codebase → 0 context cost
```

Boilerplate generated without context consumption.

### Combined Effect

**Traditional tool (all-in-one)**:
```
50k tokens loaded upfront (instructions + examples + logic)
Used: 1 time
Token efficiency: 50k tokens / 1 use = 50k per use
```

**Navigator skill (progressive disclosure)**:
```
350 tokens loaded upfront (7 skill descriptions)
3k tokens on first invoke (instructions)
0 tokens for functions (separate execution)
0 tokens for templates (file reads)
Used: 10 times
Token efficiency: 3,350 tokens / 10 uses = 335 per use
= 99.3% improvement
```

---

## Self-Improving Loop

Navigator generates tools that generate more tools.

### The Loop

```
1. Developer: "Create a skill for API endpoints"
   ↓
2. nav-skill-creator analyzes codebase
   ↓
3. Generates backend-endpoint skill
   ├── SKILL.md (description)
   ├── functions/endpoint_generator.py
   ├── templates/endpoint-template.ts
   └── examples/usage.md
   ↓
4. backend-endpoint skill available immediately
   ↓
5. Developer: "Add user endpoint"
   ↓
6. backend-endpoint skill auto-invokes
   ↓
7. Generates endpoint following project patterns
   ↓
8. Developer identifies new pattern
   ↓
9. "Create a skill for [new pattern]"
   ↓
10. Loop continues...
```

### Codebase Analysis

`nav-skill-creator` analyzes:

**1. File patterns**:
```python
# Discovers project structure
components/ → frontend-component skill
api/endpoints/ → backend-endpoint skill
migrations/ → database-migration skill
```

**2. Code conventions**:
```typescript
// Extracts patterns
export const ComponentName: React.FC<Props> = () => {
→ Generates template matching this pattern
```

**3. Import patterns**:
```typescript
import { api } from '@/lib/api'
→ Includes in generated code
```

**4. Test patterns**:
```typescript
describe('Component', () => {
→ Generates matching test template
```

### Generated Skill Quality

Skills generated by `nav-skill-creator`:
- **Accurate**: Based on actual codebase analysis
- **Consistent**: Follows discovered patterns
- **Complete**: Functions, templates, examples included
- **Token-efficient**: Same 50-token description overhead

---

## Technical Implementation

### Skill Discovery

Claude Code loads skills from `navigator/skills/*/SKILL.md`:

```markdown
---
name: backend-endpoint
triggers:
  - "add endpoint"
  - "create API"
  - "new route"
auto_invoke: true
---

Create REST/GraphQL API endpoint with validation, error handling, and tests.
```

**Token cost**: 50 tokens per skill (description only)

### Skill Invocation

When trigger phrase detected:

1. Load `SKILL.md` full instructions (3k tokens)
2. Execute predefined functions (0 tokens)
3. Apply templates (0 tokens)
4. Return result to main conversation

### Function Execution

Functions run in separate Python process:

```bash
claude-code-functions exec nav-task.task_id_generator.generate_task_id --prefix="TASK"
→ Returns: "TASK-15"
→ Context impact: 0 tokens
```

### Template Application

Templates use variable substitution:

```typescript
// Before (template)
export const {{COMPONENT_NAME}}: React.FC<{{COMPONENT_NAME}}Props>

// After (applied)
export const UserProfile: React.FC<UserProfileProps>
```

**Process**:
1. Read template file
2. Substitute variables
3. Write to destination
4. Context impact: 0 tokens

---

## Context Optimization Summary

| Component | Token Cost | Frequency | Total Impact |
|-----------|------------|-----------|--------------|
| Skill descriptions | 50 each | Always | 350 tokens |
| Skill instructions | 3k each | On invoke | ~3k per session |
| Functions | 0 | On invoke | 0 tokens |
| Templates | 0 | On invoke | 0 tokens |
| Navigator | 2k | Always | 2k tokens |
| Task doc | 3k | Per task | ~3k per task |
| System doc | 5k | As needed | ~5k if needed |
| Agent research | 200 | When used | ~200 per agent |
| **Total** | - | - | **~12k per session** |

**vs Traditional**: 150k upfront loading

**Savings**: 92%

---

## Best Practices for Contributors

### Adding New Skills

1. **Analyze pattern**: Identify repetitive task
2. **Design functions**: Extract logic into 0-token functions
3. **Create templates**: Boilerplate → template files
4. **Write description**: Keep under 50 tokens
5. **Test auto-invoke**: Verify trigger phrases work

### Optimizing Existing Skills

1. **Extract logic**: Move code → functions (reduce token cost)
2. **Templatize boilerplate**: Reduce instruction length
3. **Compress descriptions**: Every token counts (50-token limit)
4. **Add examples**: Help Claude understand usage patterns

### Documentation Guidelines

1. **Navigator-first**: Every project needs DEVELOPMENT-README.md
2. **Lazy loading**: Never load all docs at once
3. **Living docs**: Update as code changes
4. **Decision trees**: Guide "when to read what"

---

## Performance Benchmarks

Real-world measurements:

### Context Efficiency

| Metric | Without Navigator | With Navigator | Improvement |
|--------|-------------------|----------------|-------------|
| Upfront loading | 150k tokens | 2k tokens | 98.7% ↓ |
| Per-task overhead | 50k tokens | 12k tokens | 76% ↓ |
| Available context | 0% (restart) | 97% free | - |
| Session restarts | 3-4 per day | 0 per week | 100% ↓ |

### Productivity

| Metric | Without Navigator | With Navigator | Improvement |
|--------|-------------------|----------------|-------------|
| Work per session | 1 feature | 5-10 features | 5-10x ↑ |
| Context for work | 0k tokens | 185k tokens | - |
| Research cost | 100k tokens | 200 tokens | 99.8% ↓ |
| Commits per day | 5-10 | 30-50 | 6x ↑ |

---

**For user-facing documentation**: See [README.md](README.md)
**For performance metrics**: See [PERFORMANCE.md](PERFORMANCE.md)
**For workflow guide**: See [CLAUDE.md](CLAUDE.md)
