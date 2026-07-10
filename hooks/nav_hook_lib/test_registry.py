#!/usr/bin/env python3
"""Unit tests for nav_hook_lib/registry.py (TASK-60 Phase 2).

stdlib unittest only. Covers:

  - EVENT_OPS keys are EXACTLY the seven v6 manifest event surfaces.
  - OpSpec is a dataclass with exactly the five contract fields
    (name, phase, matcher, config_key, budget_ms), every field populated
    with the right type on every live row.
  - Phases are valid PHASE_ORDER values and each event's ops are listed in
    non-decreasing phase order (registry order IS merge order).
  - config_key per row names an EXISTING v6 toggle block: verified against
    the pristine fixture fixtures/nav-config-v6.18.1.json, with the exact
    block names quoted here (session_start_hook, workflow_enforcer_hook,
    brief_hook, read_guard_hook, task_graph_sync_hook, profile_sync_hook,
    workflow_state_hook, compact_hook), each carrying an 'enabled' key so
    the runtime's <config_key>.enabled gate resolves.
  - Matcher regexes compile; the contract matchers behave ('Read',
    'Edit|Write|MultiEdit|NotebookEdit').
  - Spike-gated TASK-62 ops are NOT live OpSpecs, but each is documented in
    a registry comment together with its mem-05x verdict.
  - registry.py stays pure data: no op imports, no I/O modules.
"""

import ast
import json
import re
import sys
import unittest
from dataclasses import fields, is_dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import registry  # noqa: E402  (sibling import; path pinned above)

LIB_DIR = Path(__file__).resolve().parent
FIXTURE = LIB_DIR / "fixtures" / "nav-config-v6.18.1.json"
OPS_DIR = LIB_DIR.parent / "ops"

# The seven v6 manifest event surfaces (TASK-60: new events belong to TASK-62).
V6_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "PreCompact",
    "PostCompact",
}

# The eight TASK-61 rows: expected op names, in order, per event.
EXPECTED_ROWS = {
    "SessionStart": ["session_start"],
    "UserPromptSubmit": ["prompt_gate", "prompt_brief"],
    "PreToolUse": ["read_guard"],
    "PostToolUse": ["graph_sync", "profile_sync"],
    "Stop": ["stop_state"],
    "PreCompact": ["compact_marker"],
    "PostCompact": ["compact_marker"],
}

# op name -> the EXACT v6 toggle block name in .agent/.nav-config.json.
EXPECTED_CONFIG_KEYS = {
    "session_start": "session_start_hook",
    "prompt_gate": "workflow_enforcer_hook",
    "prompt_brief": "brief_hook",
    "read_guard": "read_guard_hook",
    "graph_sync": "task_graph_sync_hook",
    "profile_sync": "profile_sync_hook",
    "stop_state": "workflow_state_hook",
    "compact_marker": "compact_hook",
}

EXPECTED_PHASES = {
    "session_start": "injectors",
    "prompt_gate": "gates",
    "prompt_brief": "injectors",
    "read_guard": "gates",
    "graph_sync": "recorders",
    "profile_sync": "recorders",
    "stop_state": "recorders",
    "compact_marker": "recorders",
}

MUTATING_MATCHER = "Edit|Write|MultiEdit|NotebookEdit"

# Manifest timeouts per TASK-60 (runtime.EVENT_TIMEOUTS mirrors these; hardcoded
# here rather than imported — runtime.py is owned by a parallel task group).
# PostToolUse/PostCompact carry the v6 10s allowances (no 5s regression).
EVENT_TIMEOUT_SECONDS = {
    "SessionStart": 10, "PostToolUse": 10, "PreCompact": 30, "PostCompact": 10,
}
DEFAULT_TIMEOUT_SECONDS = 5

# TASK-62 spike-gated ops: comments only, each citing its verdict memory.
# config_guard has no spike dependency in the routing matrix — no mem required.
FUTURE_OPS_MEM = {
    "prompt_tier1": "mem-053",
    "stop_completion": "mem-051",
    "jit_memory": "mem-050",
    "failure_diagnosis": "mem-050",
    "subagent_context": "mem-052",
    "config_guard": None,
    "setup": "mem-055",
}


def _all_specs():
    for event in registry.EVENT_OPS:
        for spec in registry.EVENT_OPS[event]:
            yield event, spec


class EventSurfaceTest(unittest.TestCase):
    def test_events_are_exactly_the_seven_v6_surfaces(self):
        self.assertEqual(set(registry.EVENT_OPS), V6_EVENTS)
        self.assertEqual(set(registry.EVENTS), V6_EVENTS)

    def test_every_event_has_at_least_one_op(self):
        for event, ops in registry.EVENT_OPS.items():
            self.assertIsInstance(ops, list, event)
            self.assertGreater(len(ops), 0, f"{event} has no ops")

    def test_expected_rows_in_order(self):
        for event, expected in EXPECTED_ROWS.items():
            names = [spec.name for spec in registry.EVENT_OPS[event]]
            self.assertEqual(names, expected, f"row mismatch for {event}")


class OpSpecShapeTest(unittest.TestCase):
    def test_opspec_is_a_dataclass_with_exactly_the_five_contract_fields(self):
        self.assertTrue(is_dataclass(registry.OpSpec))
        names = [f.name for f in fields(registry.OpSpec)]
        self.assertEqual(names, ["name", "phase", "matcher", "config_key", "budget_ms"])

    def test_every_field_populated_with_correct_type(self):
        for event, spec in _all_specs():
            where = f"{event}/{spec.name}"
            self.assertIsInstance(spec.name, str, where)
            self.assertTrue(spec.name, where)
            self.assertTrue(spec.name.isidentifier(), f"{where}: name must be a module name")
            self.assertIsInstance(spec.phase, str, where)
            self.assertIn(spec.phase, registry.PHASE_ORDER, where)
            self.assertTrue(
                spec.matcher is None or isinstance(spec.matcher, str), where
            )
            if isinstance(spec.matcher, str):
                self.assertTrue(spec.matcher, f"{where}: matcher must be None or non-empty")
            self.assertIsInstance(spec.config_key, str, where)
            self.assertTrue(spec.config_key, where)
            self.assertIsInstance(spec.budget_ms, int, where)
            self.assertNotIsInstance(spec.budget_ms, bool, where)
            self.assertGreater(spec.budget_ms, 0, where)


class PhaseTest(unittest.TestCase):
    def test_phase_order_constant(self):
        self.assertEqual(
            registry.PHASE_ORDER, ("gates", "responders", "injectors", "recorders")
        )

    def test_expected_phase_per_op(self):
        for event, spec in _all_specs():
            self.assertEqual(
                spec.phase, EXPECTED_PHASES[spec.name], f"{event}/{spec.name}"
            )

    def test_ops_listed_in_phase_order_within_each_event(self):
        # Registry order is merge order; it must never contradict phase order.
        rank = {phase: i for i, phase in enumerate(registry.PHASE_ORDER)}
        for event, ops in registry.EVENT_OPS.items():
            ranks = [rank[spec.phase] for spec in ops]
            self.assertEqual(ranks, sorted(ranks), f"{event} ops out of phase order")


class ConfigKeyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert FIXTURE.is_file(), f"missing fixture: {FIXTURE}"
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_config_key_matches_expected_v6_block_per_op(self):
        for event, spec in _all_specs():
            self.assertEqual(
                spec.config_key,
                EXPECTED_CONFIG_KEYS[spec.name],
                f"{event}/{spec.name}",
            )

    def test_every_config_key_is_a_block_in_the_v6_fixture(self):
        for event, spec in _all_specs():
            where = f"{event}/{spec.name}: {spec.config_key}"
            self.assertIn(spec.config_key, self.fixture, where)
            self.assertIsInstance(self.fixture[spec.config_key], dict, where)

    def test_every_config_key_block_has_an_enabled_toggle(self):
        # The runtime gates ops on config.get(cfg, key + '.enabled', True);
        # every mapped block must actually carry the toggle in v6.18.1.
        for event, spec in _all_specs():
            block = self.fixture[spec.config_key]
            self.assertIn(
                "enabled", block, f"{event}/{spec.name}: {spec.config_key}.enabled"
            )
            self.assertIsInstance(block["enabled"], bool, spec.config_key)


class MatcherTest(unittest.TestCase):
    def test_all_matchers_compile(self):
        for event, spec in _all_specs():
            if spec.matcher is not None:
                try:
                    re.compile(spec.matcher)
                except re.error as exc:
                    self.fail(f"{event}/{spec.name}: matcher does not compile: {exc}")

    def test_matcher_values_match_the_contract(self):
        expected = {
            "read_guard": "Read",
            "graph_sync": MUTATING_MATCHER,
            "profile_sync": MUTATING_MATCHER,
        }
        for event, spec in _all_specs():
            self.assertEqual(
                spec.matcher, expected.get(spec.name), f"{event}/{spec.name}"
            )

    def test_mutating_matcher_hits_all_four_tools_and_not_bash(self):
        pattern = re.compile(MUTATING_MATCHER)
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            self.assertTrue(pattern.search(tool), tool)
        self.assertIsNone(pattern.search("Bash"))
        self.assertIsNone(pattern.search("Read"))

    def test_module_constant_matches_registry_rows(self):
        self.assertEqual(registry.MUTATING_TOOLS, MUTATING_MATCHER)


class BudgetSanityTest(unittest.TestCase):
    def test_per_event_budgets_fit_under_the_soft_deadline(self):
        # Soft deadline = manifest timeout - 500ms. The advisory op budgets
        # for one event must collectively fit under it, or they are lies.
        for event, ops in registry.EVENT_OPS.items():
            timeout_s = EVENT_TIMEOUT_SECONDS.get(event, DEFAULT_TIMEOUT_SECONDS)
            deadline_ms = timeout_s * 1000 - 500
            total = sum(spec.budget_ms for spec in ops)
            self.assertLessEqual(
                total, deadline_ms,
                f"{event}: op budgets {total}ms exceed soft deadline {deadline_ms}ms",
            )


class FutureRowsTest(unittest.TestCase):
    """Spike-gated TASK-62 rows: comments with verdicts, never live OpSpecs."""

    @classmethod
    def setUpClass(cls):
        cls.source = Path(registry.__file__).read_text(encoding="utf-8")

    def test_future_ops_are_not_live_opspecs(self):
        live = {spec.name for _, spec in _all_specs()}
        overlap = live & set(FUTURE_OPS_MEM)
        self.assertEqual(
            overlap, set(),
            f"TASK-62 ops registered as live OpSpecs in TASK-60: {sorted(overlap)}",
        )

    def test_future_ops_documented_in_comments_with_mem_verdicts(self):
        for op_name, mem_id in FUTURE_OPS_MEM.items():
            self.assertIn(op_name, self.source, f"missing TASK-62 comment row: {op_name}")
            if mem_id is None:
                continue
            # The verdict memory must be cited on the same comment block as
            # the op name (within a few lines of its first mention).
            idx = self.source.index(op_name)
            window = self.source[idx : idx + 700]
            self.assertIn(
                mem_id, window,
                f"{op_name}: TASK-62 comment must cite its verdict memory {mem_id}",
            )


class PureDataModuleTest(unittest.TestCase):
    """registry.py imports nothing but dataclasses — no ops, no I/O, no lib."""

    def test_registry_imports_are_pure_data(self):
        source = Path(registry.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=registry.__file__)
        allowed = {"dataclasses", "__future__"}
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            offenders.extend(
                f"registry.py:{node.lineno} imports '{name}'"
                for name in names
                if name and name not in allowed
            )
        self.assertEqual(offenders, [], "\n".join(offenders))


class OpsPackageMarkerTest(unittest.TestCase):
    def test_ops_package_marker_exists(self):
        self.assertTrue((OPS_DIR / "__init__.py").is_file(), OPS_DIR / "__init__.py")

    def test_ops_readme_documents_the_protocol(self):
        readme = OPS_DIR / "README.md"
        self.assertTrue(readme.is_file(), readme)
        text = readme.read_text(encoding="utf-8")
        self.assertIn("run(ctx)", text)
        for phase in registry.PHASE_ORDER:
            self.assertIn(phase, text)


if __name__ == "__main__":
    unittest.main()
