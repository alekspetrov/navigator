"""nav_hook_lib — shared pure-stdlib runtime library for Navigator v7 hook ops (TASK-59).

Extracted from the nine v6 hook scripts in hooks/. The v6 scripts keep running
unchanged this task (library extraction is additive); v7 ops (TASK-60/61) import
these modules instead of re-implementing I/O, config reads, Pilot-executor
detection, sentinel handling, and scoring per hook.

Modules (landing incrementally): hio, config, state, sentinels, signals,
scoring, transcript, budget, memory.

Import discipline:
  - Pure Python stdlib only — enforced by the purity guard test in
    test_config.py, which scans every *.py in this directory.
  - Sibling imports use ``try: from . import x / except ImportError: import x``
    so each module works both as a package member (discovery from hooks/) and
    as a top-level module (per-directory discovery from inside this dir).

This __init__ deliberately imports nothing: eager submodule imports would break
while sibling modules land from parallel task groups.
"""
