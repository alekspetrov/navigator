---
name: nav-install-multi-claude
description: DEPRECATED. The multi-Claude orchestration scripts are deprecated in favor of native Claude Code Workflows; no installation is needed. Auto-invokes on "install multi-Claude workflows", "set up multi-Claude", "enable parallel execution" to explain the deprecation.
allowed-tools: Read
version: 2.0.0
---

# nav-install-multi-claude (DEPRECATED)

**Deprecated as of 2026-06 (TASK-25).** Do not install the multi-Claude shell
scripts. They are superseded by Claude Code's **native orchestration**, which
requires no separate installation:

- **`/workflows`** — Dynamic Workflows for multi-phase, parallel, resumable work.
- **The Agent tool / subagents** — parallel agents with git-worktree isolation.

## When invoked

Explain that the multi-Claude scripts are deprecated and **no install is needed**;
point the user to `/workflows` and the Agent tool. **Do NOT run**
`install-multi-claude.sh` (it now refuses to run).

## Removing a stale install

If a previous Navigator version installed the scripts to `~/bin`, remove them:

```bash
rm -f "$HOME/bin/navigator-multi-claude.sh" \
      "$HOME/bin/navigator-multi-claude-poc.sh" \
      "$HOME/bin/install-multi-claude.sh"
```

See `.agent/tasks/TASK-25-fix-multi-claude-reliability.md` for the deprecation
rationale.
