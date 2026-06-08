# Navigator v6.15.7 Release Notes

**Release Date**: 2026-06-08
**Type**: Patch — corrects the plugin hook env-var name (`CLAUDE_PLUGIN_DIR` → `CLAUDE_PLUGIN_ROOT`) and publishes the audit-remediation batch (wp1–wp11) that had accumulated unreleased on `main`.

---

## Headline fix: the hook env var never existed

Every Navigator lifecycle hook referenced **`${CLAUDE_PLUGIN_DIR}`** — a variable
**Claude Code has never defined**. The three documented plugin path variables are
`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, and `${CLAUDE_PROJECT_DIR}`
([plugins reference](https://code.claude.com/docs/en/plugins-reference#environment-variables)).

Because the name was wrong, the variable always expanded to empty and the
`:-fallback` always fired:

```
python3 "${CLAUDE_PLUGIN_DIR:-$HOME/.claude/plugins/marketplaces/navigator-marketplace}/hooks/X.py"
                          ^ always empty → always used the fallback
```

So since hooks moved into the plugin manifest (**v6.13.0**), every install has
resolved its hooks against the **marketplace checkout** (which tracks `main`)
rather than the **installed version**. This was invisible while `main` and the
released version carried the same hook files. It became visible the moment they
diverged: the published manifest still referenced `token_monitor.py` (retired on
`main` by the v6.15.6 audit work), so the fallback path 404'd and threw a
`PostToolUse` error on every tool call — the exact symptom the v6.14.0 /
v6.15.1 saga (`mem-036`, the "silent-fail" guard) had been chasing without
identifying the root cause.

### The fix

`CLAUDE_PLUGIN_DIR` → `CLAUDE_PLUGIN_ROOT` across all live runtime and guidance:

| Surface | Change |
|---|---|
| `.claude-plugin/plugin.json` | 8 hook commands now use `${CLAUDE_PLUGIN_ROOT:-…}`; the marketplace path stays as a last-resort fallback. The primary now actually resolves — to the *installed* version. |
| `hooks/nav_session_start.py`, `nav_profile_sync.py`, `nav_task_graph_sync.py` | `_resolve_plugin_dir()` reads `CLAUDE_PLUGIN_ROOT` first, with `CLAUDE_PLUGIN_DIR` kept as a back-compat fallback. |
| `skills/nav-release/functions/release_validator.py` | `--verify-hooks` smoke-tests under set/unset `CLAUDE_PLUGIN_ROOT`. |
| ~17 skill `SKILL.md` files | Bash snippets + prose updated to `${CLAUDE_PLUGIN_ROOT:-…}`. |
| `migrate_hooks_out_of_settings.py` docstring, `mem-027` pattern memory | Forward guidance corrected to the real variable. |

**Preserved deliberately**: all historical references (CHANGELOG, prior release
notes, `marketplace.json` metadata, task postmortems, `mem-036`, `graph.json`,
the v6.14.0 guard quote in `nav-release/SKILL.md`) — they accurately describe the
past. The 3 hooks keep `CLAUDE_PLUGIN_DIR` as a secondary read for back-compat.

---

## Also in this release: audit remediation (wp1–wp11)

This is the first tagged release since v6.15.6, so it publishes the 15 commits of
audit-remediation work (TASK-42 roadmap) that landed on `main`:

- **wp1 / TASK-43** — CI test workflow + pre-publish validation gate
- **wp2 / TASK-44** — version & release tooling correctness (+ `bump-version.sh`)
- **wp8 / TASK-50** — skill template/reference integrity
- **wp4 / TASK-45** — test coverage for hooks & blocking paths
- **wp5 / TASK-46** — hook correctness/safety, `token_monitor` retirement
- **wp6 / TASK-47** — knowledge-graph data integrity
- **wp7 / TASK-48** — detection precision (token-boundary trigger matching)
- **wp3 / TASK-49** — plugin-relative path resolution
- **wp11 / TASK-51** — misc Python correctness fixes
- **wp10 / TASK-25** — multi-Claude shell workflows deprecated (superseded by native Workflows)
- **wp9 / TASK-52** — docs & config drift cleanup

---

## Verification

- `--verify-hook-paths` → `8/8 resolve to an existing file`.
- `--verify-hooks` → `16/16 passed` (every hook under both set and unset `CLAUDE_PLUGIN_ROOT`); SessionStart emits its full payload in both cases.
- `make test` → all unit tests pass (hook suite 50/50, release validator 10/10, migrate 7/7).
- `grep -rn CLAUDE_PLUGIN_DIR` → remaining matches are history, intentional back-compat, or legacy test fixtures only.
- All five version files at `6.15.7` (`release_validator --check-version 6.15.7` ✓).

---

## Upgrade notes

No config changes. No migration.

**Restart Claude Code after upgrade** so the corrected plugin manifest is
re-registered.

Existing installs that earlier had Navigator hooks merged into a project's
`.claude/settings.json` (pre-v6.13.0 style) should run
`migrate_hooks_out_of_settings.py` (nav-upgrade Step 5) to drop those now-redundant,
absolute-path entries and let the manifest provide hooks.

---

## Files modified

```
.claude-plugin/plugin.json                     (8 hook commands: DIR→ROOT + version)
.claude-plugin/marketplace.json                (version + changelog entry)
hooks/nav_session_start.py                      (ROOT-first resolution)
hooks/nav_profile_sync.py                       (ROOT-first resolution)
hooks/nav_task_graph_sync.py                    (ROOT-first resolution)
skills/nav-release/functions/release_validator.py        (smoke-test ROOT)
skills/nav-release/functions/test_release_validator.py   (fixture ROOT)
skills/nav-release/SKILL.md                     (live refs ROOT; v6.14.0 history kept)
skills/**/SKILL.md  (×16)                        (snippets/prose DIR→ROOT)
skills/nav-upgrade/functions/migrate_hooks_out_of_settings.py  (docstring)
.agent/knowledge/memories/patterns/mem-027.md   (forward guidance)
README.md, CLAUDE.md, .agent/.nav-config.json   (version)
.agent/tasks/TASK-53-claude-plugin-root-env-var.md  (new)
CHANGELOG.md                                    (new v6.15.7 entry)
releases/RELEASE-NOTES-v6.15.7.md               (new)
```
