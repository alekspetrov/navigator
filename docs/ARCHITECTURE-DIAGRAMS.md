# Navigator Architecture - ASCII Diagrams

Visual representations of Navigator's core components and workflows.

---

## 1. Navigator Core Architecture

```ts
┌─────────────────────────────────────────────────────────────────────────┐
│                          NAVIGATOR PLUGIN v3.2.0                        │
│                     Skills + Agents + Documentation                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
        ┌───────────────┐   ┌──────────────┐   ┌──────────────┐
        │    SKILLS     │   │    AGENTS    │   │     DOCS     │
        │  (Execution)  │   │  (Research)  │   │ (Knowledge)  │
        └───────────────┘   └──────────────┘   └──────────────┘
                │                   │                   │
                │                   │                   │
    ┌───────────┴────────┐          │          ┌────────┴────────┐
    │                    │          │          │                 │
    ▼                    ▼          ▼          ▼                 ▼
┌────────┐      ┌──────────────┐  ┌────┐  ┌──────┐      ┌─────────────┐
│ Core   │      │ Development  │  │Task│  │.agent│      │   Project   │
│ Skills │      │   Skills     │  │Agent│ │  /   │      │Documentation│
│ (8)    │      │    (7)       │  │    │  │      │      │             │
└────────┘      └──────────────┘  └────┘  └──────┘      └─────────────┘
    │                    │           │         │                 │
    │                    │           │         │                 │
    ▼                    ▼           ▼         ▼                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  nav-init                product-design      Explore    DEVELOPMENT- │
│  nav-start              frontend-component   60-80%     README.md    │
│  nav-marker             backend-endpoint     token      (Navigator)  │
│  nav-compact            database-migration   savings    ~2k tokens   │
│  nav-task               backend-test                                 │
│  nav-sop                frontend-test                    tasks/      │
│  nav-skill-creator      plugin-slash-command             system/     │
│  nav-update-claude                                        sops/      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Skills System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SKILLS SYSTEM                            │
│                    Progressive Disclosure                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │ Auto-Invocation  │            │   On-Demand      │
    │   (Natural       │            │    Loading       │
    │   Language)      │            │                  │
    └──────────────────┘            └──────────────────┘
              │                               │
              ▼                               ▼
    ┌─────────────────────────────────────────────────┐
    │                                                  │
    │  User: "Review this design from Figma"          │
    │         │                                        │
    │         ▼                                        │
    │  Claude detects intent → Matches trigger        │
    │         │                                        │
    │         ▼                                        │
    │  Load SKILL.md (3k tokens, not 150k docs!)      │
    │         │                                        │
    │         ▼                                        │
    │  Execute predefined functions (0 tokens)        │
    │         │                                        │
    │         ▼                                        │
    │  Generate output using templates                │
    │                                                  │
    └─────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     SKILL STRUCTURE                              │
└─────────────────────────────────────────────────────────────────┘

    skills/product-design/
           │
           ├── SKILL.md ─────────────────┐
           │   (3k tokens)                │ Loaded only
           │   - Auto-invoke triggers     │ when skill
           │   - Workflow protocol        │ invokes
           │   - 5-step process           │
           │                              │
           ├── functions/ ───────────────┐│
           │   ├── design_analyzer.py    ││ Execute with
           │   ├── token_extractor.py    ││ 0 tokens
           │   ├── component_mapper.py   ││ (no context
           │   ├── design_system_auditor ││  pollution)
           │   └── implementation_planner││
           │                              ││
           ├── templates/ ───────────────┘│
           │   └── design-review-report   │ Use for
           │                               │ consistent
           └── examples/                   │ output
               └── dashboard-redesign ─────┘
```

---

## 3. Agents System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       AGENTS SYSTEM                              │
│                  Separate Context Research                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │  Main Context    │            │  Agent Context   │
    │  (Your Session)  │            │   (Separate)     │
    └──────────────────┘            └──────────────────┘
              │                               │
              │ Question                      │
              ├──────────────────────────────>│
              │                               │
              │                               ▼
              │                     ┌──────────────────┐
              │                     │ Agent explores:  │
              │                     │ - Reads 50 files │
              │                     │ - Searches code  │
              │                     │ - Analyzes       │
              │                     │   patterns       │
              │                     │                  │
              │                     │ Uses: 100k tokens│
              │                     └──────────────────┘
              │                               │
              │ Summary (200 tokens)          │
              │<──────────────────────────────┘
              │
              ▼
    Your context: Only 200 tokens used!
    99.8% token savings vs manual reading


┌─────────────────────────────────────────────────────────────────┐
│                    AGENT WORKFLOW EXAMPLE                        │
└─────────────────────────────────────────────────────────────────┘

User: "Find all authentication patterns in the codebase"

                         Main Context
    ┌────────────────────────────────────────────────────┐
    │ Current tokens: 45k used                           │
    │ Available: 155k                                     │
    │                                                     │
    │   Launches ──────┐                                 │
    │   Agent          │                                 │
    └──────────────────┼─────────────────────────────────┘
                       │
                       ▼
                 Agent Context (Separate)
    ┌─────────────────────────────────────────────────┐
    │ Reads 50 files:                                 │
    │   auth.ts, middleware.ts, login.tsx...         │
    │                                                 │
    │ Grep searches: "authenticate", "login", "jwt"  │
    │                                                 │
    │ Analyzes patterns:                             │
    │   - JWT in 12 files                            │
    │   - OAuth in 5 files                           │
    │   - Session in 3 files                         │
    │                                                 │
    │ Token usage: 98k                                │
    └─────────────────────────────────────────────────┘
                       │
                       │ Returns summary
                       ▼
                 Main Context
    ┌─────────────────────────────────────────────────┐
    │ Receives 200-token summary:                     │
    │                                                 │
    │ "Found 3 auth patterns:                        │
    │  1. JWT (primary) - auth.ts:45                 │
    │  2. OAuth (Google) - oauth.ts:12               │
    │  3. Session (legacy) - session.ts:78"          │
    │                                                 │
    │ Current tokens: 45.2k used                      │
    │ Saved: 97.8k tokens!                            │
    └─────────────────────────────────────────────────┘
```

---

## 4. Documentation System (Navigator-First Pattern)

```
┌─────────────────────────────────────────────────────────────────┐
│              TRADITIONAL APPROACH (Fails)                        │
└─────────────────────────────────────────────────────────────────┘

Session start
    │
    ▼
Load all documentation at once
    │
    ├── architecture.md      (30k tokens)
    ├── api-reference.md     (40k tokens)
    ├── setup-guide.md       (25k tokens)
    ├── contributing.md      (20k tokens)
    ├── troubleshooting.md   (15k tokens)
    └── examples.md          (20k tokens)
    │
    ▼
Total: 150k tokens loaded
    │
    ▼
❌ Context full! No space for work!
    │
    ▼
Session restart required after 5 messages


┌─────────────────────────────────────────────────────────────────┐
│              NAVIGATOR APPROACH (Succeeds)                       │
└─────────────────────────────────────────────────────────────────┘

Session start
    │
    ▼
"Start my Navigator session"
    │
    ▼
Load ONLY navigator (DEVELOPMENT-README.md)
    │
    ├── What to load when          (500 tokens)
    ├── Documentation index        (800 tokens)
    ├── Quick decision tree        (400 tokens)
    └── Session workflow           (300 tokens)
    │
    ▼
Total: 2k tokens loaded (98.7% reduction!)
    │
    ▼
Navigator guides you:
    │
    ├── Working on auth?    → Load system/auth.md (5k)
    ├── Fixing bug?         → Load sops/debugging/ (2k)
    ├── New feature?        → Load tasks/TASK-XX (3k)
    └── Research needed?    → Use Agent (200 token summary)
    │
    ▼
✅ 198k tokens available for actual work!
    │
    ▼
30x more productive per session


┌─────────────────────────────────────────────────────────────────┐
│                   DOCUMENTATION STRUCTURE                        │
└─────────────────────────────────────────────────────────────────┘

    .agent/
       │
       ├── DEVELOPMENT-README.md ────┐
       │   (Navigator - 2k tokens)   │ ALWAYS load first
       │   - Documentation index     │
       │   - When to read what       │
       │   - Quick reference         │
       │                             │
       ├── tasks/ ──────────────────┐│
       │   ├── TASK-01.md           ││ Load CURRENT
       │   ├── TASK-16.md           ││ task only
       │   └── archive/             ││ (~3k tokens)
       │                             ││
       ├── system/ ─────────────────┘│
       │   ├── architecture.md       │ Load AS NEEDED
       │   └── patterns.md           │ (~5k tokens)
       │                             │
       └── sops/ ────────────────────┘
           ├── debugging/             Load WHEN RELEVANT
           ├── deployment/            (~2k tokens)
           └── integrations/

    Total strategy:
    - Always load: 2k (navigator)
    - Current work: 3k (task)
    - As needed: 5k (system)
    - If relevant: 2k (SOP)
    ──────────────────────────
    Maximum: ~12k vs 150k (92% reduction)
```

---

## 5. Product Design Skill Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│           PRODUCT DESIGN SKILL - 5-STEP WORKFLOW                 │
└─────────────────────────────────────────────────────────────────┘

User: "Review this design from Figma: https://figma.com/..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1: Design Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Figma MCP Server
          │
          ├─> get_metadata ─────────> Sparse component structure
          │   (5k tokens)
          │
          ├─> get_variable_defs ────> All design tokens
          │   (10k tokens)
          │
          └─> get_code_connect_map ─> Component mappings
              (2k tokens)
                    │
                    ▼
          design_analyzer.py
                    │
                    ├─> Extract components
                    ├─> Categorize (atom/molecule/organism)
                    ├─> Calculate similarity vs existing
                    └─> Detect breaking changes
                    │
                    ▼
          Analysis Results
          - 3 new components
          - 12 new tokens
          - 2 similar components (78% match)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: Codebase Audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    token_extractor.py          component_mapper.py
            │                           │
            ├─> DTCG conversion         ├─> Search codebase
            ├─> Generate diff           ├─> Fuzzy matching
            └─> Compare existing        └─> Extract variants
            │                           │
            └───────────┬───────────────┘
                        │
                        ▼
          design_system_auditor.py
                        │
                        ├─> Compare tokens (drift?)
                        ├─> Find reuse opportunities
                        ├─> Check Tailwind config
                        └─> Assign priority level
                        │
                        ▼
          Audit Report
          ⚠️  Drift: 5 tokens
          ♻️  Reuse: 2 components (extend Badge)
          Priority: HIGH

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3: Implementation Planning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    implementation_planner.py
                │
                ├─> Phase 1: Tokens (2h)
                ├─> Phase 2: Atoms (3h)
                ├─> Phase 3: Molecules (2h)
                └─> Phase 4: Organisms (5h)
                │
                ├─> Estimate complexity
                ├─> Generate acceptance criteria
                ├─> Create test strategy
                └─> Plan rollout
                │
                ▼
    .agent/tasks/TASK-17-dashboard.md
    (Complete Navigator task document)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4: Task Assignment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Save documentation
                │
                ├─> .agent/tasks/TASK-17-dashboard.md
                ├─> .agent/design-system/reviews/2025-10-21-dashboard.md
                └─> .agent/DEVELOPMENT-README.md (update index)
                │
                ▼
    Create PM ticket (if configured)
                │
                └─> Linear/GitHub Issues/Jira
                │
                ▼
    Task ready for implementation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5: Implementation Handoff
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Present summary:
    ┌──────────────────────────────────────────────────┐
    │ ✅ Dashboard Redesign Review Complete            │
    │                                                   │
    │ Generated:                                        │
    │ - Design review report                            │
    │ - Implementation plan (TASK-17)                   │
    │ - 4 phases, 12 hours estimated                    │
    │                                                   │
    │ Summary:                                          │
    │ - Tokens: 12 new, 5 modified                      │
    │ - Components: 3 new, 2 to extend                  │
    │ - Breaking changes: 1 (MetricCard)                │
    │                                                   │
    │ Next:                                             │
    │ [1] Start implementation now                      │
    │ [2] Review plan first                             │
    │ [3] Modify plan                                   │
    └──────────────────────────────────────────────────┘
                        │
                        ▼
    User: "Start implementation"
                        │
                        ▼
    Follow autonomous completion protocol
    (Load task → Implement → Test → Commit → Archive)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Time: 15 minutes (vs 6-10 hours manual)
```

---

## 6. Token Optimization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              WITHOUT NAVIGATOR (Token Wastage)                   │
└─────────────────────────────────────────────────────────────────┘

Session Start (200k tokens available)
    │
    ├─> Load architecture.md        (-30k) = 170k left
    ├─> Load API docs               (-40k) = 130k left
    ├─> Load setup guide            (-25k) = 105k left
    ├─> Load examples               (-20k) = 85k left
    ├─> Read 10 component files     (-50k) = 35k left
    └─> Read 5 config files         (-15k) = 20k left
    │
    ▼
Available for work: 20k tokens (10% of capacity)
    │
    ▼
After 5-10 messages: Context full, restart required


┌─────────────────────────────────────────────────────────────────┐
│              WITH NAVIGATOR (Token Efficiency)                   │
└─────────────────────────────────────────────────────────────────┘

Session Start (200k tokens available)
    │
    └─> "Start my Navigator session"
        Load DEVELOPMENT-README.md   (-2k) = 198k left
    │
    ▼
Available for work: 198k tokens (99% of capacity)
    │
    │
    ▼ User needs authentication info
    │
    ├─> "Find all auth patterns"
    │   Use Agent (separate context)
    │   Returns summary              (-0.2k) = 197.8k left
    │
    ▼ User needs to implement feature
    │
    ├─> Load current task only      (-3k) = 194.8k left
    │
    ▼ User needs architecture reference
    │
    ├─> Load system/architecture.md (-5k) = 189.8k left
    │
    ▼ User has question about setup
    │
    └─> Load relevant SOP           (-2k) = 187.8k left
    │
    ▼
Available after full session: 187.8k tokens (94% of capacity)
    │
    ▼
Can continue for 50+ messages without restart!


┌─────────────────────────────────────────────────────────────────┐
│                    COMPARATIVE METRICS                           │
└─────────────────────────────────────────────────────────────────┘

                    Without Navigator  │  With Navigator
                    ──────────────────────────────────────
Upfront loading:    150k tokens        │  2k tokens
                    ──────────────────────────────────────
Research cost:      100k tokens        │  200 tokens
                    (read 50 files)    │  (agent summary)
                    ──────────────────────────────────────
Context available:  10% (20k)          │  99% (198k)
                    ──────────────────────────────────────
Work capacity:      100 lines/session  │  3,000 lines/session
                    ──────────────────────────────────────
Session restarts:   Every 5-10 msg     │  Every 50+ msg
                    ──────────────────────────────────────
Productivity:       1x (baseline)      │  30x improvement
```

---

## 7. Self-Improving System (nav-skill-creator)

```
┌─────────────────────────────────────────────────────────────────┐
│                  SELF-IMPROVING WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

User: "Create a skill for adding API endpoints"
    │
    ▼
nav-skill-creator skill invokes
    │
    ├─> Analyze codebase
    │   │
    │   ├─> Find all existing endpoints
    │   ├─> Extract common patterns
    │   ├─> Identify file structure
    │   └─> Detect frameworks (Express, Fastify, etc.)
    │
    ├─> Generate skill structure
    │   │
    │   ├─> SKILL.md (workflow protocol)
    │   ├─> functions/*.py (validation, generation)
    │   ├─> templates/*.md (code templates)
    │   └─> examples/*.md (reference implementation)
    │
    ├─> Register in plugin.json
    │
    └─> Test skill generation
    │
    ▼
New backend-endpoint skill created!
    │
    └─> Auto-invokes on "Add endpoint", "Create API"


┌─────────────────────────────────────────────────────────────────┐
│              SKILL GENERATION PATTERN                            │
└─────────────────────────────────────────────────────────────────┘

    Your Project
         │
         ▼
    nav-skill-creator analyzes:
         │
         ├─> File patterns
         │   └─> "Controllers in controllers/"
         │       "Routes in routes/"
         │       "Tests in __tests__/"
         │
         ├─> Code patterns
         │   └─> "Express middleware"
         │       "Joi validation"
         │       "Jest tests"
         │
         └─> Naming conventions
             └─> "userController.ts"
                 "user.routes.ts"
                 "user.test.ts"
         │
         ▼
    Generates skill matching YOUR patterns
         │
         ├─> Uses your file structure
         ├─> Applies your naming conventions
         ├─> Implements your validation
         └─> Follows your test patterns
         │
         ▼
    Result: Project-specific automation
    (80% token reduction for common tasks)
```

---

## 8. Complete System Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NAVIGATOR COMPLETE SYSTEM                             │
└─────────────────────────────────────────────────────────────────────────┘

                         User Session Starts
                                 │
                                 ▼
                    "Start my Navigator session"
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
  Load Navigator (2k)                          Check PM Tool
         │                                      (Linear/GitHub)
         ├─> Documentation index                       │
         ├─> Quick reference                           ▼
         └─> Workflow guide                    Load assigned task?
         │                                             │
         └─────────────────┬───────────────────────────┘
                           │
                           ▼
                    Context Optimized
                    (198k tokens free)
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌──────────┐
    │ Skills  │      │ Agents  │      │   Docs   │
    │ Execute │      │Research │      │On-Demand │
    └─────────┘      └─────────┘      └──────────┘
         │                 │                 │
         │                 │                 │
    User needs:       User asks:        User needs:
    "Create           "How does         Load specific
    component"        auth work?"       documentation
         │                 │                 │
         ▼                 ▼                 ▼
    frontend-        Task agent         Load only
    component        explores           relevant doc
    skill            (separate          (~5k tokens)
    invokes          context)
         │                 │                 │
         ▼                 ▼                 ▼
    Generates        Returns            Reference
    component        summary            for current
    + tests          (200 tokens)       work
    + styles
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                           ▼
                    Work Completed
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
    Autonomous Completion              Continue Session
         │                                   │
         ├─> Commit changes                 ▼
         ├─> Archive docs              Still 180k+
         ├─> Close ticket              tokens free!
         ├─> Create marker
         └─> Suggest compact
                           │
                           ▼
                    Session Ends
                  (50+ messages completed,
                   no restarts needed!)
```

---

## 9. Progressive Disclosure Visual

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROGRESSIVE DISCLOSURE                        │
│                  (Load only what you need)                       │
└─────────────────────────────────────────────────────────────────┘

Traditional Approach:
┌────────────────────────────────────────────────────────────────┐
│ ███████████████████████████████████████████████████████████    │
│ ▲                                                              │
│ │                                                              │
│ 150k tokens loaded upfront                                     │
│                                                                │
│ Result: Context full, no space for work                       │
└────────────────────────────────────────────────────────────────┘

Navigator Approach:
┌────────────────────────────────────────────────────────────────┐
│ ██                                                             │
│ ▲ ▲                                                            │
│ │ └─ 2k: Navigator loaded                                      │
│ └─── Load more only when needed (3k, 5k, 2k)                   │
│                                                                │
│ Result: 97% context free for actual work                      │
└────────────────────────────────────────────────────────────────┘

Layer-by-Layer Loading:

    Session Start
         │
         ├─> Layer 0: Navigator (2k) ─────────────┐ Always
         │                                        │
    Work Context                                  │
         │                                        │
         ├─> Layer 1: Current task (3k) ─────────┤ Current
         │                                        │ work
    Need Reference                                │
         │                                        │
         ├─> Layer 2: System doc (5k) ───────────┤ As
         │                                        │ needed
    Have Question                                 │
         │                                        │
         └─> Layer 3: SOP (2k) ──────────────────┘ When
                                                    relevant

    Total loaded: ~12k tokens
    Available: 188k tokens (94%)
```

---

**Created**: 2025-10-21
**Navigator Version**: 3.2.0
**Format**: ASCII Art Diagrams
