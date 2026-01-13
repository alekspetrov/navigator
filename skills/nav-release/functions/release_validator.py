#!/usr/bin/env python3
"""
Release validator for Navigator plugin.

Validates plugin integrity before release:
- All skills in plugin.json exist
- All skills are committed (not untracked)
- Version consistency across files
- Tag contains all expected files

Usage:
    python3 release_validator.py --check-all
    python3 release_validator.py --check-version 5.1.0
    python3 release_validator.py --verify-tag v5.1.0

Created: 2025-01-13 (after v5.1.0 missing nav-profile incident)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict


def get_project_root() -> Path:
    """Find project root (contains .claude-plugin/)."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude-plugin" / "plugin.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def load_plugin_json(root: Path) -> dict:
    """Load plugin.json configuration."""
    plugin_path = root / ".claude-plugin" / "plugin.json"
    if not plugin_path.exists():
        return {}
    with open(plugin_path) as f:
        return json.load(f)


def check_skills_exist(root: Path, plugin: dict) -> Tuple[List[str], List[str]]:
    """
    Check all skills referenced in plugin.json exist.

    Returns:
        (existing_skills, missing_skills)
    """
    skills = plugin.get("skills", [])
    existing = []
    missing = []

    for skill_path in skills:
        # Normalize path (remove ./ prefix)
        clean_path = skill_path.lstrip("./")
        skill_dir = root / clean_path
        skill_md = skill_dir / "SKILL.md"

        if skill_md.exists():
            existing.append(clean_path)
        else:
            missing.append(clean_path)

    return existing, missing


def check_skills_committed(root: Path, plugin: dict) -> Tuple[List[str], List[str], List[str]]:
    """
    Check git status of all skills.

    Returns:
        (committed, modified, untracked)
    """
    skills = plugin.get("skills", [])
    committed = []
    modified = []
    untracked = []

    # Get git status
    result = subprocess.run(
        ["git", "status", "--porcelain", "skills/"],
        capture_output=True,
        text=True,
        cwd=root
    )

    status_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

    # Parse status
    modified_paths = set()
    untracked_paths = set()

    for line in status_lines:
        if not line:
            continue
        status = line[:2]
        path = line[3:].strip()

        if status.startswith("?"):
            untracked_paths.add(path)
        elif status.strip():
            modified_paths.add(path)

    # Check each skill
    for skill_path in skills:
        clean_path = skill_path.lstrip("./")

        # Check if any file in skill dir is modified/untracked
        is_modified = any(p.startswith(clean_path) for p in modified_paths)
        is_untracked = any(p.startswith(clean_path) for p in untracked_paths)

        if is_untracked:
            untracked.append(clean_path)
        elif is_modified:
            modified.append(clean_path)
        else:
            committed.append(clean_path)

    return committed, modified, untracked


def check_version_consistency(root: Path) -> Dict[str, str]:
    """
    Check version across all relevant files.

    Returns:
        dict mapping filename to version found
    """
    versions = {}

    # plugin.json
    plugin_path = root / ".claude-plugin" / "plugin.json"
    if plugin_path.exists():
        with open(plugin_path) as f:
            data = json.load(f)
            versions["plugin.json"] = data.get("version", "NOT_FOUND")

    # marketplace.json
    marketplace_path = root / ".claude-plugin" / "marketplace.json"
    if marketplace_path.exists():
        with open(marketplace_path) as f:
            data = json.load(f)
            versions["marketplace.json"] = data.get("metadata", {}).get("version", "NOT_FOUND")

    # CLAUDE.md (Navigator Version line)
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()
        match = re.search(r'\*\*Navigator Version\*\*:\s*(\d+\.\d+\.\d+)', content)
        if match:
            versions["CLAUDE.md"] = match.group(1)
        else:
            versions["CLAUDE.md"] = "NOT_FOUND"

    # README.md badge
    readme = root / "README.md"
    if readme.exists():
        content = readme.read_text()
        match = re.search(r'version-(\d+\.\d+\.\d+)-blue', content)
        if match:
            versions["README.md"] = match.group(1)
        else:
            versions["README.md"] = "NOT_FOUND"

    # .nav-config.json
    nav_config = root / ".agent" / ".nav-config.json"
    if nav_config.exists():
        with open(nav_config) as f:
            data = json.load(f)
            versions[".nav-config.json"] = data.get("version", "NOT_FOUND")

    return versions


def verify_tag_contents(root: Path, tag: str) -> Tuple[List[str], List[str]]:
    """
    Verify tag contains all expected skills.

    Returns:
        (found_in_tag, missing_from_tag)
    """
    plugin = load_plugin_json(root)
    skills = plugin.get("skills", [])

    found = []
    missing = []

    for skill_path in skills:
        clean_path = skill_path.lstrip("./")
        skill_md_path = f"{clean_path}/SKILL.md"

        # Check if file exists in tag
        result = subprocess.run(
            ["git", "ls-tree", tag, skill_md_path],
            capture_output=True,
            text=True,
            cwd=root
        )

        if result.stdout.strip():
            found.append(clean_path)
        else:
            missing.append(clean_path)

    return found, missing


def print_validation_report(
    existing: List[str],
    missing: List[str],
    committed: List[str],
    modified: List[str],
    untracked: List[str],
    versions: Dict[str, str]
) -> bool:
    """Print validation report and return True if passed."""

    print("━" * 50)
    print("NAVIGATOR RELEASE VALIDATION")
    print("━" * 50)
    print()

    # Skills existence check
    print("Skills Check:")
    all_skills = existing + missing
    for skill in sorted(all_skills):
        if skill in existing:
            status = "exists"
            if skill in committed:
                status += ", committed"
            elif skill in modified:
                status += ", MODIFIED"
            elif skill in untracked:
                status += ", UNTRACKED"
            print(f"  [{'x' if skill in existing else ' '}] {skill:<20} {'✓' if skill in committed else '⚠'} {status}")
        else:
            print(f"  [ ] {skill:<20} ✗ MISSING")
    print()

    # Version check
    print("Version Check:")
    version_values = list(versions.values())
    expected_version = version_values[0] if version_values else "UNKNOWN"
    all_match = all(v == expected_version for v in version_values if v != "NOT_FOUND")

    for filename, version in versions.items():
        match_indicator = "✓" if version == expected_version else "← MISMATCH"
        print(f"  {filename:<20} {version} {match_indicator if version != expected_version else '✓'}")
    print()

    # Git status summary
    print("Git Status:")
    print(f"  Uncommitted skills: {len(modified)} {'✓' if len(modified) == 0 else '⚠'}")
    print(f"  Untracked skills:   {len(untracked)} {'✓' if len(untracked) == 0 else '⚠'}")
    print()

    # Final result
    print("━" * 50)
    passed = len(missing) == 0 and len(modified) == 0 and len(untracked) == 0 and all_match

    if passed:
        print("VALIDATION: PASSED ✓")
    else:
        print("VALIDATION: FAILED ✗")
        print()
        if missing:
            print(f"  Missing skills: {', '.join(missing)}")
        if modified:
            print(f"  Modified skills: {', '.join(modified)}")
        if untracked:
            print(f"  Untracked skills: {', '.join(untracked)}")
        if not all_match:
            print(f"  Version mismatch detected")

    print("━" * 50)

    return passed


def main():
    parser = argparse.ArgumentParser(description="Validate Navigator plugin for release")
    parser.add_argument("--check-all", action="store_true", help="Run all validation checks")
    parser.add_argument("--check-version", type=str, help="Verify specific version")
    parser.add_argument("--verify-tag", type=str, help="Verify tag contains all skills")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    root = get_project_root()
    plugin = load_plugin_json(root)

    if not plugin:
        print("Error: plugin.json not found", file=sys.stderr)
        return 1

    if args.verify_tag:
        found, missing = verify_tag_contents(root, args.verify_tag)

        if args.json:
            print(json.dumps({"found": found, "missing": missing}))
        else:
            print(f"Tag {args.verify_tag} verification:")
            print(f"  Found: {len(found)} skills")
            print(f"  Missing: {len(missing)} skills")
            if missing:
                print(f"\nMissing from tag:")
                for skill in missing:
                    print(f"  - {skill}")
                return 1
            else:
                print("\n✓ All skills present in tag")

        return 0 if not missing else 1

    # Run all checks
    existing, missing = check_skills_exist(root, plugin)
    committed, modified, untracked = check_skills_committed(root, plugin)
    versions = check_version_consistency(root)

    if args.json:
        result = {
            "existing": existing,
            "missing": missing,
            "committed": committed,
            "modified": modified,
            "untracked": untracked,
            "versions": versions,
            "passed": len(missing) == 0 and len(modified) == 0 and len(untracked) == 0
        }
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    passed = print_validation_report(
        existing, missing, committed, modified, untracked, versions
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
