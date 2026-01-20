# Navigator v4.6.0 Release Notes

**Release Date**: 2025-11-28
**Type**: Feature Release - Architecture Optimization
**Focus**: Native Claude Code integration, token monitoring, cleanup

---

## Overview

Version 4.6.0 optimizes Navigator's architecture based on Claude Code documentation review. Introduces native Claude Code agents, automatic token monitoring hooks, and cleans up unused skill metadata. These changes improve auto-invocation reliability and add proactive context management.

---

## Key Features

### 1. Native Claude Code Agents

**What's New**: Two custom agents leveraging Claude Code's native subagent system.

**agents/navigator-research.md**:
- Specialized codebase exploration
- 60-80% token savings vs manual file reading
- Samples representative files instead of reading everything
- Returns concise summaries with file references

**agents/task-planner.md**:
- Implementation planning and task breakdown
- Creates structured plans in `.agent/tasks/` format
- Identifies dependencies and critical path
- Estimates effort realistically

**Usage**:
```
"Use the navigator-research agent to explore how authentication works"
"Use the task-planner agent to create a plan for adding dark mode"
```

**Impact**: Context isolation prevents pollution of main conversation.

---

### 2. Token Budget Monitoring Hook

**What's New**: Automatic context usage monitoring that warns before you hit limits.

**Implementation**:
- `hooks/monitor-tokens.py` - Python script monitoring transcript size
- `.claude/settings.json` - Hook configuration for PostToolUse events
- Warns at 70% usage, critical alert at 85%

**Behavior**:
```
[After tool calls when approaching limits]

==================================================
  CONTEXT CRITICAL: 87% used
  156,600 / 180,000 tokens

  Run: 'Clear context and preserve markers'
  Or:  /nav:compact
==================================================
```

**Auto-Setup**:
- New projects: `nav-init` creates `.claude/settings.json`
- Existing projects: `nav-upgrade` installs hooks automatically

---

### 3. Skills Cleanup

**Removed `auto-invoke: true` field**:
- Field was not used by Claude Code
- Auto-invocation determined by description quality
- Removed from all 19 skills

**Removed `nav-social-post` skill**:
- Misaligned with Navigator's core documentation-efficiency mission
- Skills reduced: 20 → 19

**Removed `nav-markers` skill**:
- Empty skeleton (0 bytes)
- Functionality covered by `nav-marker`

---

### 4. Upgrade Path Improvements

**nav-init skill updated**:
- Creates `.claude/settings.json` with hook configuration
- Token monitoring active on new projects immediately

**nav-upgrade skill updated**:
- Step 5 added: Install/update token monitoring hooks
- Backs up existing `.claude/settings.json` before overwriting
- Existing projects get monitoring on upgrade

---

## Breaking Changes

None. All changes are backward compatible.

---

## Migration Guide

### For New Projects

```bash
# Initialize Navigator (hooks included automatically)
"Initialize Navigator in this project"
```

### For Existing Projects

```bash
# Upgrade Navigator (hooks installed automatically)
"Update Navigator"
```

### Manual Hook Installation (Optional)

If you prefer manual setup:

```bash
mkdir -p .claude

cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|Bash|Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_DIR}/hooks/monitor-tokens.py\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
```

---

## Files Changed

### Added
- `agents/navigator-research.md` - Codebase exploration agent
- `agents/task-planner.md` - Implementation planning agent
- `hooks/monitor-tokens.py` - Token budget monitoring
- `.claude/settings.json` - Hook configuration
- `.agent/tasks/TASK-26-plugin-optimization-roadmap.md` - Implementation docs

### Modified
- `.claude-plugin/plugin.json` - Version bump, removed nav-social-post
- `skills/nav-init/SKILL.md` - Added hooks setup step
- `skills/nav-upgrade/SKILL.md` - Added hooks setup step
- All `skills/*/SKILL.md` - Removed `auto-invoke: true` field

### Removed
- `skills/nav-social-post/` - Entire directory
- `skills/nav-markers/` - Empty skeleton

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Skills count | 20 | 19 |
| Native agents | 0 | 2 |
| Token monitoring | Manual | Automatic |
| Unused metadata | ~400 tokens | 0 |

---

## Documentation

- [TASK-26 Roadmap](.agent/tasks/TASK-26-plugin-optimization-roadmap.md)
- [Claude Code Agents](https://docs.anthropic.com/claude-code/agents)
- [Claude Code Hooks](https://docs.anthropic.com/claude-code/hooks)

---

## What's Next (v4.7.0)

- Task completion automation hook
- Session start hook for Navigator auto-load
- Additional agents for code review

---

**Full Changelog**: https://github.com/alekspetrov/navigator/compare/v4.5.0...v4.6.0
