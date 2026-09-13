# Navigator v7.5.0 Release Notes — "Code Intelligence"

**Release Date**: 2026-09-13
**Type**: Minor — research agent uses the LSP tool when a language-server plugin is present; no config change

## Summary

Claude Code exposes an `LSP` tool whenever a language-server plugin from the official
marketplace is enabled (pyright-lsp, typescript-lsp, gopls-lsp, rust-analyzer-lsp and
eight more). Until now Navigator's codebase research ignored it and answered every
question with Grep and sampled Reads.

v7.5.0 teaches `navigator-research` to use that tool for symbol questions — who calls X,
where is Y defined, hover for a signature, an outline of a large file — and to fall back
to Grep when the tool is absent (TASK-76). Nothing is bundled, no server is required, no
config key was added: install the plugin for your language and the agent uses it; do not,
and nothing changes.

## What's New

**Phase 1.5 in `agents/navigator-research.md`.** An availability check, a question →
operation table, and four rules learned from the measurement: retry once when the
server's first answer looks partial (pyright answers its first request before it has
indexed the workspace), Read only the range LSP located, treat string- and config-wired
code as invisible to the server and confirm with Grep, never use LSP for conventions,
markdown or config. The Sampling Report gains an `LSP calls:` line.

**`scripts/agent_tool_counts.py`.** Real per-tool call counts and token usage from any
Claude Code transcript (main session or subagent), with usage counted once per API
request instead of once per JSONL line. Six unit tests; `scripts` joins `make test`.

## Measured

A/B on this repository, pyright-lsp disabled vs enabled, same agent text, counts from the
subagent transcript:

| Question | Without plugin | With plugin |
|---|---|---|
| Who calls `dispatch` (runtime.py:418) | 5 Reads, 6 Greps, 9 requests, 284k context tokens | 2 LSP calls (1 hit, retry → 61 across 4 files), 4 Reads, 1 Grep, 5 requests, 142k |
| Convention questions (stderr emitter rule, TASK doc shape) | — | zero LSP calls, same Reads, context within run-to-run spread |

Outline questions on files under ~500 lines stay on a single Read: `documentSymbol`
returns names and lines without signatures, and on a 470-line module the outline route
cost twice the context of reading the file once. Full table and spike transcripts in
`.agent/tasks/TASK-76-lsp-aware-research-agent.md`.

## Install

```
/plugin install pyright-lsp@claude-plugins-official     # or typescript-lsp, gopls-lsp, …
npm install -g pyright                                   # the server binary must be on PATH
```

Then use the research agent as usual. Cloud sessions have no language servers; the
agent's availability check makes the new phase a no-op there.

## Known limitations

- The first LSP request after server start may return a partial result; the agent retries
  once by design.
- Language servers see static imports only. Dynamic loads, registries keyed by string, and
  code embedded in strings need Grep, which the agent runs as confirmation.
- Passive diagnostics from the plugin reach the main session when files are opened and
  have no documented off-switch. This is the plugin's behavior, not Navigator's; the
  research agent is read-only and returns a summary.

## Files

- `agents/navigator-research.md`
- `scripts/agent_tool_counts.py`, `scripts/test_agent_tool_counts.py`, `Makefile`
- `README.md`, `CLAUDE.md`, `.agent/DEVELOPMENT-README.md`, `CHANGELOG.md`
- `.agent/tasks/TASK-76-lsp-aware-research-agent.md`
