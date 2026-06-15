# Navigator v6.16.0 Release Notes

**Release Date**: 2026-06-15
**Type**: Minor — new skill (`nav-pilot`), backward compatible

---

## Summary

New skill **`nav-pilot`** — the Navigator → Pilot dispatch handoff.

Navigator has authored Pilot-compatible task specs since v6.15.4 (the `nav-task`
template is a structural superset of Pilot's `spec_validator`). But the handoff
itself stayed manual: a human ran `gh issue create --body-file
.agent/tasks/TASK-XX.md`, had to remember the polling label, and pasted the
resulting issue link back into the doc by hand.

`nav-pilot` owns that one-way step.

---

## What changed

### New skill: `skills/nav-pilot/SKILL.md`

Trigger phrases: *"dispatch TASK-XX to Pilot"*, *"hand off to Pilot"*,
*"send to Pilot"*, *"queue for Pilot"*.

Flow:
1. **Resolve** the task doc — explicit `TASK-XX` or the active task.
2. **Title** = the doc's H1; **body** = the doc file (`--body-file`, never inlined).
3. **Pre-flight confirmation** (ToM high-stakes checkpoint) showing repo, title,
   label, and body summary. A `--dry-run` prints the exact `gh` command and stops.
4. **Dispatch**: `gh issue create --label pilot --title <h1> --body-file <doc>`
   (repo defaults to the current git origin; override with `pilot.repo`).
5. **Record back**: write the issue URL into the doc's `## Refs` and set status
   to `🚀 Dispatched to Pilot`.

### No local validation — by design

`nav-pilot` does **not** lint the doc. Spec checking is Pilot's responsibility:
its `spec_validator` regex `^##\s+(Acceptance|Implementation|Context|Background|Approach|Design|Refs)\b`
is an any-match structural check, and `nav-task`-authored docs already pass it.

### New config block (`.agent/.nav-config.json`)

```json
"pilot": {
  "enabled": true,
  "label": "pilot",
  "repo": null
}
```

The polling label is deployment-configurable (default `pilot`).

### New SOP

`.agent/sops/integrations/pilot-handoff.md` — procedure, configuration, and
troubleshooting for the handoff.

---

## Scope

One-way by design. Monitoring Pilot workers and pulling PR/results back are
**out of scope**. Pairs with `nav-task` (authors the spec) → `nav-pilot`
(dispatches it). See `.agent/tasks/TASK-54-nav-pilot-dispatch-skill.md`.

---

## Upgrade

Restart Claude Code after upgrade — Claude Code caches skill paths at session
start, so `nav-pilot` will not auto-invoke until the session is restarted or
`/reload-plugins` is run.
