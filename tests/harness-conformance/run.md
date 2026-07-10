# Harness-Conformance Suite — Drive Script (TASK-58)

Re-runnable packaging of the six TASK-57 hook-channel probes (S1–S6). Run this
suite against every Claude Code version Navigator v7 ships on; check the result
in as `results/cc-<version>.json`. `make conformance-check` fails loudly when no
results file exists for the installed CC version.

**This suite is CI-adjacent, not CI**: probes drive live headless CC sessions
and need human judgment for rendering checks. Only the results-file existence
check (`make conformance-check`) and the schema test (`make test`) automate.

**Independence rule**: probes and `common.py` are stdlib-only and import
nothing from `hooks/` or `nav_hook_lib` — the suite certifies the harness the
runtime runs on, so it must not depend on the runtime (TASK-59 runs parallel).

---

## The probe + memory pairing rule (standing)

**New harness discovery → new probe + new memory, always paired.**
A memory without a probe is archaeology; a probe without a memory is
unexplained. Current pairing:

| Probe | Channel | Memory |
|-------|---------|--------|
| S1 | PostToolUse `additionalContext` | mem-050 |
| S2 | Stop `continue:true` vs `decision:block` (fuse, mem-037) | mem-051 |
| S3 | SubagentStart `additionalContext` + isolation | mem-052 |
| S4 | UserPromptSubmit block-as-answer (mem-034 hygiene) | mem-053 |
| S5 | PreToolUse stdout + `additionalContext` (mem-035 re-test) | mem-054 |
| S6 | `${CLAUDE_PLUGIN_ROOT}` binding (mem-036 re-check) | mem-055 |

Memory recall takes comma-separated concepts:
`python3 skills/nav-graph/functions/memory_recall.py --concepts "hooks,harness-behavior"`

---

## Method lessons (read before editing any probe)

1. **Injection observable — declarative, never imperative.** On tool-adjacent
   channels (PreToolUse/PostToolUse), NEVER use "quote this token verbatim" as
   the observable: the model's injection defense refuses compliance while
   delivery succeeds, producing a false FAIL (observed 2/2 on CC 2.1.205).
   Use a **declarative fact plus a driving-prompt question only answerable
   from that fact** — e.g. hook injects "the internal build codename is
   NAV-S1-xxxx", prompt asks "if any session metadata mentions an internal
   build codename, tell me what it is; otherwise say 'no codename'".
2. **macOS realpath.** Hook payload `cwd` arrives realpath'd
   (`/tmp` → `/private/tmp`). Never string-prefix-gate on cwd; compare
   `Path.resolve()`d paths (see `harness/nav-spike/hooks/spike_gate.py`).
3. **Sentinels are per-run UUIDs** (`NAV-S<n>-<uuid8>`, `common.make_sentinel`),
   never static strings — a static sentinel in the transcript from a previous
   run false-passes the position grep (mem-034 class).
4. **Silent hooks leave no transcript attachment** — conformance evidence needs
   the side-channel logs in `$NAV_SPIKE_DIR/state/` (mem-055).

---

## 1. Setup — scratch marketplace from `harness/`

The harness must run through **real marketplace manifest execution** — never
ad-hoc `.claude/settings.json` hooks, which mask `${CLAUDE_PLUGIN_ROOT}`
binding failures (mem-036).

```bash
# From the navigator repo root:
export NAV_SPIKE_DIR=/tmp/nav-v7-spike     # default; the /tmp path is the runtime home

mkdir -p "$NAV_SPIKE_DIR/project" "$NAV_SPIKE_DIR/state"
cp -R tests/harness-conformance/harness/. "$NAV_SPIKE_DIR/marketplace/"
printf 'The mango is ripe. Nothing else matters.\n' > "$NAV_SPIKE_DIR/project/notes.txt"
```

Note: if you change `NAV_SPIKE_DIR` from the default, also update the
hardcoded `/tmp/nav-v7-spike` path inside the `SessionStart` command in
`marketplace/nav-spike/.claude-plugin/plugin.json`, and export the variable in
the shell that launches `claude` so `spike_gate.py` sees it.

**Preflight (mem-036)** — the scratch project must have no settings backstop
and no `.agent/`:

```bash
test ! -e "$NAV_SPIKE_DIR/project/.claude/settings.json" && \
test ! -d "$NAV_SPIKE_DIR/project/.agent" && echo "preflight OK"
```

**Install** (user scope — the gate keeps hooks inert outside the scratch
project):

```bash
claude plugin marketplace add "$NAV_SPIKE_DIR/marketplace"
claude plugin install nav-spike@nav-spike-marketplace
claude --version        # goes into the results filename and every verdict
```

Verify the install took: `claude plugin list` shows
`nav-spike@nav-spike-marketplace ... enabled`.

---

## 2. Drive the probes — SERIAL ONLY

**Arm files (`$NAV_SPIKE_DIR/state/arm-s<n>.json`) are global state**: a probe
arms its hook for every session in the scratch project. Two probes running
concurrently cross-fire hooks into each other's sessions and corrupt both
verdicts. Run strictly one at a time, in order:

```bash
cd tests/harness-conformance
python3 probe_s1.py     # ~1 min  (1 headless turn)
python3 probe_s2.py     # ~4 min  (2 variants x 2 turns; both variants = ONE probe run)
python3 probe_s3.py     # ~2-7 min (subagent turn, timeout 420s)
python3 probe_s4.py     # ~2 min  (2 variants x 2 turns; both variants = ONE probe run)
python3 probe_s5.py     # ~2 min  (2 variants x 1 turn; both variants = ONE probe run)
python3 probe_s6.py     # seconds (reads log-s6.txt; drives 1 turn only if empty)
```

Each probe prints its verdict JSON and writes
`$NAV_SPIKE_DIR/state/verdict-s<n>.json`. Probes always disarm in a `finally`
block; if you abort one mid-run, check `state/` for stale `arm-*.json` files
before continuing.

### Pass criteria per probe

**S1 — PostToolUse `additionalContext`** (`pass` true iff all):
- `hook_emitted` — hook log shows `emitted-additionalContext`;
- `answer_quoted` — the sentinel (codename) appears in the visible answer;
- `injected_positions` non-empty — transcript grep finds the sentinel in a
  non-assistant position (injected near the tool_result, not merely echoed).

**S2 — Stop forced continuation** (single-shot fuse per mem-037):
- Probe-level `pass` tracks **`continue:true`** specifically: continuation
  carries the sentinel AND fuse consumed AND run-twice subtest shows zero
  further continuations. Do not weaken this criterion.
- Spike-gated outcome: on CC 2.1.205 `continue:true` is a NO-OP
  (`pass: false`) while `decision:block` forces the continuation
  (`decision_block_works: true`). Record whichever outcome you observe —
  the results file asserts observation, not hope. `channel_works` in the
  results file means "a forced-continuation mechanism exists".
- If continuation loops despite the fuse: record as circuit-breaker evidence
  for TASK-62 — that is a new discovery (pairing rule applies).

**S3 — SubagentStart `additionalContext` + both-way isolation** (`pass` iff):
- `event_fired`; sentinel A present in sidechain/subagent entries;
- no A leak into main-thread non-tool_result positions;
- main-thread-only sentinel B absent from sidechain entries.
- Note: subagent transcripts are separate `<session>/subagents/agent-<id>.jsonl`
  files (mem-052) — `find_transcripts(since=...)` catches them.

**S4 — UserPromptSubmit block-as-answer** (`pass` iff for at least one variant):
- `hook_blocked` fired on the exact trigger prompt `nav spike ping`;
- sentinel present in CLI output with **zero model invocation** on the blocked
  turn (check `num_turns`/usage in the verdict's `blocked_turn_stdout`);
- echo hygiene (mem-034): unrelated follow-up does not re-trigger the hook and
  does not contain the block text.
- Human judgment call: compare the two variants' rendering
  (`blocked_turn_stdout`/`stderr`) and confirm the winner. On CC 2.1.205 the
  winner is `decision:block` — exit-2 leaks hook command chrome. Also expect
  CC to append "Original prompt: <trigger>" to block messages (mem-053).

**S5 — PreToolUse re-test (mem-035)** — either outcome is a result:
- `pass: true` = at least one variant reaches the model (supersedes mem-035
  for that sub-channel); `pass: false` = reconfirms mem-035.
- On CC 2.1.205: stdout DEAD, `additionalContext` DELIVERS (mem-054) —
  `channel_works` in the results file refers to the additionalContext
  sub-channel. If a new CC version flips either half, that is a harness
  change: update mem-054 and note it in the results summary.

**S6 — `${CLAUDE_PLUGIN_ROOT}` binding (mem-036)** (`pass` iff):
- live `log-s6.txt` shows non-empty `ROOT=` values pointing into the
  marketplace install (for dir-source installs CC binds the SOURCE path,
  i.e. `$NAV_SPIKE_DIR/marketplace/nav-spike` — mem-055);
- three-variant shell test recorded: `unset` and `empty` must NOT be silent
  no-ops (CC 2.1.205: loud exit-2 failure). A silent no-op on unset is a
  regression to the mem-036 failure class — record and escalate.

---

## 3. Record the results file

Write `results/cc-<version>.json`, where `<version>` is
`claude --version | awk '{print $1}'` (e.g. `2.1.205`). Schema (validated by
`test_results_schema.py` in `make test`):

```json
{
  "cc_version": "2.1.205",
  "date": "YYYY-MM-DD",
  "recorded_by": "<who drove the suite>",
  "probes": {
    "s1": {
      "pass": true,
      "channel_works": true,
      "verdict_file": "/tmp/nav-v7-spike/state/verdict-s1.json",
      "memory": "mem-050",
      "summary": "one-line observed outcome"
    },
    "s2": { "...": "same shape" },
    "s3": { "...": "same shape" },
    "s4": { "...": "same shape" },
    "s5": { "...": "same shape" },
    "s6": { "...": "same shape" }
  }
}
```

- `pass` — the probe script's own `pass` bool, copied from its verdict file
  (S2 may legitimately be `false` while `channel_works` is `true`; see above).
- `channel_works` — does a usable channel exist for this row of the v7
  routing matrix (the thing the paired memory asserts).
- `verdict_file` — path of the verdict JSON produced by THIS run (evidence;
  not checked in — copy it somewhere durable if you need it later).
- `memory` — the paired graph memory ID (table above). If the observed
  outcome contradicts the memory, update the memory in the same change.
- All six probes `s1`..`s6` are required; the schema test fails otherwise.

Then verify:

```bash
make conformance-check                                     # exit 0
cd tests/harness-conformance && python3 -m unittest discover -p "test_*.py"
```

---

## 4. Teardown

The plugin's hooks are inert outside `$NAV_SPIKE_DIR` (cwd + arm-file gate),
so leaving it installed between runs is safe but noisy. To remove:

```bash
claude plugin uninstall nav-spike@nav-spike-marketplace
claude plugin marketplace remove nav-spike-marketplace
rm -rf "$NAV_SPIKE_DIR"
```

Keep `state/verdict-s*.json` copies if the run produced anything surprising —
verdicts are the raw evidence behind the checked-in results file.
