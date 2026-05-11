#!/usr/bin/env python3
"""
Idempotent merger for .claude/settings.json.

Used by nav-init and nav-upgrade to add Navigator's lifecycle hooks
(SessionStart, PreCompact, PostCompact, PostToolUse, etc.) without
clobbering existing user configuration.

Safety guarantees:
- Existing user hooks (different commands) are always preserved
- Top-level keys (`permissions`, `mcpServers`, `model`, etc.) pass through
- Invalid existing JSON → refuse to merge, exit 2
- Empty existing file → refuse to merge, exit 2
- Writes are atomic (tempfile + os.replace) — no partial-write corruption
- Re-running with identical fragment is a no-op (dedup by command string)
- Non-list incoming hooks values produce a stderr warning instead of silent skip

Usage:
    python3 settings_merger.py /path/to/.claude/settings.json fragment.json
    python3 settings_merger.py /path/to/.claude/settings.json - <<<'{"hooks":...}'
    python3 settings_merger.py --dry-run /path/to/.claude/settings.json fragment.json
        # writes merged JSON to stdout, never touches disk
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def _load_existing(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"settings_merger: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)
    if not raw.strip():
        print(
            f"settings_merger: {path} is empty — refusing to merge "
            "(would risk silent overwrite). Delete the file if you want "
            "a fresh install.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(
            f"settings_merger: existing {path} is invalid JSON: {e}. "
            "Refusing to merge — fix or delete the file first.",
            file=sys.stderr,
        )
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


def _atomic_write(target_path: Path, content: str) -> None:
    """Write content atomically: tempfile in same dir, fsync, then rename.

    Same-directory tempfile guarantees `os.replace` is atomic on POSIX.
    `fsync` before rename guarantees content is durable even if power-loss
    occurs after the rename returns.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=target_path.name + ".",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                # Best-effort; some filesystems (e.g. tmpfs) reject fsync
                pass
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def merge(target_path: Path, fragment: dict, *, dry_run: bool = False) -> dict:
    """Merge fragment into target file.

    Returns the merged dict. When dry_run is True, no disk write happens —
    the dict is returned and the caller is responsible for printing it.
    """
    current = _load_existing(target_path)

    # Ensure schema field is set for editor completion
    if "$schema" not in current and "$schema" in fragment:
        current["$schema"] = fragment["$schema"]

    existing_hooks = current.get("hooks") or {}
    incoming_hooks = fragment.get("hooks") or {}

    merged_hooks = dict(existing_hooks)
    for event, entries in incoming_hooks.items():
        if not isinstance(entries, list):
            print(
                f"settings_merger: incoming hooks[{event!r}] is not a list "
                f"({type(entries).__name__}) — skipping. Bug in fragment? "
                "Existing value (if any) is preserved untouched.",
                file=sys.stderr,
            )
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

    serialized = json.dumps(current, indent=2) + "\n"
    if not dry_run:
        _atomic_write(target_path, serialized)
    return current


def _load_fragment(arg: str) -> dict:
    if arg == "-":
        return json.loads(sys.stdin.read())
    p = Path(arg)
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Idempotent merger for .claude/settings.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print merged JSON to stdout; do not write to disk.",
    )
    parser.add_argument("target", help="Path to .claude/settings.json")
    parser.add_argument("fragment", help="Path to fragment JSON, or '-' for stdin")
    args = parser.parse_args()

    target = Path(args.target)
    fragment = _load_fragment(args.fragment)

    merged = merge(target, fragment, dry_run=args.dry_run)

    if args.dry_run:
        print(json.dumps(merged, indent=2))
    else:
        print(f"settings_merger: merged into {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
