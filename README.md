<div align="center">

# 🎬 Watchfy

**A multi-source video aggregation platform with a cinematic UI and security-first proxy.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://python.org)
[![Node 18+](https://img.shields.io/badge/Node-18+-green.svg)](https://nodejs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)
[![CI](https://github.com/BlusceLabs/Watchfy/actions/workflows/ci.yml/badge.svg)](https://github.com/BlusceLabs/Watchfy/actions)

</div>

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🔒 | **Security-first** | SSRF guard, signed tokens, CDN never exposed to the browser |
| 🎬 | **Multi-source streaming** | White + Black providers with quality selection (1080p, 720p, etc.) |
| 🎨 | **Cinematic UI** | Astro SSR + React/Svelte/Qwik islands, Framer Motion animations |
| 🐳 | **Docker ready** | One command to run the full stack with `docker-compose` |

---

## 🚀 Quick Start

```bash
# 1. Clone & install
git clone https://github.com/BlusceLabs/Watchfy.git && cd Watchfy
./setup.sh

# 2. Set your TMDB API key
$EDITOR backend/.env    # set TMDB_API_KEY=...

# 3. Start everything
./start.sh
```

Then open:
- **Web app** → http://localhost:4321
- **API docs** → http://localhost:8000/api/docs
- **Health check** → http://localhost:8000/api/health

<details>
<summary>🐳 Production (Docker)</summary>

```bash
cp .env.example .env
$EDITOR .env                    # set TMDB_API_KEY

make docker-build               # build all images
make docker-up                  # start the stack
make docker-logs                # tail logs
make docker-ps                  # list services
make docker-down                # stop
```

| Service   | Image               | Host port | Internal URL          |
|-----------|---------------------|-----------|-----------------------|
| frontend  | `watchfy/frontend`  | 4321      | http://frontend:4321  |
| extractor | `watchfy/extractor` | —         | http://extractor:8000 |
| gateway   | `watchfy/gateway`   | 8080      | http://gateway:8080   |

The frontend is the only port that should be exposed publicly. The extractor and gateway sit on the private network.

</details>

<details>
<summary>🔧 Running services individually</summary>

```bash
# Backend (uvicorn, with reload)
source .venv/bin/activate
cd backend && uvicorn main:app --reload --port 8000

# Frontend (Astro dev server)
cd frontend && pnpm dev --port 4321

# Go gateway (optional, dormant by default)
cd backend/gateway && go run ./cmd/api
```

Equivalent Makefile shortcuts: `make backend`, `make frontend`, `make gateway`.

</details>

---

## 📸 Screenshots

<!-- Add your screenshots here -->
| Home | Player |
|------|--------|
| ![Home](docs/home.png) | ![Player](docs/player.png) |

---

## 🏗️ Architecture

<details>
<summary>📐 Click to expand architecture diagram</summary>

```
                ┌──────────────────────────────────────────────────────────┐
                │                       Browser                            │
                │  Astro SSR (4321) + React/Svelte/Qwik islands + hls.js   │
                └────────────┬─────────────────────────────────────────────┘
                             │ /api/*  /continue-watching  /user  /ads
                             ▼
                ┌──────────────────────────────────────────────────────────┐
                │                   FastAPI backend (8000)                 │
                │                                                          │
                │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
                │  │ /api/tmdb/*  │  │ /api/proxy/* │  │ /api/ffmpeg/*  │  │
                │  │  metadata    │  │  HLS proxy   │  │  remux/probe   │  │
                │  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │
                │         │                 │                  │           │
                │  ┌──────┴───────┐  ┌──────┴───────┐  ┌───────┴────────┐  │
                │  │  SSRF guard  │  │ Token store  │  │  Subtitle      │  │
                │  │ (allowlist + │  │ (TTLCache)   │  │  proxy + hook  │  │
                │  │  private IP) │  │              │  │                │  │
                │  └──────────────┘  └──────┬───────┘  └────────────────┘  │
                │                            │                             │
                │                  ┌─────────┴──────────┐                  │
                │                  │ white / black      │                  │
                │                  │ provider extractors│                  │
                │                  └─────────┬──────────┘                  │
                └────────────────────────────┼─────────────────────────────┘
                                             │  HTTPS (allowlisted CDNs only)
                                             ▼
                          easy.speedsterwave.app · cdn.vidking.net
                          cloudnestra.com · 111movies.net · cdn.jwplayer.com
                          content.jwplatform.com · cdn.plyr.io
                          dl.subdl.com (subtitles)
```

Optional parallel Go gateway (`:8080`) exposes the same surface in Fiber. It is dormant in `start.sh`.

</details>

---

## 🛠️ Tech Stack

| Layer | Tech |
|-------|------|
| **Frontend** | Astro 4, React 19, Svelte 5, Qwik, Tailwind CSS, hls.js, Framer Motion |
| **Backend** | Python 3.11+, FastAPI, uvicorn, httpx, patchright/scrapling, ffmpeg |
| **Gateway** | Go 1.22, Fiber v2 |
| **Package Manager** | pnpm 8 (workspaces) |
| **Containers** | Docker, docker-compose |

---

## 📂 Repository Layout

<details>
<summary>📁 Click to expand</summary>

```
.
├── frontend/                       # Astro app
│   ├── astro.config.mjs            # SSR config + Vite proxy to backend
│   ├── src/
│   │   ├── pages/                  # File-based routes
│   │   ├── components/             # .astro / .tsx / .svelte / .qwik
│   │   ├── layouts/
│   │   └── lib/
│   └── packages/                   # Local workspace packages
│       ├── animations/             # GPU-accelerated effects
│       ├── design-tokens/          # Color + spacing tokens
│       ├── shared-types/           # Movie, TVShow, VideoSource
│       └── ui-primitives/          # Button, Modal, Tooltip
│
├── backend/                        # Python FastAPI service
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── api/
│   │   │   ├── providers/          # white.py, black.py
│   │   │   ├── proxy.py            # HLS proxy
│   │   │   ├── ffmpeg_remux.py     # /remux and /probe
│   │   │   └── tmdb.py             # TMDB passthrough
│   │   ├── core/extractors/        # HLS / RC4 extraction
│   │   ├── lib/                    # Cache, redis_utils
│   │   └── middleware/             # gzip, CDN, security headers
│   ├── ssrf.py                     # SSRF guard
│   ├── auth.py                     # Auth, mass-assignment guard
│   ├── tests/                      # stdlib unittest suite
│   ├── gateway/                    # Go gateway (Fiber)
│   └── requirements.txt
│
├── scripts/start.sh                # Convenience runner
├── setup.sh                        # Creates .venv, installs deps
├── docker-compose.yml              # Full stack orchestration
├── Makefile                        # Alt entry points
└── pnpm-workspace.yaml
```

</details>

---

## ⚙️ Environment Variables

<details>
<summary>🔑 Click to expand</summary>

### `backend/.env` (required)

```ini
TMDB_API_KEY=your_tmdb_api_key_here
WATCHFY_EXTRACTOR_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:4321    # comma-separated; defaults to "*"
LOG_LEVEL=INFO
```

Additional knobs:
- `BLACK_CACHE_TTL`, `BLACK_STALE_TTL` — source extraction cache
- `REDIS_URL` — optional Redis caching
- `SSL_KEYFILE`, `SSL_CERTFILE` — for HTTPS

### `frontend/.env` (optional)

```ini
BACKEND_URL=https://api.example.com   # only if backend is on a different origin in prod
```

In dev the Astro Vite proxy forwards `/api`, `/continue-watching`, `/user`, `/ads` to `http://localhost:8000`.

</details>

---

## 🧪 Test Suite

<details>
<summary>📋 Click to expand</summary>

```bash
make test
```

Runs:
1. `cd frontend && npm run build` — Astro type check + Vite build
2. `go test ./...` in `backend/gateway` — Go unit tests
3. `cd backend && python3 -m unittest discover -s tests -v` — Python unit tests (59 tests)
4. `python3 -m compileall -q backend` — syntax check

### Coverage

| File | Count | What's tested |
|------|-------|---------------|
| `test_ssrf.py` | 26 | Allowlist, RFC1918, loopback, IMDS, redirect hook |
| `test_auth.py` | 13 | Mass-assignment guard, field restrictions |
| `test_continue_watching.py` | 2 | Source server allowlist |
| `test_security_headers.py` | 19 | CSP, HSTS, COOP, CORP, Permissions-Policy |
| `tmdb_utils_test.go` | 30 | Path safety, date parsing, image URLs |

### Pre-commit hooks

```bash
make install-hooks   # installs via lefthook
```

</details>

---

## 🔒 Security Model

<details>
<summary>🛡️ Click to expand</summary>

Five layers, ordered by blast radius:

1. **SSRF guard** (`backend/ssrf.py`) — Every outbound URL is validated against an allowlist. DNS resolution to private IPs is rejected. The httpx redirect hook re-validates on every 3xx.

2. **Mass-assignment guard** (`backend/auth.py`) — Only `{email, username}` are writable. Privilege and credential columns are never exposed.

3. **Provider allowlist** (`backend/continue_watching.py`) — Source server constrained to `{white, black}`.

4. **HLS token store** (`backend/app/api/proxy.py`) — SHA256 tokens with TTL, bounded in count and age.

5. **Security headers** (`app/middleware/security_headers.py`) — CSP, HSTS, COOP, CORP, Permissions-Policy on every response. Override with env vars.

</details>

---

## 📡 Provider Model

| Name | Difficulty | Returns | Use case |
|------|------------|---------|----------|
| `white` | Easier | Multiple quality URLs (1080p, 720p) | **Default** — canonical provider |
| `black` | Cloudflare-protected | Single working source | **Fallback** when white fails |

<details>
<summary>➕ Adding a third provider</summary>

1. Create `backend/app/api/providers/yourname.py` exposing `router`
2. Mount it in `app/main.py`
3. Add the name to `_ALLOWED_SOURCE_SERVERS` in `backend/continue_watching.py`
4. Add to `allowedServers` in `frontend/src/lib/api.ts`

</details>

---

## 📊 Service Status

| Service | Status | Started by `start.sh`? |
|---------|--------|------------------------|
| `backend/` (Python · FastAPI) | ✅ Live | Yes (port 8000) |
| `frontend/` (Astro) | ✅ Live | Yes (port 4321) |
| `backend/gateway/` (Go · Fiber) | ⚠️ Dormant | No — run manually |

---

## 🔧 Troubleshooting

<details>
<summary>❓ Common issues</summary>

**`patchright install chromium` fails behind a corporate proxy.**
Set `HTTPS_PROXY=http://your-proxy:port` before running `setup.sh`.

**`hls.js` keeps reloading the manifest at ~50 min.**
Pre-9.x versions stripped `#EXT-X-ENDLIST`. The current code preserves it. Check that `proxy.py` and providers don't call `_strip_endlist`.

**`ssrf_blocked_redirect` warnings in logs.**
An upstream CDN is returning a 302 to a host outside the allowlist. Review and add to `ssrf.ALLOWED_HOSTS` if legitimate.

**`mass_assignment_blocked` in auth log.**
A request included a field outside `{email, username}`. The guard is working — nothing to do.

**`continue_watching` POST fails with `400 source_server`.**
The source server isn't in `{white, black}`. Add a new provider or correct the client.

**`pylance` reports errors in `@qwikdev/astro`.**
Third-party type mismatches — not from this codebase. Ignore or install `@types/node`.

</details>

---

## 📜 License

[MIT](./LICENSE) — Copyright (c) 2026 BlusceLabs.
