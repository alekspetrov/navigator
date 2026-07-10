"""TASK-59 re-export shim; implementation lives in hooks/nav_hook_lib/scoring.py. Delete in v8."""
import pathlib, sys  # noqa: E401
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "hooks" / "nav_hook_lib"))
import scoring; globals().update(scoring.v6_exports("complexity_detector"))  # noqa: E702
if __name__ == "__main__": sys.exit(main())  # noqa: E701,F821 — 'main' injected above
