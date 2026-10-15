#!/usr/bin/env bash
# Applies the migration to a throwaway local Postgres and runs the RLS tests.
set -euo pipefail
cd "$(dirname "$0")/.."
PG_BIN="${PG_BIN:-$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -1)}"
DIR="$(mktemp -d)"
PORT="${PG_TEST_PORT:-54330}"
RUN=()
if [ "$(id -u)" = "0" ]; then chown postgres "$DIR"; RUN=(runuser -u postgres --); fi
cleanup() {
  "${RUN[@]}" "$PG_BIN/pg_ctl" -D "$DIR/data" stop -m immediate >/dev/null 2>&1 || true
  rm -rf "$DIR"
}
trap cleanup EXIT
"${RUN[@]}" "$PG_BIN/initdb" -D "$DIR/data" -U postgres -A trust >/dev/null
"${RUN[@]}" "$PG_BIN/pg_ctl" -D "$DIR/data" -o "-p $PORT -k $DIR -c listen_addresses=''" -l "$DIR/log" -w start >/dev/null
PSQL=("${RUN[@]}" "$PG_BIN/psql" -h "$DIR" -p "$PORT" -U postgres -v ON_ERROR_STOP=1 -q -X)
"${PSQL[@]}" -c "create database test"
"${PSQL[@]}" -d test -f supabase/tests/auth_stub.sql
"${PSQL[@]}" -d test -f supabase/migrations/20261015000000_saves.sql
"${PSQL[@]}" -d test -f supabase/tests/saves_rls_test.sql
