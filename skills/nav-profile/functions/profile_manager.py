#!/usr/bin/env python3
"""
Profile Manager - CRUD operations for user profile

Manages .agent/.user-profile.json for bilateral modeling in Navigator.
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path


def load_profile(profile_path: str) -> dict:
    """Load profile from file, return empty dict if not exists."""
    path = Path(profile_path)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_profile(profile_path: str, profile: dict) -> bool:
    """Save profile to file."""
    try:
        path = Path(profile_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(profile, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving profile: {e}", file=sys.stderr)
        return False


def create_default_profile() -> dict:
    """Create a new default profile."""
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "version": "1.0",
        "created": today,
        "last_updated": today,
        "preferences": {
            "communication": {
                "verbosity": "balanced",
                "confirmation_threshold": "high-stakes",
                "explanation_style": "examples"
            },
            "technical": {
                "preferred_frameworks": [],
                "code_style": "mixed",
                "testing_preference": "tdd"
            },
            "workflow": {
                "autonomous_commits": True,
                "auto_compact_threshold": 80,
                "marker_before_risky": True
            }
        },
        "corrections": [],
        "goals": []
    }


def update_preference(profile: dict, category: str, field: str, value) -> dict:
    """Update a specific preference in the profile."""
    if "preferences" not in profile:
        profile["preferences"] = {}
    if category not in profile["preferences"]:
        profile["preferences"][category] = {}

    old_value = profile["preferences"][category].get(field)
    profile["preferences"][category][field] = value
    profile["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    return {"old_value": old_value, "new_value": value}


def add_correction(profile: dict, correction: dict) -> dict:
    """Add a correction to the profile, maintaining max 20."""
    if "corrections" not in profile:
        profile["corrections"] = []

    correction["date"] = datetime.now().strftime("%Y-%m-%d")
    profile["corrections"].append(correction)

    # Keep only last 20 corrections
    if len(profile["corrections"]) > 20:
        profile["corrections"] = profile["corrections"][-20:]

    profile["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    return profile


def add_goal(profile: dict, goal: dict) -> dict:
    """Add or update a goal in the profile."""
    if "goals" not in profile:
        profile["goals"] = []

    today = datetime.now().strftime("%Y-%m-%d")

    # Check if goal already exists
    existing = next((g for g in profile["goals"] if g["name"] == goal["name"]), None)

    if existing:
        existing["last_mentioned"] = today
        existing["status"] = goal.get("status", existing["status"])
    else:
        goal["started"] = today
        goal["last_mentioned"] = today
        goal["status"] = goal.get("status", "in-progress")
        profile["goals"].append(goal)

    profile["last_updated"] = today
    return profile


def format_profile_display(profile: dict) -> str:
    """Format profile for display."""
    if not profile:
        return "No profile found. Use 'save my preferences' to create one."

    prefs = profile.get("preferences", {})
    comm = prefs.get("communication", {})
    tech = prefs.get("technical", {})
    work = prefs.get("workflow", {})
    corrections = profile.get("corrections", [])
    goals = profile.get("goals", [])

    frameworks = tech.get("preferred_frameworks", [])
    framework_str = ", ".join(frameworks) if frameworks else "none set"

    # Recent corrections (last 3)
    recent_corrections = corrections[-3:] if corrections else []
    corrections_str = "\n".join([
        f"  - {c.get('pattern', c.get('corrected_to', 'Unknown'))}"
        for c in recent_corrections
    ]) if recent_corrections else "  None yet"

    # Active goals
    active_goals = [g for g in goals if g.get("status") == "in-progress"]
    goals_str = "\n".join([
        f"  - {g['name']}: {g.get('context', 'No context')}"
        for g in active_goals
    ]) if active_goals else "  None active"

    return f"""Your Navigator Profile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Communication Preferences:
- Verbosity: {comm.get('verbosity', 'balanced')}
- Confirmation: {comm.get('confirmation_threshold', 'high-stakes')}
- Explanations: {comm.get('explanation_style', 'examples')}

Technical Preferences:
- Preferred frameworks: {framework_str}
- Code style: {tech.get('code_style', 'mixed')}
- Testing: {tech.get('testing_preference', 'tdd')}

Workflow Preferences:
- Autonomous commits: {work.get('autonomous_commits', True)}
- Auto-compact at: {work.get('auto_compact_threshold', 80)}% context
- Markers before risky changes: {work.get('marker_before_risky', True)}

Learned Corrections ({len(corrections)}):
{corrections_str}

Active Goals ({len(active_goals)}):
{goals_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Last updated: {profile.get('last_updated', 'Unknown')}"""


def main():
    parser = argparse.ArgumentParser(description='Manage Navigator user profile')
    parser.add_argument('--action', required=True,
                       choices=['show', 'create', 'update', 'add-correction', 'add-goal', 'delete'],
                       help='Action to perform')
    parser.add_argument('--profile-path', default='.agent/.user-profile.json',
                       help='Path to profile file')
    parser.add_argument('--category', help='Preference category (communication, technical, workflow)')
    parser.add_argument('--field', help='Preference field to update')
    parser.add_argument('--value', help='New value for preference')
    parser.add_argument('--correction-json', help='JSON string of correction to add')
    parser.add_argument('--goal-json', help='JSON string of goal to add')

    args = parser.parse_args()

    if args.action == 'show':
        profile = load_profile(args.profile_path)
        print(format_profile_display(profile))

    elif args.action == 'create':
        profile = create_default_profile()
        if save_profile(args.profile_path, profile):
            print(f"✅ Profile created at {args.profile_path}")
        else:
            sys.exit(1)

    elif args.action == 'update':
        if not all([args.category, args.field, args.value]):
            print("Error: --category, --field, and --value required for update", file=sys.stderr)
            sys.exit(1)

        profile = load_profile(args.profile_path)
        if not profile:
            profile = create_default_profile()

        # Parse value (handle booleans and numbers)
        value = args.value
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.isdigit():
            value = int(value)

        result = update_preference(profile, args.category, args.field, value)

        if save_profile(args.profile_path, profile):
            print(f"✅ Updated {args.category}.{args.field}")
            print(f"   From: {result['old_value']}")
            print(f"   To: {result['new_value']}")
        else:
            sys.exit(1)

    elif args.action == 'add-correction':
        if not args.correction_json:
            print("Error: --correction-json required", file=sys.stderr)
            sys.exit(1)

        profile = load_profile(args.profile_path)
        if not profile:
            profile = create_default_profile()

        correction = json.loads(args.correction_json)
        profile = add_correction(profile, correction)

        if save_profile(args.profile_path, profile):
            print(f"✅ Correction saved: {correction.get('pattern', 'Unknown')}")
        else:
            sys.exit(1)

    elif args.action == 'add-goal':
        if not args.goal_json:
            print("Error: --goal-json required", file=sys.stderr)
            sys.exit(1)

        profile = load_profile(args.profile_path)
        if not profile:
            profile = create_default_profile()

        goal = json.loads(args.goal_json)
        profile = add_goal(profile, goal)

        if save_profile(args.profile_path, profile):
            print(f"✅ Goal saved: {goal.get('name', 'Unknown')}")
        else:
            sys.exit(1)

    elif args.action == 'delete':
        path = Path(args.profile_path)
        if path.exists():
            path.unlink()
            print(f"✅ Profile deleted: {args.profile_path}")
        else:
            print(f"No profile found at {args.profile_path}")


if __name__ == '__main__':
    main()
