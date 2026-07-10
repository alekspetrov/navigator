#!/usr/bin/env python3
"""nav_dispatch — single dispatcher entrypoint for every Navigator hook event (TASK-60).

plugin.json routes the seven v6 surfaces here: python3 nav_dispatch.py <EventName>.
Thin shim: read stdin once, delegate to nav_hook_lib.runtime.dispatch(), relay the
single JSON doc + stderr (sentinels.emit_stderr, mem-034) + exit code. Fail-open:
ANY failure — bad argv/stdin, missing runtime, escaping SystemExit, broken stdout
pipe — exits 0 (BaseException catch-all: hooks are non-interactive). stdout flushes
INSIDE the guard so a closed pipe cannot become exit 120 at interpreter shutdown.
"""
import os
import sys


def main() -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from nav_hook_lib import hio, runtime, sentinels

    event = sys.argv[1]
    payload = hio.read_stdin_payload()
    result = runtime.dispatch(event, payload)
    if result.stdout is not None:
        print(result.stdout)
    sys.stdout.flush()  # broken pipe raises HERE, inside the catch-all
    if result.stderr is not None:
        sentinels.emit_stderr(result.stderr)
    return result.exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException:
        exit_code = 0  # fail-open: Navigator must never brick the harness
    try:
        sys.stdout.flush()
    except BaseException:
        os._exit(exit_code)  # dead stdout: bypass shutdown flush (exit-120 guard)
    sys.exit(exit_code)
