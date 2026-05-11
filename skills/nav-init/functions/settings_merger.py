#!/usr/bin/env python3
"""
Idempotent merger for .claude/settings.json.

Used by nav-init and nav-upgrade to add Navigator's SessionStart hook (and
optionally PostToolUse / PreToolUse hooks) without clobbering existing
user configuration.

Rules:
- If settings.json doesn't exist: create with provided fragment.
- If it exists: deep-merge `hooks` arrays by event name. Skip identical
  entries (matched by command string) so re-running is a no-op.
- Always pretty-print, preserve key order: schema, hooks, then anything else.

Usage:
    python3 settings_merger.py /path/to/.claude/settings.json fragment.json
    python3 settings_merger.py /path/to/.claude/settings.json - <<<'{"hooks":...}'
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_existing(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"settings_merger: existing {path} is invalid JSON: {e}", file=sys.stderr)
        # Refuse to clobber — bail out
        sys.exit(2)


def _command_of(hook_entry: dict) -> str | None:
    for h in hook_entry.get("hooks", []) or []:
        if isinstance(h, dict) and h.get("type") == "command":
            return h.get("command")
    return None


def _merge_hooks(existing: list[dict], incoming: list[dict]) -> list[dict]:
    seen = {_command_of(e) for e in existing if _command_of(e)}
    out = list(existing)
    for entry in incoming:
        cmd = _command_of(entry)
        if cmd and cmd in seen:
            continue
        out.append(entry)
        if cmd:
            seen.add(cmd)
    return out


def merge(target_path: Path, fragment: dict) -> dict:
    """Merge fragment into target file. Returns the merged dict (also written to disk)."""
    current = _load_existing(target_path)

    # Ensure schema field is set for editor completion
    if "$schema" not in current and "$schema" in fragment:
        current["$schema"] = fragment["$schema"]

    existing_hooks = current.get("hooks") or {}
    incoming_hooks = fragment.get("hooks") or {}

    merged_hooks = dict(existing_hooks)
    for event, entries in incoming_hooks.items():
        if not isinstance(entries, list):
            continue
        merged_hooks[event] = _merge_hooks(
            existing_hooks.get(event, []) if isinstance(existing_hooks.get(event), list) else [],
            entries,
        )

    if merged_hooks:
        current["hooks"] = merged_hooks

    # Pass through other top-level keys from fragment (non-destructive)
    for k, v in fragment.items():
        if k in ("$schema", "hooks"):
            continue
        current.setdefault(k, v)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return current


def _load_fragment(arg: str) -> dict:
    if arg == "-":
        return json.loads(sys.stdin.read())
    p = Path(arg)
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: settings_merger.py <settings.json> <fragment.json|->", file=sys.stderr)
        return 1
    target = Path(sys.argv[1])
    fragment = _load_fragment(sys.argv[2])
    merge(target, fragment)
    print(f"settings_merger: merged into {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
