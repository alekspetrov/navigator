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
"""

from __future__ import annotations

import re

CITE_RE = re.compile(r"\[(\d+)\](?!\()")
RANGE_RE = re.compile(r"\[\d+\s*[-–—]\s*\d+\]")
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
H2_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
FINDING_RE = re.compile(r"^-\s+\((pattern|pitfall|decision|learning)\)\s+(.+?)\s*$",
                        re.IGNORECASE)
REQUIRED_SECTIONS = ("Summary", "Key findings", "Sources")
MEMORY_TYPES = ("pattern", "pitfall", "decision", "learning")


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
    """Rows of the ## Sources table: [{n, id, title, url}], in table order."""
    body = find_section(text, "Sources") or ""
    rows = []
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        rows.append({"n": int(cells[0]), "id": cells[1], "title": cells[2],
                     "url": cells[3]})
    return rows


def key_findings(text: str) -> list[dict]:
    """[{type, text, cites:[n], raw}] from ## Key findings bullets; untyped bullets skipped."""
    body = find_section(text, "Key findings") or ""
    out = []
    for line in body.splitlines():
        match = FINDING_RE.match(line.strip())
        if not match:
            continue
        mtype, rest = match.group(1).lower(), match.group(2)
        cites = [int(n) for n in CITE_RE.findall(rest)]
        clean = " ".join(CITE_RE.sub("", rest).split())
        out.append({"type": mtype, "text": clean, "cites": cites, "raw": line.strip()})
    return out


def untyped_findings(text: str) -> list[str]:
    body = find_section(text, "Key findings") or ""
    return [line.strip() for line in body.splitlines()
            if line.strip().startswith("- ") and not FINDING_RE.match(line.strip())]
