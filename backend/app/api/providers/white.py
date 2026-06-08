"""FastAPI router for watchfy's White server (111movies.net).

Mounts at /api/white/*:
  GET /api/white/source            — extract HLS + MP4 via Playwright extractor
  GET /api/white/proxy/hls         — proxy + rewrite HLS manifests (always fresh)
  GET /api/white/proxy/seg/{tok}   — proxy individual HLS segments (cached + retry)
  GET /api/white/prewarm           — background cache warm-up (single title)
  GET /api/white/prewarm/popular   — warm-up for TMDB popular titles
  GET /api/white/download          — range-aware MP4 stream-proxy
  GET /api/white/stats             — source/segment cache + circuit-breaker telemetry
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
from curl_cffi.requests import AsyncSession as CurlSession
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.extractors.white import extract_sources_legacy

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
class _WhiteConfig:
    cache_ttl: int            = int(os.environ.get("ONETOONE_CACHE_TTL",          15 * 60))
    stale_ttl: int            = int(os.environ.get("ONETOONE_STALE_TTL",          30 * 60))
    source_timeout: float     = float(os.environ.get("WHITE_SOURCE_TIMEOUT",       90.0))
    # Real-time segment fetch concurrency (curl_cffi CDN client)
    seg_concurrency: int      = int(os.environ.get("WHITE_SEG_CONCURRENCY",        8))
    # Background prefetch concurrency — kept low so real-time fetches aren't starved
    prefetch_concurrency: int = int(os.environ.get("WHITE_PREFETCH_CONCURRENCY",   3))
    prefetch_timeout: float   = float(os.environ.get("WHITE_PREFETCH_TIMEOUT",     10.0))
    seg_cache_ttl: int        = int(os.environ.get("WHITE_SEG_CACHE_TTL",          300))
    cb_threshold: int         = int(os.environ.get("WHITE_CB_THRESHOLD",           5))
    cb_recovery: float        = float(os.environ.get("WHITE_CB_RECOVERY",          60.0))
    rate_limit_rpm: int       = int(os.environ.get("WHITE_RATE_LIMIT_RPM",         30))
    short_token_len: int      = 16
    download_chunk: int       = 65_536


_cfg = _WhiteConfig()

# ── Allowed hosts ──────────────────────────────────────────────────────────────

_EXTRA_HOSTS: frozenset[str] = frozenset(
    h.strip() for h in os.environ.get("WHITE_EXTRA_HOSTS", "").split(",") if h.strip()
)

ALLOWED_ONETOONE_HOSTS: frozenset[str] = frozenset(
    {
        "easy.speedsterwave.app",
        "cdn.vidking.net",
        "vidking.net",
        "www.vidking.net",
        "cloudnestra.com",
        "whisperingauroras.com",
        "111movies.net",
        "www.111movies.net",
        "cdn.111movies.net",
        "hello.mousedoor.com",
        "mousedoor.com",
    }
    | _EXTRA_HOSTS
)

_ONETOONE_SUFFIXES: tuple[str, ...] = (
    ".mousedoor.com",
    ".speedsterwave.app",
    ".vidking.net",
    ".cloudnestra.com",
    ".workers.dev",
)

_CDN_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "video/mp2t, application/vnd.apple.mpegurl, "
        "application/x-mpegURL, text/html, application/xhtml+xml, */*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://111movies.net/",
    "Origin": "https://111movies.net",
}

_cookies: dict[str, str] = {}


def _adapt_cookies_for_domain(cookies: dict[str, str], target_url: str) -> dict[str, str]:
    adapted = {}
    for name, value in cookies.items():
        adapted[name] = value
    return adapted


async def _ensure_browser_session():
    return _cookies


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
    """Three-state circuit breaker for the Playwright extractor."""

    __slots__ = ("_state", "_failures", "_last_failure_ts", "_threshold", "_recovery")

    def __init__(self, threshold: int, recovery: float) -> None:
        self._state = _CBState.CLOSED
        self._failures = 0
        self._last_failure_ts = 0.0
        self._threshold = threshold
        self._recovery = recovery

    @property
    def state(self) -> str:
        return self._state.name

    @property
    def failures(self) -> int:
        return self._failures

    def is_open(self) -> bool:
        if self._state is _CBState.OPEN:
            if time.monotonic() - self._last_failure_ts >= self._recovery:
                self._state = _CBState.HALF_OPEN
                logger.info('"white_circuit_half_open"')
                return False
            return True
        return False

    def record_success(self) -> None:
        if self._state is not _CBState.CLOSED:
            logger.info('"white_circuit_closed"')
        self._failures = 0
        self._state = _CBState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_ts = time.monotonic()
        if self._state is _CBState.HALF_OPEN or self._failures >= self._threshold:
            self._state = _CBState.OPEN
            logger.warning('"white_circuit_open":{"failures":%d}', self._failures)


_circuit_breaker = CircuitBreaker(_cfg.cb_threshold, _cfg.cb_recovery)

# ── Rate limiter ───────────────────────────────────────────────────────────────


class _SlidingWindowRL:
    """Per-key sliding-window rate limiter (asyncio-safe, in-process)."""

    def __init__(self, rpm: int) -> None:
        self._rpm = rpm
        # TTLCache auto-evicts cold IPs after 2 min of inactivity.
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

_cache: TTLCache[str, list[SourceEntry]] = TTLCache(maxsize=400, ttl=_cfg.cache_ttl)
_master_urls: dict[str, str] = {}
_timestamps: dict[str, float] = {}
_refreshing: set[str] = set()
_dynamic_onetoone_hosts: set[str] = set()

_futures: dict[str, asyncio.Future] = {}
_futures_lock = asyncio.Lock()

_url_tokens: TTLCache[str, str] = TTLCache(maxsize=2_000, ttl=86_400)

# Segment-only byte cache.  Manifests are deliberately excluded — they are
# always fetched fresh from the CDN so URI rewrites are always applied.
_seg_cache: TTLCache[str, tuple[bytes, str]] = TTLCache(maxsize=500, ttl=_cfg.seg_cache_ttl)

# Telemetry counters
_cache_hits = 0
_cache_misses = 0
_seg_cache_hits = 0
_seg_cache_misses = 0

# Concurrency controls — lazily initialised inside the event loop
_seg_semaphore: asyncio.Semaphore | None = None
_prefetch_semaphore: asyncio.Semaphore | None = None
_prewarm_semaphore: asyncio.Semaphore | None = None

# Shared clients
_client: httpx.AsyncClient | None = None
_cdn_client: CurlSession | None = None


# ── Semaphore factory ──────────────────────────────────────────────────────────

def _semaphores() -> tuple[asyncio.Semaphore, asyncio.Semaphore, asyncio.Semaphore]:
    """Lazily create per-event-loop semaphores on first call."""
    global _seg_semaphore, _prefetch_semaphore, _prewarm_semaphore
    if _seg_semaphore is None:
        _seg_semaphore      = asyncio.Semaphore(_cfg.seg_concurrency)
        _prefetch_semaphore = asyncio.Semaphore(_cfg.prefetch_concurrency)
        _prewarm_semaphore  = asyncio.Semaphore(2)
    return _seg_semaphore, _prefetch_semaphore, _prewarm_semaphore


# ── Lifecycle ──────────────────────────────────────────────────────────────────

async def shutdown_white_browser() -> None:
    from app.core.extractors.white import shutdown_browser
    await shutdown_browser()


async def shutdown_white_client() -> None:
    global _client, _cdn_client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
    if _cdn_client:
        await _cdn_client.close()
        _cdn_client = None
    logger.info('"white_client_shutdown"')


# ── HTTP clients ───────────────────────────────────────────────────────────────

async def _get_client() -> httpx.AsyncClient:
    """Plain httpx client for TMDB API calls and MP4 downloads."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=httpx.Timeout(connect=8.0, read=30.0, write=10.0, pool=5.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=15),
        )
    return _client


async def _get_cdn_client() -> CurlSession:
    """curl_cffi client — impersonates Chrome to bypass CDN bot-protection."""
    global _cdn_client
    if _cdn_client is None:
        _cdn_client = CurlSession(
            headers=_CDN_HEADERS,
            timeout=30,
            allow_redirects=True,
            impersonate="chrome131",
        )
    return _cdn_client


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cache_key(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    return f"white:{tmdb_id}:{media_type}:{season}:{episode}"


def _store_token(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[: _cfg.short_token_len]
    _url_tokens[token] = url
    return token


def _resolve_token(token: str) -> str | None:
    return _url_tokens.get(token)


def _register_onetoone_hosts(sources: list[SourceEntry]) -> None:
    for src in sources:
        u = src.get("url")
        if not u:
            continue
        try:
            h = urlparse(u).hostname
            if h and h not in ALLOWED_ONETOONE_HOSTS:
                _dynamic_onetoone_hosts.add(h)
                logger.info('"white_dynamic_host":{"host":"%s"}', h)
        except Exception:
            pass


def _validate_host(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    hostname = parsed.hostname or ""
    if (
        hostname in ALLOWED_ONETOONE_HOSTS
        or hostname in _dynamic_onetoone_hosts
        or any(hostname.endswith(s) for s in _ONETOONE_SUFFIXES)
    ):
        return
    raise HTTPException(status_code=403, detail=f"Host not allowed: {hostname}")


def _is_stale(ck: str) -> bool:
    ts = _timestamps.get(ck)
    return ts is None or (time.monotonic() - ts) > _cfg.cache_ttl


def _rewrite_hls_uri_attr(line: str, base_url: str) -> str:
    """Rewrite URI="..." in EXT-X-KEY / EXT-X-MAP lines to go through /proxy/seg."""
    def _replace(m: re.Match) -> str:
        uri = m.group(1)
        if not uri.startswith(("http://", "https://")):
            uri = urljoin(base_url, uri)
        return f'URI="/api/white/proxy/seg/{_store_token(uri)}"'
    return re.sub(r'URI="([^"]+)"', _replace, line)


# ── CDN fetch + segment prefetch ──────────────────────────────────────────────

async def _fetch_cdn(url: str) -> tuple[bytes, str]:
    """Fetch *url* via the CDN client with exponential-backoff retry.

    Acquires ``_seg_semaphore`` so real-time segment fetches are capped at
    ``WHITE_SEG_CONCURRENCY`` concurrent requests.

    Returns ``(content_bytes, content_type)``.
    Raises HTTPException on permanent 4xx errors or exhausted retries.
    """
    seg_sem, _, _ = _semaphores()
    client = await _get_cdn_client()
    last_exc: Exception | None = None

    async with seg_sem:
        for attempt in range(3):
            try:
                resp = await client.get(url)
                if resp.ok:
                    return resp.content, resp.headers.get("content-type", "video/MP2T")
                status = resp.status_code
                if status in (404, 410):
                    raise HTTPException(status_code=410, detail="Resource expired")
                if status < 500:
                    raise HTTPException(status_code=status, detail=f"Upstream error: {status}")
                logger.warning('"white_cdn_5xx":{"attempt":%d,"status":%d}', attempt + 1, status)
                last_exc = Exception(f"HTTP {status}")
            except HTTPException:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning('"white_cdn_error":{"attempt":%d,"err":"%s"}', attempt + 1, exc)
            if attempt < 2:
                await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5 s, 1 s

    raise HTTPException(status_code=502, detail=f"CDN unavailable after 3 attempts: {last_exc}")


async def _prefetch_segment(url: str) -> None:
    """Best-effort background prefetch of a single segment into _seg_cache."""
    if url in _seg_cache:
        return
    _, prefetch_sem, _ = _semaphores()
    async with prefetch_sem:
        if url in _seg_cache:  # re-check after acquiring semaphore
            return
        try:
            client = await _get_cdn_client()
            resp = await client.get(url)
            if resp.ok:
                _seg_cache[url] = (resp.content, resp.headers.get("content-type", "video/MP2T"))
        except Exception:
            pass  # best-effort; silently swallow all failures


async def _prefetch_segments(urls: list[str]) -> None:
    """Gather background prefetches with an overall timeout guard."""
    try:
        await asyncio.wait_for(
            asyncio.gather(*(_prefetch_segment(u) for u in urls), return_exceptions=True),
            timeout=_cfg.prefetch_timeout,
        )
    except asyncio.TimeoutError:
        pass


# ── Singleflight coalescer ─────────────────────────────────────────────────────

async def _extract_coalesced(
    ck: str,
    tmdb_id: int,
    media_type: str,
    season: int,
    episode: int,
) -> list[SourceEntry] | None:
    """Coalesce concurrent callers onto one extractor run per cache key.

    Callers that arrive while an extraction is already in flight piggyback on
    the existing Future, bypassing the circuit-breaker check.  Only fresh
    extraction attempts are blocked when the circuit is open.
    """
    async with _futures_lock:
        if ck in _futures:
            fut = _futures[ck]
        else:
            if _circuit_breaker.is_open():
                raise HTTPException(
                    status_code=503,
                    detail="Extractor circuit open — upstream may be degraded, retry shortly",
                    headers={"Retry-After": str(int(_cfg.cb_recovery))},
                )

            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            _futures[ck] = fut

            async def _run() -> None:
                try:
                    sources, master_url = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        cdn_headers=_CDN_HEADERS,
                    )
                    if master_url:
                        _master_urls[ck] = master_url
                    _circuit_breaker.record_success()
                    fut.set_result(sources)
                except Exception as exc:
                    _circuit_breaker.record_failure()
                    fut.set_exception(exc)
                finally:
                    async with _futures_lock:
                        _futures.pop(ck, None)

            _spawn(_run())

    return await asyncio.shield(fut)


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/white", tags=["white"])


# ── /source ────────────────────────────────────────────────────────────────────

@router.get("/source")
async def onetoone_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    """Extract HLS + MP4 sources from 111movies.net.

    - Cached hits are returned instantly with a background stale-revalidation.
    - Concurrent callers share one extractor run (singleflight).
    - ``master_url`` is included for clients that want the raw HLS playlist.
    """
    global _cache_hits, _cache_misses

    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    _check_rate_limit(request)

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if refresh:
        _cache.pop(ck, None)
        _timestamps.pop(ck, None)
    else:
        cached = _cache.get(ck)
        if cached is not None:
            _cache_hits += 1
            stale = _is_stale(ck)
            if stale and ck not in _refreshing:
                _refreshing.add(ck)
                _spawn(_bg_refresh(ck, tmdbId, mediaType, season, episode))
            return {
                "sources": cached,
                "cached": True,
                "stale": stale,
                "cache_age": round(time.monotonic() - (_timestamps.get(ck) or 0)),
                "server": "white",
                "master_url": _master_urls.get(ck, ""),
            }

    _cache_misses += 1

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=_cfg.source_timeout,
        )
    except asyncio.TimeoutError:
        fallback = _cache.get(ck)
        if fallback:
            return {
                "sources": fallback, "cached": True, "stale": True,
                "server": "white", "master_url": _master_urls.get(ck, ""),
            }
        raise HTTPException(status_code=504, detail="Source extraction timed out")
    except HTTPException:
        raise
    except Exception as exc:
        fallback = _cache.get(ck)
        if fallback:
            return {
                "sources": fallback, "cached": True, "stale": True,
                "server": "white", "master_url": _master_urls.get(ck, ""),
            }
        raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}") from exc

    if sources:
        _cache[ck] = sources
        _timestamps[ck] = time.monotonic()
        _register_onetoone_hosts(sources)

    return {
        "sources": sources or [],
        "cached": False,
        "stale": False,
        "server": "white",
        "master_url": _master_urls.get(ck, ""),
    }


# ── /proxy/hls ─────────────────────────────────────────────────────────────────

@router.get("/proxy/hls")
async def onetoone_proxy_hls(url: str = Query(...)) -> Response:
    """Proxy and rewrite a 111movies HLS manifest.

    Manifests are **always** fetched fresh from the CDN — they are never served
    from ``_seg_cache`` — so URI rewrites are applied on every request.

    Routing:
    - ``#EXT-X-STREAM-INF`` variant URIs  → ``/proxy/hls``  (playlist)
    - Segment URIs                          → ``/proxy/seg`` (binary)
    - ``#EXT-X-KEY`` / ``#EXT-X-MAP`` ``URI=`` attributes → ``/proxy/seg``
    - Relative URIs are resolved via ``urljoin`` before tokenising.

    After processing a media playlist, its segment URLs are pre-fetched in the
    background so the first several player requests hit ``_seg_cache``.
    """
    if len(url) == _cfg.short_token_len and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate_host(url)

    try:
        content, content_type = await _fetch_cdn(url)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Manifest fetch failed: {exc}") from exc

    text = content.decode("utf-8", errors="replace")

    if not text.startswith("#EXTM3U"):
        # Binary blob (e.g., encryption key landed here) — pass straight through
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"},
        )

    base_url = url.rsplit("/", 1)[0] + "/"
    lines: list[str] = []
    segment_urls: list[str] = []  # collected for background prefetch
    next_is_variant = False

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            lines.append(line)
            continue

        # Encryption key / init segment — rewrite URI= attribute in-place
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
            lines.append(f"/api/white/proxy/hls?url={token}")
            next_is_variant = False
        else:
            lines.append(f"/api/white/proxy/seg/{token}")
            segment_urls.append(uri)

    # Pre-warm segment cache in the background for media playlists
    if segment_urls:
        _spawn(_prefetch_segments(segment_urls))

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
async def onetoone_proxy_seg(token: str) -> Response:
    """Proxy a single 111movies HLS segment with in-memory caching."""
    global _seg_cache_hits, _seg_cache_misses

    url = _resolve_token(token)
    if not url:
        return Response(
            status_code=410,
            headers={"X-Segment-Expired": "true", "Retry-After": "0"},
        )

    _validate_host(url)

    cached = _seg_cache.get(url)
    if cached is not None:
        _seg_cache_hits += 1
        content, content_type = cached
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Length": str(len(content)),
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "X-Cache": "HIT",
            },
        )

    _seg_cache_misses += 1

    try:
        content, content_type = await _fetch_cdn(url)
    except HTTPException as exc:
        if exc.status_code == 410:
            return Response(status_code=410, headers={"X-Segment-Expired": "true"})
        raise

    _seg_cache[url] = (content, content_type)

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Length": str(len(content)),
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "X-Cache": "MISS",
        },
    )


# ── /download ──────────────────────────────────────────────────────────────────

@router.get("/download")
async def onetoone_download(
    request: Request,
    url: str = Query(...),
    filename: str = Query(default="watchfy-white.mp4"),
) -> StreamingResponse:
    """Range-aware stream-proxy for MP4 downloads from the 111movies CDN.

    Forwards the client's ``Range`` header upstream so browsers and download
    managers can seek and resume without re-downloading from the start.
    """
    _validate_host(url)
    client = await _get_client()

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
    for header in ("content-length", "content-range", "content-type"):
        if val := upstream.headers.get(header):
            response_headers[header.title()] = val

    async def _stream():
        try:
            async for chunk in upstream.aiter_bytes(_cfg.download_chunk):
                yield chunk
        except Exception as exc:
            logger.error('"white_download_stream_error":{"err":"%s"}', exc)
        finally:
            await upstream.aclose()

    return StreamingResponse(
        _stream(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "video/mp4"),
        headers=response_headers,
    )


# ── /prewarm ───────────────────────────────────────────────────────────────────

@router.get("/prewarm")
async def white_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Fire-and-forget cache warm-up for a single title."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _cache:
        if _is_stale(ck) and ck not in _refreshing:
            _refreshing.add(ck)
            _spawn(_bg_refresh(ck, tmdbId, mediaType, season, episode))
            return {"status": "cached_refreshing", "server": "white"}
        return {"status": "cached", "server": "white"}
    if ck not in _futures:
        _spawn(_warm_and_cache(tmdbId, mediaType, season, episode))
    return {"status": "warming", "server": "white"}


# ── /prewarm/popular ───────────────────────────────────────────────────────────

@router.get("/prewarm/popular")
async def white_prewarm_popular(
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Warm extraction cache for TMDB popular movies and TV shows."""
    api_key = os.environ.get("TMDB_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured")

    client = await _get_client()

    async def _fetch_popular(media_type: str) -> list[dict]:
        try:
            resp = await client.get(
                f"https://api.themoviedb.org/3/{media_type}/popular",
                params={"api_key": api_key, "language": "en-US", "page": 1},
            )
            if resp.is_success:
                return (resp.json().get("results") or [])[:limit]
        except Exception as exc:
            logger.warning('"white_prewarm_popular_tmdb_error":{"err":"%s"}', exc)
        return []

    movies, tv_shows = await asyncio.gather(_fetch_popular("movie"), _fetch_popular("tv"))

    count = 0
    for item in movies:
        if tmdb_id := item.get("id"):
            _spawn(_warm_and_cache(tmdb_id, "movie", 1, 1))
            count += 1
    for item in tv_shows:
        if tmdb_id := item.get("id"):
            _spawn(_warm_and_cache(tmdb_id, "tv", 1, 1))
            count += 1

    return {
        "status": "warming",
        "server": "white",
        "movies": len(movies),
        "tv_shows": len(tv_shows),
        "total": count,
    }


# ── /stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def white_stats() -> dict:
    """Source cache, segment cache, circuit-breaker state, and in-flight counts."""
    src_total = _cache_hits + _cache_misses
    seg_total = _seg_cache_hits + _seg_cache_misses
    return {
        "server": "white",
        "source_cache": {
            "size": len(_cache),
            "maxsize": _cache.maxsize,
            "ttl_secs": _cfg.cache_ttl,
            "hits": _cache_hits,
            "misses": _cache_misses,
            "hit_rate": round(_cache_hits / src_total, 4) if src_total else 0.0,
        },
        "segment_cache": {
            "size": len(_seg_cache),
            "maxsize": _seg_cache.maxsize,
            "ttl_secs": _cfg.seg_cache_ttl,
            "hits": _seg_cache_hits,
            "misses": _seg_cache_misses,
            "hit_rate": round(_seg_cache_hits / seg_total, 4) if seg_total else 0.0,
        },
        "circuit_breaker": {
            "state": _circuit_breaker.state,
            "consecutive_failures": _circuit_breaker.failures,
            "threshold": _cfg.cb_threshold,
            "recovery_secs": _cfg.cb_recovery,
        },
        "inflight": {
            "extractions": len(_futures),
            "background_tasks": len(_background_tasks),
            "refreshing_keys": len(_refreshing),
        },
        "hosts": {
            "static": len(ALLOWED_ONETOONE_HOSTS),
            "dynamic": sorted(_dynamic_onetoone_hosts),
        },
        "token_store_size": len(_url_tokens),
    }


# ── Background helpers ─────────────────────────────────────────────────────────

async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    _, _, prewarm_sem = _semaphores()
    ck = _cache_key(tmdb_id, media_type, season, episode)
    async with prewarm_sem:
        try:
            sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
            if sources:
                _cache[ck] = sources
                _timestamps[ck] = time.monotonic()
                _register_onetoone_hosts(sources)
                logger.info('"white_prewarm_done":{"key":"%s","count":%d}', ck, len(sources))
        except Exception as exc:
            logger.error('"white_prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _bg_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        logger.info('"white_bg_refresh_start":{"key":"%s"}', ck)
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _cache[ck] = sources
            _timestamps[ck] = time.monotonic()
            _register_onetoone_hosts(sources)
            logger.info('"white_bg_refresh_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"white_bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _refreshing.discard(ck)