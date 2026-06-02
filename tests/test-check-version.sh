#!/usr/bin/env bash
#
# Unit test for scripts/check-version.sh version_lt().
#
# Guards the HIGH finding from audit wf_0dc1b9ce-7d8: version_lt() was
# logically inverted (`sort -V -C || return 0`), so the version checker
# reported "up to date" when an update was actually available.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
TARGET="$ROOT/scripts/check-version.sh"

pass=0
fail=0

# Source check-version.sh in a subshell (its main() is guarded out when
# sourced) and print LT when version_lt v1 v2 is true, GE otherwise.
vlt() {
    bash -c '
        source "$0" >/dev/null 2>&1
        if version_lt "$1" "$2"; then echo LT; else echo GE; fi
    ' "$TARGET" "$1" "$2"
}

check() {
    local desc=$1 v1=$2 v2=$3 want=$4 got
    got=$(vlt "$v1" "$v2")
    if [ "$got" = "$want" ]; then
        echo "  ok: $desc (version_lt $v1 $v2 -> $got)"
        pass=$((pass + 1))
    else
        echo "  FAIL: $desc (version_lt $v1 $v2 -> $got, expected $want)"
        fail=$((fail + 1))
    fi
}

echo "--- test-check-version.sh ---"
check "older < newer is LT"             6.15.4  6.15.5  LT
check "equal is GE (not less-than)"     6.15.5  6.15.5  GE
check "newer > older is GE"             6.16.0  6.15.5  GE
check "numeric (not lexical) ordering"  6.9.0   6.10.0  LT
check "v-prefix tolerated both sides"   v6.15.4 v6.15.5 LT
check "major older < newer"             5.9.0   6.0.0   LT
check "patch newer > older is GE"       6.15.6  6.15.5  GE

echo
if [ "$fail" -ne 0 ]; then
    echo "FAILED: $fail of $((pass + fail))"
    exit 1
fi
echo "PASSED: $pass of $pass"
