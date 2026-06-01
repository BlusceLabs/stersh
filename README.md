# Watchfy

A cinematic streaming platform — multi-source video aggregation with a cinematic UI, a
playback API, and mobile clients.

The current code in this repo is a **monorepo** with three runnable services and an
Android client. The Python backend is the source of truth for streaming; the Go gateway
is a parallel implementation that is **not yet wired into `start.sh`** (see
[Status of the three services](#status-of-the-three-services)).

---

## Tech stack (what's actually in the repo)

| Layer | Tech |
|---|---|
| Web frontend | **Astro 4** (SSR via `@astrojs/node`) with **React 19 + Svelte 5 + Qwik** islands, Tailwind CSS, `hls.js`, Framer Motion |
| Frontend packages | Local pnpm workspace packages: `animations`, `design-tokens`, `shared-types`, `ui-primitives` |
| Streaming backend | **Python 3.11+ · FastAPI** (uvicorn, httpx, patchright/scrapling for Cloudflare bypass, ffmpeg for remux) |
| Gateway (alt) | **Go 1.22 · Fiber v2** with a handler/service layout for home, search, details, watch, subtitles |
| Mobile | **Android** (Kotlin, Gradle KTS, Hilt DI, Room) — see [`android/`](./android) |
| Package manager | **pnpm 8** (workspaces) |

> ⚠️ The previous README listed `TanStack Router` and `Video.js` — neither is used. The
> project uses Astro's file-based routing and `hls.js` for playback.

---

## Repository layout

```
.
├── frontend/                    # Astro app
│   ├── astro.config.mjs         # SSR config + Vite proxy to backend
│   ├── src/
│   │   ├── pages/               # File-based routes (home, movies, tv, search, watch/...)
│   │   ├── components/          # Astro/React/Svelte/Qwik components
│   │   ├── layouts/
│   │   └── lib/
│   └── packages/                # Local pnpm workspace packages
│       ├── animations/
│       ├── design-tokens/
│       ├── shared-types/
│       └── ui-primitives/
├── backend/                     # Python FastAPI service (the live one)
│   ├── app/
│   │   ├── main.py              # FastAPI app entry — providers + feature routers
│   │   ├── api/
│   │   │   ├── providers/black.py   # Cloudflare-protected source (uses patchright)
│   │   │   ├── providers/white.py   # Easier source
│   │   │   ├── proxy.py             # Generic proxy
│   │   │   ├── ffmpeg_remux.py
│   │   │   └── tmdb.py
│   │   ├── core/extractors/     # HLS / RC4 / provider extraction
│   │   ├── lib/
│   │   └── middleware/
│   ├── *.py                     # Feature routers (auth, ads, analytics, ...)
│   ├── requirements.txt
│   ├── main.py                  # Shim → app.main:app
│   ├── black.py                 # Shim → app.core.extractors.black
│   └── gateway/                 # Go + Fiber service (separate binary, see below)
├── android/                     # Kotlin / Gradle Android client
├── scripts/start.sh             # Convenience runner (backend + frontend)
├── setup.sh                     # Installs Python deps, patchright chromium, copies .env
├── health_check.sh
├── Makefile                     # Alternative entry points (npm + uvicorn black:app)
└── pnpm-workspace.yaml
```

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | **3.11+** (3.12 recommended) | Required by `setup.sh` |
| Node.js | 18+ | |
| pnpm | 8+ | CI uses `pnpm/action-setup@v2` v8 |
| Go | 1.22+ | Only needed if you build the gateway |
| ffmpeg | any recent | **Optional** — only needed for remux/download features |
| Chromium | via patchright | Installed by `setup.sh` |

---

## Quick start

```bash
# 1. Install everything (creates .venv, installs Python deps, installs Chromium, copies .env)
./setup.sh

# 2. Fill in your TMDB key
$EDITOR backend/.env        # set TMDB_API_KEY=...

# 3. Install frontend deps
cd frontend && pnpm install && cd ..

# 4. Start backend + frontend together
./start.sh
```

Then open:

- Web app → http://localhost:4321
- API docs → http://localhost:8000/api/docs
- Backend health → http://localhost:8000/api/health

`start.sh` tails logs from both services to `/tmp/watchfy-logs/`.

### Run services individually

```bash
# Backend only
source .venv/bin/activate
cd backend && uvicorn main:app --reload --port 8000

# Frontend only
cd frontend && pnpm dev --port 4321

# Go gateway (optional / experimental)
cd backend/gateway && go run ./cmd/api
```

---

## Environment variables

### `backend/.env` (required)

```ini
TMDB_API_KEY=your_tmdb_api_key_here      # https://www.themoviedb.org/settings/api
VIDKING_EXTRACTOR_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:4321     # comma-separated; defaults to "*"
LOG_LEVEL=INFO
```

Additional knobs consumed by individual routers (see `backend/*.py`):

- `BLACK_CACHE_TTL`, `BLACK_STALE_TTL` — source extraction cache
- `REDIS_URL` — optional Redis caching
- `SSL_KEYFILE`, `SSL_CERTFILE` — for `run.py` if you want HTTPS

### `frontend/.env` (optional)

```ini
# Only needed if the backend lives on a different origin in production
BACKEND_URL=https://api.example.com
```

In dev the Astro Vite proxy already forwards `/api`, `/continue-watching`, `/user`,
`/ads`, and `/analytics` to `http://localhost:8000`.

---

## Status of the three services

| Service | Status | Started by `start.sh`? |
|---|---|---|
| `backend/` (Python · FastAPI) | ✅ Live — providers, extraction, FFmpeg, analytics, etc. | Yes (port 8000) |
| `frontend/` (Astro) | ✅ Live — UI for all pages | Yes (port 4321) |
| `backend/gateway/` (Go · Fiber) | ⚠️ Dormant — alt implementation, runs to `:8080` if you start it manually | **No** |

`backend/gateway/server` is a pre-built Linux binary committed to the repo. It is
~13 MB and won't run on macOS/Windows as-is. Run from source instead:
`cd backend/gateway && go run ./cmd/api`.

---

## Project conventions

- **Providers** live under `backend/app/api/providers/`. Each provider exposes its own
  router and is mounted by `app/main.py`. The current ones are `black` (Cloudflare,
  uses Patchright/Scrapling) and `white` (simpler source).
- **Feature routers** live at the top of `backend/` (e.g. `auth.py`, `ads.py`,
  `analytics.py`, `continue_watching.py`, `subtitles.py`, `parental_controls.py`,
  `user_features.py`, `tmdb.py`) and are wired in by `app/main.py`.
- **Frontend packages** are local pnpm workspace packages; import them as
  `@watchfy/animations`, `@watchfy/design-tokens`, `@watchfy/shared-types`,
  `@watchfy/ui-primitives`.
- **Astro islands**: pages are `.astro` files; interactive components may be `.tsx`
  (React), `.svelte`, or `.qwik` — pick the framework per component, not per page.

---

## Known setup gotchas

- `Makefile` uses **npm** and points at `uvicorn black:app`. `start.sh` uses **pnpm**
  and points at `uvicorn main:app`. **Prefer `start.sh`.**
- `health_check.sh` probes the wrong ports (frontend `:3000`, backend `/health`) and
  isn't reliable yet — use the URL table above instead.
- `pnpm-workspace.yaml` lists `apps/*` and `packages/*`, but `frontend/` sits at the
  root, not under `apps/`. CI's `pnpm --filter web build` will not match anything
  until that's restructured.
- The pre-built `backend/gateway/server` binary is committed; rebuild from source for
  your platform.
- The Android `watchfy-release.jks` keystore is committed to the repo. **Do not reuse
  it for production** — it should be moved out of source control.

---

## License

Add a `LICENSE` file at the repo root to make this explicit.
