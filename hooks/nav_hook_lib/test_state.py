#!/usr/bin/env python3
"""Tests for nav_hook_lib/state.py (RuntimeState schema v2, TASK-59 Phase 2).

stdlib unittest only, in-process (state.py is a library, not a hook entry
point). Each test builds a throwaway .agent dir. Contract under test:

  - load()/save() round-trip the namespaced sections; save is atomic via hio.
  - Schema gate: schema-less files (real v6 .nav-workflow-state.json shape)
    and non-2 schemas are ignored entirely.
  - Per-section TTLs expire independently; timestamps refresh only when a
    section's content changes; expired-then-rewritten sections get a fresh
    clock.
  - Session scoping is FAIL-CLOSED: differing OR absent stored session.id
    yields section-absent for session-scoped sections; save(session_id=X)
    stamps session.id; profile/compact survive session boundaries.
  - turn.signals.check_shown tristate True/False/None survives save+load
    exactly, in Python and in the raw JSON (mem-037).
  - meta carries schema, writer, op_errors (bounded), updated.
  - lock(): two-process read-modify-write loses updates unlocked and never
    loses them under state.lock(); a held lock times out fail-open.
"""

import contextlib
import json
import multiprocessing
import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

import state

T0 = 1_750_000_000.0  # fixed epoch base for deterministic TTL math

HOUR = 3600.0
DAY = 24 * HOUR

# Real v6 .nav-workflow-state.json shape (schema-less from v2's perspective:
# its `schema` key is top-level, there is no meta.schema). Readers must
# ignore this entirely if it ever lands at the runtime-state path.
V6_WORKFLOW_STATE = {
    "schema": 1,
    "session_id": "abc-123",
    "updated_at": "2026-07-10T12:00:00+00:00",
    "last_turn": {
        "check_shown": False,
        "nav_status_shown": False,
        "loop_phase": None,
        "assistant_text_chars": 512,
        "tools_used": ["Bash", "Edit"],
    },
}


class StateTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        # realpath so macOS /var -> /private/var resolution stays consistent
        self.agent = Path(os.path.realpath(self._tmp.name)) / ".agent"
        self.agent.mkdir(parents=True)
        self.state_file = self.agent / ".nav-runtime-state.json"

    def tearDown(self):
        self._tmp.cleanup()

    def write_raw(self, text):
        self.state_file.write_text(text, encoding="utf-8")

    def read_raw(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))


class FreshAndForeignFileTest(StateTestBase):
    def assert_fresh(self, loaded):
        self.assertEqual(
            sorted(loaded.keys()), ["meta"],
            f"expected no sections, got {sorted(loaded.keys())}",
        )
        self.assertEqual(loaded["meta"]["schema"], state.SCHEMA_VERSION)
        self.assertEqual(loaded["meta"]["sections"], {})
        self.assertEqual(loaded["meta"]["writer"], "")
        self.assertEqual(loaded["meta"]["op_errors"], [])

    def test_missing_file_yields_fresh_state(self):
        self.assert_fresh(state.load(self.agent, now=T0))

    def test_corrupt_json_yields_fresh_state(self):
        self.write_raw("{not json!!")
        self.assert_fresh(state.load(self.agent, now=T0))

    def test_non_object_top_level_yields_fresh_state(self):
        self.write_raw(json.dumps([1, 2, 3]))
        self.assert_fresh(state.load(self.agent, now=T0))

    def test_v6_workflow_state_shape_is_ignored_entirely(self):
        """v6 leftovers are schema-less (top-level schema, no meta) — ignored."""
        self.write_raw(json.dumps(V6_WORKFLOW_STATE, indent=2) + "\n")
        loaded = state.load(self.agent, session_id="abc-123", now=T0)
        self.assert_fresh(loaded)
        self.assertNotIn("last_turn", loaded)

    def test_v1_meta_schema_is_ignored_entirely(self):
        self.write_raw(json.dumps({"meta": {"schema": 1}, "turn": {"x": 1}}))
        self.assert_fresh(state.load(self.agent, now=T0))

    def test_future_meta_schema_is_ignored_entirely(self):
        self.write_raw(json.dumps({"meta": {"schema": 3}, "turn": {"x": 1}}))
        self.assert_fresh(state.load(self.agent, now=T0))


class RoundTripTest(StateTestBase):
    def test_basic_roundtrip(self):
        st = state.load(self.agent, now=T0)
        st["session"] = {"id": "s1", "started": "2026-07-10T12:00:00+00:00"}
        st["turn"] = {"signals": {"check_shown": True}, "tools_used": ["Edit"]}
        self.assertTrue(state.save(self.agent, st, now=T0))
        loaded = state.load(self.agent, session_id="s1", now=T0 + 60)
        self.assertEqual(loaded["session"]["id"], "s1")
        self.assertEqual(loaded["turn"]["tools_used"], ["Edit"])

    def test_check_shown_tristate_survives_roundtrip(self):
        """mem-037: True/False/None must survive exactly — no boolean coercion."""
        for value in (True, False, None):
            with self.subTest(check_shown=value):
                st = state.load(self.agent, now=T0)
                st["session"] = {"id": "s1"}
                st["turn"] = {"signals": {"check_shown": value}}
                self.assertTrue(state.save(self.agent, st, now=T0))
                loaded = state.load(self.agent, session_id="s1", now=T0)
                self.assertIs(loaded["turn"]["signals"]["check_shown"], value)
                # And in the raw JSON: true/false/null, never a coerced form.
                raw = self.read_raw()
                self.assertIs(raw["turn"]["signals"]["check_shown"], value)

    def test_v6_state_is_representable_in_v2_sections(self):
        """All four v6 state files map into v2 sections and round-trip verbatim."""
        st = state.load(self.agent, now=T0)
        st["session"] = {"id": "abc-123"}
        st["turn"] = {  # .nav-workflow-state.json last_turn
            "signals": {
                "check_shown": None,
                "nav_status_shown": False,
                "loop_phase": "VERIFY",
            },
            "assistant_text_chars": 512,
            "tools_used": ["Bash", "Edit"],
        }
        st["reads"] = {"count": 4}  # .nav-read-counter.json turn_count
        st["profile"] = {"last_synced_count": 7}  # .nav-profile-sync-state.json
        st["brief"] = {"pending": False}  # nav_brief.py is stateless in v6; v7 slot
        expected = {k: json.loads(json.dumps(v)) for k, v in st.items() if k != "meta"}
        self.assertTrue(state.save(self.agent, st, now=T0))
        loaded = state.load(self.agent, session_id="abc-123", now=T0)
        for name, content in expected.items():
            self.assertEqual(loaded[name], content, f"section {name} mutated in transit")
        self.assertIsInstance(loaded["turn"]["tools_used"], list)

    def test_unknown_section_passes_through(self):
        """Forward compat: sections v2 does not know keep flowing untouched."""
        st = state.load(self.agent, now=T0)
        st["future_thing"] = {"x": 1}
        self.assertTrue(state.save(self.agent, st, now=T0))
        loaded = state.load(self.agent, now=T0 + 40 * DAY)
        self.assertEqual(loaded["future_thing"], {"x": 1})


class TtlTest(StateTestBase):
    def seed(self, now=T0, session_id="s1"):
        st = state.load(self.agent, now=now)
        st["session"] = {"id": session_id}
        st["turn"] = {"signals": {"check_shown": True}}
        st["reads"] = {"count": 2}
        st["jit"] = {"injected": ["mem-001"]}
        st["profile"] = {"last_synced_count": 3}
        st["compact"] = {"marker": "m-1"}
        self.assertTrue(state.save(self.agent, st, now=now))
        return st

    def test_sections_expire_independently(self):
        self.seed(now=T0)
        cases = [
            (T0 + 3 * HOUR, {"turn": False, "reads": False, "jit": True,
                             "session": True, "profile": True, "compact": True}),
            (T0 + 25 * HOUR, {"turn": False, "reads": False, "jit": False,
                              "session": False, "profile": True, "compact": True}),
            (T0 + 31 * DAY, {"turn": False, "reads": False, "jit": False,
                             "session": False, "profile": False, "compact": False}),
        ]
        for now, expectations in cases:
            with self.subTest(now=now):
                loaded = state.load(self.agent, session_id="s1", now=now)
                for name, present in expectations.items():
                    if present:
                        self.assertIn(name, loaded, f"{name} should survive at {now}")
                    else:
                        self.assertNotIn(name, loaded, f"{name} should expire at {now}")

    def test_unchanged_section_keeps_aging_across_saves(self):
        """save() must not refresh the clock of a section it did not change."""
        self.seed(now=T0)
        st = state.load(self.agent, session_id="s1", now=T0 + 1 * HOUR)
        self.assertIn("turn", st)
        self.assertTrue(state.save(self.agent, st, now=T0 + 1 * HOUR))  # no edits
        loaded = state.load(self.agent, session_id="s1", now=T0 + 2.5 * HOUR)
        self.assertNotIn("turn", loaded, "unchanged turn must expire 2h after T0")

    def test_changed_section_gets_fresh_clock(self):
        self.seed(now=T0)
        st = state.load(self.agent, session_id="s1", now=T0 + 1 * HOUR)
        st["turn"] = {"signals": {"check_shown": False}}
        self.assertTrue(state.save(self.agent, st, now=T0 + 1 * HOUR))
        loaded = state.load(self.agent, session_id="s1", now=T0 + 2.5 * HOUR)
        self.assertIn("turn", loaded, "modified turn was re-stamped at T0+1h")
        loaded = state.load(self.agent, session_id="s1", now=T0 + 3.5 * HOUR)
        self.assertNotIn("turn", loaded)

    def test_expired_section_rewritten_identically_gets_fresh_clock(self):
        """load() prunes the stale timestamp, so identical re-writes restart TTL."""
        self.seed(now=T0)
        st = state.load(self.agent, session_id="s1", now=T0 + 3 * HOUR)
        self.assertNotIn("turn", st)
        st["turn"] = {"signals": {"check_shown": True}}  # identical to stale disk bytes
        self.assertTrue(state.save(self.agent, st, now=T0 + 3 * HOUR))
        loaded = state.load(self.agent, session_id="s1", now=T0 + 4 * HOUR)
        self.assertIn("turn", loaded, "re-written turn must live 2h from its re-write")

    def test_missing_timestamp_is_never_expired(self):
        """Hand-edited v2 docs without meta.sections stay readable (not stale)."""
        doc = {
            "meta": {"schema": 2},
            "turn": {"signals": {"check_shown": True}},
        }
        self.write_raw(json.dumps(doc))
        loaded = state.load(self.agent, now=T0 + 365 * DAY)
        self.assertIn("turn", loaded)


class SessionScopeTest(StateTestBase):
    ALL = ("session", "turn", "reads", "completion", "brief", "jit", "profile", "compact")

    def seed_all(self, session_id="A", now=T0):
        st = state.load(self.agent, now=now)
        st["session"] = {"id": session_id}
        for name in self.ALL:
            if name != "session":
                st[name] = {"seeded": name}
        self.assertTrue(state.save(self.agent, st, now=now))

    def test_differing_session_id_yields_scoped_sections_absent(self):
        self.seed_all(session_id="A")
        loaded = state.load(self.agent, session_id="B", now=T0)
        for name in state.SESSION_SCOPED_SECTIONS:
            self.assertNotIn(name, loaded, f"{name} must not leak across sessions")
        self.assertEqual(loaded["profile"], {"seeded": "profile"})
        self.assertEqual(loaded["compact"], {"seeded": "compact"})

    def test_matching_session_id_keeps_everything(self):
        self.seed_all(session_id="A")
        loaded = state.load(self.agent, session_id="A", now=T0)
        for name in self.ALL:
            self.assertIn(name, loaded)

    def test_no_session_id_skips_the_check(self):
        self.seed_all(session_id="A")
        loaded = state.load(self.agent, session_id=None, now=T0)
        for name in self.ALL:
            self.assertIn(name, loaded)

    def test_mismatch_drop_persists_through_save(self):
        """Old-session sections vanish from disk once the new session saves."""
        self.seed_all(session_id="A")
        st = state.load(self.agent, session_id="B", now=T0)
        st["session"] = {"id": "B"}
        self.assertTrue(state.save(self.agent, st, now=T0))
        raw = self.read_raw()
        self.assertEqual(raw["session"]["id"], "B")
        for name in ("turn", "reads", "completion", "brief", "jit"):
            self.assertNotIn(name, raw)
        self.assertIn("profile", raw)
        self.assertIn("compact", raw)

    def seed_unstamped(self, now=T0):
        """Session-scoped sections on disk with NO session section at all."""
        st = state.load(self.agent, now=now)
        for name in self.ALL:
            if name != "session":
                st[name] = {"seeded": name}
        self.assertTrue(state.save(self.agent, st, now=now))

    def test_absent_stored_session_id_is_fail_closed(self):
        """Unstamped file + caller session_id -> scoped sections dropped."""
        self.seed_unstamped()
        loaded = state.load(self.agent, session_id="B", now=T0)
        for name in state.SESSION_SCOPED_SECTIONS:
            self.assertNotIn(
                name, loaded, f"{name} must not pass through an unstamped file")
        self.assertEqual(loaded["profile"], {"seeded": "profile"})
        self.assertEqual(loaded["compact"], {"seeded": "compact"})

    def test_session_section_without_id_is_fail_closed(self):
        """A session section missing its id counts as absent, not a match."""
        self.seed_all(session_id="A")
        st = state.load(self.agent, session_id="A", now=T0)
        st["session"] = {"started": "2026-07-10T12:00:00+00:00"}  # no id
        self.assertTrue(state.save(self.agent, st, now=T0))
        loaded = state.load(self.agent, session_id="A", now=T0)
        for name in state.SESSION_SCOPED_SECTIONS:
            self.assertNotIn(name, loaded)

    def test_save_session_id_stamps_then_scoped_load_succeeds(self):
        """save(session_id=X) creates/stamps session.id; load(X) keeps all."""
        st = state.load(self.agent, now=T0)
        st["turn"] = {"signals": {"check_shown": True}}
        st["jit"] = {"injected": ["mem-001"]}
        self.assertTrue(state.save(self.agent, st, session_id="X", now=T0))
        self.assertEqual(self.read_raw()["session"]["id"], "X")
        loaded = state.load(self.agent, session_id="X", now=T0)
        self.assertEqual(loaded["turn"], {"signals": {"check_shown": True}})
        self.assertEqual(loaded["jit"], {"injected": ["mem-001"]})
        # ...and a different session still gets nothing scoped.
        other = state.load(self.agent, session_id="Y", now=T0)
        for name in state.SESSION_SCOPED_SECTIONS:
            self.assertNotIn(name, other)

    def test_save_session_id_overwrites_stale_id(self):
        self.seed_all(session_id="A")
        st = state.load(self.agent, session_id="A", now=T0)
        self.assertTrue(state.save(self.agent, st, session_id="B", now=T0))
        self.assertEqual(self.read_raw()["session"]["id"], "B")
        self.assertIn("turn", state.load(self.agent, session_id="B", now=T0))


def _increment_worker(agent_dir, iterations, use_lock, hold_s):
    """Read-modify-write loop over an unknown-section counter.

    Module-level so multiprocessing can target it. The tiny hold between
    load and save widens the race window, making unlocked update loss
    deterministic in practice.
    """
    for _ in range(iterations):
        guard = state.lock(agent_dir) if use_lock else contextlib.nullcontext()
        with guard:
            st = state.load(agent_dir)
            count = st.get("counter", {}).get("n", 0)
            time.sleep(hold_s)
            st["counter"] = {"n": count + 1}
            if not state.save(agent_dir, st):
                raise RuntimeError("save failed")


@unittest.skipIf(state.fcntl is None, "fcntl unavailable — lock() degrades to a no-op")
class LockTest(StateTestBase):
    """FIX 1 (TASK-59 adversarial review): cross-process read-modify-write guard."""

    ITERATIONS = 30  # per process; 2 workers -> expected total of 60
    HOLD_S = 0.002

    def _run_two_workers(self, use_lock):
        # fork: POSIX-only, like fcntl — avoids spawn re-import fragility.
        ctx = multiprocessing.get_context("fork")
        workers = [
            ctx.Process(
                target=_increment_worker,
                args=(str(self.agent), self.ITERATIONS, use_lock, self.HOLD_S),
            )
            for _ in range(2)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=120)
        for worker in workers:
            self.assertIsNotNone(worker.exitcode, "worker hung past join timeout")
            self.assertEqual(worker.exitcode, 0, "worker crashed")
        return state.load(self.agent).get("counter", {}).get("n", 0)

    def test_unlocked_increment_loses_updates(self):
        """Control: without lock() the interleaved load->save drops increments."""
        final = self._run_two_workers(use_lock=False)
        self.assertLess(
            final, 2 * self.ITERATIONS,
            "unlocked run lost no updates — race window closed? "
            "(raise HOLD_S if this ever flakes)",
        )

    def test_locked_increment_never_loses_updates(self):
        final = self._run_two_workers(use_lock=True)
        self.assertEqual(final, 2 * self.ITERATIONS)

    def test_lock_timeout_is_fail_open(self):
        """A wedged peer holding the lock must not brick the caller."""
        lock_path = self.agent / ".nav-runtime-state.lock"
        holder = open(lock_path, "a")
        self.addCleanup(holder.close)
        state.fcntl.flock(holder.fileno(), state.fcntl.LOCK_EX)
        self.addCleanup(
            setattr, state, "LOCK_TIMEOUT_SECONDS", state.LOCK_TIMEOUT_SECONDS)
        state.LOCK_TIMEOUT_SECONDS = 0.3
        started = time.monotonic()
        with state.lock(self.agent):
            pass  # body MUST run even though the lock never came free
        elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, 0.25, "gave up before the timeout window")
        self.assertLess(elapsed, 5.0, "fail-open took implausibly long")

    def test_lock_body_runs_on_unopenable_lockfile(self):
        """Lockfile path blocked by a directory -> no-op lock, body still runs."""
        (self.agent / ".nav-runtime-state.lock").mkdir()
        ran = False
        with state.lock(self.agent):
            ran = True
        self.assertTrue(ran)


class MetaTest(StateTestBase):
    def test_save_stamps_meta(self):
        st = {"turn": {"signals": {"check_shown": None}}}
        self.assertTrue(state.save(self.agent, st, now=T0))
        meta = self.read_raw()["meta"]
        self.assertEqual(meta["schema"], state.SCHEMA_VERSION)
        self.assertEqual(meta["writer"], "")
        self.assertEqual(meta["op_errors"], [])
        stamped = datetime.fromisoformat(meta["updated"])
        self.assertAlmostEqual(stamped.timestamp(), T0)
        self.assertAlmostEqual(meta["sections"]["turn"], T0)

    def test_writer_and_op_errors_are_preserved(self):
        st = {
            "meta": {"writer": "nav_dispatch", "op_errors": [{"op": "jit", "err": "boom"}]},
            "jit": {"injected": []},
        }
        self.assertTrue(state.save(self.agent, st, now=T0))
        loaded = state.load(self.agent, now=T0)
        self.assertEqual(loaded["meta"]["writer"], "nav_dispatch")
        self.assertEqual(loaded["meta"]["op_errors"], [{"op": "jit", "err": "boom"}])

    def test_op_errors_bounded_to_most_recent(self):
        errors = [{"n": i} for i in range(state.MAX_OP_ERRORS + 15)]
        st = {"meta": {"op_errors": errors}}
        self.assertTrue(state.save(self.agent, st, now=T0))
        saved = self.read_raw()["meta"]["op_errors"]
        self.assertEqual(len(saved), state.MAX_OP_ERRORS)
        self.assertEqual(saved[-1], {"n": state.MAX_OP_ERRORS + 14})
        self.assertEqual(saved[0], {"n": 15})

    def test_save_rejects_non_dict_state(self):
        self.assertFalse(state.save(self.agent, ["not", "a", "dict"], now=T0))

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_save_returns_false_on_unwritable_dir(self):
        os.chmod(self.agent, 0o500)
        try:
            self.assertFalse(state.save(self.agent, {"turn": {}}, now=T0))
        finally:
            os.chmod(self.agent, 0o700)


if __name__ == "__main__":
    unittest.main()
