#!/usr/bin/env python3
"""
Report parsing shared by ship_gate.py and report_to_graph.py (TASK-74).

The citation contract the writer, critic, patcher and gate all agree on:
- body citations are ``[n]`` (digits only) not followed by ``(``; ranges like
  ``[3-5]`` are forbidden; several cites are written ``[3][5]``; citations inside
  fenced code blocks are ignored
- ``## Sources`` is the last H2 and holds a table ``| n | id | title | url |``
  where ``id`` is the three-digit source note id (``sources/NNN.md``)
- ``## Key findings`` bullets are ``- (pattern|pitfall|decision|learning) text [n]``

The readable layout (reference/REPORT-FORMAT.md) adds two mechanical checks:
- ``## Summary`` opens with a ``**Answer:**`` line and carries at least two bullets
- no paragraph, blockquote, or single bullet before ``## Sources`` exceeds
  ``MAX_PARAGRAPH_CHARS``; tables, headings, and fenced code are exempt
"""

from __future__ import annotations

import re

CITE_RE = re.compile(r"\[(\d+)\](?!\()")
RANGE_RE = re.compile(r"\[\d+\s*[-–—]\s*\d+\]")
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
H2_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
FINDING_RE = re.compile(r"^-\s+\((pattern|pitfall|decision|learning)\)\s+(.+?)\s*$",
                        re.IGNORECASE)
REQUIRED_SECTIONS = ("Summary", "Key findings", "Open questions", "Sources")
# Mirrors source_store.LENSES; duplicated so report_parse stays import-free.
LENSES = ("breadth", "canonical", "adversarial", "gap")
UNSPECIFIED_LENS = "unspecified"
MEMORY_TYPES = ("pattern", "pitfall", "decision", "learning")
ANSWER_RE = re.compile(r"^\*\*Answer:?\*\*:?\s+\S", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
MAX_PARAGRAPH_CHARS = 700
MIN_SUMMARY_BULLETS = 2


def strip_code(text: str) -> str:
    return FENCE_RE.sub("", text or "")


def sections(text: str) -> dict[str, str]:
    """H2 title → body text (title matched case-insensitively by callers)."""
    out: dict[str, str] = {}
    matches = list(H2_RE.finditer(text or ""))
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        out[match.group(1).strip()] = text[match.end():end]
    return out


def find_section(text: str, title: str) -> str | None:
    for name, body in sections(text).items():
        if name.lower() == title.lower():
            return body
    return None


def body_without_sources(text: str) -> str:
    """Report text before the ## Sources heading (citations are counted here)."""
    match = re.search(r"^## +Sources\s*$", text or "", re.MULTILINE)
    return text[: match.start()] if match else (text or "")


def body_citations(text: str) -> list[int]:
    """Citation numbers in first-use order (code fences excluded)."""
    seen: list[int] = []
    for match in CITE_RE.finditer(strip_code(body_without_sources(text))):
        n = int(match.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def citation_ranges(text: str) -> list[str]:
    return RANGE_RE.findall(strip_code(body_without_sources(text)))


def sources_table(text: str) -> list[dict]:
    """Rows of the ## Sources table: [{n, id, title, url, lens}], in table order.

    The ``lens`` column (TASK-78) is optional: reports written before it, and rows
    whose value is not a known lens, come back as ``unspecified``.
    """
    body = find_section(text, "Sources") or ""
    rows = []
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        lens = cells[4].lower() if len(cells) > 4 else ""
        rows.append({"n": int(cells[0]), "id": cells[1], "title": cells[2],
                     "url": cells[3], "lens": lens if lens in LENSES else UNSPECIFIED_LENS})
    return rows


def key_findings(text: str) -> list[dict]:
    """[{type, text, cites:[n], raw}] from ## Key findings bullets; untyped bullets skipped."""
    body = find_section(text, "Key findings") or ""
    out = []
    for item in bullet_items(body):
        match = FINDING_RE.match(item)
        if not match:
            continue
        mtype, rest = match.group(1).lower(), match.group(2)
        cites = [int(n) for n in CITE_RE.findall(rest)]
        clean = " ".join(CITE_RE.sub("", rest).split())
        clean = re.sub(r"\s+([.,;:])", r"\1", clean)  # "one [1]." -> "one." not "one ."
        out.append({"type": mtype, "text": clean, "cites": cites, "raw": item})
    return out


def bullet_items(body: str) -> list[str]:
    """Top-level ``- `` bullets with their wrapped continuation lines joined by a space.

    Writers wrap long bullets at ~90 columns, so a finding's citation often sits on an
    indented continuation line; parsing line by line dropped those cites (TASK-77).
    """
    items: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped)
        elif stripped and line[:1].isspace() and items:
            items[-1] = f"{items[-1]} {stripped}"
    return items


def untyped_findings(text: str) -> list[str]:
    body = find_section(text, "Key findings") or ""
    return [line.strip() for line in body.splitlines()
            if line.strip().startswith("- ") and not FINDING_RE.match(line.strip())]


def summary_structure(text: str) -> dict:
    """{has_answer, bullets} for the ## Summary section (missing section → zeros)."""
    body = find_section(text, "Summary") or ""
    lines = [line.strip() for line in body.splitlines()]
    return {
        "has_answer": any(ANSWER_RE.match(line) for line in lines),
        "bullets": sum(1 for line in lines if BULLET_RE.match(line)),
    }


def paragraphs(text: str) -> list[dict]:
    """Prose blocks before ## Sources: [{section, chars, head}].

    A block is a run of non-blank lines; each bullet item starts its own block so a
    list is measured item by item. Headings, table rows, and fenced code are skipped.
    ``section`` is the enclosing H2 title, or ``(header)`` before the first H2.
    """
    out: list[dict] = []
    section = "(header)"
    block: list[str] = []

    def flush() -> None:
        if block:
            joined = " ".join(line.strip() for line in block)
            out.append({"section": section, "chars": len(joined), "head": joined[:60]})
            block.clear()

    for line in strip_code(body_without_sources(text)).splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("#"):
            flush()
            match = H2_RE.match(stripped)
            if match:
                section = match.group(1).strip()
            continue
        if stripped.startswith("|"):
            flush()
            continue
        if BULLET_RE.match(line):
            flush()
        block.append(line)
    flush()
    return out


def long_paragraphs(text: str, limit: int = MAX_PARAGRAPH_CHARS) -> list[dict]:
    return [p for p in paragraphs(text) if p["chars"] > limit]
