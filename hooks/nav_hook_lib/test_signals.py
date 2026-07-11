#!/usr/bin/env python3
"""Unit tests for nav_hook_lib/signals.py (nav-signal v3 + pilot-signal v2 compat).

stdlib unittest only (pytest not installed). Covers:

  - emit() -> parse() round-trip for all five v3 types, incl. CRLF documents.
  - pilot-signal v2 acceptance: fixtures frozen from the LIVE output of
    skills/nav-loop/functions/status_generator.py and the exit grammar in
    skills/nav-loop/SKILL.md; normalization to v3 dicts.
  - The vendored Pilot extraction regex (the frozen external contract from
    test_status_generator.py / TASK-64) round-trips our v2 fixture, and the
    CRLF adversarial case that defeats the strict Pilot regex still parses
    through signals.parse().
  - Per-channel helpers for spike-proven channels only (mem-050..055).
"""

import json
import re
import unittest

import signals

# Vendored Pilot extraction regex — Pilot's frozen external contract
# (skills/nav-loop/functions/test_status_generator.py, TASK-64 Verify).
PILOT_V2_REGEX = re.compile(r"```pilot-signal\n(.+?)\n```", re.DOTALL)

# Byte-frozen from a live run of status_generator.py (2026-07-10):
#   --phase VERIFY --iteration 3 --max-iterations 5
#   --indicators '{"code_committed": true, "tests_passing": true,
#                  "docs_updated": false}' --exit-signal absent
V2_STATUS_JSON = (
    '{"v": 2, "type": "status", "phase": "VERIFY", "progress": 91, '
    '"iteration": 3, "max_iterations": 5, "indicators": {"code_committed": true, '
    '"tests_passing": true, "docs_updated": false}, "exit_signal": false}'
)
V2_STATUS_BLOCK = f"```pilot-signal\n{V2_STATUS_JSON}\n```"

# The documented exit grammar (skills/nav-loop/SKILL.md "Setting EXIT_SIGNAL").
V2_EXIT_JSON = '{"v":2,"type":"exit","success":true,"reason":"All criteria met"}'
V2_EXIT_BLOCK = f"```pilot-signal\n{V2_EXIT_JSON}\n```"


class EmitTest(unittest.TestCase):
    def test_emit_is_single_line_with_prefix(self):
        line = signals.emit("exit", success=True, reason="done")
        self.assertNotIn("\n", line)
        self.assertTrue(line.startswith(signals.V3_PREFIX))

    def test_emit_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            signals.emit("shutdown", reason="nope")

    def test_emit_rejects_reserved_fields(self):
        with self.assertRaises(ValueError):
            signals.emit("status", type="exit")
        with self.assertRaises(ValueError):
            signals.emit("status", v=2)

    def test_emit_is_deterministic(self):
        a = signals.emit("status", phase="IMPL", progress=50)
        b = signals.emit("status", progress=50, phase="IMPL")
        self.assertEqual(a, b)


class RoundTripTest(unittest.TestCase):
    CASES = {
        "exit": {"success": True, "reason": "All criteria met"},
        "status": {"phase": "VERIFY", "progress": 91, "iteration": 3,
                   "indicators": {"tests_passing": True}},
        "check": {"loop_trigger": False, "complexity": 0.3, "mode": "DIRECT"},
        "brief": {"score": 0.7, "confirmed": False},
        "defer": {"skill": "frontend-component", "confidence": 0.95},
    }

    def test_emit_parse_round_trip_all_types(self):
        for sig_type, fields in self.CASES.items():
            with self.subTest(sig_type=sig_type):
                parsed = signals.parse(signals.emit(sig_type, **fields))
                expected = {"v": 3, "type": sig_type}
                expected.update(fields)
                self.assertEqual(parsed, [expected])

    def test_round_trip_embedded_in_prose(self):
        doc = (
            "Iteration 3 complete. All requirements met.\n\n"
            + signals.emit("exit", success=True, reason="done")
            + "\n\nEXIT_SIGNAL: true\n"
        )
        parsed = signals.parse(doc)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["type"], "exit")
        self.assertTrue(parsed[0]["success"])

    def test_round_trip_crlf_document(self):
        line = signals.emit("status", phase="IMPL", progress=50)
        doc = "NAVIGATOR_STATUS\r\n" + line + "\r\nStagnation: 1/3\r\n"
        parsed = signals.parse(doc)
        self.assertEqual(parsed, [{"v": 3, "type": "status", "phase": "IMPL", "progress": 50}])

    def test_indented_v3_line_parses(self):
        parsed = signals.parse("  " + signals.emit("brief", score=0.7))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["type"], "brief")

    # TASK-70: GFM hides HTML comments in assistant output (verified live
    # 2026-07-11), so a comment-wrapped signal is the user-invisible channel.
    def test_html_comment_wrapped_v3_line_parses(self):
        doc = "All done.\n\n<!-- " + signals.emit("exit", reason="finished") + " -->\n"
        parsed = signals.parse(doc)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["type"], "exit")
        self.assertEqual(parsed[0]["reason"], "finished")

    def test_comment_wrapped_tolerates_spacing_and_indent(self):
        line = signals.emit("exit", success=True)
        for doc in (
            "<!--" + line + "-->",
            "   <!--  " + line + "  -->  ",
            "<!-- " + line + " -->\r\n",
        ):
            parsed = signals.parse(doc)
            self.assertEqual(len(parsed), 1, repr(doc))
            self.assertEqual(parsed[0]["type"], "exit", repr(doc))

    def test_open_comment_without_close_still_parses(self):
        # Defensive: a truncated wrapper must not hide a genuine exit signal.
        parsed = signals.parse("<!-- " + signals.emit("exit"))
        self.assertEqual(len(parsed), 1)

    def test_comment_on_shared_line_with_prose_is_not_a_signal(self):
        # The signal must own its line — prose before the comment disqualifies.
        doc = "done <!-- " + signals.emit("exit") + " -->"
        self.assertEqual(signals.parse(doc), [])


class PilotV2CompatTest(unittest.TestCase):
    def test_vendored_pilot_regex_round_trips_status_fixture(self):
        # The frozen Pilot contract must extract exactly the JSON we froze.
        match = PILOT_V2_REGEX.search(V2_STATUS_BLOCK)
        self.assertIsNotNone(match, "pilot-signal block not found by Pilot regex")
        self.assertEqual(json.loads(match.group(1)), json.loads(V2_STATUS_JSON))

    def test_v2_status_normalizes_to_v3(self):
        doc = "NAVIGATOR_STATUS\n==========\nPhase: VERIFY\n\n" + V2_STATUS_BLOCK
        parsed = signals.parse(doc)
        self.assertEqual(len(parsed), 1)
        sig = parsed[0]
        self.assertEqual(sig["v"], 3)
        self.assertEqual(sig["type"], "status")
        self.assertEqual(sig["phase"], "VERIFY")
        self.assertEqual(sig["progress"], 91)
        self.assertEqual(sig["iteration"], 3)
        self.assertEqual(sig["max_iterations"], 5)
        self.assertEqual(sig["indicators"]["docs_updated"], False)
        self.assertFalse(sig["exit_signal"])

    def test_v2_exit_normalizes_to_v3(self):
        parsed = signals.parse(V2_EXIT_BLOCK)
        self.assertEqual(
            parsed,
            [{"v": 3, "type": "exit", "success": True, "reason": "All criteria met"}],
        )

    def test_v2_crlf_adversarial_case(self):
        # CRLF line endings defeat Pilot's strict \n regex but MUST still
        # parse through signals.parse() (TASK-64 adversarial case).
        crlf_block = V2_EXIT_BLOCK.replace("\n", "\r\n")
        self.assertIsNone(PILOT_V2_REGEX.search(crlf_block))
        parsed = signals.parse(crlf_block)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["type"], "exit")
        self.assertTrue(parsed[0]["success"])

    def test_mixed_v2_and_v3_document_order(self):
        doc = (
            V2_STATUS_BLOCK
            + "\n\nwork continues...\n"
            + signals.emit("exit", success=True, reason="wrapped up")
            + "\n"
        )
        parsed = signals.parse(doc)
        self.assertEqual([sig["type"] for sig in parsed], ["status", "exit"])
        self.assertEqual([sig["v"] for sig in parsed], [3, 3])


class ParseRobustnessTest(unittest.TestCase):
    def test_empty_and_none_input(self):
        self.assertEqual(signals.parse(""), [])
        self.assertEqual(signals.parse(None), [])

    def test_plain_text_yields_nothing(self):
        self.assertEqual(signals.parse("EXIT_SIGNAL: true\nPhase: VERIFY"), [])

    def test_malformed_json_skipped_silently(self):
        self.assertEqual(signals.parse("nav-signal:v3:{not json}"), [])
        self.assertEqual(signals.parse("```pilot-signal\n{broken\n```"), [])

    def test_unknown_type_skipped(self):
        self.assertEqual(signals.parse('nav-signal:v3:{"type":"shutdown"}'), [])
        self.assertEqual(
            signals.parse('```pilot-signal\n{"v":2,"type":"heartbeat"}\n```'), [])

    def test_non_dict_payload_skipped(self):
        self.assertEqual(signals.parse('nav-signal:v3:{"type"}'), [])
        self.assertEqual(signals.parse("```pilot-signal\n[1, 2, 3]\n```"), [])

    def test_trailing_text_after_json_is_not_a_signal(self):
        self.assertEqual(signals.parse('nav-signal:v3:{"type":"exit"} trailing words'), [])


class ChannelHelpersTest(unittest.TestCase):
    def test_stop_block_shape(self):
        payload = json.loads(signals.stop_block("finish the docs update"))
        self.assertEqual(payload, {"decision": "block", "reason": "finish the docs update"})

    def test_prompt_block_shape(self):
        payload = json.loads(signals.prompt_block("served deterministically"))
        self.assertEqual(payload, {"decision": "block", "reason": "served deterministically"})

    def test_additional_context_proven_events(self):
        for event in ("SessionStart", "SubagentStart", "PostToolUse", "PostToolUseFailure"):
            with self.subTest(event=event):
                payload = json.loads(signals.additional_context(event, "fact: build is green"))
                hso = payload["hookSpecificOutput"]
                self.assertEqual(hso["hookEventName"], event)
                self.assertEqual(hso["additionalContext"], "fact: build is green")
                self.assertNotIn("permissionDecision", hso)

    def test_additional_context_pretooluse_rejected(self):
        # FIX 2 (TASK-59 adversarial review): the only proven PreToolUse shape
        # (mem-054) bundles permissionDecision:'allow' — a silent tool-call
        # auto-approval no v7 op needs. PreToolUse must raise like any other
        # unproven event until a permission-clean shape is probed.
        with self.assertRaises(ValueError):
            signals.additional_context("PreToolUse", "fact: cache warmed")

    def test_additional_context_rejects_unproven_events(self):
        for event in ("Notification", "Stop", "UserPromptSubmit", "PreCompact", "PreToolUse"):
            with self.subTest(event=event):
                with self.assertRaises(ValueError):
                    signals.additional_context(event, "text")

    def test_additional_context_never_emits_permission_decision(self):
        # The permissionDecision emission existed only for PreToolUse; with
        # that event removed, NO event may carry permission side effects.
        for event in signals._ADDITIONAL_CONTEXT_EVENTS:
            with self.subTest(event=event):
                payload = json.loads(signals.additional_context(event, "fact"))
                self.assertNotIn("permissionDecision", payload["hookSpecificOutput"])
                self.assertNotIn("permissionDecisionReason", payload["hookSpecificOutput"])
        self.assertNotIn("PreToolUse", signals._ADDITIONAL_CONTEXT_EVENTS)

    def test_user_prompt_context_passthrough(self):
        text = "NAV-BRIEF: render the intent brief before writing code"
        self.assertEqual(signals.user_prompt_context(text), text)

    def test_no_pretooluse_stdout_helper_exists(self):
        # mem-054: PreToolUse plain stdout is DEAD — the helper must not exist.
        for name in ("pre_tool_use_stdout", "pretooluse_stdout", "tool_stdout"):
            self.assertFalse(hasattr(signals, name), name)


if __name__ == "__main__":
    unittest.main()
