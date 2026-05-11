#!/usr/bin/env python3
"""
Project information detection for Navigator initialization.

Detects project name and tech stack from various config files.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional


def detect_project_info(cwd: str = ".") -> Dict[str, str]:
    """
    Detect project name and tech stack from config files.

    Args:
        cwd: Current working directory (default: ".")

    Returns:
        Dictionary with keys:
        - name: Project name
        - tech_stack: Comma-separated technologies
        - detected_from: Source file used for detection
    """
    cwd_path = Path(cwd).resolve()

    # Try detection methods in order
    detectors = [
        _detect_from_package_json,
        _detect_from_pyproject_toml,
        _detect_from_go_mod,
        _detect_from_cargo_toml,
        _detect_from_composer_json,
        _detect_from_gemfile,
    ]

    for detector in detectors:
        result = detector(cwd_path)
        if result:
            return result

    # Fallback: use directory name
    return {
        "name": cwd_path.name,
        "tech_stack": "Unknown",
        "detected_from": "directory_name",
    }


def _detect_from_package_json(cwd: Path) -> Optional[Dict[str, str]]:
    """Detect from package.json (Node.js/JavaScript)."""
    package_json = cwd / "package.json"
    if not package_json.exists():
        return None

    try:
        with open(package_json) as f:
            data = json.load(f)

        name = data.get("name", cwd.name)
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

        # Detect framework — first match wins, lets downstream branch deterministically
        framework = None
        stack_parts = []

        if "next" in deps:
            framework = "nextjs"
            stack_parts.append("Next.js")
        elif "react" in deps:
            framework = "react"
            stack_parts.append("React")
        elif "vue" in deps:
            framework = "vue"
            stack_parts.append("Vue")
        elif "angular" in deps:
            framework = "angular"
            stack_parts.append("Angular")
        elif "svelte" in deps:
            framework = "svelte"
            stack_parts.append("Svelte")
        elif "express" in deps:
            framework = "express"
            stack_parts.append("Express")
        elif "fastify" in deps:
            framework = "fastify"
            stack_parts.append("Fastify")

        if "typescript" in deps:
            stack_parts.append("TypeScript")

        if "tailwindcss" in deps or "@tailwindcss/postcss" in deps:
            stack_parts.append("Tailwind")

        if "prisma" in deps:
            stack_parts.append("Prisma")
        elif "mongoose" in deps:
            stack_parts.append("MongoDB")
        elif "pg" in deps or "postgres" in deps:
            stack_parts.append("PostgreSQL")

        tech_stack = ", ".join(stack_parts) if stack_parts else "Node.js"

        return {
            "name": name,
            "tech_stack": tech_stack,
            "framework": framework,
            "detected_from": "package.json",
        }
    except (json.JSONDecodeError, IOError):
        return None


def _detect_from_pyproject_toml(cwd: Path) -> Optional[Dict[str, str]]:
    """Detect from pyproject.toml (Python)."""
    pyproject = cwd / "pyproject.toml"
    if not pyproject.exists():
        return None

    try:
        content = pyproject.read_text()

        # Extract name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        name = name_match.group(1) if name_match else cwd.name

        # Detect framework/stack
        stack_parts = []

        if "fastapi" in content.lower():
            stack_parts.append("FastAPI")
        elif "django" in content.lower():
            stack_parts.append("Django")
        elif "flask" in content.lower():
            stack_parts.append("Flask")

        if "sqlalchemy" in content.lower():
            stack_parts.append("SQLAlchemy")
        if "pydantic" in content.lower():
            stack_parts.append("Pydantic")
        if "pytest" in content.lower():
            stack_parts.append("Pytest")

        tech_stack = ", ".join(stack_parts) if stack_parts else "Python"

        return {
            "name": name,
            "tech_stack": tech_stack,
            "detected_from": "pyproject.toml",
        }
    except IOError:
        return None


def _detect_from_go_mod(cwd: Path) -> Optional[Dict[str, str]]:
    """Detect from go.mod (Go)."""
    go_mod = cwd / "go.mod"
    if not go_mod.exists():
        return None

    try:
        content = go_mod.read_text()

        # Extract module name
        module_match = re.search(r'module\s+([^\s]+)', content)
        name = module_match.group(1).split("/")[-1] if module_match else cwd.name

        # Detect framework/stack
        stack_parts = ["Go"]

        if "gin-gonic/gin" in content:
            stack_parts.append("Gin")
        elif "gorilla/mux" in content:
            stack_parts.append("Gorilla Mux")
        elif "fiber" in content:
            stack_parts.append("Fiber")

        if "gorm" in content:
            stack_parts.append("GORM")

        tech_stack = ", ".join(stack_parts)

        return {
            "name": name,
            "tech_stack": tech_stack,
            "detected_from": "go.mod",
        }
    except IOError:
        return None


def _detect_from_cargo_toml(cwd: Path) -> Optional[Dict[str, str]]:
    """Detect from Cargo.toml (Rust)."""
    cargo_toml = cwd / "Cargo.toml"
    if not cargo_toml.exists():
        return None

    try:
        content = cargo_toml.read_text()

        # Extract name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        name = name_match.group(1) if name_match else cwd.name

        # Detect framework/stack
        stack_parts = ["Rust"]

        if "actix-web" in content:
            stack_parts.append("Actix Web")
        elif "rocket" in content:
            stack_parts.append("Rocket")
        elif "axum" in content:
            stack_parts.append("Axum")

        if "diesel" in content:
            stack_parts.append("Diesel")
        elif "sqlx" in content:
            stack_parts.append("SQLx")

        tech_stack = ", ".join(stack_parts)

        return {
            "name": name,
            "tech_stack": tech_stack,
            "detected_from": "Cargo.toml",
        }
    except IOError:
        return None


def _detect_from_composer_json(cwd: Path) -> Optional[Dict[str, str]]:
    """Detect from composer.json (PHP)."""
    composer_json = cwd / "composer.json"
    if not composer_json.exists():
        return None

    try:
        with open(composer_json) as f:
            data = json.load(f)

        name = data.get("name", cwd.name).split("/")[-1]
        deps = {**data.get("require", {}), **data.get("require-dev", {})}

        # Detect framework/stack
        stack_parts = []

        if any("laravel" in dep for dep in deps):
            stack_parts.append("Laravel")
        elif any("symfony" in dep for dep in deps):
            stack_parts.append("Symfony")

        tech_stack = ", ".join(stack_parts) if stack_parts else "PHP"

        return {
            "name": name,
            "tech_stack": tech_stack,
            "detected_from": "composer.json",
        }
    except (json.JSONDecodeError, IOError):
        return None


def _detect_from_gemfile(cwd: Path) -> Optional[Dict[str, str]]:
    """Detect from Gemfile (Ruby)."""
    gemfile = cwd / "Gemfile"
    if not gemfile.exists():
        return None

    try:
        content = gemfile.read_text()

        name = cwd.name

        # Detect framework/stack
        stack_parts = []

        if "rails" in content.lower():
            stack_parts.append("Ruby on Rails")
        elif "sinatra" in content.lower():
            stack_parts.append("Sinatra")
        else:
            stack_parts.append("Ruby")

        tech_stack = ", ".join(stack_parts)

        return {
            "name": name,
            "tech_stack": tech_stack,
            "detected_from": "Gemfile",
        }
    except IOError:
        return None


if __name__ == "__main__":
    # Test detection
    info = detect_project_info()
    print(json.dumps(info, indent=2))
