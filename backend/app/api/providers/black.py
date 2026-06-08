"""FastAPI router for watchfy's Black server (vidking.net).

Mounts at /api/black/*:
  GET /api/black/source           — extract HLS + MP4 via Playwright extractor
  GET /api/black/proxy/hls        — proxy + rewrite HLS manifests
  GET /api/black/proxy/seg/{tok}  — proxy individual HLS segments (retry + exp backoff)
  GET /api/black/prewarm          — background cache warm-up
  GET /api/black/refresh          — force-evict cache + re-extract
  GET /api/black/download         — range-aware stream-proxy for MP4 downloads
  GET /api/black/stats            — cache / circuit-breaker telemetry
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import TypedDict
from urllib.parse import urljoin, urlparse

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.extractors.black import extract_sources_legacy

logger = logging.getLogger(__name__)

# ── Background task registry ───────────────────────────────────────────────────

_background_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    """Create a fire-and-forget task that won't be garbage-collected."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


# ── Config ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _BlackConfig:
    cache_ttl: int      = int(os.environ.get("BLACK_CACHE_TTL",      15 * 60))
    stale_ttl: int      = int(os.environ.get("BLACK_STALE_TTL",      30 * 60))
    source_timeout: float = float(os.environ.get("BLACK_SOURCE_TIMEOUT", 90.0))
    seg_retries: int    = int(os.environ.get("BLACK_SEG_RETRIES",    3))
    seg_backoff: float  = float(os.environ.get("BLACK_SEG_BACKOFF",  0.5))
    # Circuit breaker: open after N consecutive failures, attempt recovery after M seconds
    cb_threshold: int   = int(os.environ.get("BLACK_CB_THRESHOLD",   5))
    cb_recovery: float  = float(os.environ.get("BLACK_CB_RECOVERY",  60.0))
    # Per-IP sliding-window rate limit on /source
    rate_limit_rpm: int = int(os.environ.get("BLACK_RATE_LIMIT_RPM", 30))
    short_token_len: int = 16
    download_chunk: int = 65_536


_cfg = _BlackConfig()

# ── Allowed hosts ──────────────────────────────────────────────────────────────

_EXTRA_HOSTS: frozenset[str] = frozenset(
    h.strip() for h in os.environ.get("BLACK_EXTRA_HOSTS", "").split(",") if h.strip()
)

ALLOWED_BLACK_HOSTS: frozenset[str] = frozenset(
    {
        "easy.speedsterwave.app",
        "cdn.vidking.net",
        "vidking.net",
        "www.vidking.net",
        "cloudnestra.com",
        "whisperingauroras.com",
        "hello.mousedoor.com",
        "mousedoor.com",
    }
    | _EXTRA_HOSTS
)

_ALLOWED_SUFFIXES: tuple[str, ...] = (
    ".mousedoor.com",
    ".speedsterwave.app",
    ".vidking.net",
    ".cloudnestra.com",
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

# ── Types ──────────────────────────────────────────────────────────────────────


class SourceEntry(TypedDict, total=False):
    url: str
    type: str      # "hls" | "mp4"
    quality: str
    label: str


# ── Circuit breaker ────────────────────────────────────────────────────────────

class _CBState(Enum):
    CLOSED    = auto()   # normal
    OPEN      = auto()   # failing fast
    HALF_OPEN = auto()   # probing recovery


class CircuitBreaker:
    """Three-state circuit breaker for the Playwright extractor.

    CLOSED → OPEN  : after ``threshold`` consecutive failures.
    OPEN   → HALF_OPEN : after ``recovery`` seconds.
    HALF_OPEN → CLOSED : on next success.
    HALF_OPEN → OPEN   : on next failure.
    """

    __slots__ = ("_state", "_failures", "_last_failure_ts", "_threshold", "_recovery")

    def __init__(self, threshold: int, recovery: float) -> None:
        self._state = _CBState.CLOSED
        self._failures = 0
        self._last_failure_ts = 0.0
        self._threshold = threshold
        self._recovery = recovery

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state.name

    @property
    def failures(self) -> int:
        return self._failures

    def is_open(self) -> bool:
        """Return True when new requests should be rejected.

        Automatically transitions OPEN → HALF_OPEN after the recovery window.
        """
        if self._state is _CBState.OPEN:
            if time.monotonic() - self._last_failure_ts >= self._recovery:
                self._state = _CBState.HALF_OPEN
                logger.info('"black_circuit_half_open"')
                return False
            return True
        return False

    def record_success(self) -> None:
        if self._state is not _CBState.CLOSED:
            logger.info('"black_circuit_closed"')
        self._failures = 0
        self._state = _CBState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_ts = time.monotonic()
        if self._state is _CBState.HALF_OPEN or self._failures >= self._threshold:
            self._state = _CBState.OPEN
            logger.warning('"black_circuit_open":{"failures":%d}', self._failures)


_circuit_breaker = CircuitBreaker(_cfg.cb_threshold, _cfg.cb_recovery)


# ── Rate limiter ───────────────────────────────────────────────────────────────

class _SlidingWindowRL:
    """Per-key sliding-window rate limiter (asyncio-safe, in-process)."""

    def __init__(self, rpm: int) -> None:
        self._rpm = rpm
        # TTLCache auto-evicts cold IPs after 2 minutes of inactivity.
        self._windows: TTLCache[str, list[float]] = TTLCache(maxsize=5_000, ttl=120)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - 60.0
        hits: list[float] = list(self._windows.get(key) or [])
        hits = [t for t in hits if t >= cutoff]
        if len(hits) >= self._rpm:
            self._windows[key] = hits
            return False
        hits.append(now)
        self._windows[key] = hits
        return True


_rate_limiter = _SlidingWindowRL(_cfg.rate_limit_rpm)


def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — try again shortly",
            headers={"Retry-After": "60"},
        )


# ── In-memory state ────────────────────────────────────────────────────────────

_black_cache: TTLCache[str, list[SourceEntry]] = TTLCache(maxsize=400, ttl=_cfg.cache_ttl)
_black_timestamps: dict[str, float] = {}
_black_refreshing: set[str] = set()

# Singleflight gate — one Future per cache key
_black_futures: dict[str, asyncio.Future] = {}
_black_futures_lock = asyncio.Lock()

# Token ↔ URL store (tokens live 24 h)
_url_tokens: TTLCache[str, str] = TTLCache(maxsize=2_000, ttl=86_400)

_dynamic_hosts: set[str] = set()

# Telemetry counters
_cache_hits = 0
_cache_misses = 0

# Shared httpx client
_black_client: httpx.AsyncClient | None = None

# ── Playwright browser singleton ───────────────────────────────────────────────

_black_browser = None
_black_playwright = None
_black_browser_lock = asyncio.Lock()


async def _get_black_browser():
    global _black_browser, _black_playwright
    async with _black_browser_lock:
        if _black_browser is None or not _black_browser.is_connected():
            from patchright.async_api import async_playwright
            _black_playwright = await async_playwright().start()
            _black_browser = await _black_playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--mute-audio",
                    "--autoplay-policy=no-user-gesture-required",
                ],
            )
    return _black_browser


async def shutdown_black_browser() -> None:
    global _black_browser, _black_playwright
    async with _black_browser_lock:
        for obj, method in [(_black_browser, "close"), (_black_playwright, "stop")]:
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass
        _black_browser = None
        _black_playwright = None
    logger.info('"black_browser_shutdown"')


async def shutdown_black_client() -> None:
    global _black_client
    if _black_client and not _black_client.is_closed:
        await _black_client.aclose()
        _black_client = None
    logger.info('"black_client_shutdown"')


# ── HTTP client ────────────────────────────────────────────────────────────────

async def _get_black_client() -> httpx.AsyncClient:
    global _black_client
    if _black_client is None or _black_client.is_closed:
        _black_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            # Fine-grained timeouts: connect fast, allow generous reads for large segments.
            timeout=httpx.Timeout(connect=8.0, read=30.0, write=10.0, pool=5.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=15),
        )
    return _black_client


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cache_key(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    return f"black:{tmdb_id}:{media_type}:{season}:{episode}"


def _store_token(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[: _cfg.short_token_len]
    _url_tokens[token] = url
    return token


def _resolve_token(token: str) -> str | None:
    return _url_tokens.get(token)


def _register_hosts(sources: list[SourceEntry]) -> None:
    for src in sources:
        u = src.get("url")
        if not u:
            continue
        try:
            h = urlparse(u).hostname
            if h and h not in ALLOWED_BLACK_HOSTS:
                _dynamic_hosts.add(h)
                logger.info('"black_dynamic_host":{"host":"%s"}', h)
        except Exception:
            pass


def _validate_host(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL must include a hostname")
    if (
        hostname in ALLOWED_BLACK_HOSTS
        or hostname in _dynamic_hosts
        or any(hostname.endswith(s) for s in _ALLOWED_SUFFIXES)
    ):
        return
    raise HTTPException(status_code=403, detail=f"Host not allowed: {hostname}")


def _is_stale(ck: str) -> bool:
    ts = _black_timestamps.get(ck)
    return ts is None or (time.monotonic() - ts) > _cfg.cache_ttl


def _rewrite_hls_uri_attr(line: str, base_url: str) -> str:
    """Rewrite ``URI="..."`` attributes in EXT-X-KEY / EXT-X-MAP lines.

    Relative URIs are resolved against *base_url* before tokenising, so
    encryption keys and init segments are served through our proxy.
    """
    def _replace(m: re.Match) -> str:
        uri = m.group(1)
        if not uri.startswith(("http://", "https://")):
            uri = urljoin(base_url, uri)
        return f'URI="/api/black/proxy/seg/{_store_token(uri)}"'

    return re.sub(r'URI="([^"]+)"', _replace, line)


# ── Singleflight coalescer ─────────────────────────────────────────────────────

async def _extract_coalesced(
    ck: str,
    tmdb_id: int,
    media_type: str,
    season: int,
    episode: int,
) -> list[SourceEntry] | None:
    """Coalesce concurrent callers onto a single Playwright tab per cache key.

    If a future for *ck* is already in flight the caller piggybacks on it,
    bypassing the circuit-breaker check (the in-flight request pre-dates the
    open state and may still succeed).  New extractions are rejected while the
    breaker is open.
    """
    async with _black_futures_lock:
        if ck in _black_futures:
            fut = _black_futures[ck]
        else:
            if _circuit_breaker.is_open():
                raise HTTPException(
                    status_code=503,
                    detail="Extractor circuit open — upstream may be degraded, retry shortly",
                    headers={"Retry-After": str(int(_cfg.cb_recovery))},
                )

            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            _black_futures[ck] = fut

            async def _run() -> None:
                try:
                    browser = await _get_black_browser()
                    result = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        browser=browser,
                        cdn_headers=_CDN_HEADERS,
                    )
                    _circuit_breaker.record_success()
                    fut.set_result(result)
                except Exception as exc:
                    _circuit_breaker.record_failure()
                    fut.set_exception(exc)
                finally:
                    async with _black_futures_lock:
                        _black_futures.pop(ck, None)

            _spawn(_run())

    return await asyncio.shield(fut)


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/black", tags=["black"])


# ── /source ────────────────────────────────────────────────────────────────────

@router.get("/source")
async def black_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    """Extract HLS + MP4 sources from vidking.net.

    - **Cached** hits are returned instantly; stale entries trigger a silent
      background revalidation so the next caller gets fresh data.
    - **Singleflight** — concurrent callers for the same key share one
      Playwright tab rather than spawning duplicate browser contexts.
    - **MP4** entries carry ``"type": "mp4"`` for client download UI.
    - **Circuit breaker** prevents hammering a degraded upstream.
    """
    global _cache_hits, _cache_misses

    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    _check_rate_limit(request)

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if refresh:
        _black_cache.pop(ck, None)
        _black_timestamps.pop(ck, None)
    else:
        cached = _black_cache.get(ck)
        if cached is not None:
            _cache_hits += 1
            stale = _is_stale(ck)
            if stale and ck not in _black_refreshing:
                _black_refreshing.add(ck)
                _spawn(_bg_refresh(ck, tmdbId, mediaType, season, episode))
            return {
                "sources": cached,
                "cached": True,
                "stale": stale,
                "cache_age": round(time.monotonic() - (_black_timestamps.get(ck) or 0)),
                "server": "black",
            }

    _cache_misses += 1

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=_cfg.source_timeout,
        )
    except asyncio.TimeoutError:
        fallback = _black_cache.get(ck)
        if fallback:
            return {"sources": fallback, "cached": True, "stale": True, "server": "black"}
        raise HTTPException(status_code=504, detail="Source extraction timed out")
    except HTTPException:
        raise
    except Exception as exc:
        fallback = _black_cache.get(ck)
        if fallback:
            return {"sources": fallback, "cached": True, "stale": True, "server": "black"}
        raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}") from exc

    if sources:
        _black_cache[ck] = sources
        _black_timestamps[ck] = time.monotonic()
        _register_hosts(sources)

    return {"sources": sources or [], "cached": False, "stale": False, "server": "black"}


# ── /prewarm ───────────────────────────────────────────────────────────────────

@router.get("/prewarm")
async def black_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Fire-and-forget cache warm-up for vidking sources."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _black_cache:
        if _is_stale(ck) and ck not in _black_refreshing:
            _black_refreshing.add(ck)
            _spawn(_bg_refresh(ck, tmdbId, mediaType, season, episode))
            return {"status": "cached_refreshing"}
        return {"status": "cached"}
    if ck not in _black_futures:
        _spawn(_warm_and_cache(tmdbId, mediaType, season, episode))
    return {"status": "warming"}


# ── /refresh ───────────────────────────────────────────────────────────────────

@router.get("/refresh")
async def black_refresh(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Evict cache and synchronously re-extract from vidking."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    _black_cache.pop(ck, None)
    _black_timestamps.pop(ck, None)
    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=_cfg.source_timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Refresh failed: {exc}") from exc
    if sources:
        _black_cache[ck] = sources
        _black_timestamps[ck] = time.monotonic()
        _register_hosts(sources)
    return {"sources": sources or [], "refreshed": True, "server": "black"}


# ── /proxy/hls ─────────────────────────────────────────────────────────────────

@router.get("/proxy/hls")
async def black_proxy_hls(url: str = Query(...)) -> Response:
    """Proxy and rewrite a vidking HLS manifest.

    Rewrites all segment/variant URIs to local token paths so the browser
    never talks directly to the CDN.  Correctly handles:

    - Master playlists (``#EXT-X-STREAM-INF`` variant URIs)
    - Media playlists (segment URIs)
    - ``#EXT-X-KEY`` encryption-key ``URI=`` attributes
    - ``#EXT-X-MAP`` initialization-segment ``URI=`` attributes
    - Relative and absolute URIs
    """
    # Token shorthand → full URL
    if len(url) == _cfg.short_token_len and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate_host(url)
    client = await _get_black_client()

    try:
        resp = await client.get(url)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="HLS upstream timed out")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"HLS upstream unreachable: {exc}") from exc

    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="HLS upstream error")

    base_url = url.rsplit("/", 1)[0] + "/"
    lines: list[str] = []
    next_is_variant = False

    for line in resp.text.splitlines():
        stripped = line.strip()

        if not stripped:
            lines.append(line)
            continue

        # EXT-X-KEY / EXT-X-MAP: rewrite URI= attribute inline
        if stripped.startswith(("#EXT-X-KEY", "#EXT-X-MAP")):
            lines.append(_rewrite_hls_uri_attr(line, base_url))
            continue

        if stripped.startswith("#EXT-X-STREAM-INF:"):
            next_is_variant = True
            lines.append(line)
            continue

        if stripped.startswith("#"):
            lines.append(line)
            continue

        # URI line — resolve relative paths, then tokenise
        uri = stripped if stripped.startswith(("http://", "https://")) else urljoin(base_url, stripped)
        token = _store_token(uri)
        if next_is_variant:
            lines.append(f"/api/black/proxy/hls?url={token}")
            next_is_variant = False
        else:
            lines.append(f"/api/black/proxy/seg/{token}")

    return Response(
        content="\n".join(lines),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── /proxy/seg/{token} ─────────────────────────────────────────────────────────

@router.get("/proxy/seg/{token}")
async def black_proxy_seg(token: str) -> Response:
    """Proxy a single vidking HLS segment with exponential-backoff retry."""
    url = _resolve_token(token)
    if not url:
        return Response(
            status_code=410,
            headers={"X-Segment-Expired": "true", "Retry-After": "0"},
        )

    _validate_host(url)
    client = await _get_black_client()
    last_exc: Exception | None = None

    for attempt in range(_cfg.seg_retries):
        try:
            resp = await client.get(url)
            if resp.is_success:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "video/MP2T"),
                    headers={
                        "Content-Length": str(len(resp.content)),
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            if resp.status_code in (404, 410):
                return Response(status_code=410, headers={"X-Segment-Expired": "true"})
            last_exc = Exception(f"HTTP {resp.status_code}")
        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning('"black_seg_timeout":{"attempt":%d}', attempt + 1)
        except Exception as exc:
            last_exc = exc
            logger.warning('"black_seg_error":{"attempt":%d,"err":"%s"}', attempt + 1, exc)

        if attempt < _cfg.seg_retries - 1:
            await asyncio.sleep(_cfg.seg_backoff * (2 ** attempt))  # 0.5 s, 1 s, …

    raise HTTPException(
        status_code=502,
        detail=f"Segment unavailable after {_cfg.seg_retries} attempts: {last_exc}",
    )


# ── /download ──────────────────────────────────────────────────────────────────

@router.get("/download")
async def black_download(
    request: Request,
    url: str = Query(...),
    filename: str = Query(default="watchfy-black.mp4"),
) -> StreamingResponse:
    """Range-aware stream-proxy for MP4 downloads from vidking CDN.

    Forwards the client's ``Range`` header to the upstream so browsers and
    download managers can seek, pause, and resume without re-downloading from
    the start.  No content is buffered to disk.
    """
    _validate_host(url)
    client = await _get_black_client()

    upstream_req_headers: dict[str, str] = {}
    if range_header := request.headers.get("range"):
        upstream_req_headers["Range"] = range_header

    try:
        req = client.build_request("GET", url, headers=upstream_req_headers)
        upstream = await client.send(req, stream=True)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Download upstream timed out")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Download upstream unreachable: {exc}") from exc

    if not upstream.is_success and upstream.status_code != 206:
        await upstream.aclose()
        raise HTTPException(status_code=upstream.status_code, detail="Download upstream error")

    response_headers: dict[str, str] = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-store",
        "Accept-Ranges": "bytes",
    }
    # Bubble up Content-Length, Content-Range, etc. from the upstream response
    for header in ("content-length", "content-range", "content-type"):
        if val := upstream.headers.get(header):
            response_headers[header.title()] = val

    async def _stream():
        try:
            async for chunk in upstream.aiter_bytes(_cfg.download_chunk):
                yield chunk
        except Exception as exc:
            logger.error('"black_download_stream_error":{"err":"%s"}', exc)
        finally:
            await upstream.aclose()

    return StreamingResponse(
        _stream(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "video/mp4"),
        headers=response_headers,
    )


# ── /stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def black_stats() -> dict:
    """Cache usage, circuit-breaker state, and in-flight task counts."""
    total = _cache_hits + _cache_misses
    return {
        "server": "black",
        "cache": {
            "size": len(_black_cache),
            "maxsize": _black_cache.maxsize,
            "ttl_secs": _cfg.cache_ttl,
            "hits": _cache_hits,
            "misses": _cache_misses,
            "hit_rate": round(_cache_hits / total, 4) if total else 0.0,
        },
        "circuit_breaker": {
            "state": _circuit_breaker.state,
            "consecutive_failures": _circuit_breaker.failures,
            "threshold": _cfg.cb_threshold,
            "recovery_secs": _cfg.cb_recovery,
        },
        "inflight": {
            "extractions": len(_black_futures),
            "background_tasks": len(_background_tasks),
            "refreshing_keys": len(_black_refreshing),
        },
        "hosts": {
            "static": len(ALLOWED_BLACK_HOSTS),
            "dynamic": sorted(_dynamic_hosts),
        },
        "token_store_size": len(_url_tokens),
    }


# ── Background helpers ─────────────────────────────────────────────────────────

async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    ck = _cache_key(tmdb_id, media_type, season, episode)
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _black_cache[ck] = sources
            _black_timestamps[ck] = time.monotonic()
            _register_hosts(sources)
            logger.info('"black_prewarm_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"black_prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _bg_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        logger.info('"black_bg_refresh_start":{"key":"%s"}', ck)
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _black_cache[ck] = sources
            _black_timestamps[ck] = time.monotonic()
            _register_hosts(sources)
            logger.info('"black_bg_refresh_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"black_bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _black_refreshing.discard(ck)