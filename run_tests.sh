#!/usr/bin/env bash
# Runs all GUT tests headless. Starts a mock Supabase server for integration tests.
set -euo pipefail
cd "$(dirname "$0")"
GODOT="${GODOT:-godot}"
PORT="${MOCK_SUPABASE_PORT:-54329}"

python3 tests/mock_supabase.py "$PORT" &
MOCK_PID=$!
trap 'kill $MOCK_PID 2>/dev/null || true' EXIT
export MOCK_SUPABASE_URL="http://127.0.0.1:$PORT"

"$GODOT" --headless --import >/dev/null 2>&1 || true
LOG="$(mktemp)"
status=0
"$GODOT" --headless -s addons/gut/gut_cmdln.gd -gconfig=res://.gutconfig.json 2>&1 | tee "$LOG" || status=$?
# GUT exits 0 when a test script fails to parse, so also fail on script errors.
if grep -qE "SCRIPT ERROR|Ignoring script|Nothing was run" "$LOG"; then
  echo "run_tests.sh: script errors found" >&2
  status=1
fi
rm -f "$LOG"
exit "$status"
