# Navigator v5.3.0 Release Notes

**Release Date**: 2025-01-21

## Task Verification Enhancement

This release adds structured verification to Navigator's task system, inspired by GSD (Get Shit Done) spec-driven development.

### New Features

#### Verify/Done Sections in Tasks

Tasks now include executable verification:

```markdown
## Verify

```bash
npm test src/auth
npm run build
```

## Done

- [ ] User can log in with OAuth
- [ ] Session persists across refresh
```

**Benefits**:
- Machine-parseable completion requirements
- Executable validation commands
- Observable "done" criteria

#### verify_extractor.py Utility

New utility to parse verification data from task files:

```bash
# Human-readable output
python3 skills/nav-task/functions/verify_extractor.py .agent/tasks/TASK-30.md

# JSON output for automation
python3 skills/nav-task/functions/verify_extractor.py --json .agent/tasks/TASK-30.md

# Commands only (for scripting)
python3 skills/nav-task/functions/verify_extractor.py --commands-only .agent/tasks/TASK-30.md
```

#### Multi-Claude Review Integration

Review phase now automatically:
1. Detects `## Verify` section in task file
2. Extracts and executes verification commands
3. Checks `## Done` criteria
4. Reports pass/fail in review output

### Reliability Improvements

- **Atomic state file writes**: Prevents corruption during concurrent access
- **Enhanced marker instructions**: Clearer "FINAL STEP (MANDATORY)" language
- **Increased Review timeout**: 180s → 300s for comprehensive verification
- **Touch verification**: Added `&& echo 'Marker created'` confirmation

### Files Changed

- `templates/task-template.md` - Added Verify/Done sections
- `skills/nav-task/SKILL.md` - Updated CREATE + ARCHIVE templates
- `skills/nav-task/functions/task_formatter.py` - Added sections to output
- `skills/nav-task/functions/verify_extractor.py` - NEW utility
- `scripts/navigator-multi-claude.sh` - Enhanced Review phase

### Backward Compatibility

- Existing tasks without Verify/Done sections continue to work
- No migration required
- Optional: Manually add sections to existing tasks

## Upgrade

```bash
# Update plugin
/plugin uninstall navigator && /plugin install navigator
```

Or update via skill:
```
"Upgrade Navigator to latest version"
```

---

**Full Changelog**: [v5.2.0...v5.3.0](https://github.com/alekspetrov/navigator/compare/v5.2.0...v5.3.0)
