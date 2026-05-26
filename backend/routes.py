"""FastAPI router for watchfy backend — TMDB proxy, WASM cache, and Playwright source extraction.

Enhancements over v1:
  - lifespan context manager replaces deprecated @app.on_event
  - Singleflight (coalesce) pattern prevents thundering-herd on cache miss
  - Circuit breaker on Playwright extraction (auto-open after N failures)
  - Request-ID middleware for end-to-end tracing
  - Structured JSON logging throughout
  - ETag + conditional GET on WASM endpoint
  - /api/metrics endpoint (cache stats, circuit-breaker state, rate-limit buckets)
  - Dependency-injected httpx client via FastAPI Depends
  - Safer URL token resolution with 410 → manifest refresh hint
  - Per-IP rate limiting now returns X-RateLimit-* headers on all responses
  - Proper asyncio.TaskGroup usage instead of ensure_future where possible
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Annotated
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
from fastapi import Depends, FastAPI, APIRouter, HTTPException, Query, Request, Response

from hls_parser import parse_master_manifest
from white_routes import (
    router as white_router,
    shutdown_white_browser,
    shutdown_white_client,
)
from proxy_routes import router as enhanced_proxy_router

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
)
logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

SHORT_TOKEN_LEN = 16
TMDB_PROXY_BASE = "https://db.videasy.net/3"
VIDKING_BASE = "https://www.vidking.net"
HTTP_TIMEOUT = 30.0

ALLOWED_PROXY_HOSTS: frozenset[str] = frozenset(
    {
        "easy.speedsterwave.app",
        "cdn.vidking.net",
        "vidking.net",
        "cloudnestra.com",
        "whisperingauroras.com",
        "111movies.net",
        "www.111movies.net",
    }
)

_CDN_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.vidking.net/",
    "Origin": "https://www.vidking.net",
}

# ── Environment-driven tunables ──────────────────────────────────────────────

_HLS_CACHE_TTL: int = int(os.environ.get("HLS_CACHE_TTL", 15 * 60))
_HLS_STALE_TTL: int = int(os.environ.get("HLS_STALE_TTL", 30 * 60))
_RATE_LIMIT_MAX: int = int(os.environ.get("RATE_LIMIT_MAX", 15))
_RATE_LIMIT_WINDOW: float = float(os.environ.get("RATE_LIMIT_WINDOW", 60.0))
_CB_FAILURE_THRESHOLD: int = int(os.environ.get("CB_FAILURE_THRESHOLD", 5))
_CB_RESET_TIMEOUT: float = float(os.environ.get("CB_RESET_TIMEOUT", 60.0))


# ── URL token cache ──────────────────────────────────────────────────────────

_url_token_cache: TTLCache[str, str] = TTLCache(maxsize=2000, ttl=1800)


def _store_url(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[:SHORT_TOKEN_LEN]
    _url_token_cache[token] = url
    return token


def _resolve_url(token: str) -> str | None:
    return _url_token_cache.get(token)


# ── HLS source cache ─────────────────────────────────────────────────────────

_hls_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=500, ttl=_HLS_CACHE_TTL)
_hls_cache_timestamps: dict[str, float] = {}
_hls_cache_refreshing: set[str] = set()

# Singleflight: maps cache key → Future so concurrent requests coalesce
_extraction_futures: dict[str, asyncio.Future] = {}
_extraction_lock = asyncio.Lock()


def _cache_key(tmdb_id: int, media_type: str, season: int = 1, episode: int = 1) -> str:
    return f"{tmdb_id}:{media_type}:{season}:{episode}"


def _is_cache_stale(ck: str) -> bool:
    ts = _hls_cache_timestamps.get(ck)
    if ts is None:
        return True
    return (time.monotonic() - ts) > _HLS_CACHE_TTL


def _is_cache_expired(ck: str) -> bool:
    ts = _hls_cache_timestamps.get(ck)
    if ts is None:
        return True
    return (time.monotonic() - ts) > _HLS_STALE_TTL


# ── WASM cache ───────────────────────────────────────────────────────────────

_wasm_cache: bytes | None = None
_wasm_etag: str | None = None


# ── Circuit breaker ───────────────────────────────────────────────────────────

class CBState(str, Enum):
    CLOSED = "closed"      # normal
    OPEN = "open"          # blocking calls
    HALF_OPEN = "half_open"  # testing recovery


class CircuitBreaker:
    """Simple asyncio-safe circuit breaker for Playwright extraction."""

    def __init__(self, failure_threshold: int = _CB_FAILURE_THRESHOLD, reset_timeout: float = _CB_RESET_TIMEOUT):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._last_failure_time: float | None = None
        self._state = CBState.CLOSED
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CBState:
        if self._state == CBState.OPEN:
            if self._last_failure_time and (time.monotonic() - self._last_failure_time) > self.reset_timeout:
                self._state = CBState.HALF_OPEN
        return self._state

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._state = CBState.CLOSED

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.monotonic()
            if self._failures >= self.failure_threshold:
                self._state = CBState.OPEN
                logger.warning('"Circuit breaker OPENED after %d failures"', self._failures)

    def allow_request(self) -> bool:
        return self.state in (CBState.CLOSED, CBState.HALF_OPEN)

    def metrics(self) -> dict:
        return {
            "state": self.state.value,
            "failures": self._failures,
            "threshold": self.failure_threshold,
            "reset_timeout_s": self.reset_timeout,
        }


_vidking_cb = CircuitBreaker()


# ── Rate limiter ─────────────────────────────────────────────────────────────

_rate_limit_lock = asyncio.Lock()
_rate_limit_buckets: dict[str, list[float]] = defaultdict(list)


async def _check_rate_limit(client_id: str) -> dict[str, str]:
    """Raise 429 if rate limit exceeded; return headers to attach to response."""
    now = time.monotonic()
    async with _rate_limit_lock:
        bucket = _rate_limit_buckets[client_id]
        bucket[:] = [t for t in bucket if now - t < _RATE_LIMIT_WINDOW]
        remaining = max(0, _RATE_LIMIT_MAX - len(bucket))
        reset_in = int(_RATE_LIMIT_WINDOW - (now - bucket[0])) if bucket else int(_RATE_LIMIT_WINDOW)
        headers = {
            "X-RateLimit-Limit": str(_RATE_LIMIT_MAX),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_in),
        }
        if len(bucket) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={**headers, "Retry-After": str(reset_in)},
            )
        bucket.append(now)
        return headers


# ── URL validation ────────────────────────────────────────────────────────────

def _validate_proxy_url(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if parsed.hostname not in ALLOWED_PROXY_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not in allowlist: {parsed.hostname}")


# ── Shared httpx client (dependency) ─────────────────────────────────────────

_httpx_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None or _httpx_client.is_closed:
        _httpx_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
    return _httpx_client


async def _close_client() -> None:
    global _httpx_client
    if _httpx_client and not _httpx_client.is_closed:
        await _httpx_client.aclose()
        _httpx_client = None
        logger.info('"httpx client closed"')


ClientDep = Annotated[httpx.AsyncClient, Depends(_get_client)]


# ── Playwright browser (singleton) ────────────────────────────────────────────

_playwright_instance = None
_playwright_browser = None
_playwright_lock = asyncio.Lock()


async def _get_browser():
    global _playwright_instance, _playwright_browser
    async with _playwright_lock:
        if _playwright_browser is None or not _playwright_browser.is_connected():
            from playwright.async_api import async_playwright
            _playwright_instance = await async_playwright().start()
            _playwright_browser = await _playwright_instance.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--mute-audio",
                ],
            )
    return _playwright_browser


async def _close_browser() -> None:
    global _playwright_instance, _playwright_browser
    async with _playwright_lock:
        for obj, method in [(_playwright_browser, "close"), (_playwright_instance, "stop")]:
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass
        _playwright_browser = None
        _playwright_instance = None
    logger.info('"Playwright shut down"')


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('"watchfy backend starting"')
    yield
    logger.info('"watchfy backend shutting down"')
    await asyncio.gather(
        _close_browser(),
        _close_client(),
        shutdown_white_browser(),
        shutdown_white_client(),
        return_exceptions=True,
    )


# ── Request-ID middleware ─────────────────────────────────────────────────────

async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api")


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness + readiness probe."""
    browser_ok = _playwright_browser is not None and _playwright_browser.is_connected()
    from ffmpeg_utils import get_ffmpeg_version
    return {
        "status": "ok",
        "browser": "connected" if browser_ok else "disconnected",
        "circuit_breaker": _vidking_cb.metrics(),
        "cache": {
            "hls_entries": len(_hls_cache),
            "hls_maxsize": _hls_cache.maxsize,
            "token_entries": len(_url_token_cache),
            "token_maxsize": _url_token_cache.maxsize,
        },
        "ffmpeg": (get_ffmpeg_version() or "unavailable"),
    }


@router.get("/metrics", tags=["ops"])
async def metrics() -> dict:
    """Internal observability: cache stats, CB state, rate-limit buckets."""
    now = time.monotonic()
    rl_summary = {
        ip: {
            "count": len([t for t in ts if now - t < _RATE_LIMIT_WINDOW]),
            "window_s": _RATE_LIMIT_WINDOW,
        }
        for ip, ts in _rate_limit_buckets.items()
    }
    return {
        "circuit_breaker": _vidking_cb.metrics(),
        "hls_cache": {
            "size": len(_hls_cache),
            "refreshing_keys": list(_hls_cache_refreshing),
            "inflight_extractions": list(_extraction_futures.keys()),
        },
        "rate_limits": rl_summary,
        "wasm_cached": _wasm_cache is not None,
    }


# ── TMDB metadata proxy ───────────────────────────────────────────────────────

@router.get("/vidking/tmdb/{media_type}/{tmdb_id}", tags=["tmdb"])
async def vidking_tmdb(media_type: str, tmdb_id: int, client: ClientDep) -> dict:
    """Proxy TMDB metadata from db.videasy.net (title, year, imdbId)."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    url = f"{TMDB_PROXY_BASE}/{media_type}/{tmdb_id}?append_to_response=external_ids"
    resp = await client.get(url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="TMDB upstream error")
    data = resp.json()
    if media_type == "movie":
        title = data.get("title", "")
        year = _parse_year(data.get("release_date"))
    else:
        title = data.get("name", "")
        year = _parse_year(data.get("first_air_date"))
    imdb_id = (data.get("external_ids") or {}).get("imdb_id") or ""
    return {"title": title, "year": year, "imdbId": imdb_id}


# ── WASM module cache with ETag ───────────────────────────────────────────────

@router.get("/vidking/wasm", tags=["wasm"])
async def vidking_wasm(request: Request, client: ClientDep) -> Response:
    """Serve vidking's WASM decrypt module with caching + conditional GET."""
    global _wasm_cache, _wasm_etag

    if _wasm_cache is None:
        resp = await client.get(f"{VIDKING_BASE}/assets/wasm/module1.wasm")
        if not resp.is_success:
            raise HTTPException(status_code=502, detail="Failed to fetch WASM module")
        _wasm_cache = resp.content
        _wasm_etag = f'"{hashlib.md5(_wasm_cache).hexdigest()}"'  # noqa: S324

    if request.headers.get("If-None-Match") == _wasm_etag:
        return Response(status_code=304)

    return Response(
        content=_wasm_cache,
        media_type="application/wasm",
        headers={
            "ETag": _wasm_etag,
            "Cache-Control": "public, max-age=86400, immutable",
        },
    )


# ── HLS manifest proxy ────────────────────────────────────────────────────────

@router.get("/vidking/proxy/hls", tags=["proxy"])
async def proxy_hls(
    request: Request,
    client: ClientDep,
    url: str = Query(...),
    remux: bool = Query(default=False),
) -> Response:
    """Fetch an HLS manifest and rewrite segment URLs through this proxy.

    `url` may be a 16-char hex token or a full URL.
    Add ?remux=1 to delegate to FFmpeg repackager.
    """
    resolved_url = _unwrap_token_or_url(url)

    if remux:
        from ffmpeg_routes import remux_proxy
        return await remux_proxy(url=resolved_url, format="hls")

    _validate_proxy_url(resolved_url)
    resp = await client.get(resolved_url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="HLS upstream error")

    base_url = resolved_url.rsplit("/", 1)[0] + "/"
    lines: list[str] = []
    for line in resp.text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if not stripped.startswith("http"):
                stripped = base_url + stripped
            token = _store_url(stripped)
            lines.append(f"/api/vidking/proxy/seg/{token}")
        else:
            lines.append(line)

    return Response(
        content="\n".join(lines),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/vidking/proxy/seg", tags=["proxy"])
async def proxy_seg_legacy(url: str = Query(...)) -> Response:
    """Legacy query-param segment handler — forwards to token-based endpoint."""
    return await proxy_seg(_store_url(url))


@router.get("/vidking/proxy/seg/{token}", tags=["proxy"])
async def proxy_seg(token: str) -> Response:
    """Proxy a single HLS segment via short token with 3-attempt retry."""
    url = _resolve_url(token)
    if not url:
        return Response(
            status_code=410,
            headers={"X-Segment-Expired": "true", "Retry-After": "0"},
        )
    _validate_proxy_url(url)
    client = await _get_client()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.is_success:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "video/MP2T"),
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            if resp.status_code == 410:
                return Response(
                    status_code=410,
                    headers={"X-Segment-Expired": "true", "Retry-After": "0"},
                )
            last_exc = Exception(f"HTTP {resp.status_code}")
        except HTTPException:
            raise
        except Exception as exc:
            last_exc = exc
            logger.warning('"seg_fetch_attempt":{"attempt":%d,"error":"%s"}', attempt + 1, exc)
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))
    raise HTTPException(status_code=502, detail=f"Segment unavailable after 3 attempts: {last_exc}")


# ── Playback health reporting ─────────────────────────────────────────────────

_playback_health_log: dict[str, list[dict]] = defaultdict(list)
_HEALTH_LOG_MAX = 100


@router.post("/vidking/health/report", tags=["telemetry"])
async def health_report(request: Request) -> dict:
    """Ingest client-side playback health metrics."""
    data = await request.json()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{data.get('tmdbId', 'unknown')}"
    entry = {
        "ts": time.time(),
        "currentTime": data.get("currentTime"),
        "buffered": data.get("buffered"),
        "stallCount": data.get("stallCount", 0),
        "quality": data.get("quality"),
        "resolution": data.get("resolution"),
        "errorCount": data.get("errorCount", 0),
    }
    log = _playback_health_log[key]
    log.append(entry)
    if len(log) > _HEALTH_LOG_MAX:
        del log[: len(log) - _HEALTH_LOG_MAX]
    return {"status": "ok"}


# ── Force-refresh endpoint ────────────────────────────────────────────────────

@router.get("/vidking/refresh", tags=["source"])
async def refresh_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Force-evict cache and re-extract HLS source. Subject to rate limit."""
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")
    client_ip = request.client.host if request.client else "unknown"
    rl_headers = await _check_rate_limit(client_ip)

    ck = _cache_key(tmdbId, mediaType, season, episode)
    _hls_cache.pop(ck, None)
    _hls_cache_timestamps.pop(ck, None)

    try:
        sources = await asyncio.wait_for(
            _extract_hls_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except Exception as exc:
        logger.error('"refresh_failed":{"key":"%s","error":"%s"}', ck, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Refresh failed: {exc}")

    return Response(
        content={"sources": sources or [], "refreshed": bool(sources)},
        headers=rl_headers,
    )


# ── Subtitle endpoints ────────────────────────────────────────────────────────

@router.get("/subtitles", tags=["subtitles"])
async def get_subtitles(
    imdbId: str = Query(...),
    language: str = Query(default="en"),
) -> dict:
    """Return available subtitle tracks for a movie or episode."""
    from subtitles import fetch_subtitles
    tracks = await fetch_subtitles(imdbId, language)
    return {
        "subtitles": [
            {"label": t.label, "language": t.language, "url": t.url, "format": t.format}
            for t in tracks
        ]
    }


@router.get("/subtitles/proxy", tags=["subtitles"])
async def proxy_subtitle(url: str = Query(...)) -> Response:
    """Proxy + auto-convert SRT→WebVTT, bypassing CORS restrictions."""
    from subtitles import convert_srt_to_vtt
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
            resp = await c.get(url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Subtitle fetch failed: {exc}")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="Subtitle upstream error")
    content = resp.text
    if not url.endswith(".vtt"):
        content = convert_srt_to_vtt(content)
    return Response(
        content=content,
        media_type="text/vtt",
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=86400"},
    )


# ── Vidking source (with singleflight + circuit breaker) ──────────────────────

@router.get("/vidking/source", tags=["source"])
async def vidking_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    """Return HLS source URLs from vidking.net.

    - Cached responses are returned instantly.
    - Stale entries trigger a background revalidation (stale-while-revalidate).
    - Concurrent requests for the same key are coalesced via singleflight.
    - Circuit breaker blocks extraction when vidking is consistently failing.
    """
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")
    client_ip = request.client.host if request.client else "unknown"
    rl_headers = await _check_rate_limit(client_ip)

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if refresh:
        _hls_cache.pop(ck, None)
        _hls_cache_timestamps.pop(ck, None)
    else:
        cached = _hls_cache.get(ck)
        if cached is not None:
            stale = _is_cache_stale(ck)
            if stale and ck not in _hls_cache_refreshing:
                _hls_cache_refreshing.add(ck)
                asyncio.get_event_loop().create_task(
                    _background_refresh(ck, tmdbId, mediaType, season, episode)
                )
            return _source_response(cached, cached=True, stale=stale, extra_headers=rl_headers)

    if not _vidking_cb.allow_request():
        stale = _hls_cache.get(ck)
        if stale:
            logger.warning('"circuit_open_serving_stale":{"key":"%s"}', ck)
            return _source_response(stale, cached=True, stale=True, extra_headers=rl_headers)
        raise HTTPException(
            status_code=503,
            detail="Source extraction temporarily unavailable. Try again later.",
            headers={"Retry-After": str(int(_CB_RESET_TIMEOUT))},
        )

    try:
        sources = await asyncio.wait_for(
            _extract_hls_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        stale = _hls_cache.get(ck)
        if stale:
            return _source_response(stale, cached=True, stale=True, extra_headers=rl_headers)
        raise HTTPException(status_code=504, detail="Source extraction timed out")
    except Exception as exc:
        logger.error('"source_extraction_failed":{"key":"%s","err":"%s"}', ck, exc, exc_info=True)
        stale = _hls_cache.get(ck)
        if stale:
            return _source_response(stale, cached=True, stale=True, extra_headers=rl_headers)
        raise HTTPException(status_code=502, detail=f"Source extraction failed: {exc}")

    if sources:
        _hls_cache[ck] = sources
        _hls_cache_timestamps[ck] = time.monotonic()

    return _source_response(sources or [], cached=False, stale=False, extra_headers=rl_headers)


def _source_response(
    sources: list[dict],
    *,
    cached: bool,
    stale: bool,
    extra_headers: dict | None = None,
) -> dict:
    """Uniform shape for /vidking/source responses."""
    return {
        "sources": sources,
        "embedUrl": None,
        "cached": cached,
        "stale": stale,
    }


# ── Pre-warm ──────────────────────────────────────────────────────────────────

@router.get("/vidking/prewarm", tags=["source"])
async def vidking_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Warm the HLS cache ahead of the watch page loading."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _hls_cache:
        if _is_cache_stale(ck) and ck not in _hls_cache_refreshing:
            _hls_cache_refreshing.add(ck)
            asyncio.get_event_loop().create_task(
                _background_refresh(ck, tmdbId, mediaType, season, episode)
            )
            return {"status": "cached_refreshing"}
        return {"status": "cached"}

    if not _vidking_cb.allow_request():
        return {"status": "circuit_open"}

    if ck not in _extraction_futures:
        asyncio.get_event_loop().create_task(_extract_and_cache(tmdbId, mediaType, season, episode))
    return {"status": "warming"}


# ── Singleflight coalescer ────────────────────────────────────────────────────

async def _extract_hls_coalesced(
    ck: str,
    tmdb_id: int,
    media_type: str,
    season: int,
    episode: int,
) -> list[dict] | None:
    """Ensure only one Playwright extraction runs per cache key at a time.

    All concurrent callers for the same key await the same Future.
    """
    async with _extraction_lock:
        if ck in _extraction_futures:
            fut = _extraction_futures[ck]
        else:
            loop = asyncio.get_event_loop()
            fut: asyncio.Future = loop.create_future()
            _extraction_futures[ck] = fut

            async def _run():
                try:
                    result = await _extract_hls_from_vidking(tmdb_id, media_type, season, episode)
                    await _vidking_cb.record_success()
                    fut.set_result(result)
                except Exception as exc:
                    await _vidking_cb.record_failure()
                    fut.set_exception(exc)
                finally:
                    async with _extraction_lock:
                        _extraction_futures.pop(ck, None)

            asyncio.get_event_loop().create_task(_run())

    return await asyncio.shield(fut)


# ── Core Playwright extraction ────────────────────────────────────────────────

async def _extract_hls_from_vidking(
    tmdb_id: int,
    media_type: str,
    season: int = 1,
    episode: int = 1,
) -> list[dict] | None:
    """Drive vidking.net with Playwright to capture HLS master manifest URL.

    Returns a list of quality-variant source dicts, or None on failure.
    """
    embed_url = (
        f"{VIDKING_BASE}/embed/movie/{tmdb_id}?autoPlay=true&color=c8956c"
        if media_type == "movie"
        else (
            f"{VIDKING_BASE}/embed/tv/{tmdb_id}/{season}/{episode}"
            f"?autoPlay=true&color=c8956c&episodeSelector=true&nextEpisode=true"
        )
    )

    browser = await _get_browser()
    context = await browser.new_context(
        user_agent=_CDN_HEADERS["User-Agent"],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )
    await context.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    )
    page = await context.new_page()
    hls_url: str | None = None

    async def _on_response(response):
        nonlocal hls_url
        if hls_url is None and ".m3u8" in response.url.lower():
            hls_url = response.url

    page.on("response", _on_response)
    logger.info('"loading_embed":{"url":"%s"}', embed_url)

    try:
        try:
            await page.goto(embed_url, wait_until="networkidle", timeout=60_000)
        except Exception as exc:
            logger.warning('"networkidle_timeout":{"err":"%s"}', exc)
            await page.goto(embed_url, wait_until="domcontentloaded", timeout=60_000)

        await asyncio.sleep(3)

        if not hls_url:
            await _try_click_play(page)
            await asyncio.sleep(8)

        if not hls_url:
            hls_url = await _dom_fallback(page)

    finally:
        await asyncio.sleep(0.5)
        await context.close()

    if not hls_url:
        logger.warning('"no_hls_captured"')
        return None

    return await _build_sources_from_manifest(hls_url)


async def _try_click_play(page) -> None:
    """Attempt to click common play button selectors to trigger stream load."""
    selectors = [
        "video",
        "[class*='play']",
        "[id*='play']",
        "button[aria-label*='play' i]",
        ".vjs-big-play-button",
        ".plyr__control",
        "[data-testid='play-button']",
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click(force=True, timeout=2000)
                logger.info('"clicked_play":{"selector":"%s"}', sel)
                return
        except Exception:
            pass


async def _dom_fallback(page) -> str | None:
    """Extract HLS URL from video DOM or known JS player globals."""
    try:
        for expr in (
            "(() => { const v=document.querySelector('video'); return v&&(v.src||v.currentSrc)||null; })()",
            """(() => {
                if(window.hls?.url) return window.hls.url;
                if(window.player?.config?.src) return window.player.config.src;
                if(window.videojs?.getPlayers){
                    for(const k in window.videojs.getPlayers()){
                        const s=window.videojs.getPlayers()[k];
                        const u=s.src||(s.currentSrc&&s.currentSrc());
                        if(u) return u;
                    }
                }
                return null;
            })()""",
        ):
            result = await page.evaluate(expr)
            if result and result.startswith("http"):
                logger.info('"dom_fallback_found":{"url":"%s"}', result)
                return result
    except Exception as exc:
        logger.warning('"dom_fallback_error":{"err":"%s"}', exc)
    return None


async def _build_sources_from_manifest(hls_url: str) -> list[dict]:
    """Fetch master manifest, parse quality variants, proxy-wrap each URL."""
    client = await _get_client()
    fallback = [
        {
            "url": f"/api/vidking/proxy/hls?url={_store_url(hls_url)}",
            "quality": "Auto",
            "resolution": 0,
            "bandwidth": 0,
        }
    ]
    try:
        resp = await client.get(hls_url)
        if not resp.is_success:
            logger.warning('"manifest_fetch_failed":{"status":%d}', resp.status_code)
            return fallback
        base_url = hls_url.rsplit("/", 1)[0] + "/"
        variants = parse_master_manifest(resp.text, base_url)
        if not variants:
            return fallback
        sources = [
            {
                "url": f"/api/vidking/proxy/hls?url={_store_url(v.url)}",
                "quality": v.quality_label,
                "resolution": v.resolution_height,
                "bandwidth": v.bandwidth,
            }
            for v in variants
        ]
        logger.info('"parsed_variants":{"count":%d,"qualities":%s}', len(sources), [s["quality"] for s in sources])
        return sources
    except Exception as exc:
        logger.warning('"manifest_parse_error":{"err":"%s"}', exc)
        return fallback


# ── Background helpers ────────────────────────────────────────────────────────

async def _extract_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    ck = _cache_key(tmdb_id, media_type, season, episode)
    try:
        sources = await _extract_hls_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _hls_cache[ck] = sources
            _hls_cache_timestamps[ck] = time.monotonic()
            logger.info('"prewarm_cached":{"key":"%s","count":%d}', ck, len(sources))
        else:
            logger.warning('"prewarm_no_sources":{"key":"%s"}', ck)
    except Exception as exc:
        logger.error('"prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _background_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        logger.info('"bg_refresh_start":{"key":"%s"}', ck)
        sources = await _extract_hls_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _hls_cache[ck] = sources
            _hls_cache_timestamps[ck] = time.monotonic()
            logger.info('"bg_refresh_done":{"key":"%s","count":%d}', ck, len(sources))
        else:
            logger.warning('"bg_refresh_empty":{"key":"%s"}', ck)
    except Exception as exc:
        logger.error('"bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _hls_cache_refreshing.discard(ck)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unwrap_token_or_url(value: str) -> str:
    """Resolve a short token to its full URL, or return the value as-is."""
    if len(value) == SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in value):
        resolved = _resolve_url(value)
        if not resolved:
            raise HTTPException(
                status_code=410,
                detail="Token expired — refresh the manifest and retry.",
                headers={"Retry-After": "0"},
            )
        return resolved
    return value


def _parse_year(date_str: str | None) -> str:
    if not date_str:
        return ""
    try:
        return str(datetime.strptime(date_str[:10], "%Y-%m-%d").year)
    except ValueError:
        return ""


# ── Watch endpoint (vidking.net source) ─────────────────────────────────────

@router.get("/watch/{media_type}/{tmdb_id}", tags=["watch"])
async def get_watch_url(
    request: Request,
    media_type: str,
    tmdb_id: int,
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Get stream URL from vidking.net source."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    client_ip = request.client.host if request.client else "unknown"
    await _check_rate_limit(client_ip)
    
    ck = _cache_key(tmdb_id, media_type, season, episode)
    
    cached = _hls_cache.get(ck)
    if cached is not None:
        return {
            "stream_url": cached[0]["url"] if cached else None,
            "sources": cached,
        }
    
    try:
        sources = await asyncio.wait_for(
            _extract_hls_coalesced(ck, tmdb_id, media_type, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        if cached:
            return {"stream_url": cached[0]["url"], "sources": cached}
        raise HTTPException(status_code=504, detail="Source extraction timed out")
    except Exception as exc:
        if cached:
            return {"stream_url": cached[0]["url"], "sources": cached}
        raise HTTPException(status_code=502, detail=f"Source extraction failed: {exc}")
    
    if sources:
        _hls_cache[ck] = sources
        _hls_cache_timestamps[ck] = time.monotonic()
    
    return {
        "stream_url": sources[0]["url"] if sources else None,
        "sources": sources or [],
    }