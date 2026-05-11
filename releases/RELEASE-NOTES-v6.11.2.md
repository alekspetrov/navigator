# Navigator v6.11.2 Release Notes

**Release Date**: 2026-05-11
**Type**: Patch — UX fixes for v6.11.1's blocking hook after live verification

---

## Summary

v6.11.1 shipped the first blocking hook in Navigator. Within an hour of release, the first live block in Claude Code surfaced two UX bugs the smoke tests couldn't catch.

v6.11.2 fixes them. No behavior change to *when* the block fires — only to *what the user sees* and how Claude Code handles retries.

---

## What changed

### 1. Stderr addresses the user, not Claude

**Before** (v6.11.1):

```
Navigator workflow_enforcer: blocked.
  Reason: loop trigger 'run until done' detected, ...
  Action: emit the WORKFLOW CHECK block at the top of the next
  response, then continue with NAVIGATOR_STATUS for Loop Mode.
  Opt-out: set workflow_enforcer_hook.strict_block=false in
  .agent/.nav-config.json.
```

The `Action:` line addressed Claude. **But Claude never runs when `UserPromptSubmit` exits 2** — the prompt is blocked before the model is invoked. Stderr surfaces to the user in the CC UI, not to the model. So "emit the WORKFLOW CHECK block" was dead text — Claude couldn't act on it because Claude wasn't there.

**After** (v6.11.2):

```
Navigator workflow_enforcer: blocked.
  Why: the prior assistant turn skipped its required workflow check
  block, but your prompt requests autonomous iteration.
  State: .agent/.nav-workflow-state.json check_shown=false
  How to proceed (your choice):
    1. Send any different prompt that does not request autonomous
       iteration. The next assistant response will restore state;
       then retry your original prompt.
    2. Edit .agent/.nav-workflow-state.json and set
       last_turn.check_shown=true.
    3. Disable strict enforcement: set workflow_enforcer_hook
       .strict_block=false in .agent/.nav-config.json.
```

Three explicit user actions, none of which require the assistant to run.

### 2. Recursive-block trap fixed via sentinel + strip

**The bug**: v6.11.1's stderr quoted the matched trigger phrase verbatim (`loop trigger 'run until done' detected`). Claude Code echoes blocked stderr into the next prompt's context (visible as `Original prompt:` in the UI). When the user retried, the next prompt contained the prior block message — and that message contained the trigger phrase — so the hook re-matched and re-blocked. Observed live as **three nested blocks in one screen**.

**The fix**:

1. The stderr message no longer quotes the trigger phrase verbatim — it describes the situation in neutral language ("your prompt requests autonomous iteration").
2. The entire message is wrapped in `<nav-workflow-block>...</nav-workflow-block>` sentinel tags.
3. On every hook invocation, the incoming prompt is run through `strip_block_messages()` which excises any sentinel-wrapped sections before LOOP_TRIGGERS matching runs.

**Result**: even if a prior block message ends up in a subsequent prompt's context, the hook strips it out before matching. No recursive blocks.

### 3. Soft-warn stdout suppressed on block

Before: when blocking, the hook printed BOTH the new stderr message AND the legacy soft-warn block (which contained `LOOP MODE TRIGGER DETECTED: 'run until done'` on stdout). That stdout line was another leaked trigger phrase.

After: when the block fires, only the sentinel-wrapped stderr is emitted. Stdout stays empty. No surface for trigger phrases to leak through.

---

## Pitfall captured

`.agent/knowledge/memories/pitfalls/mem-034.md` — **"UserPromptSubmit exit 2 bypasses the model + recursive-block via echoed trigger phrase"**

Documents both findings for future blocking-hook authors:

- Stderr "Action:" lines must address the user, not the model.
- Never quote trigger phrases verbatim in stderr (or any output that could end up back in a future prompt).
- Test the recursive case explicitly — re-feed the block message back as a prompt and confirm it doesn't re-trigger.
- Provide at least one zero-config recovery path.

Phase 3 blocking hooks (Opp 5, Opp 6 in TASK-38) inherit these constraints.

---

## Verification

3/3 smoke-test scenarios pass:

```bash
echo '{"schema":1,"last_turn":{"check_shown":false}}' > .agent/.nav-workflow-state.json

# Test 1: trigger prompt → blocks, stdout empty (no trigger leak)
echo '{"prompt":"run until done: ship"}' | python3 hooks/workflow_enforcer.py
# exit=2, stderr is sentinel-wrapped, stdout is 0 bytes

# Test 2: re-feed the entire stderr as next prompt → must NOT block
python3 -c "import json,sys;print(json.dumps({'prompt':sys.stdin.read()}))" < /tmp/stderr.txt \
  | python3 hooks/workflow_enforcer.py
# exit=0, no output (sentinel stripped before matching)

# Test 3: sentinel-wrapped block + real trigger AFTER → still blocks correctly
python3 -c "import json;print(json.dumps({'prompt':'<nav-workflow-block>old</nav-workflow-block> run until done: real'}))" \
  | python3 hooks/workflow_enforcer.py
# exit=2 (real trigger survives strip)
```

---

## Migration

**Existing projects**:
- Run `nav-upgrade` or wait for auto-update.
- Restart Claude Code to load the updated hook.
- No config changes required.

**No new dependencies, no schema changes.**

---

## Files Changed

**Modified**:
- `hooks/workflow_enforcer.py` — sentinel wrap + strip; user-addressed stderr; stdout suppressed on block
- `.agent/.nav-config.json`, `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `README.md`, `CLAUDE.md` — version bump
- `CHANGELOG.md` — v6.11.2 entry

**Created**:
- `.agent/knowledge/memories/pitfalls/mem-034.md` — UserPromptSubmit exit-2 + recursive-block pitfall
- `releases/RELEASE-NOTES-v6.11.2.md` (this file)

---

## Compatibility

- **Backward compatible.** Hook config unchanged; no state schema changes.
- **Restart required after upgrade** — Claude Code caches hook definitions at session start.
