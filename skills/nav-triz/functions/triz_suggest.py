#!/usr/bin/env python3
"""
TRIZ Suggest - candidate inventive principles for a declared contradiction (TASK-73)

Given "improving A vs worsening B", rank a curated set of software-mapped
TRIZ principles by keyword overlap and return up to N candidates drawn from
DIFFERENT separation modes, plus prior decisions from the knowledge graph
that resolved a matching contradiction (graph_manager.query_contradictions).

Design constraints:
- Deterministic, stdlib only, always exits 0 (callers are model-side prompts).
- Diversity over score: one candidate per separation mode first, so the
  model gets genuinely different moves, not three flavours of the same one.
- Never silent: with no keyword hits it falls back to a generic trio and
  says so, because "no suggestion" reads as "nothing to try".
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "nav-graph" / "functions"))
try:
    from graph_manager import load_graph, query_contradictions  # noqa: E402
except Exception:  # pragma: no cover - graph skill missing in a stripped install
    load_graph = query_contradictions = None

# (number, name, separation, software move, keywords)
PRINCIPLES = [
    (1, "Segmentation", "level",
     "split one thing into independent parts: modules, ops, per-feature toggles, per-tenant state",
     ["monolith", "coupled", "coupling", "big", "large", "single", "one", "shared", "all",
      "granular", "isolate", "blast", "radius", "module", "modules"]),
    (2, "Taking out", "space",
     "extract the disturbing part into its own place: sidecar, separate process, adapter, quarantine",
     ["noise", "noisy", "leak", "leakage", "secret", "secrets", "side", "effect", "effects",
      "pollute", "pollution", "isolate", "extract", "diagnostic", "diagnostics", "logging"]),
    (3, "Local quality", "space",
     "make different parts behave differently: per-path config, hot-path fast, cold-path safe",
     ["uniform", "everywhere", "global", "hot", "path", "cold", "special", "case", "cases",
      "specific", "local", "per", "quality", "divergence", "depth", "thorough"]),
    (5, "Merging", "level",
     "combine identical operations in space or time: batch, single state file, one dispatcher",
     ["many", "multiple", "writers", "writes", "duplicate", "duplicated", "scattered",
      "consistent", "consistency", "batch", "n+1", "fan-out", "several"]),
    (6, "Universality", "level",
     "one part performs several functions: shared runtime, one query interface, one CLI",
     ["several", "interfaces", "surfaces", "separate", "implementations", "drift",
      "duplicate", "reuse", "generic", "unified"]),
    (7, "Nesting", "level",
     "place one thing inside another: composition, wrappers, layered config, plugin-in-plugin",
     ["wrap", "wrapper", "layer", "layers", "compose", "composition", "nested", "embed",
      "inherit", "override"]),
    (10, "Prior action", "time",
     "do it beforehand: precompute, cache, prefetch, strip/normalize before scan, warm up",
     ["slow", "latency", "startup", "start", "load", "loading", "cold", "cache", "precompute",
      "before", "scan", "parse", "upfront", "context", "tokens", "budget"]),
    (11, "Beforehand cushioning", "time",
     "prepare a fallback in advance: additive-only migration, verified rollback, feature flag",
     ["rollback", "reversible", "reversibility", "irreversible", "migration", "big-bang",
      "replacement", "replace", "risky", "risk", "regression", "downgrade", "recover"]),
    (13, "Inversion", "condition",
     "do it the other way round: pull instead of push, lazy instead of eager, deny-list to allow-list",
     ["push", "pull", "eager", "lazy", "polling", "poll", "invert", "inverse", "opposite",
      "allow", "deny", "opt-in", "opt-out", "default"]),
    (15, "Dynamization", "condition",
     "make it adjustable at runtime: config toggle, threshold, ship OFF then opt in, adaptive limits",
     ["toggle", "flag", "config", "configurable", "adjust", "adjustable", "threshold",
      "opt-in", "default", "off", "on", "value", "feature", "features", "new", "ship",
      "adaptive", "tune"]),
    (16, "Partial or excessive action", "condition",
     "do slightly less or slightly more: sample instead of read-all, over-fetch then trim, best-effort",
     ["complete", "completeness", "exhaustive", "all", "everything", "partial", "sample",
      "sampling", "approximate", "best-effort", "coverage", "precision", "recall",
      "cost", "expensive", "overhead", "ceremony", "cheap", "tokens", "budget"]),
    (17, "Another dimension", "space",
     "add an axis: separate score/axis per concern, multi-level index, tags instead of folders",
     ["score", "scoring", "axis", "axes", "dimension", "dimensions", "one", "single",
      "distinct", "concerns", "concern", "nuance", "explainability", "flat", "hierarchy"]),
    (19, "Periodic action", "time",
     "replace continuous with periodic: cron, decay passes, batch reconcile, heartbeat",
     ["continuous", "continuously", "always", "every", "constant", "polling", "poll",
      "interval", "periodic", "schedule", "scheduled", "cron", "stale", "decay"]),
    (21, "Skipping", "time",
     "run the harmful step very fast or skip it: fail-open, short-circuit gates, timeouts",
     ["block", "blocking", "blocked", "hang", "hangs", "timeout", "timeouts", "fail-open",
      "fail", "crash", "slow", "gate", "gates", "short-circuit"]),
    (23, "Feedback", "condition",
     "introduce or change feedback: telemetry, health checks, stagnation detection, self-tuning",
     ["silent", "silently", "invisible", "unknown", "observe", "observability", "telemetry",
      "detect", "detection", "measure", "metrics", "signal", "signals", "false-fire"]),
    (24, "Intermediary", "space",
     "put a carrier between: adapter, single emitter, gateway, shim, facade",
     ["compat", "compatibility", "compatible", "contract", "contracts", "versions",
      "version", "emitter", "emit", "adapter", "shim", "shims", "gateway", "clean", "codebase",
      "diagnostics", "diagnostic", "consumer", "consumers"]),
    (25, "Self-service", "level",
     "the system maintains itself: auto-update, reconcile on session start, auto-register",
     ["manual", "manually", "forget", "forgotten", "maintenance", "maintain", "drift",
      "sync", "auto", "automatic", "self", "update", "updates"]),
    (26, "Copying", "space",
     "use a cheap copy instead of the real thing: fixtures, goldens, replica, dry-run, staging",
     ["production", "prod", "live", "real", "test", "testing", "tests", "fixture", "fixtures",
      "golden", "goldens", "staging", "dry-run", "replica", "confidence", "evidence"]),
    (27, "Cheap short-living objects", "time",
     "replace the durable thing with disposable ones: ephemeral env, tmp worktree, per-turn state",
     ["ephemeral", "temporary", "temp", "disposable", "worktree", "sandbox", "state",
      "durable", "persistent", "session", "turn", "cleanup"]),
    (34, "Discarding and recovering", "time",
     "discard what has done its job, regenerate on demand: prune, archive to resolved/, rebuild index",
     ["stale", "prune", "pruned", "archive", "archived", "resolved", "rebuild", "regenerate",
      "garbage", "bloat", "grow", "growth", "size"]),
    (35, "Parameter change", "condition",
     "change a property: confidence instead of boolean, soft budget instead of hard limit, score instead of gate",
     ["boolean", "binary", "hard", "soft", "limit", "limits", "strict", "lenient", "score",
      "threshold", "degree", "confidence", "weight", "weights"]),
]

SEPARATION_ORDER = ("time", "space", "condition", "level")
GENERIC_TRIO = (10, 15, 1)  # prior action, dynamization, segmentation

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+\-]*")
_STOP = {"vs", "and", "or", "the", "a", "an", "of", "to", "with", "for", "in", "on", "at",
         "improving", "improve", "worsening", "worsens", "worse", "better", "more", "less"}


def _tokens(text: str) -> set:
    toks = set()
    for t in _TOKEN_RE.findall((text or "").lower()):
        if t in _STOP or len(t) < 2:
            continue
        toks.add(t)
        if t.endswith("s") and len(t) > 3:
            toks.add(t[:-1])
    return toks


def score_principles(contradiction: str) -> list:
    """[(score, principle_tuple)] sorted by score desc, then principle number.

    Keywords are normalized with the same tokenizer as the input, so
    "tokens"/"token" and "shims"/"shim" match either way.
    """
    toks = _tokens(contradiction)
    scored = []
    for p in PRINCIPLES:
        hits = toks & _tokens(" ".join(p[4]))
        scored.append((len(hits), p))
    scored.sort(key=lambda s: (-s[0], s[1][0]))
    return scored


def suggest(contradiction: str, limit: int = 3) -> dict:
    """Up to `limit` candidates, diverse by separation mode; generic fallback."""
    scored = score_principles(contradiction)
    hits = [(s, p) for s, p in scored if s > 0]
    generic = not hits
    if generic:
        by_num = {p[0]: p for p in PRINCIPLES}
        chosen = [by_num[n] for n in GENERIC_TRIO][:limit]
    else:
        chosen, seen_modes = [], set()
        for s, p in hits:                       # one per separation mode first
            if p[2] not in seen_modes:
                chosen.append(p); seen_modes.add(p[2])
            if len(chosen) >= limit:
                break
        for s, p in hits:                       # then fill by score
            if len(chosen) >= limit:
                break
            if p not in chosen:
                chosen.append(p)
        by_num = {p[0]: p for p in PRINCIPLES}
        for n in GENERIC_TRIO:                  # then pad with the generic trio
            if len(chosen) >= limit:
                break
            if by_num[n] not in chosen:
                chosen.append(by_num[n])
    return {
        "contradiction": contradiction,
        "generic": generic,
        "candidates": [
            {"number": p[0], "name": p[1], "separation": p[2], "move": p[3]}
            for p in chosen
        ],
    }


def prior_resolutions(contradiction: str, graph_path: str, limit: int = 5) -> list:
    """Decisions in the graph whose contradiction shares a keyword; [] if no graph."""
    if load_graph is None or not Path(graph_path).exists():
        return []
    graph = load_graph(graph_path)
    seen, out = set(), []
    for tok in sorted(_tokens(contradiction)):
        for m in query_contradictions(graph, tok):
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            out.append({"id": m["id"], "summary": m.get("summary", ""),
                        "contradiction": m.get("contradiction", ""),
                        "separation": m.get("separation", ""),
                        "principle": m.get("principle", "")})
    out.sort(key=lambda m: m["id"])
    return out[:limit]


def render_text(result: dict, priors: list) -> str:
    lines = [f"Contradiction: {result['contradiction']}", ""]
    lines.append(f"Prior resolutions in this graph ({len(priors)}):")
    for m in priors:
        sep = f" [separation: {m['separation']}]" if m["separation"] else ""
        lines.append(f"  - {m['id']}: {m['contradiction']}{sep}")
        if m["principle"]:
            lines.append(f"      principle: {m['principle']}")
    if not priors:
        lines.append("  (none — this shape of tension is new here)")
    lines.append("")
    label = "Candidate principles (generic fallback — no keyword match)" if result["generic"] \
        else "Candidate principles (one per separation mode first)"
    lines.append(f"{label}:")
    for i, c in enumerate(result["candidates"], 1):
        lines.append(f"  {i}. [{c['separation']}] #{c['number']} {c['name']} — {c['move']}")
    lines.append("")
    lines.append("Next: draft one concrete candidate per line above (what changes, cost S/M/L, "
                 "what it worsens), then recommend one. See skills/nav-triz/SKILL.md.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest TRIZ principles + prior graph resolutions for a contradiction")
    parser.add_argument("--contradiction", required=True,
                        help='"<improving A> vs <worsening B>"')
    parser.add_argument("--graph-path", default=".agent/knowledge/graph.json")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    result = suggest(args.contradiction, max(1, args.limit))
    priors = prior_resolutions(args.contradiction, args.graph_path)
    if args.format == "json":
        print(json.dumps({**result, "prior_resolutions": priors}, indent=2))
    else:
        print(render_text(result, priors))
    return 0


if __name__ == "__main__":
    sys.exit(main())
