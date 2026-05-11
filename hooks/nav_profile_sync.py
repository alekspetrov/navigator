#!/usr/bin/env python3
"""
Navigator user-profile → corrections-memory sync hook (Opp 3 / v6.11.0).

Fires on `PostToolUse` after `Write` or `Edit` calls. When the touched
file is `.agent/.user-profile.json`, this hook diffs the corrections
array against a tracked last_synced_count and runs
`correction_to_memory.py --action sync --last-synced N` only when the
array grew. Replaces the soft "monitor ALL conversations for corrections"
rule that depended on the model remembering to invoke nav-profile.

Idempotency is provided by `.agent/.nav-profile-sync-state.json`, which
records the corrections count after the last successful sync.

Spec: https://docs.claude.com/en/docs/claude-code/hooks#posttooluse
- stdin JSON: tool_name, tool_input (with file_path), cwd
- Exit 0 always — never block tool execution.
- stdout is empty JSON `{}` — pure side effect.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _safe_read(path: Path, max_bytes: int = 500_000) -> str | None:
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception as e:
        print(f"nav_profile_sync: skip {path}: {e}", file=sys.stderr)
        return None


def _safe_json(path: Path) -> dict | None:
    raw = _safe_read(path)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"nav_profile_sync: invalid JSON in {path}: {e}", file=sys.stderr)
        return None


def _project_root(stdin_data: dict) -> Path:
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def _hook_enabled(root: Path) -> bool:
    cfg = _safe_json(root / ".agent" / ".nav-config.json") or {}
    hook_cfg = cfg.get("profile_sync_hook") or {}
    return hook_cfg.get("enabled", True)


def _resolve_plugin_dir() -> Path | None:
    env = os.environ.get("CLAUDE_PLUGIN_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    candidates = [
        Path.home() / ".claude" / "plugins" / "cache" / "jitd-marketplace" / "navigator",
        Path.home() / ".claude" / "plugins" / "marketplaces" / "jitd-marketplace",
    ]
    for c in candidates:
        if (c / "skills" / "nav-graph").is_dir():
            return c
    here = Path(__file__).resolve().parent.parent
    if (here / "skills" / "nav-graph").is_dir():
        return here
    return None


def _is_profile_write(stdin_data: dict, root: Path) -> Path | None:
    """Return the profile path if this tool call touched it."""
    tool_input = stdin_data.get("tool_input") or {}
    candidate = tool_input.get("file_path")
    if not isinstance(candidate, str) or not candidate:
        return None
    p = Path(candidate)
    if not p.is_absolute():
        p = root / candidate
    # Match either the conventional .agent/.user-profile.json or any path
    # whose basename is .user-profile.json (defensive)
    if p.name == ".user-profile.json" and p.is_file():
        return p
    return None


def _load_state(root: Path) -> dict:
    state_path = root / ".agent" / ".nav-profile-sync-state.json"
    return _safe_json(state_path) or {}


def _save_state(root: Path, state: dict) -> None:
    state_path = root / ".agent" / ".nav-profile-sync-state.json"
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as e:
        print(f"nav_profile_sync: state save failed: {e}", file=sys.stderr)


def main() -> int:
    raw_stdin = sys.stdin.read() if not sys.stdin.isatty() else ""
    stdin_data: dict[str, Any] = {}
    if raw_stdin.strip():
        try:
            stdin_data = json.loads(raw_stdin)
        except json.JSONDecodeError:
            stdin_data = {}

    root = _project_root(stdin_data)
    if not (root / ".agent").is_dir():
        print(json.dumps({}))
        return 0

    if not _hook_enabled(root):
        print(json.dumps({}))
        return 0

    profile_path = _is_profile_write(stdin_data, root)
    if profile_path is None:
        print(json.dumps({}))
        return 0

    profile = _safe_json(profile_path)
    if profile is None:
        print(json.dumps({}))
        return 0

    corrections = profile.get("corrections") or []
    current_count = len(corrections) if isinstance(corrections, list) else 0

    state = _load_state(root)
    last_synced = int(state.get("last_synced_count") or 0)

    if current_count <= last_synced:
        # No new corrections — nothing to sync. Pure no-op for non-correction
        # profile edits (preferences, goals, etc.).
        print(json.dumps({}))
        return 0

    graph_path = root / ".agent" / "knowledge" / "graph.json"
    if not graph_path.is_file():
        # No graph initialized — skip silently
        print(json.dumps({}))
        return 0

    plugin_dir = _resolve_plugin_dir()
    if plugin_dir is None:
        print("nav_profile_sync: plugin dir not found", file=sys.stderr)
        print(json.dumps({}))
        return 0

    syncer = plugin_dir / "skills" / "nav-graph" / "functions" / "correction_to_memory.py"
    if not syncer.is_file():
        print(f"nav_profile_sync: {syncer} missing", file=sys.stderr)
        print(json.dumps({}))
        return 0

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(syncer),
                "--action",
                "sync",
                "--profile-path",
                str(profile_path),
                "--graph-path",
                str(graph_path),
                "--last-synced",
                str(last_synced),
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0:
            print(
                f"nav_profile_sync: sync failed (rc={result.returncode}): "
                f"{(result.stderr or result.stdout).strip()[:300]}",
                file=sys.stderr,
            )
        else:
            print(
                f"nav_profile_sync: synced {current_count - last_synced} new correction(s)",
                file=sys.stderr,
            )
            # Only advance the counter on success — failed syncs retry next time
            state["last_synced_count"] = current_count
            _save_state(root, state)
    except subprocess.TimeoutExpired:
        print("nav_profile_sync: subprocess timeout", file=sys.stderr)
    except Exception as e:
        print(f"nav_profile_sync: subprocess failure: {e}", file=sys.stderr)

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
