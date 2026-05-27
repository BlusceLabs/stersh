#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
VENV_DIR=".venv"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4321}"
LOG_DIR="/tmp/watchfy-logs"

mkdir -p "$LOG_DIR"

# ── Ensure dependencies are installed ────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    echo "=== Running setup.sh (first time) ==="
    bash setup.sh
fi

if [[ ! -d "node_modules" ]]; then
    echo "=== Installing frontend dependencies ==="
    cd frontend && pnpm install && cd ..
fi

# ── Start backend ────────────────────────────────────────────
echo "=== Starting backend (uvicorn) ==="
cd backend
../"$VENV_DIR/bin/uvicorn" main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --log-level info \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
cd ..

# ── Start frontend ───────────────────────────────────────────
echo "=== Starting frontend (astro) ==="
cd frontend
pnpm dev --host "$HOST" --port "$FRONTEND_PORT" \
    > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "  Backend  → http://$HOST:$PORT        (pid $BACKEND_PID)"
echo "  Frontend → http://$HOST:$FRONTEND_PORT  (pid $FRONTEND_PID)"
echo "  Logs     → $LOG_DIR/"
echo ""

# ── Trap to clean up on exit ─────────────────────────────────
cleanup() {
    echo ""
    echo "=== Shutting down ==="
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    echo "Stopped."
}
trap cleanup EXIT INT TERM

# ── Tail both logs ───────────────────────────────────────────
echo "=== Watching logs (Ctrl+C to stop) ==="
echo ""
tail -f \
    "$LOG_DIR/backend.log" \
    "$LOG_DIR/frontend.log" &
TAIL_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
kill "$TAIL_PID" 2>/dev/null || true
