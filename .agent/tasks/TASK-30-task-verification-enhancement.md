# TASK-30: Task Verification Enhancement

**Status**: ✅ Completed
**Priority**: High
**Created**: 2025-01-21
**Target Version**: v5.3.0

## Context

**Problem**: Navigator tasks use checkboxes for completion but lack:
- Executable verification commands
- Observable done criteria
- Machine-parseable completion requirements

**Inspiration**: GSD (Get Shit Done) uses XML task format with `<verify>` and `<done>` tags. Navigator should have equivalent using markdown (not XML).

**Goal**: Add `## Verify` and `## Done` sections to task system.

## Implementation Plan

### Phase 1: Template Updates
- [x] Update `templates/task-template.md` with Verify/Done sections
- [x] Update `skills/nav-task/SKILL.md` CREATE template
- [x] Update `skills/nav-task/SKILL.md` ARCHIVE template
- [x] Update `skills/nav-task/functions/task_formatter.py`

### Phase 2: Tooling
- [x] Create `skills/nav-task/functions/verify_extractor.py`

### Phase 3: Documentation
- [x] Update `.agent/DEVELOPMENT-README.md` with TASK-30
- [x] Test with verify_extractor.py

## Technical Decisions

| Decision | Options | Chosen | Why |
|----------|---------|--------|-----|
| Format | XML, YAML frontmatter, Markdown sections | Markdown sections | Consistent with existing, readable |
| Metadata | YAML frontmatter | Keep `**Key**: Value` | No migration, backward compatible |
| Auto-execute verify | Yes, No | No (manual/review) | Avoid infinite loops |

## Verify

```bash
# Test verify_extractor.py parses this file correctly
python3 skills/nav-task/functions/verify_extractor.py .agent/tasks/TASK-30-task-verification-enhancement.md

# Check templates have new sections
grep -A 3 "## Verify" templates/task-template.md
grep -A 3 "## Done" templates/task-template.md

# Check skill has new sections
grep -A 3 "## Verify" skills/nav-task/SKILL.md
```

## Done

- [x] New tasks include Verify/Done sections in template
- [x] verify_extractor.py parses commands correctly
- [x] Existing tasks work without modification (backward compatible)
- [x] DEVELOPMENT-README.md lists TASK-30

## Completion Checklist

- [ ] Code changes committed
- [ ] Documentation updated
- [ ] Tests pass

---

**Created**: 2025-01-21
