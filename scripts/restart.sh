#!/usr/bin/env bash
# Stop any running bot, wait until it is gone, then start the new one in this terminal.
# Two bots on one token fight over updates, so it refuses to start while one is still alive.
set -euo pipefail

pattern='(^uv run companion run$|\.venv/bin/companion run$)'

if pgrep -f "$pattern" >/dev/null; then
  pkill -TERM -f "$pattern" || true
  for _ in $(seq 1 20); do
    pgrep -f "$pattern" >/dev/null || break
    sleep 0.5
  done
fi

if pgrep -f "$pattern" >/dev/null; then
  echo "the old bot did not stop; not starting a second one" >&2
  exit 1
fi

exec uv run companion run
