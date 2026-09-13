#!/usr/bin/env python3
"""Tests for agent_tool_counts.py (TASK-76): per-request usage dedup, tool counts."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import agent_tool_counts as atc


def _assistant(request_id, usage, content, ts="2026-09-13T10:00:00Z"):
    return {"type": "assistant", "requestId": request_id, "timestamp": ts,
            "message": {"role": "assistant", "usage": usage, "content": content}}


def _usage(inp, out, creation=0, read=0):
    return {"input_tokens": inp, "output_tokens": out,
            "cache_creation_input_tokens": creation, "cache_read_input_tokens": read}


READ_A = {"type": "tool_use", "name": "Read", "input": {"file_path": "/repo/a.py"}}
LINES = [
    json.dumps({"type": "user", "message": {"role": "user", "content": "q"}}),
    # one API response, two JSONL lines: input/cache repeat, output grows on the last block
    json.dumps(_assistant("r1", _usage(100, 1, creation=50, read=10),
                          [{"type": "thinking", "thinking": "..."}])),
    json.dumps(_assistant("r1", _usage(100, 400, creation=50, read=10),
                          [{"type": "tool_use", "name": "LSP",
                            "input": {"operation": "findReferences", "filePath": "/repo/a.py"}}])),
    json.dumps(_assistant("r2", _usage(20, 5), [READ_A])),
    json.dumps(_assistant("r3", _usage(30, 7), [READ_A, {"type": "tool_use", "name": "Grep",
                                                          "input": {"pattern": "x"}}],
                          ts="2026-09-13T10:01:00Z")),
    "{not json",
]


class CountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "agent-1.jsonl"
        self.path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
        self.result = atc.count(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_tool_counts_by_name(self):
        self.assertEqual(self.result["tools"], {"LSP": 1, "Read": 2, "Grep": 1})
        self.assertEqual(self.result["lsp_ops"], {"findReferences": 1})
        self.assertEqual(self.result["read_distinct_paths"], 1)

    def test_usage_counted_once_per_request(self):
        self.assertEqual(self.result["requests"], 3)
        self.assertEqual(self.result["usage"]["input_tokens"], 150)      # not 250 (per-line)
        self.assertEqual(self.result["usage"]["output_tokens"], 412)     # max of r1 = 400
        self.assertEqual(self.result["usage"]["cache_creation_input_tokens"], 50)
        self.assertEqual(self.result["fresh_input"], 200)

    def test_span_and_undecodable_line_tolerated(self):
        self.assertEqual(self.result["first_ts"], "2026-09-13T10:00:00Z")
        self.assertEqual(self.result["last_ts"], "2026-09-13T10:01:00Z")

    def test_text_output_mentions_lsp_ops(self):
        text = atc.format_text(self.result)
        self.assertIn("findReferences x1", text)
        self.assertIn("Read distinct paths: 1", text)


class HelperTests(unittest.TestCase):
    def test_lsp_op_unknown_input(self):
        self.assertEqual(atc.lsp_op({"path": "/x"}), "?")
        self.assertEqual(atc.lsp_op(None), "?")

    def test_latest_subagent_picks_newest_by_mtime(self):
        with tempfile.TemporaryDirectory() as root:
            project = Path(root) / "proj.dir"
            project.mkdir()
            encoded = str(project.resolve()).translate(str.maketrans("/.", "--"))
            sub = Path(root) / "projects" / encoded / "sess" / "subagents"
            sub.mkdir(parents=True)
            old, new = sub / "agent-old.jsonl", sub / "agent-new.jsonl"
            old.write_text("{}\n")
            new.write_text("{}\n")
            os.utime(old, (1, 1))
            found = atc.latest_subagent(project, projects_root=Path(root) / "projects")
            self.assertEqual(found, new)
            self.assertIsNone(atc.latest_subagent(Path(root) / "missing",
                                                  projects_root=Path(root) / "projects"))


if __name__ == "__main__":
    unittest.main()
