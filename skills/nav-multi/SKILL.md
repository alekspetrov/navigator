---
name: nav-multi
description: DEPRECATED. Multi-Claude shell orchestration is superseded by native Claude Code Workflows. Auto-invokes on "run multi-agent workflow", "parallel agents for", "multi-claude for", "spawn agents for" to redirect the user to the native Workflow and Agent tools.
allowed-tools: Read
version: 2.0.0
---

# nav-multi (DEPRECATED)

**Deprecated as of 2026-06 (TASK-25).**

Navigator's marker-coordinated, headless `claude -p` multi-agent scripts are
superseded by Claude Code's **native orchestration** — more reliable, no external
scripts, and what this project itself now uses for its own audits and planning:

- **`/workflows` — Dynamic Workflows**: deterministic multi-phase orchestration
  (plan → implement → test → review), parallel/pipeline fan-out, structured
  output, in-session resume. No marker files, no context bloat.
- **The Agent tool / subagents**: parallel independent agents with optional git
  worktree isolation; can run in the background and report back.

## When invoked

Tell the user the multi-Claude scripts are deprecated and point them to the
native tools above. **Do NOT run** `navigator-multi-claude*.sh`.

Example response:

> Multi-Claude shell workflows are deprecated. Use native Claude Code
> orchestration instead: `/workflows` for multi-phase work, or the Agent tool
> for parallel subagents. Both supersede the old marker-file scripts.

## History

The scripts (`scripts/navigator-multi-claude*.sh`, `sub-claude-monitor.sh`,
`resume-workflow.sh`, `multi-claude-dashboard.sh`) remain in the repo for
reference under a `DEPRECATED` banner but are unmaintained (~30% success rate).
See `.agent/tasks/TASK-25-fix-multi-claude-reliability.md` for the deprecation
rationale and the research that informed it.
