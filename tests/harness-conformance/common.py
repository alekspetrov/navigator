"""Shared driver helpers for the harness-conformance probes (TASK-58).

Ported verbatim from the validated TASK-57 spike bodies
(/tmp/nav-v7-spike/probes/common.py). Stdlib only — deliberately NO imports
from hooks/ or nav_hook_lib: this suite runs parallel to TASK-59 and must
stay independent of the runtime it certifies.

Each probe: arms its hook via a state file, drives a live headless Claude Code
session in the scratch project, then checks BOTH observables — the visible
answer (quote-check) and the transcript JSONL (position-aware grep).

The spike dir is parametrized via NAV_SPIKE_DIR (default /tmp/nav-v7-spike);
the /tmp harness stays the runtime home. See run.md for setup/teardown.
"""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

SPIKE = Path(os.environ.get("NAV_SPIKE_DIR", "/tmp/nav-v7-spike"))
PROJECT = SPIKE / "project"
STATE = SPIKE / "state"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


def make_sentinel(tag: str) -> str:
    return f"NAV-S{tag}-{uuid.uuid4().hex[:8]}"


def arm(probe: str, data: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"arm-{probe}.json").write_text(json.dumps(data))


def disarm(probe: str) -> None:
    f = STATE / f"arm-{probe}.json"
    if f.exists():
        f.unlink()


def clear_log(probe: str) -> None:
    f = STATE / f"log-{probe}.jsonl"
    if f.exists():
        f.unlink()


def read_log(probe: str) -> list:
    f = STATE / f"log-{probe}.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def preflight() -> None:
    """mem-036: scratch project must have no settings backstop and no .agent."""
    assert not (PROJECT / ".claude" / "settings.json").exists(), \
        "scratch project must not have .claude/settings.json"
    assert not (PROJECT / ".agent").exists(), \
        "scratch project must not have .agent/"


def cc_version() -> str:
    out = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    return out.stdout.strip()


def run_claude(prompt: str, allowed=None, resume=None, timeout=240) -> dict:
    """Drive one headless turn in the scratch project. Returns raw + parsed."""
    cmd = ["claude", "-p", prompt, "--output-format", "json"]
    if allowed:
        cmd += ["--allowedTools", ",".join(allowed)]
    if resume:
        cmd += ["--resume", resume]
    started = time.time()
    proc = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True,
                          timeout=timeout)
    parsed = None
    try:
        parsed = json.loads(proc.stdout)
    except Exception:
        pass
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed": parsed,
        "result_text": (parsed or {}).get("result", "") if isinstance(parsed, dict) else "",
        "session_id": (parsed or {}).get("session_id") if isinstance(parsed, dict) else None,
        "started": started,
        "duration": time.time() - started,
    }


def find_transcripts(session_id=None, since=None) -> list:
    """Locate transcript JSONLs for the scratch project.

    session_id -> exact file match anywhere under ~/.claude/projects.
    since      -> all scratch-project JSONLs modified after that epoch
                  (catches subagent/sidechain files too).
    """
    hits = []
    if session_id:
        hits += list(CLAUDE_PROJECTS.glob(f"*/{session_id}.jsonl"))
        hits += list(CLAUDE_PROJECTS.glob(f"*/**/{session_id}.jsonl"))
    if since is not None:
        for d in CLAUDE_PROJECTS.glob(f"*{SPIKE.name}*"):
            for f in d.rglob("*.jsonl"):
                if f.stat().st_mtime >= since - 1:
                    hits.append(f)
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def scan_jsonl(path: Path, needle: str) -> list:
    """Position-aware grep: where does the needle sit inside the transcript?"""
    occurrences = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if needle not in line:
            continue
        entry_type = role = None
        block_types = []
        sidechain = None
        try:
            entry = json.loads(line)
            entry_type = entry.get("type")
            sidechain = entry.get("isSidechain")
            msg = entry.get("message") or {}
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if needle in json.dumps(block):
                        block_types.append(block.get("type"))
            elif isinstance(content, str) and needle in content:
                block_types.append("str")
            if not block_types and needle in json.dumps(entry):
                for key in entry:
                    if key != "message" and needle in json.dumps(entry.get(key)):
                        block_types.append(f"entry.{key}")
        except Exception:
            block_types.append("unparsed-line")
        occurrences.append({
            "file": str(path), "line": i, "entry_type": entry_type,
            "role": role, "is_sidechain": sidechain, "block_types": block_types,
        })
    return occurrences


def entry_lines(path: Path, predicate) -> list:
    """Line numbers of entries matching predicate(entry)."""
    out = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        try:
            entry = json.loads(line)
        except Exception:
            continue
        try:
            if predicate(entry):
                out.append(i)
        except Exception:
            continue
    return out


def write_verdict(probe: str, data: dict) -> None:
    data = {"probe": probe, "cc_version": cc_version(),
            "date": time.strftime("%Y-%m-%d"), **data}
    STATE.mkdir(parents=True, exist_ok=True)
    out = STATE / f"verdict-{probe}.json"
    out.write_text(json.dumps(data, indent=2, default=str))
    print(json.dumps(data, indent=2, default=str))
