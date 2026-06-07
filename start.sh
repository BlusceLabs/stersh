#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# watchfy dev start script
# Usage:
#   ./start.sh                    start both services
#   ./start.sh --backend          start backend only
#   ./start.sh --frontend         start frontend only
#   ./start.sh --skip-deps        skip dependency checks
#   ./start.sh --verbose          stream logs to console (no log files)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${CYAN}▶ $*${NC}"; }
ok()   { echo -e "${GREEN}✔ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
err()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

# ── Defaults ──────────────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR=".venv"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4321}"
LOG_DIR="/tmp/watchfy-logs"
START_BACKEND=1
START_FRONTEND=1
SKIP_DEPS=0
VERBOSE=0

# ── Parse flags ───────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --backend)       START_FRONTEND=0 ;;
        --frontend)      START_BACKEND=0 ;;
        --skip-deps)     SKIP_DEPS=1 ;;
        --verbose|-v)    VERBOSE=1 ;;
        --help|-h)
            echo "Usage: $0 [--backend|--frontend] [--skip-deps] [--verbose]"
            echo ""
            echo "  --backend     Start backend only"
            echo "  --frontend    Start frontend only"
            echo "  --skip-deps   Skip dependency installation checks"
            echo "  --verbose     Stream logs to console instead of log files"
            exit 0
            ;;
        *) err "Unknown flag: $arg" ;;
    esac
done

cd "$ROOT_DIR"

# ── Find Python ───────────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[[ -n "$PYTHON" ]] || { err "Python 3.11+ not found. Install it first."; }
PYVER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=${PYVER%%.*}
PY_MINOR=${PYVER##*.}
if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 11 ]]; }; then
    err "Python 3.11+ required (got $PYVER)"
fi

# ── Preflight checks ─────────────────────────────────────────────────────────
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        err "$1 is not installed. $2"
    fi
}

if [[ "$START_FRONTEND" -eq 1 ]]; then
    check_cmd pnpm  "Install pnpm: https://pnpm.io/installation"
    check_cmd node   "Install Node.js 18+: https://nodejs.org/"
fi

# ── Kill previous instances ──────────────────────────────────────────────────
kill_stale() {
    local label="$1"
    shift
    for pid_file in "$@"; do
        if [[ -f "$pid_file" ]]; then
            local old_pid
            old_pid=$(cat "$pid_file" 2>/dev/null || true)
            if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
                warn "Stopping previous $label (pid $old_pid)"
                kill "$old_pid" 2>/dev/null || true
                local waited=0
                while kill -0 "$old_pid" 2>/dev/null && [[ $waited -lt 10 ]]; do
                    sleep 1; waited=$((waited + 1))
                done
                kill -9 "$old_pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done
}

mkdir -p "$LOG_DIR"

for pidfile in "$LOG_DIR/backend.pid" "$LOG_DIR/frontend.pid" "$LOG_DIR/tail.pid"; do
    kill_stale "process" "$pidfile"
done

for port in "$PORT" "$FRONTEND_PORT"; do
    stale_pids=""
    if command -v lsof &>/dev/null; then
        stale_pids=$(lsof -ti :"$port" 2>/dev/null || true)
    elif command -v ss &>/dev/null; then
        stale_pids=$(ss -tlnp 2>/dev/null | grep ":${port} " | grep -oP 'pid=\K[0-9]+' || true)
    fi
    for pid in $stale_pids; do
        if kill -0 "$pid" 2>/dev/null; then
            warn "Killing process $pid occupying port $port"
            kill "$pid" 2>/dev/null || true
        fi
    done
done

# ── Install dependencies ──────────────────────────────────────────────────────
if [[ "$SKIP_DEPS" -eq 0 ]]; then

    # ── Backend: venv + pip ───────────────────────────────────────────────────
    if [[ "$START_BACKEND" -eq 1 ]]; then
        if [[ ! -d "$VENV_DIR" ]]; then
            log "Creating virtual environment in $VENV_DIR…"
            $PYTHON -m venv "$VENV_DIR"
            ok "Virtual environment created"
        fi

        # shellcheck disable=SC1091
        source "$VENV_DIR/bin/activate"

        if [[ ! -f "$VENV_DIR/bin/uvicorn" ]] || ! "$VENV_DIR/bin/python" -c "import scrapling" 2>/dev/null; then
            log "Installing Python dependencies…"
            pip install --upgrade pip
            pip install -r backend/requirements.txt || true
            ok "Python dependencies installed"
        fi

        # ── Browser for patchright ────────────────────────────────────────────
        if [[ ! -f "$HOME/.cache/ms-playwright/INSTALLATION_COMPLETE" ]]; then
            log "Installing Chromium browser for patchright…"
            "$VENV_DIR/bin/python" -m patchright install chromium || warn "Patchright install may need manual run"
            ok "Chromium browser installed"
        else
            # Verify the browser binary actually exists
            chromium_dir=$(ls -d "$HOME/.cache/ms-playwright/chromium-"*/chrome-linux64 2>/dev/null | head -1)
            if [[ -z "$chromium_dir" ]] || [[ ! -x "$chromium_dir/chrome" ]]; then
                log "Chromium browser binary missing — reinstalling…"
                "$VENV_DIR/bin/python" -m patchright install chromium || warn "Patchright install may need manual run"
                ok "Chromium browser reinstalled"
            fi
        fi

        # ── .env ──────────────────────────────────────────────────────────────
        if [[ ! -f "backend/.env" ]]; then
            if [[ -f "backend/.env.example" ]]; then
                cp backend/.env.example backend/.env
                warn "Created backend/.env from .env.example — set your TMDB_API_KEY"
            else
                err "backend/.env missing and no .env.example found"
            fi
        fi
        if grep -q "your_tmdb_api_key_here" backend/.env 2>/dev/null; then
            warn "TMDB_API_KEY is still the placeholder — set your real key in backend/.env"
        fi

        # ── Quick import sanity check ─────────────────────────────────────────
        log "Verifying backend imports…"
        if ! (cd backend && "../$VENV_DIR/bin/python" -c "from app.main import app; print('OK')" 2>/dev/null); then
            warn "Backend import check failed — reinstalling dependencies…"
            pip install --quiet -r backend/requirements.txt
            pip install --quiet curl_cffi 2>/dev/null || true
            if ! (cd backend && "../$VENV_DIR/bin/python" -c "from app.main import app" 2>/dev/null); then
                err "Backend imports still failing. Run ./setup.sh or check logs above."
            fi
            ok "Backend dependencies repaired"
        else
            ok "Backend imports OK"
        fi
    fi

    # ── Frontend: pnpm ────────────────────────────────────────────────────────
    if [[ "$START_FRONTEND" -eq 1 ]]; then
        if [[ ! -d "frontend/node_modules" ]]; then
            log "Installing frontend dependencies…"
            (cd frontend && pnpm install)
            ok "Frontend dependencies installed"
        fi
    fi

    # ── ffmpeg (optional) ────────────────────────────────────────────────────
    if command -v ffmpeg &>/dev/null; then
        ok "ffmpeg found: $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"
    else
        warn "ffmpeg not found — remux/download features unavailable"
    fi
fi

# ── Start backend ────────────────────────────────────────────────────────────
BACKEND_PID="" FRONTEND_PID="" TAIL_PID=""

if [[ "$START_BACKEND" -eq 1 ]]; then
    log "Starting backend on http://$HOST:$PORT"
    UVICORN="$VENV_DIR/bin/uvicorn"
    if [[ ! -x "$UVICORN" ]]; then
        err "$UVICORN not found — re-run ./start.sh or ./setup.sh"
    fi

    if [[ "$VERBOSE" -eq 1 ]]; then
        (cd backend && "../$UVICORN" main:app \
            --host "$HOST" --port "$PORT" --reload --log-level info) &
    else
        (cd backend && "../$UVICORN" main:app \
            --host "$HOST" --port "$PORT" --reload --log-level info \
            > "$LOG_DIR/backend.log" 2>&1) &
    fi
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
    ok "Backend pid $BACKEND_PID"
fi

# ── Start frontend ────────────────────────────────────────────────────────────
if [[ "$START_FRONTEND" -eq 1 ]]; then
    log "Starting frontend on http://$HOST:$FRONTEND_PORT"
    if [[ "$VERBOSE" -eq 1 ]]; then
        (cd frontend && pnpm dev --host "$HOST" --port "$FRONTEND_PORT") &
    else
        (cd frontend && pnpm dev --host "$HOST" --port "$FRONTEND_PORT" \
            > "$LOG_DIR/frontend.log" 2>&1) &
    fi
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"
    ok "Frontend pid $FRONTEND_PID"
fi

# ── Wait for services to be ready ────────────────────────────────────────────
HEALTH_RETRIES=30
HEALTH_INTERVAL=2

wait_for() {
    local label="$1"
    local url="$2"
    local retries="$HEALTH_RETRIES"
    local interval="$HEALTH_INTERVAL"

    log "Waiting for $label to be ready…"
    while [[ $retries -gt 0 ]]; do
        if curl -sf "$url" &>/dev/null; then
            ok "$label is ready"
            return 0
        fi
        sleep "$interval"
        retries=$((retries - 1))
    done
    warn "$label did not become ready within $((HEALTH_RETRIES * HEALTH_INTERVAL))s"
    return 1
}

if [[ "$START_BACKEND" -eq 1 ]]; then
    wait_for "Backend" "http://localhost:$PORT/api/health" || true
fi
if [[ "$START_FRONTEND" -eq 1 ]]; then
    wait_for "Frontend" "http://localhost:$FRONTEND_PORT/" || true
fi

# ── Print summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Watchfy dev server${NC}"
echo -e "  ──────────────────────────────────────────"
[[ "$START_BACKEND" -eq 1 ]]  && echo -e "  ${GREEN}Backend${NC}  → http://$HOST:$PORT  (pid $BACKEND_PID)"
[[ "$START_FRONTEND" -eq 1 ]] && echo -e "  ${GREEN}Frontend${NC} → http://$HOST:$FRONTEND_PORT  (pid $FRONTEND_PID)"
[[ "$VERBOSE" -eq 0 ]]        && echo -e "  ${CYAN}Logs${NC}    → $LOG_DIR/"
echo -e "  ${CYAN}API docs${NC} → http://localhost:$PORT/api/docs"
echo ""

# ── Trap to clean up on exit ─────────────────────────────────────────────────
cleanup() {
    echo ""
    log "Shutting down…"
    [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID" 2>/dev/null || true
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
    [[ -n "$TAIL_PID" ]]      && kill "$TAIL_PID" 2>/dev/null || true
    local waited=0
    while [[ $waited -lt 10 ]]; do
        local all_gone=1
        [[ -n "$BACKEND_PID" ]]  && kill -0 "$BACKEND_PID"  2>/dev/null && all_gone=0
        [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null && all_gone=0
        [[ "$all_gone" -eq 1 ]] && break
        sleep 1; waited=$((waited + 1))
    done
    [[ -n "$BACKEND_PID" ]]  && kill -9 "$BACKEND_PID"  2>/dev/null || true
    [[ -n "$FRONTEND_PID" ]] && kill -9 "$FRONTEND_PID" 2>/dev/null || true
    rm -f "$LOG_DIR/backend.pid" "$LOG_DIR/frontend.pid" "$LOG_DIR/tail.pid"
    ok "Stopped"
}
trap cleanup EXIT INT TERM

# ── Tail logs ────────────────────────────────────────────────────────────────
if [[ "$VERBOSE" -eq 0 ]] && [[ -n "$BACKEND_PID" ]] || [[ -n "$FRONTEND_PID" ]]; then
    log "Tailing logs (Ctrl+C to stop)"
    echo ""
    tail -f \
        "$LOG_DIR/backend.log" \
        "$LOG_DIR/frontend.log" 2>/dev/null &
    TAIL_PID=$!
    echo "$TAIL_PID" > "$LOG_DIR/tail.pid"
fi

# ── Wait for processes ───────────────────────────────────────────────────────
if [[ -n "$BACKEND_PID" ]] && [[ -n "$FRONTEND_PID" ]]; then
    wait "$BACKEND_PID" "$FRONTEND_PID"
elif [[ -n "$BACKEND_PID" ]]; then
    wait "$BACKEND_PID"
elif [[ -n "$FRONTEND_PID" ]]; then
    wait "$FRONTEND_PID"
else
    warn "Nothing to start — use --help for options"
    exit 0
fi