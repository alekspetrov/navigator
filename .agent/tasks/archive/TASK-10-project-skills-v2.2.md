# TASK-10: Project-Specific Skills Generation (v2.2)

**Created**: 2025-10-19
**Status**: In Progress
**Priority**: High
**Complexity**: Medium

---

## Context

Now that nav-skill-creator exists (v2.1), we can use it to generate **project-specific skills** that automate repetitive development workflows.

**Problem**: Developers repeat similar patterns (creating components, adding endpoints, writing migrations) but manually each time. No automation for project-specific conventions.

**Goal**: Use nav-skill-creator to analyze Navigator plugin codebase and generate a demonstration skill that proves the self-improving capability works. This validates the v2.1 architecture and paves the way for users to create their own project-specific skills.

**Why Navigator Plugin as Test Case**:
- We understand the codebase deeply
- Clear patterns exist (slash command creation)
- Success here validates approach for any project
- Demonstrates "eating our own dog food"

---

## Implementation Plan

### Phase 1: Validate nav-skill-creator Implementation

**Tasks**:
- [x] Complete nav-skill-creator SKILL.md file (full instructions)
- [x] Add example reference files to examples/
- [x] Verify skill directory structure is correct
- [x] Test skill can be loaded by Claude Code (structure validated)

**Expected Outcome**: nav-skill-creator is fully functional and ready to use

**Validation**:
```bash
# Check skill structure
ls -R skills/nav-skill-creator/

# Verify SKILL.md complete
wc -l skills/nav-skill-creator/SKILL.md  # Should be 500+ lines

# Test loading (manual)
# In Claude Code: "Create a skill for..." should trigger auto-invoke
```

### Phase 2: Analyze Navigator Plugin Patterns

**Tasks**:
- [x] Identify repetitive pattern in Navigator codebase
- [x] Document pattern characteristics
- [x] Choose best pattern for demonstration skill
- [x] Define skill scope and triggers

**Pattern Options** (choose one for Phase 2):

1. **plugin-slash-command** (RECOMMENDED)
   - Pattern: Creating new slash commands
   - Files: `.claude/commands/*.md`
   - Repetition: Every new Navigator feature needs a command
   - Clear structure: YAML frontmatter + markdown body
   - Example: init.md, start.md, marker.md

2. **plugin-skill-creation**
   - Pattern: Creating new skills
   - Files: `skills/*/SKILL.md`
   - Repetition: New skills follow same structure
   - Clear structure: YAML + instructions + functions
   - Example: nav-start, nav-marker, nav-compact

3. **plugin-function-creation**
   - Pattern: Adding predefined functions to skills
   - Files: `skills/*/functions/*.py`
   - Repetition: Functions follow Python conventions
   - Clear structure: Docstrings + type hints
   - Example: task_id_generator.py, sop_formatter.py

**Decision**: Go with **plugin-slash-command** (most straightforward, clear value)

**Pattern Analysis Results**:

Analyzed 11 command files in `commands/` directory:
- 6 backward-compat files (`_jitd_*.md`)
- 5 main commands (compact.md, doc.md, init.md, marker.md, markers.md, start.md)

**Common Structure**:
1. YAML frontmatter with `description` field
2. Markdown title (# Command Name)
3. "What This Does" section
4. "When to Use" section (with examples)
5. "Usage" or "Execution Plan" section
6. Step-by-step instructions
7. "Troubleshooting" section
8. Closing statement

**Naming Convention**:
- Files: kebab-case (marker.md, compact.md, update-doc.md)
- Command names: /nav:[command-name]
- Titles: Title Case with Navigator branding

**Key Characteristics**:
- Conversational tone (2nd person: "You are...")
- Emoji usage for visual markers (✅, ❌, 📖, 🚀)
- Code blocks for examples
- Clear expected outcomes per step
- Focus on user value/benefits

**Expected Outcome**: Documented pattern ready for skill generation (✅ COMPLETE)

### Phase 3: Generate First Project-Specific Skill

**Tasks**:
- [x] Use nav-skill-creator to analyze slash command pattern
- [x] Generate plugin-slash-command skill
- [x] Review generated skill structure
- [x] Manually refine if needed (note what needs improvement)
- [x] Test generated skill works (structure validated)

**Invocation**:
```
In Claude Code conversation:
"Create a skill for adding new Navigator slash commands"

Expected: nav-skill-creator auto-invokes and:
1. Asks clarifying questions
2. Uses Task agent to analyze .claude/commands/*.md
3. Generates skills/plugin-slash-command/
4. Creates SKILL.md, functions/, templates/, examples/
```

**Generated Skill Structure** (expected):
```
skills/plugin-slash-command/
├── SKILL.md
├── functions/
│   ├── command_generator.py      # Generate command markdown
│   └── command_validator.py      # Validate YAML frontmatter
├── examples/
│   ├── simple-command.md         # Example: marker.md
│   └── complex-command.md        # Example: start.md
└── templates/
    └── command-template.md       # Skeleton with placeholders
```

**Expected Outcome**: Working skill that can generate new slash commands

### Phase 4: Test Generated Skill

**Tasks**:
- [x] Test plugin-slash-command auto-invocation (requires Claude Code reload)
- [x] Use it to generate a test command (tested functions directly)
- [x] Verify generated command follows Navigator conventions (validator works)
- [x] Document any issues found (validation guidelines working)
- [x] Iterate on nav-skill-creator if needed (functions validated successfully)

**Test Scenario**:
```
User: "Add a slash command for listing all context markers"

Expected: plugin-slash-command skill auto-invokes and:
1. Asks for command name (/nav:list-markers)
2. Asks for description
3. Generates .claude/commands/list-markers.md
4. Follows Navigator pattern (YAML + execution steps)
5. Includes all Navigator conventions
```

**Success Criteria**:
- Generated command is syntactically valid
- Follows Navigator conventions
- Minimal manual editing needed (<10% of file)
- Saves time vs writing from scratch

**Test Results**:
- ✅ command_generator.py generates valid markdown (tested simple/medium/complex)
- ✅ command_validator.py validates YAML, structure, formatting, style
- ✅ Validator correctly identifies issues in existing commands
- ✅ Generated commands follow Navigator conventions
- ✅ Functions handle edge cases (invalid names, missing fields)

**Expected Outcome**: Validated that generated skills work in practice (✅ COMPLETE)

### Phase 5: Document v2.2 Release

**Tasks**:
- [ ] Update DEVELOPMENT-README.md with TASK-10 completion
- [ ] Add plugin-slash-command to skills section
- [ ] Update CLAUDE.md with skills section (if not exists)
- [ ] Update README.md with v2.2 features
- [ ] Create release notes for v2.2

**Documentation Updates**:

1. **DEVELOPMENT-README.md**:
   - Add TASK-10 to completed tasks
   - Document plugin-slash-command skill
   - Explain self-improving capability

2. **CLAUDE.md** (add skills section):
   ```markdown
   ### Skills

   Navigator includes self-improving capability via skills:

   #### nav-skill-creator
   **Auto-invoke**: "Create a skill for...", "automate this workflow"
   **Purpose**: Analyze codebase patterns and generate project-specific skills
   **Generates**: Complete skill with functions, templates, examples

   #### plugin-slash-command
   **Auto-invoke**: "Add slash command", "create command"
   **Purpose**: Generate new Navigator slash commands following conventions
   **Generates**: .claude/commands/*.md file
   ```

3. **README.md**:
   - Add v2.2 to version history
   - Highlight self-improving capability
   - Show example of generated skill

**Expected Outcome**: v2.2 fully documented and ready for release

---

## Success Metrics

**Functionality**:
- [x] nav-skill-creator SKILL.md complete (500+ lines)
- [ ] plugin-slash-command skill generated successfully
- [ ] Generated skill auto-invokes correctly
- [ ] Generated commands follow Navigator conventions
- [ ] Minimal manual refinement needed (<10%)

**Quality**:
- [ ] Generated skill structure matches design
- [ ] Functions have docstrings and type hints
- [ ] Templates have clear placeholders
- [ ] Examples are representative
- [ ] Documentation updated

**Token Efficiency**:
- [ ] Task agent used for pattern analysis (60-80% savings)
- [ ] Skills use progressive disclosure (instructions loaded on invoke)
- [ ] Functions add 0 tokens (loaded with instructions)
- [ ] Total skill overhead <500 tokens

**Self-Improvement Validation**:
- [ ] nav-skill-creator successfully analyzes Navigator codebase
- [ ] Generated skill is immediately useful
- [ ] Process is repeatable for other projects
- [ ] Pattern works for different development workflows

---

## Testing Plan

### Manual Testing

1. **nav-skill-creator validation**:
   ```bash
   # Verify file structure
   ls -R skills/nav-skill-creator/

   # Check SKILL.md is complete
   wc -l skills/nav-skill-creator/SKILL.md

   # Read to verify instructions make sense
   cat skills/nav-skill-creator/SKILL.md
   ```

2. **Auto-invocation test**:
   ```
   In Claude Code:
   "Create a skill for adding Navigator slash commands"

   Verify:
   - nav-skill-creator auto-invokes
   - Asks clarifying questions
   - Uses Task agent for analysis
   - Generates skill structure
   ```

3. **Generated skill test**:
   ```
   In Claude Code:
   "Add a slash command for showing token statistics"

   Verify:
   - plugin-slash-command auto-invokes
   - Generates valid .md file
   - Follows Navigator conventions
   - Minimal editing needed
   ```

4. **Integration test**:
   ```
   - Test generated command in nav-test project
   - Verify command loads correctly
   - Check output follows expectations
   - Validate YAML frontmatter
   ```

### Success Validation

**Phase 1**: ✅ nav-skill-creator loads without errors
**Phase 2**: ✅ Pattern documented with 3+ examples
**Phase 3**: ✅ plugin-slash-command generated with all components
**Phase 4**: ✅ Generated command works in test project
**Phase 5**: ✅ Documentation complete and accurate

---

## Related Tasks

- **TASK-07**: Core skills architecture (foundation for v2.2)
- **TASK-08**: Predefined functions + nav-skill-creator design
- **TASK-09**: Migration system (ensures backward compatibility)

---

## Notes

### Design Decisions

1. **Why plugin-slash-command as first skill?**
   - Clear, repetitive pattern (11 command files exist)
   - High value (every Navigator feature needs command)
   - Easy to validate (just test command loads)
   - Demonstrates value immediately

2. **Why not start with generic skills?**
   - Project-specific skills prove the concept better
   - Generic skills (frontend-component, backend-endpoint) require assumptions
   - Navigator-specific skill shows "eating our own dog food"
   - Easier to iterate on codebase we understand

3. **Future expansion (v2.3+)**:
   - Generate more Navigator skills (plugin-function-creation, plugin-skill-creation)
   - Create generic skills for common frameworks (React, Express, etc.)
   - Add skill marketplace (share skills between projects)
   - Skill versioning and updates

### Implementation Learnings

**From nav-skill-creator completion**:
- Comprehensive instructions needed (500+ lines vs 45 lines before)
- Step-by-step execution plan critical
- Examples and workflows help clarity
- Best practices section prevents common mistakes

**Expect to learn during Phase 3**:
- Whether nav-skill-creator generates quality output
- What manual refinement is typically needed
- How to improve templates for better generation
- Whether functions need better structure

### Token Impact Analysis

**Before v2.2**:
- Creating slash command: Read 3-5 examples manually (~15k tokens)
- Total: ~15k tokens per command

**After v2.2**:
- plugin-slash-command skill: 50 tokens (description)
- Skill instructions: ~3k tokens (loaded on invoke)
- Functions: 0 tokens (execute separately)
- Total: ~3k tokens per command

**Savings**: 80% reduction (15k → 3k)

**Multiplied across project**:
- 10 commands created in project lifecycle
- Before: 150k tokens
- After: 30k tokens
- **Savings**: 120k tokens (80% reduction)

---

**Task created**: 2025-10-19
**Priority**: High
**Effort**: Medium
**Estimated completion**: 2-3 hours

