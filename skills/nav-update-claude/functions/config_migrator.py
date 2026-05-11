#!/usr/bin/env python3
"""
Navigator Config Migrator
Migrates .nav-config.json to latest version, adding missing sections.

Usage:
    python3 config_migrator.py .agent/.nav-config.json

Output:
    Updated config with new sections added
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Fallback version used only if plugin.json cannot be located/read.
# The real current version is loaded at runtime from .claude-plugin/plugin.json
# (see _read_plugin_version below). Keeping a fallback avoids hard-failing
# migrations on broken installs, but it intentionally lags far behind so a
# stale literal cannot silently downgrade a user's config.
_FALLBACK_VERSION = "0.0.0"


def _read_plugin_version() -> str:
    """
    Resolve the current Navigator version from .claude-plugin/plugin.json.

    Walks upward from this file's location looking for a sibling
    ``.claude-plugin/plugin.json``. This works both when invoked from the
    plugin source repo and from an installed plugin cache directory, since
    Claude Code preserves the ``skills/<skill>/functions/`` layout.

    Returns the ``version`` field, or ``_FALLBACK_VERSION`` if the file
    cannot be found or parsed.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".claude-plugin" / "plugin.json"
        if candidate.is_file():
            try:
                with open(candidate, "r") as f:
                    data = json.load(f)
                version = data.get("version")
                if isinstance(version, str) and version:
                    return version
            except (OSError, json.JSONDecodeError):
                break
            break
    return _FALLBACK_VERSION


CURRENT_VERSION = _read_plugin_version()

# Config sections added in each version
VERSION_CONFIGS: Dict[str, Dict[str, Any]] = {
    "5.4.0": {
        "simplification": {
            "enabled": False,
            "trigger": "post-implementation",
            "scope": "modified"
        }
    },
    "5.5.0": {
        "auto_update": {
            "enabled": True,
            "check_interval_hours": 1
        }
    },
    "5.6.0": {
        "task_mode": {
            "enabled": True,
            "auto_detect": True,
            "defer_to_skills": True,
            "complexity_threshold": 0.5,
            "show_phase_indicator": True
        }
    }
}


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string to tuple for comparison."""
    parts = version.replace("v", "").split(".")
    return tuple(int(p) for p in parts[:3])


def version_less_than(v1: str, v2: str) -> bool:
    """Check if v1 < v2."""
    return parse_version(v1) < parse_version(v2)


def get_missing_configs(current_version: str, config: Dict) -> Dict[str, Any]:
    """
    Determine which config sections are missing based on version.

    Args:
        current_version: Current config version
        config: Current config dict

    Returns:
        Dict of missing config sections to add
    """
    missing = {}

    for version, configs in VERSION_CONFIGS.items():
        # Check if this version's configs should be added
        if version_less_than(current_version, version) or current_version == version:
            for key, default_value in configs.items():
                if key not in config:
                    missing[key] = default_value

    return missing


def migrate_config(config_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Migrate config to latest version.

    Args:
        config_path: Path to .nav-config.json
        dry_run: If True, don't write changes

    Returns:
        Dict with migration results
    """
    path = Path(config_path)

    if not path.exists():
        return {
            "success": False,
            "error": f"Config not found: {config_path}",
            "changes": []
        }

    try:
        with open(path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON: {e}",
            "changes": []
        }

    current_version = config.get("version", "1.0.0")
    changes = []

    # Get missing configs
    missing = get_missing_configs(current_version, config)

    # Add missing sections
    for key, value in missing.items():
        config[key] = value
        changes.append({
            "action": "added",
            "key": key,
            "value": value
        })

    # Update version — only when the existing config is OLDER than the
    # current Navigator version. A direction-blind `!=` here previously
    # caused downgrades when the running plugin's CURRENT_VERSION was a
    # stale literal lower than the user's installed version (issue #7).
    if version_less_than(current_version, CURRENT_VERSION):
        old_version = current_version
        config["version"] = CURRENT_VERSION
        changes.append({
            "action": "updated",
            "key": "version",
            "old": old_version,
            "new": CURRENT_VERSION
        })

    # Write if not dry run and there are changes
    if changes and not dry_run:
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Trailing newline

    return {
        "success": True,
        "config_path": str(path),
        "old_version": current_version,
        # Reflect the version actually stored in the config. If the user is
        # already on a newer version we leave it alone (see guard above), so
        # reporting CURRENT_VERSION here would be a lie.
        "new_version": config.get("version", current_version),
        "changes": changes,
        "config": config
    }


def format_changes(result: Dict) -> str:
    """Format migration result for display."""
    if not result["success"]:
        return f"❌ Migration failed: {result['error']}"

    if not result["changes"]:
        return f"✅ Config already up to date (v{result['new_version']})"

    lines = [
        f"✅ Config migrated: v{result['old_version']} → v{result['new_version']}",
        "",
        "Changes:"
    ]

    for change in result["changes"]:
        if change["action"] == "added":
            key = change["key"]
            lines.append(f"  + {key}: (new section added)")
        elif change["action"] == "updated":
            lines.append(f"  ~ {change['key']}: {change['old']} → {change['new']}")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Navigator config")
    parser.add_argument("config_path", help="Path to .nav-config.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without applying")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    result = migrate_config(args.config_path, dry_run=args.dry_run)

    if args.json:
        # Don't include full config in JSON output (too verbose)
        output = {k: v for k, v in result.items() if k != "config"}
        print(json.dumps(output, indent=2))
    else:
        print(format_changes(result))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
