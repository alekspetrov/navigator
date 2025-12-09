#!/usr/bin/env python3
"""
Progress tracking for Navigator onboarding.

Manages .agent/onboarding/PROGRESS.md to track learning completion.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def init_progress(
    project_dir: str,
    flow_type: str,
    project_type: str,
    project_name: str,
    skills: Dict
) -> str:
    """
    Initialize progress tracking file.

    Args:
        project_dir: Project directory path
        flow_type: "quick_start" or "full_education"
        project_type: Detected project type
        project_name: Project name
        skills: Skill recommendations from skill_recommender

    Returns:
        Path to created progress file
    """
    onboarding_dir = Path(project_dir) / ".agent" / "onboarding"
    onboarding_dir.mkdir(parents=True, exist_ok=True)

    progress_file = onboarding_dir / "PROGRESS.md"

    # Determine curriculum based on flow
    if flow_type == "quick_start":
        essential = ["nav-start", "nav-marker", "nav-task"]
        development = skills.get("recommended_skills", [])[:1]  # Just first dev skill
    else:  # full_education
        essential = skills.get("essential_skills", [])
        development = skills.get("recommended_skills", [])

    # Build progress table
    essential_rows = []
    for i, skill in enumerate(essential, 1):
        essential_rows.append(f"| {i} | {skill} | pending | - | - |")

    dev_rows = []
    for i, skill in enumerate(development, len(essential) + 1):
        dev_rows.append(f"| {i} | {skill} | pending | - | - |")

    total_skills = len(essential) + len(development)

    # Format flow name
    flow_name = "Quick Start" if flow_type == "quick_start" else "Full Education"

    content = f"""# Navigator Onboarding Progress

**Started**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Flow**: {flow_name}
**Project**: {project_name} ({project_type})

---

## Essential Skills

| # | Skill | Status | Completed | Notes |
|---|-------|--------|-----------|-------|
{chr(10).join(essential_rows)}

## Development Skills

| # | Skill | Status | Completed | Notes |
|---|-------|--------|-----------|-------|
{chr(10).join(dev_rows) if dev_rows else "| - | (none for this flow) | - | - | - |"}

---

**Progress**: 0/{total_skills} (0%)
**Next Task**: {essential[0] if essential else "complete"}

*Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""

    progress_file.write_text(content)

    # Also save structured data for programmatic access
    data_file = onboarding_dir / ".progress-data.json"
    data = {
        "started": datetime.now().isoformat(),
        "flow_type": flow_type,
        "project_type": project_type,
        "project_name": project_name,
        "essential_skills": essential,
        "development_skills": development,
        "progress": {skill: {"status": "pending", "completed": None, "notes": ""} for skill in essential + development},
        "total": total_skills,
        "completed": 0,
    }
    data_file.write_text(json.dumps(data, indent=2))

    return str(progress_file)


def update_progress(
    project_dir: str,
    skill_name: str,
    status: str,
    notes: str = ""
) -> Dict:
    """
    Update progress for a specific skill.

    Args:
        project_dir: Project directory path
        skill_name: Name of skill to update
        status: "pending", "in_progress", or "completed"
        notes: Optional notes about completion

    Returns:
        Updated progress summary
    """
    onboarding_dir = Path(project_dir) / ".agent" / "onboarding"
    data_file = onboarding_dir / ".progress-data.json"

    if not data_file.exists():
        return {"error": "Progress not initialized. Run init first."}

    data = json.loads(data_file.read_text())

    if skill_name not in data["progress"]:
        return {"error": f"Unknown skill: {skill_name}"}

    # Update skill status
    data["progress"][skill_name]["status"] = status
    if status == "completed":
        data["progress"][skill_name]["completed"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        data["completed"] = sum(1 for s in data["progress"].values() if s["status"] == "completed")
    if notes:
        data["progress"][skill_name]["notes"] = notes

    # Save updated data
    data_file.write_text(json.dumps(data, indent=2))

    # Regenerate markdown
    _regenerate_markdown(onboarding_dir, data)

    return {
        "skill": skill_name,
        "status": status,
        "completed": data["completed"],
        "total": data["total"],
        "percentage": round(data["completed"] / data["total"] * 100) if data["total"] > 0 else 0,
        "next_task": get_next_task(project_dir),
    }


def get_progress(project_dir: str) -> Dict:
    """
    Get current progress summary.

    Args:
        project_dir: Project directory path

    Returns:
        Progress summary dictionary
    """
    onboarding_dir = Path(project_dir) / ".agent" / "onboarding"
    data_file = onboarding_dir / ".progress-data.json"

    if not data_file.exists():
        return {"initialized": False}

    data = json.loads(data_file.read_text())

    return {
        "initialized": True,
        "flow_type": data["flow_type"],
        "project_type": data["project_type"],
        "completed": data["completed"],
        "total": data["total"],
        "percentage": round(data["completed"] / data["total"] * 100) if data["total"] > 0 else 0,
        "skills": data["progress"],
        "next_task": get_next_task(project_dir),
    }


def get_next_task(project_dir: str) -> Optional[str]:
    """
    Determine the next task to complete.

    Args:
        project_dir: Project directory path

    Returns:
        Next skill name or None if complete
    """
    onboarding_dir = Path(project_dir) / ".agent" / "onboarding"
    data_file = onboarding_dir / ".progress-data.json"

    if not data_file.exists():
        return None

    data = json.loads(data_file.read_text())

    # Find first non-completed skill in order
    all_skills = data["essential_skills"] + data["development_skills"]
    for skill in all_skills:
        if data["progress"][skill]["status"] != "completed":
            return skill

    return None


def _regenerate_markdown(onboarding_dir: Path, data: Dict) -> None:
    """Regenerate PROGRESS.md from data."""
    progress_file = onboarding_dir / "PROGRESS.md"

    # Build tables
    essential_rows = []
    for i, skill in enumerate(data["essential_skills"], 1):
        p = data["progress"][skill]
        status_icon = {"pending": "pending", "in_progress": "in_progress", "completed": "completed"}[p["status"]]
        completed = p["completed"] or "-"
        notes = p["notes"] or "-"
        essential_rows.append(f"| {i} | {skill} | {status_icon} | {completed} | {notes} |")

    dev_rows = []
    for i, skill in enumerate(data["development_skills"], len(data["essential_skills"]) + 1):
        p = data["progress"][skill]
        status_icon = {"pending": "pending", "in_progress": "in_progress", "completed": "completed"}[p["status"]]
        completed = p["completed"] or "-"
        notes = p["notes"] or "-"
        dev_rows.append(f"| {i} | {skill} | {status_icon} | {completed} | {notes} |")

    percentage = round(data["completed"] / data["total"] * 100) if data["total"] > 0 else 0
    next_task = get_next_task(str(onboarding_dir.parent.parent)) or "complete"

    flow_name = "Quick Start" if data["flow_type"] == "quick_start" else "Full Education"

    content = f"""# Navigator Onboarding Progress

**Started**: {data["started"][:16].replace("T", " ")}
**Flow**: {flow_name}
**Project**: {data["project_name"]} ({data["project_type"]})

---

## Essential Skills

| # | Skill | Status | Completed | Notes |
|---|-------|--------|-----------|-------|
{chr(10).join(essential_rows)}

## Development Skills

| # | Skill | Status | Completed | Notes |
|---|-------|--------|-----------|-------|
{chr(10).join(dev_rows) if dev_rows else "| - | (none for this flow) | - | - | - |"}

---

**Progress**: {data["completed"]}/{data["total"]} ({percentage}%)
**Next Task**: {next_task}

*Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""

    progress_file.write_text(content)


def format_progress_bar(completed: int, total: int, width: int = 30) -> str:
    """Generate ASCII progress bar."""
    if total == 0:
        return "[" + " " * width + "]"

    filled = int(width * completed / total)
    empty = width - filled
    return "[" + "=" * filled + " " * empty + "]"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: progress_tracker.py <command> [args]")
        print("Commands: init, update, get, next")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        # init <project_dir> <flow_type> <project_type> <project_name> <skills_json>
        if len(sys.argv) < 7:
            print("Usage: progress_tracker.py init <project_dir> <flow_type> <project_type> <project_name> <skills_json>")
            sys.exit(1)
        result = init_progress(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5],
            json.loads(sys.argv[6])
        )
        print(result)

    elif command == "update":
        # update <project_dir> <skill_name> <status> [notes]
        if len(sys.argv) < 5:
            print("Usage: progress_tracker.py update <project_dir> <skill_name> <status> [notes]")
            sys.exit(1)
        notes = sys.argv[5] if len(sys.argv) > 5 else ""
        result = update_progress(sys.argv[2], sys.argv[3], sys.argv[4], notes)
        print(json.dumps(result, indent=2))

    elif command == "get":
        # get <project_dir>
        if len(sys.argv) < 3:
            print("Usage: progress_tracker.py get <project_dir>")
            sys.exit(1)
        result = get_progress(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif command == "next":
        # next <project_dir>
        if len(sys.argv) < 3:
            print("Usage: progress_tracker.py next <project_dir>")
            sys.exit(1)
        result = get_next_task(sys.argv[2])
        print(result or "complete")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
