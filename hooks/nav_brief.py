#!/usr/bin/env python3
"""
Navigator Intent-Brief Hook (TASK-56)

Claude Code hook that runs on UserPromptSubmit, scores the prompt for
ambiguity, and — when a task-shaped prompt scores at/above threshold —
instructs the model to render a one-screen INTENT BRIEF before implementing,
pre-filled from knowledge-graph memories relevant to the prompt.

Composes with hooks/workflow_enforcer.py (a sibling entry in plugin.json's
UserPromptSubmit array); this hook is deliberately read-only and non-blocking:

  - ALWAYS exits 0. Exit 2 on UserPromptSubmit blocks the prompt before the
    model runs (stderr reaches only the user), which would silently defeat
    a feature whose whole point is instructing the model. See mem-034.
  - Below threshold / question / confirmation / disabled -> prints nothing.
  - Memory recall degrades silently (missing graph, helper failure, timeout).

Input (from Claude Code):
    stdin JSON: {"prompt": "...", "cwd": "..."} for UserPromptSubmit

Output:
    stdout: NAV-BRIEF instruction block (surfaced into the model's context).
    exit 0 always.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# workflow_enforcer's blocked-stderr sentinel: Claude Code echoes blocked
# stderr into the next prompt's context; excise it before scoring so echoed
# instruction text can't fake a task-shaped prompt (mem-034).
NAV_BLOCK_PATTERN = re.compile(
    re.escape("<nav-workflow-block>") + r".*?" + re.escape("</nav-workflow-block>"),
    re.DOTALL,
)

RECALL_TIMEOUT = 3
RECALL_LIMIT = 5
DEFAULT_THRESHOLD = 0.5
DEFAULT_MEMORY_BUDGET = 1200
MAX_CONCEPTS = 8

CONCEPT_STOPWORDS = {
    "this", "that", "these", "those", "with", "from", "into", "onto",
    "over", "under", "about", "after", "before", "please", "then",
    "them", "they", "their", "have", "been", "will", "would", "should",
    "could", "make", "sure", "need", "want", "like", "some", "more",
    "when", "what", "where", "which", "until", "done", "everything",
}

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "nav-brief" / "functions"))

try:
    from ambiguity_scorer import score_ambiguity
except ImportError as exc:
    print(f"nav_brief: ambiguity_scorer import failed ({exc}); hook disabled this invocation.",
          file=sys.stderr)

    def score_ambiguity(prompt):
        return {"score": 0.0, "task_shaped": False,
                "undefined_dimensions": [], "matched_signals": []}


def read_stdin_payload() -> dict:
    """Read and parse the UserPromptSubmit stdin JSON exactly once.

    Mirrors workflow_enforcer.read_stdin_payload: {} when stdin absent/empty,
    {"prompt": raw} when the body is non-JSON text.
    """
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            raw = sys.stdin.read().strip()
            if raw:
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"prompt": raw}
    except Exception:
        pass
    return {}


def get_user_message(stdin_data: dict) -> str:
    prompt = stdin_data.get("prompt") or stdin_data.get("user_message") or ""
    if not prompt:
        prompt = os.environ.get("CLAUDE_USER_MESSAGE", "")
    if "<nav-workflow-block>" in prompt:
        prompt = NAV_BLOCK_PATTERN.sub("", prompt)
    return prompt


def _project_root(stdin_data: dict) -> Path:
    """Resolve the project root the same way every other Navigator hook does."""
    cwd = stdin_data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd)


def check_config(root: Path) -> dict:
    config_path = root / ".agent" / ".nav-config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _resolve_plugin_dir() -> Path | None:
    """Env var first (tests inject fakes this way), then file-relative."""
    env = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    here = Path(__file__).resolve().parent.parent
    if (here / "skills" / "nav-graph").is_dir():
        return here
    return None


def _extract_concepts(message: str) -> list:
    tokens = re.findall(r"[a-z][a-z\-_]{3,}", message.lower())
    concepts = []
    for token in tokens:
        if token in CONCEPT_STOPWORDS or token in concepts:
            continue
        concepts.append(token)
        if len(concepts) >= MAX_CONCEPTS:
            break
    return concepts


def _recall_memories(root: Path, message: str, budget: int) -> str:
    """Fetch relevant memories via memory_recall.py; empty string on any failure."""
    graph_path = root / ".agent" / "knowledge" / "graph.json"
    if not graph_path.is_file():
        return ""
    plugin_dir = _resolve_plugin_dir()
    if plugin_dir is None:
        return ""
    recall = plugin_dir / "skills" / "nav-graph" / "functions" / "memory_recall.py"
    if not recall.is_file():
        return ""
    concepts = _extract_concepts(message)
    if not concepts:
        return ""
    try:
        out = subprocess.run(
            [
                sys.executable, str(recall),
                "--concepts", ",".join(concepts),
                "--agent-dir", str(root / ".agent"),
                "--graph-path", str(graph_path),
                "--limit", str(RECALL_LIMIT),
                "--format", "compact",
            ],
            capture_output=True,
            text=True,
            timeout=RECALL_TIMEOUT,
        )
        if out.returncode != 0:
            return ""
        return (out.stdout or "").strip()[:budget]
    except Exception:
        return ""


def emit_brief_instruction(result: dict, threshold: float, memories: str):
    print(f"🧭 NAV-BRIEF: ambiguous task-shaped prompt "
          f"(score={result['score']}, threshold={threshold})")
    if result["undefined_dimensions"]:
        print(f"Undefined: {', '.join(result['undefined_dimensions'])}")
    print("")
    print("Render a one-screen INTENT BRIEF before writing any code:")
    print("  Goal | Scope | Approach | Limits | Verify | Won't do")
    print("Pre-fill defaults from the memories below when present. "
          "Max 2 open questions.")
    print("Wait for user confirmation before implementation. (skill: nav-brief)")
    if memories:
        print("")
        print("## Relevant Memories")
        print(memories)


def main():
    # Escape hatch for autonomous executors (e.g. PILOT): a dispatch loop has
    # no human to answer a brief's open questions, so interactive gating is
    # pure noise there. Parity with workflow_enforcer.py.
    if os.environ.get("PILOT_EXECUTOR"):
        sys.exit(0)

    stdin_data = read_stdin_payload()
    message = get_user_message(stdin_data)
    if not message:
        sys.exit(0)

    root = _project_root(stdin_data)
    config = check_config(root)
    brief_cfg = config.get("brief_hook", {})
    if brief_cfg.get("enabled", True) is False:
        sys.exit(0)
    threshold = float(brief_cfg.get("ambiguity_threshold", DEFAULT_THRESHOLD))
    budget = int(brief_cfg.get("memory_budget_chars", DEFAULT_MEMORY_BUDGET))

    result = score_ambiguity(message)
    if not result["task_shaped"] or result["score"] < threshold:
        sys.exit(0)

    memories = _recall_memories(root, message, budget)
    emit_brief_instruction(result, threshold, memories)
    sys.exit(0)


if __name__ == "__main__":
    main()
