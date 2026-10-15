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
"$GODOT" --headless -s addons/gut/gut_cmdln.gd -gconfig=res://.gutconfig.json
