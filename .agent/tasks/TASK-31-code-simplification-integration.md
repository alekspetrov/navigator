# TASK-31: Code Simplification Integration

**Status**: ✅ Completed
**Created**: 2025-01-22
**Version**: v5.4.0
**Priority**: High

## Summary

Integrate Anthropic's code-simplifier pattern into Navigator as a comprehensive simplification system across all execution modes.

## Context

Anthropic uses a code-simplifier agent internally that:
- Simplifies recently modified code
- Preserves exact functionality
- Applies project standards from CLAUDE.md
- Runs autonomously after code changes
- Uses Opus model for quality judgment

This aligns with Navigator's "Finish What You Start" philosophy - code should be clean before commit.

## Requirements

### R1: nav-simplify Skill (Standalone)
- Natural language triggers: "simplify this code", "review for clarity", "clean up recent changes"
- Scope options: modified files, specific file, entire feature
- Model preference: Opus (configurable)
- Output: simplified code with change summary

### R2: Autonomous Completion Integration
- Add simplification step to completion protocol
- Position: Implement → **Simplify** → Verify → Commit → Archive
- Configurable via `.nav-config.json`
- Skip if no code changes (docs-only tasks)

### R3: Multi-Claude Simplifier Role
- New role template: `simplifier`
- Role-specific CLAUDE.md (~5k tokens)
- Parallel execution with `review` role
- Fresh context for unbiased judgment

### R4: Loop Mode VERIFY Phase
- Add `[x] Code simplified` completion indicator
- Stagnation detection for over-simplification
- Required before EXIT_SIGNAL (configurable)

## Implementation Plan

### Phase 1: Skill Creation
1. Create `skills/nav-simplify/SKILL.md`
2. Create predefined functions:
   - `code_analyzer.py` - identify modified code sections
   - `simplification_rules.py` - project-aware rules engine
   - `change_reporter.py` - generate change summary
3. Add skill to `plugin.json`

### Phase 2: Autonomous Completion
1. Update `sops/development/autonomous-completion.md`
2. Add simplification step to protocol
3. Update CLAUDE.md forbidden/required actions

### Phase 3: Multi-Claude Role
1. Create `templates/multi-claude/simplifier-claude.md`
2. Update orchestrator to include simplifier phase
3. Add to role documentation

### Phase 4: Loop Mode
1. Update Loop Mode completion indicators
2. Add simplification to VERIFY phase
3. Update nav-loop skill

### Phase 5: Configuration
1. Add `simplification` config section to `.nav-config.json`
2. Document configuration options
3. Update DEVELOPMENT-README.md

## Technical Design

### Skill Structure
```
skills/nav-simplify/
├── SKILL.md                    # Skill definition
└── scripts/
    ├── code_analyzer.py        # Find modified sections
    ├── simplification_rules.py # Rules engine
    └── change_reporter.py      # Change summary
```

### Configuration Schema
```json
{
  "simplification": {
    "enabled": true,
    "trigger": "post-implementation",
    "scope": "modified",
    "model": "opus",
    "skip_patterns": ["*.md", "*.json"],
    "max_file_size": 50000
  }
}
```

### Simplification Rules (from Anthropic prompt)
1. Preserve functionality - never change behavior
2. Apply project standards from CLAUDE.md
3. Reduce unnecessary complexity/nesting
4. Eliminate redundant code
5. Improve naming clarity
6. Avoid nested ternaries
7. Choose clarity over brevity
8. Don't over-simplify (maintain helpful abstractions)

### Multi-Claude Role Template
```markdown
# Simplifier Claude

You are a code simplification specialist. Your role:
- Review code from implementation phase
- Simplify without changing functionality
- Apply project standards
- Report changes made

You receive: Implementation marker with file list
You produce: Simplified code + change summary marker
```

## Verify

```bash
# Skill exists and is registered
test -f "skills/nav-simplify/SKILL.md" && echo "✓ Skill exists"
grep -q "nav-simplify" plugin.json && echo "✓ Skill registered"

# Config schema updated
grep -q "simplification" .agent/.nav-config.json && echo "✓ Config updated"

# Multi-Claude role exists
test -f "templates/multi-claude/simplifier-claude.md" && echo "✓ Role template exists"

# Documentation updated
grep -q "simplif" CLAUDE.md && echo "✓ CLAUDE.md updated"
grep -q "TASK-31" .agent/DEVELOPMENT-README.md && echo "✓ README updated"
```

## Done

- [ ] `nav-simplify` skill invocable via natural language
- [ ] Autonomous completion includes simplification step
- [ ] Multi-Claude workflows have `simplifier` role option
- [ ] Loop Mode VERIFY phase includes simplification indicator
- [ ] Configuration documented in `.nav-config.json`
- [ ] CLAUDE.md references simplification workflow
- [ ] DEVELOPMENT-README.md lists TASK-31 as completed

## Notes

- Model preference: Opus for quality judgment (configurable to Sonnet for speed)
- Scope default: only modified files (avoid unnecessary churn)
- Skip patterns: exclude non-code files by default
- Integration is additive - all existing workflows continue to work

## References

- Source: Anthropic internal code-simplifier prompt
- Related: TASK-05 (Autonomous Completion), TASK-19 (Multi-Claude)
