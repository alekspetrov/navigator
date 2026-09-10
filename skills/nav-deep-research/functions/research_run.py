#!/usr/bin/env python3
"""
Research run manifest for nav-deep-research (TASK-74).

One run = one directory under ``.agent/research/<slug>/`` holding the verbatim
query, a manifest (``run.json``) with per-step status, and the step artifacts.
The manifest is the primary resume path; the artifact scan is the fallback
for a manifest that was not kept up to date (compaction ate the step calls).

Commands (all print JSON, exit 0 unless the run is missing):
  init   --query TEXT            create the run (slug, query.md, run.json)
  step   --run SLUG --start N | --done N | --block N --reason TEXT
  set    --run SLUG --key K --value V     store a meta value (e.g. sources_rows_before_patch)
  resume --run SLUG              next step + reason (manifest first, artifacts fallback)
  status --run SLUG              manifest + source counts
  list                           runs, newest first

Design constraints:
- Stdlib only. Writes are whole-file, tmp + rename.
- ``backend`` is ``hyperresearch`` when the project has a ``.hyperresearch/``
  directory; the router then hands off instead of running the native pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
STEPS = [
    (1, "decompose"),
    (2, "sweep"),
    (3, "draft"),
    (4, "critique"),
    (5, "patch"),
    (6, "ship"),
]
# Canonical artifact per step; a step "looks done" when its artifact exists.
ARTIFACTS = {
    1: "search-plan.md",
    2: "sources",
    3: "report.md",
    4: "findings/critic.json",
    5: "patch-log.json",
    6: "ship.json",
}
STATUSES = ("pending", "running", "done", "blocked", "skipped")
_SLUG_WORDS = 6
_STOP = {"a", "an", "the", "of", "on", "in", "for", "to", "and", "is", "are", "what", "how",
         "why", "do", "does", "vs", "with", "about"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def research_root(agent_dir: str = ".agent") -> Path:
    return Path(agent_dir) / "research"


def run_dir(slug: str, agent_dir: str = ".agent") -> Path:
    return research_root(agent_dir) / slug


def make_slug(query: str, existing: set[str] | None = None) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", (query or "").lower()) if w not in _STOP]
    if not words:
        words = re.findall(r"[a-z0-9]+", (query or "").lower())
    base = "-".join(words[:_SLUG_WORDS]) or "research"
    existing = existing or set()
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def detect_backend(project_root: str = ".") -> str:
    return "hyperresearch" if (Path(project_root) / ".hyperresearch").is_dir() else "native"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_manifest(slug: str, agent_dir: str = ".agent") -> dict:
    path = run_dir(slug, agent_dir) / "run.json"
    if not path.exists():
        raise FileNotFoundError(f"no run manifest at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(manifest: dict, agent_dir: str = ".agent") -> Path:
    manifest["updated"] = now_iso()
    path = run_dir(manifest["slug"], agent_dir) / "run.json"
    _atomic_write(path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return path


def init_run(query: str, agent_dir: str = ".agent", project_root: str = ".",
             tier: str = "light") -> dict:
    query = (query or "").strip()
    if not query:
        raise ValueError("query is empty")
    root = research_root(agent_dir)
    root.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in root.iterdir() if p.is_dir()}
    slug = make_slug(query, existing)
    created = now_iso()
    backend = detect_backend(project_root)
    manifest = {
        "schema": SCHEMA,
        "slug": slug,
        "created": created,
        "updated": created,
        "tier": tier,
        "backend": backend,
        "query_file": "query.md",
        "steps": {str(n): {"name": name, "status": "pending"} for n, name in STEPS},
        "atomic_items": [],
        "meta": {},
    }
    directory = run_dir(slug, agent_dir)
    (directory / "sources").mkdir(parents=True, exist_ok=True)
    (directory / "findings").mkdir(parents=True, exist_ok=True)
    query_md = (
        "---\n"
        f"slug: {slug}\n"
        f"created: {created}\n"
        f"tier: {tier}\n"
        f"backend: {backend}\n"
        "---\n\n"
        "# Research query (verbatim, gospel)\n\n"
        f"{query}\n"
    )
    _atomic_write(directory / "query.md", query_md)
    save_manifest(manifest, agent_dir)
    return {"slug": slug, "dir": str(directory), "backend": backend, "tier": tier}


def read_query(slug: str, agent_dir: str = ".agent") -> str:
    """Verbatim query text (the part after the H1) or '' when missing."""
    path = run_dir(slug, agent_dir) / "query.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    marker = "# Research query (verbatim, gospel)\n\n"
    idx = text.find(marker)
    return text[idx + len(marker):].strip() if idx >= 0 else text.strip()


def set_step(slug: str, number: int, status: str, reason: str | None = None,
             agent_dir: str = ".agent") -> dict:
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    manifest = load_manifest(slug, agent_dir)
    key = str(number)
    if key not in manifest["steps"]:
        raise ValueError(f"unknown step {number}")
    entry = manifest["steps"][key]
    entry["status"] = status
    stamp = now_iso()
    if status == "running":
        entry["started_at"] = stamp
        entry.pop("finished_at", None)
    elif status in ("done", "skipped"):
        entry["finished_at"] = stamp
    if reason:
        entry["reason"] = reason
    else:
        entry.pop("reason", None)
    save_manifest(manifest, agent_dir)
    return entry


def set_meta(slug: str, key: str, value, agent_dir: str = ".agent") -> dict:
    manifest = load_manifest(slug, agent_dir)
    manifest.setdefault("meta", {})[key] = value
    save_manifest(manifest, agent_dir)
    return manifest["meta"]


def artifact_exists(slug: str, number: int, agent_dir: str = ".agent") -> bool:
    path = run_dir(slug, agent_dir) / ARTIFACTS[number]
    if number == 2:
        return path.is_dir() and any(path.glob("*.md"))
    return path.exists()


def resume(slug: str, agent_dir: str = ".agent") -> dict:
    """Next step to run. Manifest wins; artifact scan is the fallback."""
    manifest = load_manifest(slug, agent_dir)
    manifest_next = None
    for n, _ in STEPS:
        status = manifest["steps"][str(n)]["status"]
        if status in ("done", "skipped"):
            continue
        manifest_next = n
        break
    highest_artifact = 0
    for n, _ in STEPS:
        if artifact_exists(slug, n, agent_dir):
            highest_artifact = n
    artifact_next = highest_artifact + 1 if highest_artifact < len(STEPS) else None

    if manifest_next is None:
        next_step, reason = None, "manifest: all steps done"
    elif artifact_next is not None and artifact_next > manifest_next:
        next_step, reason = artifact_next, (
            f"artifacts: step {highest_artifact} artifact exists but manifest says "
            f"step {manifest_next} pending; trusting the disk")
    else:
        next_step, reason = manifest_next, "manifest"
    blocked = [n for n, _ in STEPS if manifest["steps"][str(n)]["status"] == "blocked"]
    return {
        "slug": slug,
        "backend": manifest.get("backend", "native"),
        "next_step": next_step,
        "next_name": dict(STEPS).get(next_step) if next_step else None,
        "reason": reason,
        "blocked_steps": blocked,
        "artifacts": {str(n): artifact_exists(slug, n, agent_dir) for n, _ in STEPS},
    }


def status(slug: str, agent_dir: str = ".agent") -> dict:
    manifest = load_manifest(slug, agent_dir)
    sources = run_dir(slug, agent_dir) / "sources"
    counts = {"ok": 0, "blocked": 0, "skipped": 0, "other": 0}
    for note in sorted(sources.glob("*.md")) if sources.is_dir() else []:
        head = note.read_text(encoding="utf-8", errors="replace")[:2000]
        match = re.search(r"^status:\s*(\w+)", head, re.MULTILINE)
        key = match.group(1) if match and match.group(1) in counts else "other"
        counts[key] += 1
    manifest["source_counts"] = counts
    return manifest


def list_runs(agent_dir: str = ".agent") -> list[dict]:
    root = research_root(agent_dir)
    if not root.is_dir():
        return []
    runs = []
    for directory in root.iterdir():
        manifest_path = directory / "run.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        done = sum(1 for s in manifest.get("steps", {}).values()
                   if s.get("status") in ("done", "skipped"))
        runs.append({"slug": manifest.get("slug", directory.name),
                     "created": manifest.get("created", ""),
                     "steps_done": done, "backend": manifest.get("backend", "native")})
    return sorted(runs, key=lambda r: r["created"], reverse=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="nav-deep-research run manifest")
    parser.add_argument("--agent-dir", default=".agent")
    parser.add_argument("--project-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--query", required=True)
    p_init.add_argument("--tier", default="light", choices=["light"])

    p_step = sub.add_parser("step")
    p_step.add_argument("--run", required=True)
    group = p_step.add_mutually_exclusive_group(required=True)
    group.add_argument("--start", type=int)
    group.add_argument("--done", type=int)
    group.add_argument("--skip", type=int)
    group.add_argument("--block", type=int)
    p_step.add_argument("--reason")

    p_set = sub.add_parser("set")
    p_set.add_argument("--run", required=True)
    p_set.add_argument("--key", required=True)
    p_set.add_argument("--value", required=True)

    for name in ("resume", "status"):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True)
    sub.add_parser("list")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            out = init_run(args.query, args.agent_dir, args.project_root, args.tier)
        elif args.command == "step":
            if args.start is not None:
                out = set_step(args.run, args.start, "running", args.reason, args.agent_dir)
            elif args.done is not None:
                out = set_step(args.run, args.done, "done", args.reason, args.agent_dir)
            elif args.skip is not None:
                out = set_step(args.run, args.skip, "skipped", args.reason, args.agent_dir)
            else:
                out = set_step(args.run, args.block, "blocked", args.reason, args.agent_dir)
        elif args.command == "set":
            value = args.value
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
            out = set_meta(args.run, args.key, value, args.agent_dir)
        elif args.command == "resume":
            out = resume(args.run, args.agent_dir)
        elif args.command == "status":
            out = status(args.run, args.agent_dir)
        else:
            out = list_runs(args.agent_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
