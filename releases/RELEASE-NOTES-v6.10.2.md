# Navigator v6.10.2 Release Notes

**Release Date**: 2026-05-11
**Type**: Patch (auto-updater fix — SessionStart auto-update now actually works)

---

## Summary

The SessionStart hook prints `"Auto-update failed. Run nav-upgrade manually."` at the top of every session — and it has been doing so on every release since auto-update was introduced. Three bugs in the auto-updater were stacked on top of each other:

1. The plugin was being referenced by its unqualified name.
2. The marketplace cache was never refreshed before the update call.
3. Version detection couldn't parse Claude Code's actual `plugin list` output.

Each one alone would have failed the auto-update. All three together meant SessionStart hooks essentially always reported failure, the user always had to run `nav-upgrade` manually, and every release became a chore.

This patch fixes all three. The notification message you've been ignoring should start meaning something again.

---

## Fixes (all in `skills/nav-start/functions/auto_updater.py`)

### 1. Qualified plugin name

**Before**:
```python
subprocess.run(['claude', 'plugin', 'update', 'navigator'], ...)
# → "Plugin 'navigator' not found"
```

Claude Code's plugin manager requires `<plugin>@<marketplace>` form when the plugin exists in a registered marketplace. The unqualified name is rejected.

**After**:
```python
PLUGIN_QUALIFIED = 'navigator@navigator-marketplace'
subprocess.run(['claude', 'plugin', 'update', PLUGIN_QUALIFIED], ...)
```

Applied to update, uninstall, and install in the reinstall fallback.

### 2. Marketplace cache refresh

**Before**: `claude plugin update navigator@navigator-marketplace` would frequently report `"already at the latest version"` even when GitHub had a newer release. Claude Code maintains a local marketplace cache and does **not** refresh it before running an update — so the update sees the stale version manifest and concludes there's nothing to do.

**After**: a new `refresh_marketplace()` helper runs `claude plugin marketplace update navigator-marketplace` first, then proceeds with the update:

```python
def update_plugin_via_claude() -> Dict:
    refresh = refresh_marketplace()
    if not refresh['success']:
        return {'success': False, 'error': ..., 'method': 'update'}
    # ... then run plugin update
```

### 3. Multi-line `plugin list` parser

**Before**: `get_current_version` looked for the version on the same line as the plugin name:

```python
for line in result.stdout.split('\n'):
    if 'navigator' in line.lower():
        match = re.search(r'v?(\d+\.\d+\.\d+)', line)  # ← always misses
```

But Claude Code's actual output is:

```
❯ navigator@navigator-marketplace
  Version: 6.10.2
  Scope: user
  Status: ✔ enabled
```

The plugin entry header and the version are on **separate lines**. So `current_version` was always `None`, and the auto-updater short-circuited with `"Could not detect current Navigator version"` before it even got to comparing versions.

**After**: the parser scans forward from the navigator entry header until it finds a `Version: X.Y.Z` line:

```python
in_navigator_block = False
for line in lines:
    if 'navigator' in line.lower() and '@' in line:
        in_navigator_block = True
        continue
    if in_navigator_block:
        match = re.search(r'Version:\s*v?(\d+\.\d+\.\d+)', line)
        if match:
            return match.group(1)
        if line.strip().startswith('❯'):
            in_navigator_block = False
```

---

## Verification

Run the auto-updater directly to see it work end-to-end:

```bash
python3 ~/.claude/plugins/cache/navigator-marketplace/navigator/6.10.2/skills/nav-start/functions/auto_updater.py
```

Expected output:
```json
{
  "status": "up-to-date",
  "message": "Already on latest version",
  "current_version": "6.10.2",
  "latest_version": "6.10.2"
}
```

Or with an older version installed, you should see `"status": "updated"` with `current_version` < `new_version`.

---

## Upgrade

This is the version that fixes the upgrade flow. So this one time, please run the upgrade manually:

```bash
claude plugin marketplace update navigator-marketplace
claude plugin update navigator@navigator-marketplace
```

From v6.10.2 onward, SessionStart's auto-update should handle it on its own.
