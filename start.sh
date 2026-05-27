#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
VENV_DIR=".venv"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "No .venv found — run ./setup.sh first" >&2
    exit 1
fi

cd backend
exec ../"$VENV_DIR/bin/uvicorn" main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --log-level info
