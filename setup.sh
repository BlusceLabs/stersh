#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# watchfy setup script
# Usage:
#   chmod +x setup.sh && ./setup.sh          # full install
#   ./setup.sh --dev                         # install + start dev server
#   ./setup.sh --docker                      # build + start Docker stack
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MODE="${1:-}"
PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}▶ $*${NC}"; }
ok()   { echo -e "${GREEN}✔ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
err()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

# ── Docker mode ───────────────────────────────────────────────────────────────
if [[ "$MODE" == "--docker" ]]; then
    log "Building and starting watchfy Docker stack…"
    command -v docker compose &>/dev/null || err "docker compose not found"
    docker compose build --no-cache
    docker compose up -d
    ok "watchfy running at http://localhost"
    docker compose logs -f backend
    exit 0
fi

# ── Check Python version ──────────────────────────────────────────────────────
PYTHON_CANDIDATES=("python3.12" "python3.11" "python3")
PYTHON="${PYTHON:-}"
for candidate in "${PYTHON_CANDIDATES[@]}"; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
PYVER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log "Detected Python $PYVER"
[[ $(echo "$PYVER >= 3.11" | bc -l) -eq 1 ]] || err "Python 3.11+ required (got $PYVER)"

# ── Create virtualenv ─────────────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtual environment in $VENV_DIR…"
    $PYTHON -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ok "Virtual environment active"

# ── Install Python deps ───────────────────────────────────────────────────────
log "Installing Python dependencies…"
pip install --quiet --upgrade pip
if [[ -f "backend/requirements.txt" ]]; then
    pip install --quiet -r backend/requirements.txt
else
    pip install --quiet -r requirements.txt
fi
# Install curl_cffi (needed by scrapling, not always pulled automatically)
pip install --quiet curl_cffi 2>/dev/null || true
ok "Python dependencies installed"

# ── Install Patchright (Playwright fork) browser ────────────────────────────
log "Installing Chromium browser for patchright/scrapling…"
if ! python3 -m patchright install chromium 2>&1 | tail -5; then
    warn "Patchright install may need manual intervention - run manually if needed"
fi
ok "Chromium ready for scrapling Cloudflare bypass"

# ── Check ffmpeg ──────────────────────────────────────────────────────────────
if command -v ffmpeg &>/dev/null; then
    FFVER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    ok "ffmpeg found: $FFVER"
else
    warn "ffmpeg not found — remux / download features will be unavailable"
    warn "Install with: sudo apt install ffmpeg  OR  brew install ffmpeg"
fi

# ── Scaffold .env ─────────────────────────────────────────────────────────────
if [[ ! -f "backend/.env" ]]; then
    if [[ -f "backend/.env.example" ]]; then
        cp backend/.env.example backend/.env
    else
        cp .env.example backend/.env
    fi
    ok "Created backend/.env from .env.example — fill in your API keys"
else
    ok "backend/.env already exists"
fi

# ── Create frontend dir ───────────────────────────────────────────────────────
mkdir -p frontend
if [[ -f "index.html" ]] && [[ ! -f "frontend/index.html" ]]; then
    cp index.html frontend/index.html
    ok "Copied index.html → frontend/index.html"
fi

# ── Nginx SSL stub ────────────────────────────────────────────────────────────
if [[ -d "nginx" ]] && [[ ! -d "nginx/ssl" ]]; then
    mkdir -p nginx/ssl
    warn "No SSL certificates found at nginx/ssl/"
    warn "For local dev: openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem -days 365 -nodes -subj '/CN=localhost'"
fi

echo ""
ok "watchfy setup complete!"
echo ""
echo "  Start dev server:     cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo "  Start Docker stack:   ./setup.sh --docker"
echo "  Open browser:         http://localhost:8000"
echo ""

# ── Dev server mode ───────────────────────────────────────────────────────────
if [[ "$MODE" == "--dev" ]]; then
    log "Starting dev server…"
    cd backend && exec uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
fi