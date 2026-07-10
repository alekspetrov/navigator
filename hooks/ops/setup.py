#!/usr/bin/env python3
"""setup op — Setup-event onboarding hint / runtime status (TASK-62 Phase 5).

Setup responder on the systemMessage channel. The EVENT registration went
through the TASK-62 validate-or-drop step (`claude plugin validate` on CC
2.1.205 accepted Setup — registration kept). mem-055 (S6) backs the delivery
plumbing: ``${CLAUDE_PLUGIN_ROOT}`` binds correctly in plugin-manifest hook
commands, so the manifest guard resolves this dispatcher on Setup fires.

Behavior:
  - ``.agent/`` missing → onboarding hint pointing at the nav-init skill.
    DELIVERY CAVEAT: through the shared dispatcher this branch is
    unreachable — runtime._dispatch early-outs on a missing ``.agent/``
    (TASK-60 contract: Navigator must not scaffold foreign projects). The
    branch is kept for direct/driver invocation and locked by tests; the
    dispatch-level contract test asserts the silence explicitly.
  - ``.agent/`` present → ONE line of runtime status (config version,
    dispatcher toggle, knowledge graph and runtime-state presence).

Config: ``setup_hook.enabled`` — seeded True in config.DEFAULTS (a one-line
status on an explicit user-driven event is not an injecting feature). No
ctx.pilot_executor gate: the message blocks nothing.
"""
from __future__ import annotations

from nav_hook_lib import config, hio

ONBOARDING_HINT = (
    "Navigator is not initialized in this project (.agent/ missing). "
    'The nav-init skill scaffolds it: say "Initialize Navigator in this project".'
)


def run(ctx):
    root = hio.project_root(ctx.payload)
    agent_dir = root / ".agent"
    if not agent_dir.is_dir():
        return {"system_message": ONBOARDING_HINT}

    version = config.get(ctx.config, "version")
    version_text = f"v{version}" if version else "unversioned"
    dispatcher_on = bool(config.get(ctx.config, "dispatcher.enabled", True))
    graph_present = (agent_dir / "knowledge" / "graph.json").is_file()
    state_present = (agent_dir / ".nav-runtime-state.json").is_file()

    status = (
        f"Navigator runtime status: config {version_text}; "
        f"dispatcher {'on' if dispatcher_on else 'off'}; "
        f"knowledge graph {'present' if graph_present else 'absent'}; "
        f"runtime state {'present' if state_present else 'not yet written'}."
    )
    return {"system_message": status}
