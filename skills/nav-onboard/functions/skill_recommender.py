#!/usr/bin/env python3
"""
Skill recommendation engine for Navigator onboarding.

Maps project analysis to recommended skills and workflow order.
"""

import json
import sys
from typing import Dict, List


# Skill definitions with metadata
SKILLS = {
    # Essential skills (all projects)
    "nav-start": {
        "name": "nav-start",
        "description": "Start sessions efficiently with context loading",
        "category": "essential",
        "project_types": ["all"],
        "workflow_position": 1,
        "time_savings": "92%",
        "triggers": ["Start my Navigator session"],
    },
    "nav-marker": {
        "name": "nav-marker",
        "description": "Save progress checkpoints before breaks",
        "category": "essential",
        "project_types": ["all"],
        "workflow_position": 5,
        "time_savings": "97%",
        "triggers": ["Create checkpoint [name]", "Save my progress"],
    },
    "nav-task": {
        "name": "nav-task",
        "description": "Document what you build for future reference",
        "category": "essential",
        "project_types": ["all"],
        "workflow_position": 2,
        "time_savings": "80%",
        "triggers": ["Create task doc for [feature]", "Archive TASK-XX"],
    },
    "nav-sop": {
        "name": "nav-sop",
        "description": "Capture solutions for reuse",
        "category": "essential",
        "project_types": ["all"],
        "workflow_position": 4,
        "time_savings": "85%",
        "triggers": ["Create SOP for [issue]", "Document this solution"],
    },
    "nav-compact": {
        "name": "nav-compact",
        "description": "Clear context without losing work",
        "category": "essential",
        "project_types": ["all"],
        "workflow_position": 6,
        "time_savings": "90%",
        "triggers": ["Clear context and preserve markers"],
    },
    # Frontend skills
    "frontend-component": {
        "name": "frontend-component",
        "description": "Generate React/Vue components with tests",
        "category": "development",
        "project_types": ["frontend", "fullstack"],
        "workflow_position": 3,
        "time_savings": "70%",
        "triggers": ["Create component [name]", "Add component [name]"],
        "frameworks": ["React", "Next.js", "Vue", "Angular", "Svelte"],
    },
    "frontend-test": {
        "name": "frontend-test",
        "description": "Generate component tests with RTL",
        "category": "development",
        "project_types": ["frontend", "fullstack"],
        "workflow_position": 3.5,
        "time_savings": "65%",
        "triggers": ["Test this component", "Write component test"],
    },
    "visual-regression": {
        "name": "visual-regression",
        "description": "Setup Storybook + visual regression testing",
        "category": "optional",
        "project_types": ["frontend", "fullstack"],
        "workflow_position": 3.7,
        "time_savings": "96%",
        "triggers": ["Set up visual regression", "Add Chromatic tests"],
        "requires": ["has_storybook"],
    },
    "product-design": {
        "name": "product-design",
        "description": "Automate design handoff from Figma",
        "category": "optional",
        "project_types": ["frontend", "fullstack"],
        "workflow_position": 2.5,
        "time_savings": "95%",
        "triggers": ["Review this Figma design", "Design handoff"],
        "requires": ["has_figma_mcp"],
    },
    # Backend skills
    "backend-endpoint": {
        "name": "backend-endpoint",
        "description": "Create API endpoints with validation",
        "category": "development",
        "project_types": ["backend", "fullstack"],
        "workflow_position": 3,
        "time_savings": "70%",
        "triggers": ["Add endpoint [path]", "Create API [name]"],
    },
    "backend-test": {
        "name": "backend-test",
        "description": "Generate backend tests with mocks",
        "category": "development",
        "project_types": ["backend", "fullstack"],
        "workflow_position": 3.5,
        "time_savings": "65%",
        "triggers": ["Write test for [function]", "Add test [name]"],
    },
    "database-migration": {
        "name": "database-migration",
        "description": "Create migrations with rollback",
        "category": "development",
        "project_types": ["backend", "fullstack"],
        "workflow_position": 2.8,
        "time_savings": "60%",
        "triggers": ["Create migration [name]", "Add table [name]"],
        "requires": ["database"],
    },
    # Advanced skills
    "nav-skill-creator": {
        "name": "nav-skill-creator",
        "description": "Create custom skills for your workflow",
        "category": "advanced",
        "project_types": ["all"],
        "workflow_position": 7,
        "time_savings": "80%",
        "triggers": ["Create a skill for [workflow]"],
    },
}


def recommend_skills(project_analysis: Dict) -> Dict:
    """
    Generate skill recommendations based on project analysis.

    Args:
        project_analysis: Output from project_analyzer.py

    Returns:
        Dictionary with skill recommendations and workflow order
    """
    project_type = project_analysis.get("project_type", "unknown")

    essential = []
    recommended = []
    optional = []

    for skill_id, skill in SKILLS.items():
        # Check project type compatibility
        skill_types = skill["project_types"]
        if "all" not in skill_types and project_type not in skill_types:
            continue

        # Check requirements
        requirements = skill.get("requires", [])
        meets_requirements = True
        for req in requirements:
            if req == "has_storybook" and not project_analysis.get("has_storybook"):
                meets_requirements = False
            elif req == "has_figma_mcp" and not project_analysis.get("has_figma_mcp"):
                meets_requirements = False
            elif req == "database" and not project_analysis.get("database"):
                meets_requirements = False

        # Categorize skill
        category = skill["category"]
        skill_info = {
            "id": skill_id,
            "name": skill["name"],
            "description": skill["description"],
            "triggers": skill["triggers"],
            "time_savings": skill["time_savings"],
            "workflow_position": skill["workflow_position"],
        }

        if category == "essential":
            essential.append(skill_info)
        elif category == "development" and meets_requirements:
            recommended.append(skill_info)
        elif category == "optional" and meets_requirements:
            optional.append(skill_info)
        elif category == "advanced":
            optional.append(skill_info)

    # Sort by workflow position
    essential.sort(key=lambda x: x["workflow_position"])
    recommended.sort(key=lambda x: x["workflow_position"])
    optional.sort(key=lambda x: x["workflow_position"])

    # Generate workflow order
    all_skills = essential + recommended
    all_skills.sort(key=lambda x: x["workflow_position"])
    workflow_order = [s["id"] for s in all_skills]

    return {
        "project_type": project_type,
        "essential_skills": [s["id"] for s in essential],
        "recommended_skills": [s["id"] for s in recommended],
        "optional_skills": [s["id"] for s in optional],
        "workflow_order": workflow_order,
        "skill_details": {
            "essential": essential,
            "recommended": recommended,
            "optional": optional,
        },
        "curriculum": {
            "quick_start": _generate_quick_start_curriculum(essential, recommended),
            "full_education": _generate_full_curriculum(essential, recommended, optional),
        },
    }


def _generate_quick_start_curriculum(essential: List[Dict], recommended: List[Dict]) -> List[Dict]:
    """Generate Quick Start curriculum (4 skills, 15 min)."""
    curriculum = []

    # First 3 essential skills
    essential_subset = ["nav-start", "nav-marker", "nav-task"]
    for skill in essential:
        if skill["id"] in essential_subset:
            curriculum.append({
                "skill": skill["id"],
                "estimated_time": "3 min",
                "task_file": f"{len(curriculum) + 1:02d}-{skill['id']}.md",
            })

    # One dev skill if available
    if recommended:
        dev_skill = recommended[0]
        curriculum.append({
            "skill": dev_skill["id"],
            "estimated_time": "5 min",
            "task_file": f"{len(curriculum) + 1:02d}-{dev_skill['id']}.md",
        })

    return curriculum


def _generate_full_curriculum(
    essential: List[Dict], recommended: List[Dict], optional: List[Dict]
) -> List[Dict]:
    """Generate Full Education curriculum (~45 min)."""
    curriculum = []

    # Philosophy section
    curriculum.append({
        "section": "Philosophy",
        "skill": None,
        "estimated_time": "5 min",
        "description": "Read context efficiency principles",
        "file": ".agent/philosophy/CONTEXT-EFFICIENCY.md",
    })

    # All essential skills
    for i, skill in enumerate(essential):
        curriculum.append({
            "section": "Essential",
            "skill": skill["id"],
            "estimated_time": "3 min",
            "task_file": f"{i + 1:02d}-{skill['id']}.md",
        })

    # All recommended skills
    for i, skill in enumerate(recommended):
        curriculum.append({
            "section": "Development",
            "skill": skill["id"],
            "estimated_time": "5 min",
            "task_file": f"0{len(essential) + i + 1}-{skill['id']}.md",
        })

    # Summary
    curriculum.append({
        "section": "Summary",
        "skill": None,
        "estimated_time": "5 min",
        "description": "Generate personalized workflow guide",
    })

    return curriculum


def format_recommendations(recommendations: Dict) -> str:
    """Format recommendations for display."""
    lines = []
    lines.append(f"Project Type: {recommendations['project_type']}")
    lines.append("")
    lines.append("Essential Skills:")
    for skill in recommendations["skill_details"]["essential"]:
        lines.append(f"  - {skill['name']}: {skill['description']}")

    lines.append("")
    lines.append("Recommended Skills:")
    for skill in recommendations["skill_details"]["recommended"]:
        lines.append(f"  - {skill['name']}: {skill['description']}")

    if recommendations["skill_details"]["optional"]:
        lines.append("")
        lines.append("Optional Skills:")
        for skill in recommendations["skill_details"]["optional"]:
            lines.append(f"  - {skill['name']}: {skill['description']}")

    lines.append("")
    lines.append(f"Workflow Order: {' -> '.join(recommendations['workflow_order'])}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Read project analysis from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            project_analysis = json.load(f)
    else:
        project_analysis = json.load(sys.stdin)

    recommendations = recommend_skills(project_analysis)
    print(json.dumps(recommendations, indent=2))
