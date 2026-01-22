# Navigator v5.5.0 Release Notes

**Release Date**: 2025-01-22
**Type**: Minor Release (New Feature)

---

## 🎯 Headline: Auto-Update on Session Start

Navigator v5.5.0 introduces **Auto-Update** - automatically updates to the latest version when you start a session. No more manual `nav-upgrade` for daily releases.

**Core principle**: Zero friction updates. Say "start my session" → get latest version.

---

## ✨ What's New

### Auto-Update on Session Start

With 2x daily releases, manual updates create friction. Auto-update removes this barrier entirely.

**How it works**:
1. Session start checks for newer version
2. If update available AND `auto_update.enabled: true`:
   - Runs `claude plugin update navigator` (60s timeout)
   - Falls back to uninstall/reinstall if needed
3. Shows result and continues session

**UX Flow**:
```
User: "Start my Navigator session"

[Checking for updates...]
[✅ Auto-updated to v5.5.1]

╔═══════════════════════════════════════╗
║  🚀 Navigator Session Started (v5.5.1) ║
╚═══════════════════════════════════════╝
```

### Smart Update Interval

Avoids excessive GitHub API calls:

```json
{
  "auto_update": {
    "enabled": true,
    "check_interval_hours": 1
  }
}
```

- Checks at most once per hour (configurable)
- Stores `last_check` timestamp in config
- Skips if recently checked

### Graceful Failure Handling

Auto-update never blocks your session:

- **Network failure**: Skip update, continue session
- **Update timeout**: Show warning, continue session
- **Command failure**: Try reinstall fallback, then continue
- **Disabled in config**: Respect setting, just show version notification

---

## 📦 Files Changed

### New Files
- `skills/nav-start/functions/auto_updater.py` - Auto-update logic with version detection, update execution, and fallback reinstall

### Modified Files
- `skills/nav-start/SKILL.md` - Added Step 1.5 for auto-update execution
- `skills/nav-init/SKILL.md` - Updated default config template
- `.agent/.nav-config.json` - Added auto_update section
- `.claude-plugin/plugin.json` - Version 5.5.0, updated description
- `CLAUDE.md` - Auto-update documentation and config examples

---

## ⚙️ Configuration

Add to `.agent/.nav-config.json`:

```json
{
  "auto_update": {
    "enabled": true,
    "check_interval_hours": 1
  }
}
```

**Options**:
- `enabled`: Enable/disable auto-update (default: `true`)
- `check_interval_hours`: Minimum hours between checks (default: `1`)

**To disable**:
```json
{
  "auto_update": {
    "enabled": false
  }
}
```

You'll still see update notifications - just run `nav-upgrade` manually when ready.

---

## 🔄 Upgrade Path

1. Update plugin: `nav-upgrade` or wait for next session
2. New projects get `auto_update.enabled: true` by default
3. Existing projects: Add config manually or let defaults apply

**Existing config?** Add the `auto_update` section:
```json
{
  "version": "5.5.0",
  "auto_update": {
    "enabled": true,
    "check_interval_hours": 1
  }
}
```

---

## 🎯 Use Cases

### Daily Development
```
User: "Start my Navigator session"
→ Auto-update runs silently
→ Session starts with latest version
→ New features available immediately
```

### Slow Networks
```
User: "Start my Navigator session"
→ Update check times out after 10s
→ "⚠️ Auto-update failed, run nav-upgrade manually"
→ Session continues normally
```

### Controlled Updates
```json
{
  "auto_update": {
    "enabled": false
  }
}
```
```
User: "Start my Navigator session"
→ Version check shows update available
→ Session starts with current version
→ Manual "nav-upgrade" when ready
```

---

## ⚠️ Known Limitations

- **First session after install**: No update needed
- **Offline mode**: Gracefully skips, continues session
- **Rate limiting**: GitHub API has limits (1 check/hour default avoids this)
- **Plugin permissions**: Requires `claude` CLI in PATH

---

## 📊 Impact

- **Zero friction updates**: Latest version without manual intervention
- **Faster feature adoption**: New skills available immediately
- **Reduced support burden**: Users always on latest version
- **Graceful degradation**: Never blocks session on failure

---

## 🙏 Credits

Inspired by the frustration of releasing 2x daily and asking users to run `nav-upgrade` each time.

---

**Full changelog**: [v5.4.0...v5.5.0](https://github.com/alekspetrov/navigator/compare/v5.4.0...v5.5.0)
