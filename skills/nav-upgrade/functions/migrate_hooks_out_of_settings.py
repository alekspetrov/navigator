#!/usr/bin/env python3
"""
Migrate Navigator's lifecycle hooks out of a project's .claude/settings.json.

Context
-------
Navigator v6.13.0+ ships its lifecycle hooks via the plugin manifest
(`.claude-plugin/plugin.json`'s top-level `hooks` field). Prior versions
merged the same hook entries into the user's project `.claude/settings.json`
via skills/nav-init/functions/settings_merger.py. Those entries are now
duplicated (plugin manifest + user settings) AND broken (user-settings hooks
don't get `${CLAUDE_PLUGIN_ROOT}` substitution — only plugin-manifest hooks
do). Both problems disappear if we strip the Navigator-installed entries
out of `.claude/settings.json` and let the plugin manifest handle them.

Safety
------
- Match is conservative: a hook entry is removed only when its `type=command`
  string contains BOTH "hooks/" AND one of the known Navigator hook names.
  This prevents false positives if a user wrote their own hook that happens
  to share a substring with a Navigator hook.
- A backup is always written before any modification:
  `.claude/settings.json.pre-migrate.<UTC-timestamp>`.
- Removed entries are logged to stderr.
- Idempotent: re-running on an already-migrated file is a no-op (no backup
  is written, no log lines beyond the summary).
- Atomic write: tempfile + fsync + os.replace.

Usage
-----
    python3 migrate_hooks_out_of_settings.py /path/to/.claude/settings.json
    python3 migrate_hooks_out_of_settings.py --dry-run /path/to/.claude/settings.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import tempfile
from pathlib import Path

# Navigator hook script basenames (without .py). Match against the command
# string only when "hooks/" also appears, so a user script named e.g.
# "/scripts/token_monitor.sh" is not mistakenly classified as Navigator.
NAV_HOOK_NAMES = (
    "nav_session_start",
    "nav_pre_compact",
    "nav_post_compact",
    "nav_workflow_state",
    "nav_read_guard",
    "nav_task_graph_sync",
    "nav_profile_sync",
    "nav_commit_reminder",
    "nav_brief",
    "token_monitor",
    "workflow_enforcer",
)


def _is_navigator_command(cmd: str) -> bool:
    """A command counts as Navigator's iff it references hooks/<known-name>."""
    if not isinstance(cmd, str) or not cmd:
        return False
    if "hooks/" not in cmd:
        return False
    return any(name in cmd for name in NAV_HOOK_NAMES)


def _filter_hook_entry(entry: dict) -> tuple[dict | None, list[str]]:
    """Return (kept_entry_or_None, removed_command_strings).

    A "hook entry" looks like:
        {"matcher": "...", "hooks": [{"type": "command", "command": "..."}, ...]}

    We strip Navigator commands. If the resulting `hooks` list is empty,
    the whole entry is dropped (returns None).
    """
    if not isinstance(entry, dict):
        return entry, []
    inner = entry.get("hooks")
    if not isinstance(inner, list):
        return entry, []

    kept: list[dict] = []
    removed: list[str] = []
    for h in inner:
        if isinstance(h, dict) and h.get("type") == "command":
            cmd = h.get("command", "")
            if _is_navigator_command(cmd):
                removed.append(cmd)
                continue
        kept.append(h)

    if not kept:
        return None, removed
    new_entry = dict(entry)
    new_entry["hooks"] = kept
    return new_entry, removed


def _migrate_hooks_block(hooks: dict) -> tuple[dict, list[tuple[str, str]]]:
    """Walk every event → entries[] and strip Navigator commands.

    Returns (new_hooks_dict, list_of_(event, removed_command) tuples).
    Empty event arrays are dropped from the result.
    """
    new_hooks: dict = {}
    removed_log: list[tuple[str, str]] = []
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            new_hooks[event] = entries
            continue
        kept_entries: list[dict] = []
        for entry in entries:
            new_entry, removed_cmds = _filter_hook_entry(entry)
            for cmd in removed_cmds:
                removed_log.append((event, cmd))
            if new_entry is not None:
                kept_entries.append(new_entry)
        if kept_entries:
            new_hooks[event] = kept_entries
    return new_hooks, removed_log


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        os.replace(tmp_path, target)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _backup_path(target: Path) -> Path:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return target.with_name(target.name + f".pre-migrate.{ts}")


def migrate(target: Path, *, dry_run: bool = False) -> dict:
    """Migrate `target` settings.json. Returns a summary dict.

    Summary keys:
        removed:  list of (event, command) tuples — entries we stripped
        kept_user_hooks: int — total non-Navigator hook entries left intact
        backup_path:  str | None
        modified: bool
    """
    if not target.is_file():
        return {"removed": [], "kept_user_hooks": 0, "backup_path": None, "modified": False}

    raw = target.read_text(encoding="utf-8")
    if not raw.strip():
        return {"removed": [], "kept_user_hooks": 0, "backup_path": None, "modified": False}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(
            f"migrate_hooks_out_of_settings: {target} is invalid JSON ({e}). "
            "Refusing to migrate — fix or restore from backup first.",
            file=sys.stderr,
        )
        sys.exit(2)

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return {"removed": [], "kept_user_hooks": 0, "backup_path": None, "modified": False}

    new_hooks, removed = _migrate_hooks_block(hooks)

    # Count kept user hooks for the summary
    kept_user = 0
    for entries in new_hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            inner = (entry or {}).get("hooks") or []
            kept_user += sum(1 for _ in inner)

    if not removed:
        # No-op; idempotent.
        return {
            "removed": [],
            "kept_user_hooks": kept_user,
            "backup_path": None,
            "modified": False,
        }

    # Replace `hooks` (drop key entirely if it's now empty)
    new_data = dict(data)
    if new_hooks:
        new_data["hooks"] = new_hooks
    else:
        new_data.pop("hooks", None)

    serialized = json.dumps(new_data, indent=2) + "\n"
    backup_str: str | None = None
    if not dry_run:
        backup = _backup_path(target)
        backup.write_text(raw, encoding="utf-8")
        backup_str = str(backup)
        _atomic_write(target, serialized)

    return {
        "removed": removed,
        "kept_user_hooks": kept_user,
        "backup_path": backup_str,
        "modified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove legacy Navigator hook entries from .claude/settings.json",
    )
    parser.add_argument("target", help="Path to .claude/settings.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change; don't write.",
    )
    args = parser.parse_args()

    summary = migrate(Path(args.target), dry_run=args.dry_run)

    if not summary["modified"]:
        print(
            "migrate_hooks_out_of_settings: nothing to do "
            "(no Navigator hook entries found).",
            file=sys.stderr,
        )
        return 0

    print(f"✓ Backup written → {summary['backup_path']}", file=sys.stderr)
    print(
        f"✓ Removed {len(summary['removed'])} Navigator hook entries:",
        file=sys.stderr,
    )
    for event, cmd in summary["removed"]:
        print(f"    {event}: {cmd[:100]}", file=sys.stderr)
    print(
        f"✓ Preserved {summary['kept_user_hooks']} unrelated user hooks",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
