#!/usr/bin/env python3
"""nav_hook_lib.hio — hook I/O primitives shared by every v7 op (TASK-59 Phase 1).

Extracted from the nine v6 hook scripts (hooks/*.py), which each re-implemented
stdin parsing, safe file reads, project-root resolution, and state writes.
This module is the single home for those patterns.

Contract highlights:
  - Everything is tolerant: bad input degrades to {} / None / False, never an
    exception. Hooks must not crash the harness.
  - NO stderr writes here — sentinels.py owns the only stderr emitter under
    hooks/ (mem-034). hio failures are silent by design.
  - resolve_cwd() ALWAYS returns a resolved path: hook payload cwd arrives
    realpath'd on macOS (/tmp -> /private/tmp) while $PWD may stay logical,
    so raw string-prefix cwd comparisons are unsafe (mem-055 / S6 verdict).

Pure Python stdlib only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def read_stdin_payload() -> dict:
    """Read and parse the hook's stdin JSON payload exactly once.

    Tolerant by contract: empty stdin, a TTY stdin (manual invocation),
    closed/broken stdin, non-JSON bodies, or JSON that is not an object all
    yield {}. Claude Code writes the payload and closes the pipe, so a
    blocking read never hangs in hook context.
    """
    try:
        stdin = sys.stdin
        if stdin is None or getattr(stdin, "closed", False):
            return {}
        if stdin.isatty():
            return {}
        raw = stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def safe_read(path, max_bytes=None):
    """Return the text content of ``path``, or None if missing/unreadable.

    Undecodable bytes are replaced (errors="replace"), mirroring the v6
    _safe_read helpers. ``max_bytes`` head-truncates when given.
    """
    try:
        p = Path(path)
        if not p.is_file():
            return None
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    if max_bytes is not None:
        return text[:max_bytes]
    return text


def safe_json(path):
    """Parse ``path`` as a JSON object; None on missing/corrupt/non-object."""
    raw = safe_read(path)
    if raw is None or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def atomic_write_text(path, text) -> bool:
    """Atomically write ``text`` to ``path`` (tmp file + os.replace).

    Parent directories are created. The tmp file lives in the destination
    directory so os.replace stays a same-filesystem atomic rename. Returns
    False (and cleans up the tmp file) on any failure.
    """
    tmp = None
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.parent / f".{p.name}.{os.getpid()}.tmp"
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, p)
        return True
    except Exception:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        return False


def atomic_write_json(path, obj) -> bool:
    """Atomically serialize ``obj`` as pretty JSON to ``path``.

    JSON-native values round-trip exactly (state.py's check_shown tristate
    True/False/None stays true/false/null — mem-037); non-serializable leaves
    fall back to str() like the v6 profile dump did. Returns False on failure
    (e.g. circular references, unwritable destination).
    """
    try:
        data = json.dumps(obj, indent=2, default=str) + "\n"
    except Exception:
        return False
    return atomic_write_text(path, data)


def resolve_cwd(payload=None) -> Path:
    """Resolve the effective working directory for this hook invocation.

    Order (extracted verbatim from all nine v6 hooks): payload["cwd"], then
    the CLAUDE_PROJECT_DIR env var, then os.getcwd(). The result is ALWAYS
    .resolve()'d — macOS realpaths /tmp in hook payloads (mem-055), so
    logical and physical paths must be normalized before any comparison.

    Tolerant per the module contract: a candidate that cannot become a Path
    (non-string cwd, embedded NUL, OS-level resolve failure) falls through to
    the next candidate instead of raising.
    """
    if not isinstance(payload, dict):
        payload = {}
    candidates = (payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return Path(candidate).resolve()
        except (TypeError, ValueError, OSError):
            continue  # bad candidate — fall through (hooks must not crash)
    return Path(os.getcwd()).resolve()


def project_root(payload=None) -> Path:
    """Locate the Navigator project root for this invocation.

    Walks up from resolve_cwd(payload) to the nearest directory containing
    .agent/; falls back to the resolved cwd itself when no ancestor has one
    (callers then see a root without .agent and degrade per their own rules).
    """
    cwd = resolve_cwd(payload)
    for candidate in (cwd, *cwd.parents):
        try:
            if (candidate / ".agent").is_dir():
                return candidate
        except Exception:
            break
    return cwd
