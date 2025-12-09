#!/usr/bin/env python3
"""
Extended project analysis for Navigator onboarding.

Detects project type, frameworks, database, and testing setup
to recommend appropriate skills and workflow.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional


def analyze_project(cwd: str = ".") -> Dict:
    """
    Comprehensive project analysis for onboarding recommendations.

    Args:
        cwd: Current working directory (default: ".")

    Returns:
        Dictionary with project analysis results
    """
    cwd_path = Path(cwd).resolve()

    result = {
        "project_name": cwd_path.name,
        "project_type": "unknown",
        "frontend_framework": None,
        "backend_framework": None,
        "database": None,
        "orm": None,
        "testing_framework": None,
        "has_navigator": False,
        "has_storybook": False,
        "has_figma_mcp": False,
        "detected_from": [],
        "confidence": 0.0,
    }

    # Check Navigator status
    result["has_navigator"] = (cwd_path / ".agent").exists()

    # Analyze different config files
    _analyze_package_json(cwd_path, result)
    _analyze_pyproject_toml(cwd_path, result)
    _analyze_go_mod(cwd_path, result)
    _analyze_cargo_toml(cwd_path, result)
    _analyze_composer_json(cwd_path, result)
    _analyze_gemfile(cwd_path, result)

    # Detect Storybook
    result["has_storybook"] = (cwd_path / ".storybook").exists()

    # Detect Figma MCP (check Claude settings)
    result["has_figma_mcp"] = _check_figma_mcp()

    # Determine project type
    result["project_type"] = _classify_project_type(result)

    # Calculate confidence
    result["confidence"] = _calculate_confidence(result)

    return result


def _analyze_package_json(cwd: Path, result: Dict) -> None:
    """Analyze package.json for Node.js/JavaScript projects."""
    package_json = cwd / "package.json"
    if not package_json.exists():
        return

    try:
        with open(package_json) as f:
            data = json.load(f)

        result["project_name"] = data.get("name", result["project_name"])
        result["detected_from"].append("package.json")

        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

        # Frontend frameworks
        if "next" in deps:
            result["frontend_framework"] = "Next.js"
        elif "react" in deps:
            result["frontend_framework"] = "React"
        elif "vue" in deps:
            result["frontend_framework"] = "Vue"
        elif "@angular/core" in deps:
            result["frontend_framework"] = "Angular"
        elif "svelte" in deps:
            result["frontend_framework"] = "Svelte"

        # Backend frameworks (Node.js)
        if "express" in deps:
            result["backend_framework"] = "Express"
        elif "fastify" in deps:
            result["backend_framework"] = "Fastify"
        elif "@nestjs/core" in deps:
            result["backend_framework"] = "NestJS"
        elif "koa" in deps:
            result["backend_framework"] = "Koa"
        elif "hono" in deps:
            result["backend_framework"] = "Hono"

        # Database/ORM
        if "prisma" in deps or "@prisma/client" in deps:
            result["orm"] = "Prisma"
        if "mongoose" in deps:
            result["database"] = "MongoDB"
            result["orm"] = "Mongoose"
        if "pg" in deps:
            result["database"] = "PostgreSQL"
        if "mysql2" in deps or "mysql" in deps:
            result["database"] = "MySQL"
        if "drizzle-orm" in deps:
            result["orm"] = "Drizzle"
        if "typeorm" in deps:
            result["orm"] = "TypeORM"
        if "sequelize" in deps:
            result["orm"] = "Sequelize"

        # Testing
        if "jest" in deps:
            result["testing_framework"] = "Jest"
            if "@testing-library/react" in deps:
                result["testing_framework"] = "Jest + React Testing Library"
        elif "vitest" in deps:
            result["testing_framework"] = "Vitest"
        elif "mocha" in deps:
            result["testing_framework"] = "Mocha"
        elif "playwright" in deps:
            result["testing_framework"] = "Playwright"
        elif "cypress" in deps:
            result["testing_framework"] = "Cypress"

        # Storybook
        if "@storybook/react" in deps or "@storybook/vue" in deps:
            result["has_storybook"] = True

    except (json.JSONDecodeError, IOError):
        pass


def _analyze_pyproject_toml(cwd: Path, result: Dict) -> None:
    """Analyze pyproject.toml for Python projects."""
    pyproject = cwd / "pyproject.toml"
    if not pyproject.exists():
        return

    try:
        content = pyproject.read_text().lower()
        result["detected_from"].append("pyproject.toml")

        # Extract name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if name_match and not result["project_name"]:
            result["project_name"] = name_match.group(1)

        # Backend frameworks
        if "fastapi" in content:
            result["backend_framework"] = "FastAPI"
        elif "django" in content:
            result["backend_framework"] = "Django"
        elif "flask" in content:
            result["backend_framework"] = "Flask"
        elif "starlette" in content:
            result["backend_framework"] = "Starlette"

        # ORM/Database
        if "sqlalchemy" in content:
            result["orm"] = "SQLAlchemy"
        if "sqlmodel" in content:
            result["orm"] = "SQLModel"
        if "tortoise-orm" in content:
            result["orm"] = "Tortoise ORM"
        if "psycopg" in content or "asyncpg" in content:
            result["database"] = "PostgreSQL"
        if "pymysql" in content:
            result["database"] = "MySQL"
        if "pymongo" in content:
            result["database"] = "MongoDB"

        # Testing
        if "pytest" in content:
            result["testing_framework"] = "Pytest"

    except IOError:
        pass


def _analyze_go_mod(cwd: Path, result: Dict) -> None:
    """Analyze go.mod for Go projects."""
    go_mod = cwd / "go.mod"
    if not go_mod.exists():
        return

    try:
        content = go_mod.read_text()
        result["detected_from"].append("go.mod")

        # Extract module name
        module_match = re.search(r'module\s+([^\s]+)', content)
        if module_match:
            result["project_name"] = module_match.group(1).split("/")[-1]

        # Backend frameworks
        if "gin-gonic/gin" in content:
            result["backend_framework"] = "Gin"
        elif "gofiber/fiber" in content:
            result["backend_framework"] = "Fiber"
        elif "labstack/echo" in content:
            result["backend_framework"] = "Echo"
        elif "go-chi/chi" in content:
            result["backend_framework"] = "Chi"

        # ORM/Database
        if "gorm.io/gorm" in content:
            result["orm"] = "GORM"
        if "sqlc" in content:
            result["orm"] = "sqlc"
        if "lib/pq" in content or "jackc/pgx" in content:
            result["database"] = "PostgreSQL"
        if "go-sql-driver/mysql" in content:
            result["database"] = "MySQL"

    except IOError:
        pass


def _analyze_cargo_toml(cwd: Path, result: Dict) -> None:
    """Analyze Cargo.toml for Rust projects."""
    cargo_toml = cwd / "Cargo.toml"
    if not cargo_toml.exists():
        return

    try:
        content = cargo_toml.read_text()
        result["detected_from"].append("Cargo.toml")

        # Extract name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if name_match:
            result["project_name"] = name_match.group(1)

        # Backend frameworks
        if "actix-web" in content:
            result["backend_framework"] = "Actix Web"
        elif "rocket" in content:
            result["backend_framework"] = "Rocket"
        elif "axum" in content:
            result["backend_framework"] = "Axum"
        elif "warp" in content:
            result["backend_framework"] = "Warp"

        # ORM/Database
        if "diesel" in content:
            result["orm"] = "Diesel"
        elif "sqlx" in content:
            result["orm"] = "SQLx"
        elif "sea-orm" in content:
            result["orm"] = "SeaORM"

    except IOError:
        pass


def _analyze_composer_json(cwd: Path, result: Dict) -> None:
    """Analyze composer.json for PHP projects."""
    composer_json = cwd / "composer.json"
    if not composer_json.exists():
        return

    try:
        with open(composer_json) as f:
            data = json.load(f)

        result["detected_from"].append("composer.json")
        name = data.get("name", "")
        if name:
            result["project_name"] = name.split("/")[-1]

        deps = {**data.get("require", {}), **data.get("require-dev", {})}
        deps_str = " ".join(deps.keys()).lower()

        if "laravel" in deps_str:
            result["backend_framework"] = "Laravel"
        elif "symfony" in deps_str:
            result["backend_framework"] = "Symfony"

        if "doctrine" in deps_str:
            result["orm"] = "Doctrine"
        if "eloquent" in deps_str:
            result["orm"] = "Eloquent"

        if "phpunit" in deps_str:
            result["testing_framework"] = "PHPUnit"

    except (json.JSONDecodeError, IOError):
        pass


def _analyze_gemfile(cwd: Path, result: Dict) -> None:
    """Analyze Gemfile for Ruby projects."""
    gemfile = cwd / "Gemfile"
    if not gemfile.exists():
        return

    try:
        content = gemfile.read_text().lower()
        result["detected_from"].append("Gemfile")

        if "rails" in content:
            result["backend_framework"] = "Ruby on Rails"
        elif "sinatra" in content:
            result["backend_framework"] = "Sinatra"

        if "activerecord" in content or "rails" in content:
            result["orm"] = "ActiveRecord"

        if "rspec" in content:
            result["testing_framework"] = "RSpec"
        elif "minitest" in content:
            result["testing_framework"] = "Minitest"

    except IOError:
        pass


def _check_figma_mcp() -> bool:
    """Check if Figma MCP is configured in Claude settings."""
    # Check common Claude config locations
    config_paths = [
        Path.home() / ".claude" / "settings.json",
        Path.home() / ".config" / "claude" / "settings.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    mcp_servers = config.get("mcpServers", {})
                    return "figma" in str(mcp_servers).lower()
            except (json.JSONDecodeError, IOError):
                pass

    return False


def _classify_project_type(result: Dict) -> str:
    """Classify project as frontend, backend, fullstack, or unknown."""
    has_frontend = result["frontend_framework"] is not None
    has_backend = result["backend_framework"] is not None

    if has_frontend and has_backend:
        return "fullstack"
    elif has_frontend:
        return "frontend"
    elif has_backend:
        return "backend"
    elif result["detected_from"]:
        # Has config files but couldn't determine type
        return "library"
    else:
        return "unknown"


def _calculate_confidence(result: Dict) -> float:
    """Calculate confidence score based on detection completeness."""
    score = 0.0

    # Base score for having any detection
    if result["detected_from"]:
        score += 0.3

    # Framework detection
    if result["frontend_framework"]:
        score += 0.2
    if result["backend_framework"]:
        score += 0.2

    # Additional context
    if result["database"] or result["orm"]:
        score += 0.15
    if result["testing_framework"]:
        score += 0.1
    if result["has_navigator"]:
        score += 0.05

    return min(score, 1.0)


def format_tech_stack(result: Dict) -> str:
    """Format detected technologies as readable string."""
    parts = []

    if result["frontend_framework"]:
        parts.append(result["frontend_framework"])
    if result["backend_framework"]:
        parts.append(result["backend_framework"])
    if result["orm"]:
        parts.append(result["orm"])
    elif result["database"]:
        parts.append(result["database"])
    if result["testing_framework"]:
        parts.append(result["testing_framework"])

    return ", ".join(parts) if parts else "Unknown"


if __name__ == "__main__":
    import sys

    cwd = sys.argv[1] if len(sys.argv) > 1 else "."
    result = analyze_project(cwd)
    result["tech_stack"] = format_tech_stack(result)
    print(json.dumps(result, indent=2))
