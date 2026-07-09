#!/usr/bin/env python3
"""
Ambiguity scorer for nav-brief (TASK-56).

Scores a user prompt for AMBIGUITY — a third axis, distinct from the two
complexity scorers (workflow_detector.py, complexity_detector.py), which
TASK-48 deliberately kept separate. A small task can be highly ambiguous
("fix the bug") while a large one can be fully specified.

Pure function, stdlib only, no I/O, no config: the caller (hooks/nav_brief.py)
applies its own threshold. All phrase matching is word-boundary regex —
substring matching caused the TASK-48 false-positive class.

Scoring model:
  gates:   questions and short confirmations -> 0.0, task_shaped=False
  base:    0.5 when a task-shaped verb is present (else 0.0, not task-shaped)
  bonus:   +0.2 vague-scope signal ("the api", bare plural nouns), once
  credits: file path -0.4, number -0.2, limiter word -0.2,
           acceptance-criteria phrase -0.3 (each counted once, all stack)
  result:  clamp to [0.0, 1.0], round to 2 decimals
"""

import re

QUESTION_STARTERS = {
    "what", "why", "how", "when", "where", "who", "which",
    "can", "could", "should", "is", "are", "do", "does", "did",
    "will", "would",
}

CONFIRMATION_PREFIXES = [
    "yes", "ok", "okay", "sure", "sounds good", "go ahead", "proceed",
    "continue", "looks good", "lgtm", "do it", "correct", "confirmed",
    "approved", "agreed", "that's right", "that's correct",
    "no", "nope", "cancel", "stop",
]
CONFIRMATION_MAX_WORDS = 6

TASK_SHAPED_VERBS = [
    "add", "create", "build", "implement", "refactor", "fix", "update",
    "change", "improve", "enhance", "redesign", "migrate", "integrate",
    "optimize", "rewrite", "replace", "remove", "delete", "write",
    "design", "develop", "extend", "generate", "configure",
    "set up", "clean up",
]

VAGUE_SCOPE_SIGNALS = [
    "the app", "the system", "the api", "the codebase", "the platform",
    "the backend", "the frontend", "the ui", "the project", "the entire",
    "everything", "all of it", "the whole thing",
    "endpoints", "components", "tests", "files", "bugs", "issues", "features",
]

LIMITER_WORDS = [
    "only", "just", "specifically", "excluding", "except",
    "up to", "no more than", "limit to", "solely",
]

ACCEPTANCE_PHRASES = [
    "acceptance criteria", "when done", "success looks like",
    "verify with", "verify that", "done when", "definition of done",
]

APPROACH_CONNECTORS = ["using", "via", "with", "through", "by using", "based on"]

PATH_RE = re.compile(r"[\w.\-]+/[\w.\-/]+")
FILE_RE = re.compile(
    r"\b[\w\-]+\.(?:py|ts|tsx|js|jsx|md|json|yaml|yml|go|rb|java|rs|css|html)\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
WORD_RE = re.compile(r"[a-z']+")

BASE_SCORE = 0.5
VAGUE_BONUS = 0.2
CREDIT_FILE_PATH = 0.4
CREDIT_NUMBER = 0.2
CREDIT_LIMITER = 0.2
CREDIT_ACCEPTANCE = 0.3


def _contains_phrase(text: str, phrase: str) -> bool:
    """Word-boundary match; multiword phrases tolerate any whitespace run."""
    pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text) is not None


def _first_match(text: str, phrases: list) -> str:
    for phrase in phrases:
        if _contains_phrase(text, phrase):
            return phrase
    return ""


def _is_question(text: str) -> bool:
    if text.rstrip().endswith("?"):
        return True
    words = WORD_RE.findall(text)
    return bool(words) and words[0] in QUESTION_STARTERS


def _is_confirmation(text: str) -> bool:
    words = WORD_RE.findall(text)
    if not words or len(words) > CONFIRMATION_MAX_WORDS:
        return False
    normalized = " ".join(words)
    for phrase in CONFIRMATION_PREFIXES:
        bare = " ".join(WORD_RE.findall(phrase))
        if normalized == bare or normalized.startswith(bare + " "):
            return True
    return False


def _has_file_reference(text: str) -> bool:
    return bool(PATH_RE.search(text) or FILE_RE.search(text))


def score_ambiguity(prompt: str) -> dict:
    """Score a prompt's ambiguity.

    Returns {"score": float, "task_shaped": bool,
             "undefined_dimensions": [str], "matched_signals": [str]}.
    Deterministic: same input always produces the same output.
    """
    empty = {
        "score": 0.0,
        "task_shaped": False,
        "undefined_dimensions": [],
        "matched_signals": [],
    }
    text = (prompt or "").lower().strip()
    if not text:
        return empty

    if _is_question(text):
        return {**empty, "matched_signals": ["gate:question"]}
    if _is_confirmation(text):
        return {**empty, "matched_signals": ["gate:confirmation"]}

    verb = _first_match(text, TASK_SHAPED_VERBS)
    if not verb:
        return empty

    signals = [f"verb:{verb}"]
    score = BASE_SCORE

    vague = _first_match(text, VAGUE_SCOPE_SIGNALS)
    if vague:
        score += VAGUE_BONUS
        signals.append(f"vague:{vague}")

    has_file = _has_file_reference(prompt)  # original case: paths matter
    has_number = bool(NUMBER_RE.search(text))
    limiter = _first_match(text, LIMITER_WORDS)
    acceptance = _first_match(text, ACCEPTANCE_PHRASES)
    approach = _first_match(text, APPROACH_CONNECTORS)

    if has_file:
        score -= CREDIT_FILE_PATH
        signals.append("credit:file_path")
    if has_number:
        score -= CREDIT_NUMBER
        signals.append("credit:number")
    if limiter:
        score -= CREDIT_LIMITER
        signals.append(f"credit:limiter:{limiter}")
    if acceptance:
        score -= CREDIT_ACCEPTANCE
        signals.append(f"credit:acceptance:{acceptance}")

    undefined = []
    if not has_file:
        undefined.append("scope")
    if not limiter and not acceptance:
        undefined.append("limits")
    if not approach:
        undefined.append("approach")
    if not acceptance:
        undefined.append("verification")

    return {
        "score": round(max(0.0, min(1.0, score)), 2),
        "task_shaped": True,
        "undefined_dimensions": undefined,
        "matched_signals": signals,
    }
