#!/usr/bin/env python3
"""
Navigator SessionStart hook — zero-Read context injection.

Invoked by Claude Code on session start (and on --resume). Emits a JSON
payload whose `additionalContext` is injected as a system reminder into
the model's context window, eliminating the ~6 Read tool calls that
nav-start would otherwise make.

Parity goal: produce the SAME content nav-start currently renders
(navigator + active marker + config + graph stats + profile + auto-update).
Only the *delivery mechanism* changes.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#sessionstart
- stdout MUST be valid JSON
- additionalContext capped at 10_000 chars by Claude Code
- stderr is logged but does not block; non-zero exit is tolerated

Sentinel: every successful injection emits `<!-- nav-session-start-injected:v1 -->`
so nav-start can detect prior injection and skip its own reads.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SENTINEL = "<!-- nav-session-start-injected:v1 -->"
CHAR_BUDGET = 9500  # leave headroom under Claude Code's 10k limit
TRUNCATION_FOOTER = (
    "\n\n[truncated: ask nav-start for full detail]"
)


def _safe_read(path: Path, max_bytes: int = 50_000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception as e:
        print(f"nav_session_start: skip {path}: {e}", file=sys.stderr)
        return None


def _safe_json(path: Path) -> dict | None:
    raw = _safe_read(path)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"nav_session_start: invalid JSON in {path}: {e}", file=sys.stderr)
        return None


def _project_root(stdin_data: dict) -> Path:
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_ROOT") or os.getcwd()
    return Path(cwd)


def _section_navigator(root: Path) -> str | None:
    nav = _safe_read(root / ".agent" / "DEVELOPMENT-README.md", max_bytes=8_000)
    if not nav:
        return None
    return f"## Navigator Index (.agent/DEVELOPMENT-README.md)\n\n{nav}"


def _section_active_marker(root: Path) -> str | None:
    active = root / ".agent" / ".context-markers" / ".active"
    name = _safe_read(active, max_bytes=200)
    if not name:
        return None
    name = name.strip()
    if not name:
        return None
    marker_file = root / ".agent" / ".context-markers" / name
    body = _safe_read(marker_file, max_bytes=6_000)
    if not body:
        return f"## Active Marker\n\n`{name}` referenced but file missing."
    return (
        f"## Active Marker: `{name}`\n\n"
        f"User was working on this before compact. Offer to resume.\n\n"
        f"{body}"
    )


def _section_config(root: Path) -> str | None:
    cfg = _safe_json(root / ".agent" / ".nav-config.json")
    if not cfg:
        return None
    summary = {
        "version": cfg.get("version"),
        "project_management": cfg.get("project_management"),
        "task_prefix": cfg.get("task_prefix"),
        "team_chat": cfg.get("team_chat"),
        "loop_mode": (cfg.get("loop_mode") or {}).get("enabled"),
        "task_mode": (cfg.get("task_mode") or {}).get("enabled"),
        "knowledge_graph": (cfg.get("knowledge_graph") or {}).get("enabled"),
        "tom_features": cfg.get("tom_features"),
        "auto_update": (cfg.get("auto_update") or {}).get("enabled"),
    }
    return (
        "## Navigator Config (.agent/.nav-config.json)\n\n"
        f"```json\n{json.dumps(summary, indent=2)}\n```"
    )


def _section_user_profile(root: Path) -> str | None:
    profile = _safe_json(root / ".agent" / ".user-profile.json")
    if not profile:
        return None
    prefs = profile.get("preferences", {})
    corrections = profile.get("corrections", [])
    goals = profile.get("goals", [])
    body = {
        "preferences": prefs,
        "recent_corrections": corrections[-5:] if corrections else [],
        "goals": goals[-5:] if goals else [],
    }
    return (
        "## User Profile (Theory of Mind)\n\n"
        "Apply these preferences for this session.\n\n"
        f"```json\n{json.dumps(body, indent=2, default=str)}\n```"
    )


def _section_graph_stats(root: Path, plugin_dir: Path | None) -> str | None:
    graph_path = root / ".agent" / "knowledge" / "graph.json"
    if not graph_path.is_file():
        return None
    if plugin_dir is None:
        return f"## Knowledge Graph\n\nGraph present at {graph_path} (stats unavailable: plugin dir unknown)."
    manager = plugin_dir / "skills" / "nav-graph" / "functions" / "graph_manager.py"
    if not manager.is_file():
        return f"## Knowledge Graph\n\nGraph present (stats helper not found)."
    try:
        out = subprocess.run(
            [
                sys.executable,
                str(manager),
                "--action",
                "stats",
                "--graph-path",
                str(graph_path),
            ],
            capture_output=True,
            text=True,
            timeout=4,
        )
        text = (out.stdout or "").strip()
        if not text:
            return None
        return f"## Knowledge Graph Stats\n\n```\n{text[:1500]}\n```"
    except Exception as e:
        print(f"nav_session_start: graph stats failed: {e}", file=sys.stderr)
        return None


def _section_auto_update(root: Path, plugin_dir: Path | None) -> str | None:
    """Read-only version-drift notice for session start.

    Historically this invoked auto_updater with no args, which triggered a
    *mutating* `claude plugin update` (a 30s marketplace refresh + a 60s
    update) from inside the SessionStart hook's 10s budget — the update could
    never finish and the blocking hook risked timing out. We now run the
    updater in read-only `--check-drift` mode: it only compares the installed
    plugin version against the project config and reports drift. Performing the
    actual update is left to nav-upgrade, which is off the session-start path.
    """
    if plugin_dir is None:
        return None
    updater = plugin_dir / "skills" / "nav-start" / "functions" / "auto_updater.py"
    if not updater.is_file():
        return None
    config_path = root / ".agent" / ".nav-config.json"
    try:
        out = subprocess.run(
            [
                sys.executable,
                str(updater),
                "--check-drift",
                "--config-path",
                str(config_path),
            ],
            capture_output=True,
            text=True,
            timeout=4,
        )
        raw = (out.stdout or "").strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not data.get("has_drift"):
            return None
        message = data.get("message") or "Navigator version drift detected."
        return f"## Auto-Update\n\n⚠️  {message}"
    except Exception as e:
        print(f"nav_session_start: drift check failed: {e}", file=sys.stderr)
        return None


def _section_open_tasks(root: Path) -> str | None:
    tasks_dir = root / ".agent" / "tasks"
    if not tasks_dir.is_dir():
        return None
    entries: list[str] = []
    try:
        for p in sorted(tasks_dir.glob("*.md")):
            if p.name.upper().startswith("README"):
                continue
            head = _safe_read(p, max_bytes=600) or ""
            title = next(
                (
                    line.lstrip("# ").strip()
                    for line in head.splitlines()
                    if line.startswith("#")
                ),
                p.stem,
            )
            status = "open"
            for line in head.splitlines():
                low = line.lower()
                if "status" in low and ":" in low:
                    status = line.split(":", 1)[1].strip().strip("*` ")
                    break
            entries.append(f"- `{p.name}` — {title} [{status}]")
            if len(entries) >= 20:
                entries.append("- … (more in .agent/tasks/)")
                break
    except Exception as e:
        print(f"nav_session_start: task scan failed: {e}", file=sys.stderr)
        return None
    if not entries:
        return None
    return "## Open Tasks\n\n" + "\n".join(entries)


def _resolve_plugin_dir() -> Path | None:
    env = os.environ.get("CLAUDE_PLUGIN_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    candidates = [
        Path.home() / ".claude" / "plugins" / "cache" / "navigator-marketplace" / "navigator",
        Path.home() / ".claude" / "plugins" / "marketplaces" / "navigator-marketplace",
    ]
    for c in candidates:
        if (c / "skills" / "nav-start").is_dir():
            return c
    here = Path(__file__).resolve().parent.parent
    if (here / "skills" / "nav-start").is_dir():
        return here
    return None


def _read_hook_config(root: Path) -> dict:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    hook_cfg = cfg.get("session_start_hook") or {}
    return {
        "enabled": hook_cfg.get("enabled", True),
        "include_sections": hook_cfg.get(
            "include_sections",
            ["navigator", "marker", "config", "graph", "profile", "tasks", "auto_update"],
        ),
        "char_budget": int(hook_cfg.get("char_budget", CHAR_BUDGET)),
    }


def _build_payload(stdin_data: dict) -> str | None:
    root = _project_root(stdin_data)
    if not (root / ".agent").is_dir():
        return None  # not a Navigator project — emit nothing

    cfg = _read_hook_config(root)
    if not cfg["enabled"]:
        return None

    plugin_dir = _resolve_plugin_dir()
    source = stdin_data.get("source") or "startup"
    sections_enabled = set(cfg["include_sections"])

    header_lines = [
        SENTINEL,
        "# Navigator Session Start",
        f"_source: {source}_",
        "",
        (
            "This block was injected by the SessionStart hook — Navigator content "
            "is already in your context. Do NOT re-Read these files. Render the "
            "session summary directly from this data."
        ),
        "",
    ]
    if source == "resume":
        header_lines.insert(2, "**RESUMED FROM PREVIOUS SESSION** — prioritize active marker.")

    sections: list[str] = []

    def add(name: str, builder):
        if name not in sections_enabled:
            return
        try:
            out = builder()
        except Exception as e:
            print(f"nav_session_start: section '{name}' failed: {e}", file=sys.stderr)
            return
        if out:
            sections.append(out)

    # Order: small high-signal sections first, navigator (biggest) last so
    # truncation eats its tail rather than dropping config/profile/graph.
    # On resume, marker also hoisted to top.
    if source == "resume":
        add("marker", lambda: _section_active_marker(root))
    add("config", lambda: _section_config(root))
    add("auto_update", lambda: _section_auto_update(root, plugin_dir))
    add("graph", lambda: _section_graph_stats(root, plugin_dir))
    add("profile", lambda: _section_user_profile(root))
    add("tasks", lambda: _section_open_tasks(root))
    if source != "resume":
        add("marker", lambda: _section_active_marker(root))
    add("navigator", lambda: _section_navigator(root))

    body = "\n".join(header_lines) + "\n\n" + "\n\n---\n\n".join(sections)

    budget = cfg["char_budget"]
    if len(body) > budget:
        body = body[: budget - len(TRUNCATION_FOOTER)] + TRUNCATION_FOOTER
    return body


def main() -> int:
    raw_stdin = sys.stdin.read() if not sys.stdin.isatty() else ""
    stdin_data: dict[str, Any] = {}
    if raw_stdin.strip():
        try:
            stdin_data = json.loads(raw_stdin)
        except json.JSONDecodeError:
            stdin_data = {}

    payload = _build_payload(stdin_data)
    if not payload:
        # Emit empty JSON object — Claude Code treats it as "no additional context"
        print(json.dumps({}))
        return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": payload,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
