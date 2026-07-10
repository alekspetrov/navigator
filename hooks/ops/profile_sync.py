#!/usr/bin/env python3
"""profile_sync op — user-profile corrections → memory sync (TASK-61 Phase 3).

Parity port of hooks/nav_profile_sync.py. PostToolUse recorder: when an
Edit/Write call touched `.user-profile.json`, diffs the corrections array
against the tracked last-synced count and runs `correction_to_memory.py
--action sync --last-synced N` only when the array grew. Pure side effect.

v6 fidelity:
  - The registry matcher is coarse (Edit|Write|MultiEdit|NotebookEdit) but the
    v6 manifest fired on Edit|Write only — this op filters back down to that
    surface. MultiEdit and NotebookEdit payloads (the latter carry
    ``notebook_path``, not ``file_path``) are skipped silently: v6 never saw
    them, so the op emits nothing for them.
  - v6 printed a bare ``{}`` doc on every Edit|Write branch; ``{"ack": True}``
    reproduces that byte shape (golden: profile_sync.json).
  - Idempotency state moves from v6's .nav-profile-sync-state.json to the
    schema-2 runtime state (``ctx.state['profile'].last_synced_count`` — the
    section survives session boundaries, so old corrections are never
    re-synced). The counter still advances ONLY on a successful sync, so
    failed syncs retry next time (v6 rule). This is the one sanctioned
    parity delta (internal state-file paths).
  - stderr diagnostics keep the v6 message text and route through the result
    ``stderr`` key — nav_hook_lib.sentinels owns the only emitter (mem-034).
  - ``.agent/`` presence and ``profile_sync_hook.enabled`` gates are
    runtime-owned (dispatch early-out + OpSpec.config_key).

No ctx.pilot_executor check on purpose: v6 ran this hook under Pilot too (it
blocks nothing), and the runtime belt covers blocking keys anyway.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from nav_hook_lib import hio

# The exact v6 manifest surface; the coarse registry matcher is wider.
V6_TOOLS = frozenset({"Edit", "Write"})

PROFILE_BASENAME = ".user-profile.json"

SYNC_TIMEOUT_SECONDS = 8


def _resolve_plugin_dir() -> Path | None:
    """v6 _resolve_plugin_dir, with the file-relative fallback at op depth."""
    env = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    candidates = [
        Path.home() / ".claude" / "plugins" / "cache" / "navigator-marketplace" / "navigator",
        Path.home() / ".claude" / "plugins" / "marketplaces" / "navigator-marketplace",
    ]
    for candidate in candidates:
        if (candidate / "skills" / "nav-graph").is_dir():
            return candidate
    here = Path(__file__).resolve().parent.parent.parent  # hooks/ops/ -> repo root
    if (here / "skills" / "nav-graph").is_dir():
        return here
    return None


def _profile_write_path(payload: dict, root: Path) -> Path | None:
    """The profile path when this tool call touched it, else None (v6 logic)."""
    tool_input = payload.get("tool_input") or {}
    candidate = tool_input.get("file_path")
    if not isinstance(candidate, str) or not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = root / candidate
    # v6 matched any path whose basename is .user-profile.json (defensive).
    if path.name == PROFILE_BASENAME and path.is_file():
        return path
    return None


def _last_synced_count(ctx) -> int:
    section = ctx.state.get("profile")
    if not isinstance(section, dict):
        return 0
    return int(section.get("last_synced_count") or 0)


def _sync(ctx, root: Path, profile_path: Path, stderr_lines: list) -> None:
    """v6 main() sync body: diff corrections, subprocess, advance on success."""
    profile = hio.safe_json(profile_path)
    if profile is None:
        return

    corrections = profile.get("corrections") or []
    current_count = len(corrections) if isinstance(corrections, list) else 0
    last_synced = _last_synced_count(ctx)
    if current_count <= last_synced:
        # No new corrections — pure no-op for non-correction profile edits.
        return

    graph_path = root / ".agent" / "knowledge" / "graph.json"
    if not graph_path.is_file():
        return  # no graph initialized — skip silently (v6)

    plugin_dir = _resolve_plugin_dir()
    if plugin_dir is None:
        stderr_lines.append("nav_profile_sync: plugin dir not found")
        return
    syncer = plugin_dir / "skills" / "nav-graph" / "functions" / "correction_to_memory.py"
    if not syncer.is_file():
        stderr_lines.append(f"nav_profile_sync: {syncer} missing")
        return

    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(syncer),
                "--action", "sync",
                "--profile-path", str(profile_path),
                "--graph-path", str(graph_path),
                "--last-synced", str(last_synced),
            ],
            capture_output=True,
            text=True,
            timeout=SYNC_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        stderr_lines.append("nav_profile_sync: subprocess timeout")
        return
    except Exception as exc:
        stderr_lines.append(f"nav_profile_sync: subprocess failure: {exc}")
        return
    if proc.returncode != 0:
        stderr_lines.append(
            f"nav_profile_sync: sync failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:300]}"
        )
    else:
        stderr_lines.append(
            f"nav_profile_sync: synced {current_count - last_synced} new correction(s)"
        )
        # Only advance the counter on success — failed syncs retry next time.
        section = ctx.state.get("profile")
        if not isinstance(section, dict):
            section = {}
            ctx.state["profile"] = section
        section["last_synced_count"] = current_count


def run(ctx):
    payload = ctx.payload
    if payload.get("tool_name") not in V6_TOOLS:
        return None  # MultiEdit/NotebookEdit: outside the v6 surface — silent skip

    result = {"ack": True}  # v6 printed {} on every Edit|Write branch
    stderr_lines: list = []
    root = hio.project_root(payload)

    profile_path = _profile_write_path(payload, root)
    if profile_path is not None:
        _sync(ctx, root, profile_path, stderr_lines)

    if stderr_lines:
        result["stderr"] = "\n".join(stderr_lines)
    return result
