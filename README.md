# Watchfy

A multi-source video aggregation platform with a cinematic UI, an HLS-aware
playback proxy, and a security-first server side. The Python backend is the
source of truth for streaming; the Go gateway is a parallel implementation
that runs alongside when started manually.

---

## Table of contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Running services individually](#running-services-individually)
- [Environment variables](#environment-variables)
- [Test suite](#test-suite)
- [Security model](#security-model)
- [Provider model](#provider-model)
- [Known setup gotchas](#known-setup-gotchas)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## What it does

Watchfy aggregates public movie and TV metadata from TMDB and pairs it with
streaming sources from a small allowlist of upstream CDNs. The browser never
contacts those CDNs directly — every manifest, segment, and subtitle request
flows through the backend's signed-token proxy, which:

- Resolves TMDB metadata once and caches it.
- Resolves the actual HLS source per request (via the `white` provider for
  quality URLs, or the `black` provider as a Cloudflare-protected fallback).
- Rewrites manifest URLs to a per-token `proxy/hls` endpoint so the upstream
  CDN is never exposed to the client.
- Serves segments through the same proxy with short-lived tokens.
- Injects subtitles from `dl.subdl.com` through `/subtitles/proxy`.

The frontend is a single Astro app with islands of React, Svelte 5, and Qwik
chosen per component, not per page.

---

## Architecture

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

Optional parallel Go gateway (`:8080`) exposes the same surface in Fiber.
It is dormant in `start.sh` — see [Status of the three services](#status-of-the-three-services).

---

## Tech stack

| Layer | Tech |
|---|---|
| Web frontend | **Astro 4** (SSR via `@astrojs/node`) with **React 19 + Svelte 5 + Qwik** islands, Tailwind CSS, `hls.js`, Framer Motion |
| Frontend packages | Local workspace packages: `animations`, `design-tokens`, `shared-types`, `ui-primitives` |
| Streaming backend | **Python 3.11+ · FastAPI** (uvicorn, httpx, patchright/scrapling for Cloudflare bypass, ffmpeg for remux) |
| Gateway (alt) | **Go 1.22 · Fiber v2** with handler/service layout for home, search, details, watch, subtitles |
| Package manager | **pnpm 8** (workspaces) |

---

## Repository layout

```
.
├── frontend/                       # Astro app
│   ├── astro.config.mjs            # SSR config + Vite proxy to backend
│   ├── src/
│   │   ├── pages/                  # File-based routes (home, movies, tv, search, watch/...)
│   │   ├── components/             # .astro / .tsx / .svelte / .qwik components
│   │   ├── layouts/
│   │   └── lib/
│   └── packages/                   # Local workspace packages
│       ├── animations/             # GPU-accelerated fade/scale/slide entrance effects
│       ├── design-tokens/          # Color + spacing tokens (typed)
│       ├── shared-types/           # Movie, TVShow, VideoSource, MediaItem
│       └── ui-primitives/          # Button, Modal, Tooltip (React)
│
├── backend/                        # Python FastAPI service (the live one)
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry — providers + feature routers
│   │   ├── api/
│   │   │   ├── providers/
│   │   │   │   ├── black.py        # Cloudflare-protected source (patchright)
│   │   │   │   └── white.py        # Easier source — quality URLs
│   │   │   ├── proxy.py            # Generic proxy (HLS + segments)
│   │   │   ├── ffmpeg_remux.py     # /remux and /probe
│   │   │   └── tmdb.py             # TMDB passthrough
│   │   ├── core/extractors/        # HLS / RC4 / provider extraction
│   │   ├── lib/                    # Cache, redis_utils
│   │   └── middleware/             # gzip, CDN, etc.
│   ├── ssrf.py                     # SSRF guard (allowlist + private-IP rejection)
│   ├── auth.py                     # Auth, mass-assignment guard
│   ├── ads.py                      # Ad tracking with placement validation
│   ├── continue_watching.py        # Resume-watching, source_server allowlist
│   ├── startup_tasks.py            # Warmup + cache priming
│   ├── main.py                     # Shim → app.main:app
│   ├── black.py                    # Shim → app.core.extractors.black
│   ├── tests/                      # stdlib unittest suite (no pytest required)
│   │   ├── test_ssrf.py            # 26 tests: allowlist, private IP, control chars, redirect hook
│   │   ├── test_auth.py            # 13 tests: mass-assignment guard
│   │   └── test_continue_watching.py # 2 tests: source_server allowlist
│   ├── gateway/
│   │   ├── cmd/                    # Go entry points
│   │   └── internal/services/      # Service layer + tmdb_utils_test.go
│   └── requirements.txt
│
├── scripts/start.sh                # Convenience runner (backend + frontend)
├── setup.sh                        # Creates .venv, installs deps, copies .env
├── health_check.sh                 # Smoke probe
├── Makefile                        # Alt entry points
└── pnpm-workspace.yaml
```

---

## Quick start

```bash
# 1. Install everything (Python deps, patchright chromium, frontend deps, .env)
./setup.sh

# 2. Fill in your TMDB key
$EDITOR backend/.env                # set TMDB_API_KEY=...

# 3. Start backend + frontend together (logs → /tmp/watchfy-logs/)
./start.sh
```

Then open:

- Web app → http://localhost:4321
- API docs → http://localhost:8000/api/docs
- Backend health → http://localhost:8000/api/health

---

## Running services individually

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

---

## Environment variables

### `backend/.env` (required)

```ini
TMDB_API_KEY=your_tmdb_api_key_here
WATCHFY_EXTRACTOR_URL=http://localhost:8000   # legacy alias: VIDKING_EXTRACTOR_URL
ALLOWED_ORIGINS=http://localhost:4321        # comma-separated; defaults to "*"
LOG_LEVEL=INFO
```

Additional knobs consumed by individual routers:

- `BLACK_CACHE_TTL`, `BLACK_STALE_TTL` — source extraction cache
- `REDIS_URL` — optional Redis caching
- `SSL_KEYFILE`, `SSL_CERTFILE` — for `run.py` if you want HTTPS

### `frontend/.env` (optional)

```ini
BACKEND_URL=https://api.example.com   # only if backend is on a different origin in prod
```

In dev the Astro Vite proxy forwards `/api`, `/continue-watching`, `/user`,
`/ads`, `/analytics` to `http://localhost:8000`.

---

## Test suite

```bash
make test
```

Runs:

1. `cd frontend && npm run build` — Astro type check + Vite build
2. `go test ./...` in `backend/gateway` — Go unit tests (30 subtests across `tmdb_utils_test.go`)
3. `cd backend && python3 -m unittest discover -s tests -v` — Python unit tests
4. `python3 -m compileall -q backend` — syntax check on every `.py` file

The Python suite uses only the stdlib `unittest` module — no extra deps.

### What's covered

| File | Count | Pins |
|---|---|---|
| `test_ssrf.py` | 26 | Allowlist miss · RFC1918/loopback/IMDS/link-local/multicast/unspecified rejection · control characters · oversize URLs · non-http schemes · async redirect hook (`async def redirect_event_hook` re-validates 3xx Location headers) |
| `test_auth.py` | 13 | `_UPDATABLE_USER_FIELDS = {email, username}` — blocks `is_admin`, `is_active`, `password_hash`, `id`, `role`, non-dict input · 404 on missing user |
| `test_continue_watching.py` | 2 | `_ALLOWED_SOURCE_SERVERS = frozenset({white, black})` — no hostnames or IPs leak in |
| `tmdb_utils_test.go` | 30 | `isSafePathSegment` (digit-only, no `..`, no `%`, no Unicode digit substitution) · `yearFromDate` · `tmdbImage` |

### What's deliberately not covered

- React component rendering (would need jsdom + a build harness)
- The Astro/Svelte 5 components themselves (no e2e framework committed)
- Provider extractor logic (depends on live upstream CDNs and Cloudflare)

Add a test under `backend/tests/` for any new mass-assignment guard, allowlist,
Pydantic validator, or URL validation — these are the layers that take the
largest blast radius when they regress.

---

## Security model

Five layers, ordered by blast radius if they fail:

1. **SSRF guard** — `backend/ssrf.py`
   Every outbound URL the backend fetches server-side (`/remux`, `/probe`,
   `/subtitles/proxy`) goes through `validate_outbound_url`, which enforces:
   - Scheme allowlist (`http`/`https` only)
   - Length cap (2048)
   - No control characters
   - Hostname in `ALLOWED_HOSTS` frozenset
   - DNS resolution to a public IP (rejects `127.0.0.1`, RFC1918, IMDS
     `169.254.169.254`, link-local, multicast, unspecified)

   The httpx `redirect_event_hook` re-runs the same check on every 3xx
   response, so a CDN that 302's to `http://127.0.0.1:6379/` is rejected
   before httpx follows the redirect.

   **Known limitation (DNS-rebinding TOCTOU):** we resolve once and check,
   then httpx resolves again on connect. A short-TTL hostname on the
   allowlist could in theory return a private IP on the second resolution.
   The allowlist constrains the attacker set; a full fix would pin the
   resolved IP via a custom httpx transport. See the docstring in
   `_hostname_resolves_to_public`.

2. **Mass-assignment guard** — `backend/auth.py:update_user`
   The Pydantic `updates` body is checked against `_UPDATABLE_USER_FIELDS
   = frozenset({"email", "username"})` before any `setattr`. Privilege
   columns (`is_admin`, `is_active`) and credential columns
   (`password_hash`, `id`) are never writable through this path.

3. **Provider allowlist** — `backend/continue_watching.py:_ALLOWED_SOURCE_SERVERS`
   The `source_server` column on continue-watching rows is constrained to
   `frozenset({"white", "black"})`. Anything else is rejected with 400.

4. **HLS token store** — `backend/app/api/proxy.py:_url_store`
   The token table is a `TTLCache(maxsize=5000, ttl=86400)` — bounded both
   in entry count and age. Tokens are SHA256 of the source URL truncated
   to 16 hex chars. Manifest tokens live 24 h, segment tokens live only as
   long as the manifest that referenced them.

5. **Rate-limit + health-log bounds**
   - `_rate_limit_buckets`: capped at 10K keys with opportunistic eviction
   - `_playback_health_log`: capped at 5K keys with `asyncio.Lock` + LRU
     eviction, per-key list capped at 100 entries

### What's deliberately exposed

- `/api/tmdb/*` — TMDB is itself a public API; the backend just proxies
  through it. No secrets in the response.
- `/api/{server}/source` — returns the master URL + first variant. The
  master URL is a short-lived signed token, not a CDN URL.

---

## Provider model

Two source providers are wired in `app/main.py`:

| Name | Difficulty | What it returns | When to use |
|---|---|---|---|
| `white` | Easier source | Multiple quality URLs (1080p, 720p, etc.) with `quality` and `resolution` fields | **Default for quality** — this is the canonical provider for new development |
| `black` | Cloudflare-protected, uses Patchright/Scrapling | A single working source | **Fallback** when `white` returns nothing or errors |

`continue_watching` rows record which provider was used so a resume starts
on the same source. The user-facing source switcher in the watch UI lets
viewers toggle between them mid-playback.

Adding a third provider:

1. Drop a new module in `backend/app/api/providers/yourname.py` exposing
   `router`.
2. Mount it in `app/main.py` alongside the existing two.
3. Add the name to `_ALLOWED_SOURCE_SERVERS` in
   `backend/continue_watching.py` (and add a test in
   `backend/tests/test_continue_watching.py`).
4. Add the `yourname` to the source-server allowlist at
   `frontend/src/lib/api.ts:35` (`allowedServers`).

---

## Known setup gotchas

- `pnpm-workspace.yaml` lists `apps/*` and `packages/*`, but `frontend/`
  sits at the repo root, not under `apps/`. CI's `pnpm --filter web build`
  will not match anything until that's restructured.
- The pre-built `backend/gateway/server` binary is committed; rebuild
  from source for your platform (`cd backend/gateway && go run ./cmd/api`).
- The Android `watchfy-release.jks` keystore is committed to the repo.
  **Do not reuse it for production** — it should be moved out of source
  control.

---

## Status of the three services

| Service | Status | Started by `start.sh`? |
|---|---|---|
| `backend/` (Python · FastAPI) | ✅ Live — providers, extraction, FFmpeg, analytics | Yes (port 8000) |
| `frontend/` (Astro) | ✅ Live — UI for all pages | Yes (port 4321) |
| `backend/gateway/` (Go · Fiber) | ⚠️ Dormant — alt implementation, runs to `:8080` if you start it manually | **No** |

---

## Troubleshooting

**`patchright install chromium` fails behind a corporate proxy.**
Set `HTTPS_PROXY=http://your-proxy:port` before running `setup.sh`.

**`hls.js` keeps reloading the manifest at ~50 min into a movie.**
Pre-9.x versions stripped `#EXT-X-ENDLIST`, which made hls.js treat VOD as
live and rotate manifests. The current code preserves ENDLIST. If this
regresses, check that `proxy.py`, `providers/white.py`, and
`providers/black.py` do not call `_strip_endlist` on the rewritten
manifest.

**`ssrf_blocked_redirect` warnings in the backend log.**
An upstream CDN is returning a 302 to a host outside the allowlist. Either
the CDN is misconfigured (add the new host to `ssrf.ALLOWED_HOSTS` after
reviewing it) or someone is attempting SSRF (the guard is working —
nothing to do).

**`mass_assignment_blocked` in the auth log.**
A request body included a field outside `{email, username}`. Either a
client is misconfigured or someone is trying to escalate privileges. The
guard is working — nothing to do.

**`continue_watching` POST fails with `400 source_server`.**
The source server in the request body isn't in `{white, black}`. Either
add a new provider (see above) or correct the client to send `white` or
`black`.

**`pylance` or `svelte-check` reports 24 errors, all in
`node_modules/@qwikdev/astro/src/index.ts`.**
These are third-party package errors caused by a version mismatch
between `@qwikdev/astro`'s bundled `astro@4` types and the project's
`astro@4`. They are not from this codebase. Ignore, or install
`@types/node` (already a devDep) and re-run.

---

## License

Add a `LICENSE` file at the repo root to make this explicit.
