#!/usr/bin/env bash

# =========================================================
# WATCH!FY UNIVERSAL STARTER
# =========================================================
# Detects OS
# Installs dependencies
# Installs Go / Python / Node if missing
# Installs frontend + backend packages
# Starts:
#   - Golang Gateway
#   - Python Streaming Service
#   - React Frontend
#
# Supports:
#   - Ubuntu / Debian
#   - Arch Linux
#   - Fedora
#   - macOS
#   - Windows (Git Bash / WSL)
#
# =========================================================

set -e
set -m

# =========================================================
# COLORS
# =========================================================

GREEN='\033[1;32m'
RED='\033[1;31m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

# =========================================================
# LOGGING
# =========================================================

log() {
  echo -e "${GREEN}[WATCH!FY]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

info() {
  echo -e "${CYAN}[INFO]${NC} $1"
}

# Get script directory and change to Watch!fy root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHIFY_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$WATCHIFY_ROOT"
log "Working directory: $(pwd)"

# =========================================================
# BANNER
# =========================================================

clear

echo -e "${BLUE}"
cat << "EOF"

██╗    ██╗ █████╗ ███████╗ ██████╗██╗  ██╗██╗███████╗██╗   ██╗
██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║██║██╔════╝╚██╗ ██╔╝
██║ ██╗██║███████║   ██║   ██║     ███████║██║█████╗   ╚████╔╝
██║███╗██║██╔══██║   ██║   ██║     ██╔══██║██║██╔══╝    ╚██╔╝
╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║██║██║        ██║
 ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝

EOF
echo -e "${NC}"

# =========================================================
# OS DETECTION
# =========================================================

OS="unknown"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then

  if [ -f /etc/arch-release ]; then
    OS="arch"

  elif [ -f /etc/fedora-release ]; then
    OS="fedora"

  else
    OS="debian"
  fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"

elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
  OS="windows"
fi

log "Detected OS: $OS"

# =========================================================
# PACKAGE INSTALLERS
# =========================================================

install_debian() {

  sudo apt update

  sudo apt install -y \
    curl \
    wget \
    git \
    unzip \
    ffmpeg \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm

  # GO
  if ! command -v go &> /dev/null; then

    log "Installing Golang..."

    wget https://go.dev/dl/go1.24.2.linux-amd64.tar.gz

    sudo rm -rf /usr/local/go

    sudo tar -C /usr/local -xzf go1.24.2.linux-amd64.tar.gz

    export PATH=$PATH:/usr/local/go/bin

    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
  fi
}

install_arch() {

  sudo pacman -Sy --noconfirm \
    curl \
    wget \
    git \
    unzip \
    ffmpeg \
    base-devel \
    python \
    python-pip \
    nodejs \
    npm \
    go
}

install_fedora() {

  sudo dnf install -y \
    curl \
    wget \
    git \
    unzip \
    ffmpeg \
    gcc \
    gcc-c++ \
    make \
    python3 \
    python3-pip \
    nodejs \
    npm \
    golang
}

install_macos() {

  if ! command -v brew &> /dev/null; then

    error "Homebrew not installed."

    echo "Install Homebrew first:"
    echo "https://brew.sh"

    exit 1
  fi

  brew install \
    ffmpeg \
    python \
    node \
    go \
    git
}

# =========================================================
# RUN INSTALLER
# =========================================================

log "Installing dependencies..."

case $OS in

  debian)
    install_debian
    ;;

  arch)
    install_arch
    ;;

  fedora)
    install_fedora
    ;;

  macos)
    install_macos
    ;;

  windows)
    warn "Use WSL recommended."
    ;;

  *)
    error "Unsupported OS"
    exit 1
    ;;
esac

# =========================================================
# CHECK REQUIRED COMMANDS
# =========================================================

REQUIRED_COMMANDS=(
  node
  npm
  python3
  pip3
  go
  ffmpeg
)

for cmd in "${REQUIRED_COMMANDS[@]}"
do
  if ! command -v $cmd &> /dev/null; then
    error "$cmd not installed"
    exit 1
  fi
done

log "All required binaries installed."

# =========================================================
# ROOT CHECK
# =========================================================

if [ ! -f "pnpm-workspace.yaml" ]; then
  error "Run this script from Watch!fy root."
  exit 1
fi

# =========================================================
# INSTALL PNPM
# =========================================================

if ! command -v pnpm &> /dev/null; then

  log "Installing pnpm..."

  npm install -g pnpm
fi

# =========================================================
# FRONTEND INSTALL
# =========================================================

log "Installing frontend dependencies..."

cd "$WATCHIFY_ROOT/apps/web"

pnpm install

cd "$WATCHIFY_ROOT"

# =========================================================
# PYTHON STREAMING SERVICE
# =========================================================

log "Setting up Python streaming service..."

cd "$WATCHIFY_ROOT/backend/services/streaming"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate

pip install --upgrade pip

pip install \
  fastapi \
  uvicorn \
  httpx \
  playwright \
  cachetools \
  python-dotenv \
  ffmpeg-python

python -m playwright install chromium

deactivate

cd "$WATCHIFY_ROOT"

# =========================================================
# GOLANG GATEWAY
# =========================================================

log "Installing Go dependencies..."

cd "$WATCHIFY_ROOT/backend/gateway"

go mod tidy

cd "$WATCHIFY_ROOT"

# =========================================================
# ENV FILES
# =========================================================

if [ ! -f "$WATCHIFY_ROOT/backend/gateway/.env" ]; then

cat > "$WATCHIFY_ROOT/backend/gateway/.env" <<EOF
TMDB_API_KEY=
VIDKING_EXTRACTOR_URL=http://localhost:8000
EOF

  warn "Fill backend/gateway/.env"
fi

if [ ! -f "$WATCHIFY_ROOT/apps/web/.env" ]; then

cat > "$WATCHIFY_ROOT/apps/web/.env" <<EOF
VITE_API_URL=http://localhost:8080/api
EOF
fi

# =========================================================
# CHECK PORT HELPER
# =========================================================

port_in_use() {
  lsof -i ":$1" >/dev/null 2>&1
}

# Find first available port in 18000-18999 range
find_available_port() {
  for port in $(seq 18000 18999); do
    if ! port_in_use $port; then
      echo $port
      return
    fi
  done
  error "No available ports in 18000-18999"
  exit 1
}

# =========================================================
# START SERVICES
# =========================================================

log "Starting Watch!fy services..."

# Kill any leftover servers from previous runs
for port in 8000 8080; do
  pid=$(lsof -ti:$port 2>/dev/null) && kill -9 $pid 2>/dev/null || true
done

log "Starting streaming service..."

cd "$WATCHIFY_ROOT/backend/services/streaming"

source venv/bin/activate

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload &

STREAMING_PID=$!

cd "$WATCHIFY_ROOT"

# =========================================================
# GOLANG GATEWAY
# =========================================================

log "Starting gateway..."

cd "$WATCHIFY_ROOT/backend/gateway"

go run cmd/server/main.go &

GATEWAY_PID=$!

cd "$WATCHIFY_ROOT"

# =========================================================
# FRONTEND
# =========================================================

FRONTEND_PORT=$(find_available_port)

log "Starting frontend..."

cd "$WATCHIFY_ROOT/apps/web"

PORT=$FRONTEND_PORT GATEWAY_PORT=8080 pnpm dev &

FRONTEND_PID=$!

cd "$WATCHIFY_ROOT"

# =========================================================
# SUCCESS
# =========================================================

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} WATCH!FY IS RUNNING${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

echo -e "${CYAN}Frontend:${NC}  http://localhost:$FRONTEND_PORT"
echo -e "${CYAN}Gateway:${NC}   http://localhost:8080"
echo -e "${CYAN}Streaming:${NC} http://localhost:8000"

echo ""
echo -e "${YELLOW}Press CTRL+C to stop all services${NC}"

# =========================================================
# CLEANUP
# =========================================================

CLEANED_UP=0

cleanup() {

  # Prevent re-entry from multiple signals
  [ "$CLEANED_UP" = "1" ] && return
  CLEANED_UP=1

  echo ""
  warn "Stopping Watch!fy..."

  # Kill entire process groups (negative PID = process group)
  # This ensures all spawned child processes are cleaned up
  for pid in "$STREAMING_PID" "$GATEWAY_PID" "$FRONTEND_PID"; do
    [ -n "$pid" ] && kill -- -$pid 2>/dev/null || kill $pid 2>/dev/null || true
  done

  log "Stopped."
}

trap cleanup EXIT INT TERM

wait
