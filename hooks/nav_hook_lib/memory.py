#!/usr/bin/env python3
"""Knowledge-graph memory recall for hook ops (TASK-59, Phase 5).

Thin subprocess wrapper over ``skills/nav-graph/functions/memory_recall.py``
preserving the v6 hook semantics (``nav_brief.py`` / ``nav_session_start.py``):
silence over noise. Any failure — missing graph, missing script, non-zero
exit, timeout, bad arguments — collapses to ``''`` so a broken recall path
can never break a hook.

``--concepts`` takes ONE comma-separated argument; list inputs are joined
here so callers cannot accidentally splat them into argv.

Pure stdlib. Never writes to stdout/stderr itself (mem-034 —
``sentinels.py`` owns emission).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RECALL_RELPATH = Path("skills") / "nav-graph" / "functions" / "memory_recall.py"


def _plugin_dir():
    """Directory containing ``skills/nav-graph`` or None.

    Mirrors the v6 ``_resolve_plugin_dir``: ``CLAUDE_PLUGIN_ROOT`` (legacy
    fallback ``CLAUDE_PLUGIN_DIR``) wins when it names a directory;
    otherwise fall back to the checkout containing this library.
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    here = Path(__file__).resolve().parent.parent.parent  # repo/plugin root
    if (here / "skills" / "nav-graph").is_dir():
        return here
    return None


def recall(concepts=None, auto: bool = False, agent_dir=".agent",
           limit: int = 5, timeout_s: float = 3) -> str:
    """Compact ranked-memory summary, or ``''`` silently on any failure.

    Exactly one of ``concepts``/``auto`` should be requested; passing both
    is delegated to the underlying script, whose non-zero exit collapses
    to ``''`` here. ``concepts`` may be a string (already comma-separated)
    or a list/tuple of concept strings.

    ``timeout_s`` defaults to 3 — v6 parity with nav_brief's
    RECALL_TIMEOUT=3: a hook runs on every prompt, so a wedged recall
    subprocess must be cut off well inside the hook's own budget.
    """
    if not concepts and not auto:
        return ""
    plugin_dir = _plugin_dir()
    if plugin_dir is None:
        return ""
    script = plugin_dir / RECALL_RELPATH
    if not script.is_file():
        return ""

    try:
        agent_path = Path(agent_dir)
        graph_path = agent_path / "knowledge" / "graph.json"
        if not graph_path.is_file():
            return ""

        cmd = [sys.executable, str(script)]
        if concepts:
            if isinstance(concepts, (list, tuple)):
                concepts = ",".join(str(c) for c in concepts)
            cmd += ["--concepts", str(concepts)]
        if auto:
            cmd.append("--auto")
        cmd += [
            "--agent-dir", str(agent_path),
            "--graph-path", str(graph_path),
            "--limit", str(int(limit)),
            "--format", "compact",
        ]
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_s,
        )
        if out.returncode != 0:
            return ""
        return (out.stdout or "").strip()
    except Exception:
        return ""
