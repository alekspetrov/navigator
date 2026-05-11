# Navigator v6.13.0 Release Notes

**Release Date**: 2026-05-12
**Type**: Minor — hook distribution refactor + three latent-bug fixes

---

## Summary

v6.13.0 closes three upstream issues that turned out to compound:

- **#9 (architectural)** — hooks shipped through the wrong distribution channel. The merge-into-user-settings path made `${CLAUDE_PLUGIN_DIR}` un-substitutable. Every Navigator install since hooks were introduced had silently broken plugin-dir hook paths.
- **#8 (wiring)** — `workflow_enforcer.py` was registered under the wrong Claude Code event, making the first-ever blocking hook in Navigator a no-op.
- **#7 (migrator)** — `config_migrator.py` would downgrade newer configs to a hardcoded literal.

All three landed in one minor because #9 is the root cause that made #8 visible and structurally invited the duplicate-distribution problem #7 (different file, same anti-pattern of hard-coding the canonical version somewhere other than `plugin.json`).

---

## Change A: hooks now declared in plugin.json (#9)

**Symptom:** every fresh install since the lifecycle hooks landed reported:

```
[python3 "${CLAUDE_PLUGIN_DIR}/hooks/nav_workflow_state.py"]: can't open file '/hooks/nav_workflow_state.py'
```

Same error on `nav_pre_compact.py`, `nav_post_compact.py`, `nav_read_guard.py`, `nav_task_graph_sync.py`, `nav_profile_sync.py`, etc. The Stop hook fired every turn, the PreCompact hook fired before every compact, the PostToolUse hooks fired on every edit — and every one of them tried to run `/hooks/X.py` because the variable wasn't expanding.

**Root cause:** `${CLAUDE_PLUGIN_DIR}` is set by Claude Code **only** for hooks declared in a plugin manifest (`.claude-plugin/plugin.json`'s `hooks` field). It's not a globally-available environment variable. Hooks defined in a project's `.claude/settings.json` aren't tied to any plugin — Claude Code has no plugin context to inject, the shell expands the unset variable to empty, and the path becomes `/hooks/X.py`.

`.claude-plugin/plugin.json` had no `hooks` field. All Navigator hooks shipped through `templates/claude-settings-hooks.json` → `skills/nav-init/functions/settings_merger.py` → user's project settings. The two halves of the system were mutually incompatible.

**Fix:**

- `.claude-plugin/plugin.json` declares all 7 events (`SessionStart`, `PreCompact`, `PostCompact`, `Stop`, `UserPromptSubmit`, `PreToolUse:Read`, `PostToolUse` with three matchers including the new `nav_commit_reminder` Bash probe). `${CLAUDE_PLUGIN_DIR}` substitutes correctly when hooks come from the plugin manifest.
- `templates/claude-settings-hooks.json` deleted.
- `skills/nav-init/SKILL.md` and `skills/nav-upgrade/SKILL.md` no longer prompt to merge hooks into user settings.
- `settings_merger.py` retained for `permissions` and other non-hook keys; its hook-merge path is now dead code in Navigator's own flows but still works for downstream consumers if they want it. All 11 existing merger tests still pass.

**Migration for existing installs:**

`skills/nav-upgrade/functions/migrate_hooks_out_of_settings.py` (new, 7 tests) scans `.claude/settings.json` and removes hook entries whose command path contains both `hooks/` and one of 10 Navigator hook basenames. Writes `.pre-migrate.<UTC-ts>` backup. Atomic. Idempotent. Leaves user-defined hooks and non-hook top-level keys untouched. Wired into `skills/nav-upgrade/SKILL.md` Step 5.

After upgrading to v6.13.0, **restart Claude Code** — hook registrations are cached at session start, so the plugin manifest's new hooks won't activate until the next session.

---

## Change B: workflow_enforcer.py correctly wired (#8)

**Symptom:** v6.11.1 advertised `workflow_enforcer.py` as Navigator's first blocking hook — `exit 2` when the prior assistant turn skipped its `WORKFLOW CHECK` block. In practice, the hook never blocked anything, because:

```python
def get_user_message() -> str:
    """Get user message from stdin JSON (UserPromptSubmit) or env (legacy)."""
    ...
    data = json.loads(raw)
    prompt = data.get("prompt") or data.get("user_message") or ""
```

The script reads stdin shaped like `{"prompt": "<user text>"}`. The hook was registered under `PreToolUse` (matcher `Edit|Write|Bash|Task`), where stdin is `{"tool_name": "Edit", "tool_input": {...}, "session_id": ..., "cwd": ...}` — no `prompt` key.

`message = ""` → `if not message: sys.exit(0)` at line 125. The `exit 2` blocking branch (lines 173–198) was unreachable. The "first blocking hook in Navigator" was a no-op in every install since v6.11.1.

(v6.12.1 release notes claimed this was already fixed in the template. It was, in `templates/claude-settings-hooks.json` — but the template wasn't what users ran, because the merge step also installed entries that survived from earlier versions. The architectural fix in Change A makes this moot: hooks now come from the plugin manifest, which had the correct wiring from this release forward.)

**Fix:**

- `.claude-plugin/plugin.json` registers `workflow_enforcer.py` under `UserPromptSubmit` (no `matcher` field — `UserPromptSubmit` doesn't take one). Stdin shape now matches what the script expects.
- `hooks/workflow_enforcer.py` gains an escape hatch at the top of `main()`:

  ```python
  if os.environ.get("PILOT_EXECUTOR"):
      sys.exit(0)
  ```

  For autonomous executors (Pilot is the concrete case, but the pattern generalizes) that spawn `claude-code` with a single `-p <prompt>` and don't run the WORKFLOW CHECK protocol by design. Pilot already injects `PILOT_EXECUTOR=1` in `backend_claudecode.go:379`.

---

## Change C: config_migrator.py direction-guarded (#7)

**Symptom:** Running `nav-update-claude` on a project whose `.agent/.nav-config.json` was newer than the migrator's hardcoded version would *downgrade* it to that literal. Specifically observed at v6.8.0 → v5.7.0 — i.e., the migrator was 8 minor releases stale and would happily rewrite live configs to match.

**Root cause:** two stacked bugs.

1. `CURRENT_VERSION = "5.7.0"` on line 19 was a hardcoded literal. Every release left it stale.
2. The decision used `if current_version != CURRENT_VERSION` — direction-blind. A newer config was rewritten just as readily as an older one. The module already had a `version_less_than` helper defined at line 54, unused at the decision point.

**Fix:**

- `CURRENT_VERSION` now reads from `.claude-plugin/plugin.json` at import time via a `pathlib.Path(__file__).resolve().parents` upward walk. Works from both repo root and installed-plugin cache because Claude Code preserves the `skills/<skill>/functions/` layout.
- Fallback `"0.0.0"` (deliberately stale) is used only if the file is missing or unparseable. Guarantees the new direction guard cannot trigger a downgrade even on a broken install — `0.0.0` will never be greater than any real version.
- The decision now uses `if version_less_than(current_version, CURRENT_VERSION)` — only migrate when the existing version is *older*. Equal and newer configs are no-ops.
- Bonus fix: the returned `new_version` field used to always report `CURRENT_VERSION` regardless of what was actually written. Fixed — it now reflects the on-disk state. The display string in `format_changes` reads from this field, so the lie was user-visible.

7 new tests in `skills/nav-update-claude/functions/test_config_migrator.py`:

- `test_newer_config_is_not_downgraded` — writes 999.0.0, asserts no version-update change and file unchanged
- `test_equal_version_is_noop_for_version_field`
- `test_older_config_is_upgraded`
- `test_older_config_dry_run_does_not_write`
- `test_reads_version_from_plugin_json`
- `test_module_current_version_matches_plugin_json`
- `test_basic_orderings` (version_less_than sanity)

---

## Test summary

25/25 tests green:

```
$ python3 -m unittest skills.nav-update-claude.functions.test_config_migrator
Ran 7 tests in 0.003s — OK

$ python3 -m unittest skills.nav-upgrade.functions.test_migrate_hooks_out_of_settings
Ran 7 tests in 0.006s — OK

$ python3 -m unittest skills.nav-init.functions.test_settings_merger
Ran 11 tests in 0.010s — OK
```

---

## Upgrade path

```
"upgrade navigator"
```

The plugin will pull v6.13.0. After install, **restart Claude Code** to register the new plugin-manifest hooks (mid-session updates don't refresh hook registrations). On first run after restart, `nav-upgrade` will invoke the migration script, scan your `.claude/settings.json` for the now-redundant Navigator hook entries, write a `.pre-migrate.<ts>` backup, and remove them. Your user-defined hooks, permissions, and other settings are untouched.

---

## Notes

- Detected during a v6.12.0 upgrade audit on the Pilot project. The same bug had been silently shipping since hooks were introduced — the merge channel hid the failure by making every hook always-emit a "command not found" error that most users ignored as benign noise.
- Three upstream issues filed and resolved here: [#7](https://github.com/alekspetrov/navigator/issues/7), [#8](https://github.com/alekspetrov/navigator/issues/8), [#9](https://github.com/alekspetrov/navigator/issues/9).
- `settings_merger.py` is still load-bearing for projects that customize Navigator with extra `permissions` or `mcpServers` blocks. It's the hook-merge path that's now dead-code in Navigator flows.
