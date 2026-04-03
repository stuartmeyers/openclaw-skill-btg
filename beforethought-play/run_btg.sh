#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PLAY_PY="$SCRIPT_DIR/play.py"

fail() {
  echo "BTG runner error: $1" >&2
  exit 1
}

command -v bash >/dev/null 2>&1 || fail "bash is not installed or not in PATH"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "python3 is not installed or not in PATH"

[ -f "$PLAY_PY" ] || fail "play.py not found at $PLAY_PY"

"$PYTHON_BIN" "$PLAY_PY" "$@"
